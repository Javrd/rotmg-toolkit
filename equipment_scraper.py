#!/usr/bin/env python3
"""Scrape RealmEye equipment category pages (weapons/abilities/armor) into
a flat item list for the equipment-comparison tool.

Each item's "classes" (who can equip it) is taken from the category page's
intro paragraph ("Swords are used by Warriors, Knights, and Paladins") and
applied to every item on that page. This is exact for all Tiered items and
almost all Untiered ones; a handful of Set-Tier items are actually
restricted to a single class within that family even though the page
covers several classes (see docs/decisions/0002-*.md) -- known v1 gap.

Rings (/wiki/rings) are deliberately NOT scraped: that single page mixes
at least 4 mutually-inconsistent table layouts (a 3-row "grid" of several
items per row for the basic T0-T7 stat rings, plus untiered/other rings
tables that split the name across two <td>s unlike every other category)
and would need bespoke parsing per layout -- see docs/decisions/0002-*.md.
"""
import re
import sys
import json
import html as htmlmod

from scraper import fetch, extract_links, build_icon_map, TAG_RE, TD_RE, TR_RE, BASE

CATEGORY_SLUGS = {
    "Weapon": ["daggers", "dual-blades", "bows", "longbows", "staves", "spellblades",
               "wands", "morning-stars", "swords", "flails", "katanas", "tachis"],
    "Ability": ["cloaks", "poisons", "prisms", "quivers", "traps", "stars", "sigils",
                "spells", "skulls", "orbs", "tomes", "scepters", "maces", "lutes",
                "helms", "shields", "seals", "wakizashi", "sheaths"],
    "Armor": ["leather-armors", "robes", "heavy-armors"],
}

STAT_HEADERS = ["ATT", "DEF", "SPD", "DEX", "VIT", "WIS", "HP", "MP"]

H4_OR_TABLE_RE = re.compile(
    r'<h4[^>]*>(.*?)</h4>|<table class="table table-striped">(.*?)</table>', re.S)
THEAD_RE = re.compile(r'<thead>(.*?)</thead>', re.S)
TH_RE = re.compile(r'<th[^>]*>(.*?)</th>', re.S)
IMG_ALT_RE = re.compile(r'<img[^>]*alt="([^"]*)"[^>]*>')
BR_RE = re.compile(r'<br\s*/?>')
NUM_RE = re.compile(r'([+-]?\d+)')


def clean_cell(cell_html):
    """HTML table cell -> (display text, [effect names from <img alt>])."""
    effects = [e for e in IMG_ALT_RE.findall(cell_html) if e]
    text = IMG_ALT_RE.sub(lambda m: f'[{m.group(1)}] ' if m.group(1) else '', cell_html)
    text = BR_RE.sub(' | ', text)
    text = re.sub(r'<sup>(.*?)</sup>', r'^\1', text)  # e.g. tiles/second<sup>2</sup> -> tiles/second^2
    text = TAG_RE.sub('', text)
    text = htmlmod.unescape(text)
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'(\s*\|\s*)+', ' | ', text).strip(' |').strip()
    return text, effects


BULLET_RE = re.compile(r'^(Bullet \d+):\s*(.*)$')
LABELED_RE = re.compile(r'^([A-Za-z][A-Za-z ]{2,30}):\s*(.+)$')
BRACKET_RE = re.compile(r'^\[([^\]]+)\]\s*(.*)$')


def split_segments(text, header):
    """A cell's cleaned text (pipe-joined <br>-separated bits, e.g. a weapon's
    'Damage (Average)' column mixing damage range, projectile speed, an
    embedded effect + its description, and rate of fire) into one
    {label, value} dict per bit, instead of one blob. Falls back to the
    column header as the label for the one unlabeled bit (usually the
    primary number, e.g. the damage range itself).

    Some multi-bullet weapons (e.g. Arcane Rapier) put the 'Bullet N:'
    marker and its value on separate <br>-separated bits ('Bullet 1:' then
    '115-170 (142.5)' as two bits, rather than one 'Bullet 1: 325-375
    (350)' bit like Heartsteel Claymore) -- pending_bullet_label carries
    that marker forward so the next unlabeled bit is still recorded under
    'Bullet N' instead of falling through to the column header."""
    out = []
    bullet_prefix = ''
    pending_bullet_label = None
    for part in (p.strip() for p in text.split('|')):
        if not part:
            continue
        m = BULLET_RE.match(part)
        if m:
            bullet_prefix = m.group(1) + ' '
            value = m.group(2).strip()
            if value:
                out.append({"label": m.group(1), "value": value})
                pending_bullet_label = None
            else:
                pending_bullet_label = m.group(1)
            continue
        m = LABELED_RE.match(part)
        if m:
            out.append({"label": bullet_prefix + m.group(1).strip(), "value": m.group(2).strip()})
            pending_bullet_label = None
            continue
        m = BRACKET_RE.match(part)
        if m:
            out.append({"label": m.group(1).strip(), "value": m.group(2).strip()})
            continue
        if pending_bullet_label:
            out.append({"label": pending_bullet_label, "value": part})
            pending_bullet_label = None
            continue
        out.append({"label": header, "value": part})
    return out


# RotMG's 19 playable classes. Category intro text phrases the "who can
# equip this" sentence inconsistently ("used by X", "worn by X", "give X
# the ability to...", "for Knights"...), so instead of anchoring on a
# specific phrase we scan the intro for links to any of these class pages.
CLASS_SLUGS = {
    "warrior", "knight", "paladin", "wizard", "priest", "necromancer",
    "mystic", "sorcerer", "bard", "summoner", "rogue", "archer", "assassin",
    "huntress", "trickster", "ninja", "druid", "samurai", "kensei",
}


def extract_classes(html_doc):
    i = html_doc.find('<div class="wiki-page"')
    if i == -1:
        i = 0
    segment = html_doc[i:i + 3000]
    classes, seen = [], set()
    for href, _name in extract_links(segment):
        slug = href.rstrip('/').rsplit('/', 1)[-1]
        if slug in CLASS_SLUGS and href not in seen:
            seen.add(href)
            classes.append(slug.replace('-', ' ').title())
    return classes


def parse_item_tables(html_doc, category):
    items = []
    family = None
    for m in H4_OR_TABLE_RE.finditer(html_doc):
        if m.group(1) is not None:
            family = TAG_RE.sub('', m.group(1)).strip()
            continue
        table_html = m.group(2)
        thead_m = THEAD_RE.search(table_html)
        if not thead_m:
            continue
        headers = [TAG_RE.sub('', h).strip() for h in TH_RE.findall(thead_m.group(1))]
        if 'Name' not in headers:
            continue  # banner table, or the grid-style rings table
        name_idx = headers.index('Name')
        tier_idx = headers.index('Tier') if 'Tier' in headers else None
        body = table_html[thead_m.end():]
        for tr in TR_RE.findall(body):
            if '<th' in tr:
                continue
            cells = TD_RE.findall(tr)
            if len(cells) < len(headers):
                continue
            name_links = extract_links(cells[name_idx])
            if not name_links:
                continue
            href, name = name_links[0]
            icon_map_row = build_icon_map(cells[0])
            icon = icon_map_row.get(href) or (next(iter(icon_map_row.values()), None))

            tier_raw, tier_effects = ('', [])
            soulbound = False
            if tier_idx is not None:
                tier_raw, tier_effects = clean_cell(cells[tier_idx])
                soulbound = 'Soulbound' in tier_effects
                if soulbound:
                    tier_raw = re.sub(r'\s*\|?\s*\[Soulbound\]\s*', '', tier_raw).strip(' |')

            columns, all_effects, stats = {}, set(tier_effects) - {'Soulbound'}, {}
            for i, h in enumerate(headers):
                if i in (0, name_idx, tier_idx):
                    continue
                if h == 'Projectile':
                    # sprite names, not gameplay effects -- keep as plain text
                    names = [n for n in IMG_ALT_RE.findall(cells[i]) if n]
                    if names:
                        columns[h] = [{"label": h, "value": ", ".join(dict.fromkeys(names))}]
                    continue
                text, effects = clean_cell(cells[i])
                if not text:
                    continue
                all_effects.update(e for e in effects if e and e != 'Soulbound')
                if h in STAT_HEADERS:
                    nm = NUM_RE.search(text)
                    if nm:
                        stats[h] = int(nm.group(1))
                columns[h] = split_segments(text, h)

            effect_descriptions = {}
            for segs in columns.values():
                for seg in segs:
                    if seg["label"] in all_effects and seg["value"]:
                        effect_descriptions[seg["label"]] = seg["value"]

            items.append({
                "name": name, "href": href, "icon": icon, "category": category,
                "family": family, "tier": tier_raw, "soulbound": soulbound,
                "stats": stats, "columns": columns, "effects": sorted(all_effects),
                "effect_descriptions": effect_descriptions,
            })
    return items


BULLET_LABEL_RE = re.compile(r'^Bullet (\d+)$')
PROJECTILE_TABLE_RE = re.compile(
    r'<div class="table-responsive"><table>\s*<tbody>(.*?)</tbody></table></div>', re.S)
PROJECTILE_ROW_RE = re.compile(r'<tr>\s*<th[^>]*>([^<]*)</th>\s*<td[^>]*>(.*?)</td>\s*</tr>', re.S)
DAMAGE_RANGE_AVERAGE_RE = re.compile(r'average:\s*')


def normalize_damage_range(text):
    """Item pages write damage ranges as '15–20 (average: 17.5)'; category
    pages (the usual data source) write the same thing as '15-20 (17.5)'.
    Normalize to the category-page shape so it parses the same way
    everywhere (readAvg() in build_html.py expects '(NUMBER)')."""
    text = DAMAGE_RANGE_AVERAGE_RE.sub('', text)
    return text.replace('–', '-').replace('‒', '-')


def fetch_projectile_groups(href):
    """A weapon's own item page has one small table per projectile
    definition (each starting with its own 'Shots' row) with the full
    per-shot detail -- Shots, Damage, Rate of Fire (if not implicitly
    100%), Projectile Speed, Range, and Effect(s) -- that many
    category-listing pages omit entirely for basic Tiered weapons (see
    docs/decisions/0005-thin-category-page-weapons.md). Returns an ordered
    list of {"Shots": ..., "Damage": ..., ..., "_effects": [...],
    "_effect_descriptions": {...}} dicts, or [] if the page has no such
    tables."""
    try:
        detail_html = fetch(BASE + href)
    except Exception as e:
        print(f"    ! projectile-detail fetch failed for {href}: {e}", file=sys.stderr)
        return []
    groups = []
    for tbl in PROJECTILE_TABLE_RE.findall(detail_html):
        rows, effects, effect_descriptions = {}, [], {}
        for label_html, value_html in PROJECTILE_ROW_RE.findall(tbl):
            label = TAG_RE.sub('', label_html).strip()
            if not label:
                continue
            text, seg_effects = clean_cell(value_html)
            if label == 'Effect(s)':
                effects = [e for e in seg_effects if e]
                for seg in split_segments(text, label):
                    if seg["label"] in effects and seg["value"]:
                        effect_descriptions[seg["label"]] = seg["value"]
                continue
            rows[label] = text
        if 'Shots' in rows:
            rows['_effects'] = effects
            rows['_effect_descriptions'] = effect_descriptions
            groups.append(rows)
    return groups


def enrich_multi_bullet_shots(items):
    """For weapons with 2+ simultaneous/alternate 'Bullet N' damage groups,
    add a 'Bullet N Shots' segment per group (sourced from the item's own
    page) so the DPS calculator in build_html.py can weight each group by
    its own shot count instead of assuming 1 -- see
    docs/decisions/0003-multi-bullet-dps.md."""
    for it in items:
        if it["category"] != "Weapon":
            continue
        key = "Damage (Average)" if "Damage (Average)" in it["columns"] else (
            "Damage" if "Damage" in it["columns"] else None)
        if not key:
            continue
        segs = it["columns"][key]
        bullet_ns = sorted({
            int(m.group(1)) for m in (BULLET_LABEL_RE.match(s["label"]) for s in segs) if m
        })
        if len(bullet_ns) < 2 or any(s["label"].endswith("Shots") for s in segs):
            continue
        groups = fetch_projectile_groups(it["href"])
        if len(groups) != len(bullet_ns):
            continue
        for n, g in zip(bullet_ns, groups):
            shots = g.get("Shots", "1")
            segs.append({"label": f"Bullet {n} Shots", "value": shots})
    return items


def enrich_thin_weapons(items):
    """Basic Tiered weapons (T0-T13, across every weapon line) often have
    a category-listing row that only shows a bare damage range -- no
    Shots, no Rate of Fire, no effects at all (e.g. Shortbow: 'Main:
    15-20 (17.5)' / 'Side (2): 5-10 (7.5)', nothing else). That page is
    the sole data source for ~170 weapons, so without this the DPS
    calculator silently assumes 1 shot at 100% RoF and effects like
    Piercing never show up in Equipment Compare. This rebuilds Damage
    (Average)/Shots/effects from the item's own page instead, using the
    same 'Bullet N' shape the multi-bullet DPS logic already understands
    when there's more than one projectile definition (Main/Side become
    Bullet 1/Bullet 2 by position -- their own labels don't matter, only
    matching them up with the multi-bullet DPS reader does). See
    docs/decisions/0005-thin-category-page-weapons.md."""
    for it in items:
        if it["category"] != "Weapon":
            continue
        if "Shots" in it["columns"] or "Fire Rate" in it["columns"]:
            continue
        key = "Damage (Average)" if "Damage (Average)" in it["columns"] else (
            "Damage" if "Damage" in it["columns"] else None)
        if key:
            bullet_ns = {m for s in it["columns"][key] for m in [BULLET_LABEL_RE.match(s["label"])] if m}
            if bullet_ns:
                continue  # already has its own per-bullet Shots via enrich_multi_bullet_shots
        groups = fetch_projectile_groups(it["href"])
        if not groups:
            continue

        def build_segs(prefix, g):
            segs = []
            dmg = g.get("Damage")
            if not dmg:
                return None
            segs.append({"label": prefix or "Damage (Average)", "value": normalize_damage_range(dmg)})
            if prefix:
                # unprefixed single-group Shots/Range are set as their own
                # top-level columns below instead, to match how every other
                # weapon stores them (avoids duplicate "Shots"/"Range" rows
                # in the UI when compared against a naturally-rich item --
                # see docs/decisions/0006-duplicate-range-rows.md)
                segs.append({"label": f"{prefix} Shots", "value": g.get("Shots", "1")})
            if "Rate of Fire" in g:
                segs.append({"label": f"{prefix} Rate of Fire" if prefix else "Rate of Fire",
                             "value": g["Rate of Fire"]})
            if "Projectile Speed" in g:
                segs.append({"label": f"{prefix} Projectile Speed" if prefix else "Projectile Speed",
                             "value": g["Projectile Speed"]})
            if prefix and "Range" in g:
                segs.append({"label": f"{prefix} Range", "value": g["Range"]})
            return segs

        if len(groups) == 1:
            new_segs = build_segs("", groups[0])
        else:
            new_segs = []
            for i, g in enumerate(groups, start=1):
                gs = build_segs(f"Bullet {i}", g)
                if gs:
                    new_segs.extend(gs)
        if not new_segs:
            continue

        all_effects = set(it["effects"])
        for g in groups:
            all_effects.update(g.get("_effects") or [])
            it["effect_descriptions"].update(g.get("_effect_descriptions") or {})
        it["effects"] = sorted(all_effects)

        it["columns"].pop("Damage", None)
        it["columns"]["Damage (Average)"] = new_segs
        if len(groups) == 1:
            it["columns"]["Shots"] = [{"label": "Shots", "value": groups[0].get("Shots", "1")}]
            if "Range" in groups[0]:
                it["columns"]["Range"] = [{"label": "Range", "value": groups[0]["Range"]}]
    return items


def scrape_category(slug, category):
    html_doc = fetch(BASE + "/wiki/" + slug)
    classes = extract_classes(html_doc)
    items = parse_item_tables(html_doc, category)
    items = enrich_multi_bullet_shots(items)
    items = enrich_thin_weapons(items)
    for it in items:
        it["classes"] = classes
        it["category_slug"] = slug
    return items, classes


BULLET_PREFIX_RE = re.compile(r'^Bullet \d+(\s|$)')


def normalize_collision_labels(all_items):
    """Some category pages expose a field as its own dedicated <th> column
    (e.g. most Wands have a 'Range' column, some Ability lines have a
    'Shots' or 'Life Steal' column), while others fold the same field
    into a labeled bit inside the Damage cell instead (e.g. Fire Wand's
    'Range' segment, Mace of the Celestial Forest's 'Shots: 3-6' bit).
    Comparing one of each in Equipment Compare produced two separate rows
    for what's conceptually the same field -- see
    docs/decisions/0006-duplicate-range-rows.md. This finds any label
    used both ways anywhere in the dataset and hoists every embedded
    (non-'Bullet N'-prefixed) occurrence to a top-level column, matching
    whichever representation is already more common."""
    top_keys, embedded_labels = set(), set()
    for it in all_items:
        top_keys.update(k for k in it["columns"] if k not in ("Damage (Average)", "Damage"))
        key = "Damage (Average)" if "Damage (Average)" in it["columns"] else (
            "Damage" if "Damage" in it["columns"] else None)
        if not key:
            continue
        embedded_labels.update(
            s["label"] for s in it["columns"][key]
            if s["label"] not in ("Damage (Average)", "Damage") and not BULLET_PREFIX_RE.match(s["label"])
        )
    collision_labels = top_keys & embedded_labels
    if not collision_labels:
        return all_items
    print(f"  normalizing duplicate-row labels: {sorted(collision_labels)}", file=sys.stderr)
    for it in all_items:
        key = "Damage (Average)" if "Damage (Average)" in it["columns"] else (
            "Damage" if "Damage" in it["columns"] else None)
        if not key:
            continue
        keep, hoist = [], []
        for s in it["columns"][key]:
            (hoist if s["label"] in collision_labels and not BULLET_PREFIX_RE.match(s["label"]) else keep).append(s)
        if not hoist:
            continue
        it["columns"][key] = keep
        for s in hoist:
            it["columns"].setdefault(s["label"], []).append(s)
    return all_items


def run_all(out_path):
    all_items = []
    per_category = {}
    for category, slugs in CATEGORY_SLUGS.items():
        for slug in slugs:
            print(f"[{category}] {slug}", file=sys.stderr)
            try:
                items, classes = scrape_category(slug, category)
            except Exception as e:
                print(f"    ! failed: {e}", file=sys.stderr)
                continue
            print(f"    -> {len(items)} items, classes={classes}", file=sys.stderr)
            per_category[slug] = len(items)
            all_items.extend(items)

    all_items = normalize_collision_labels(all_items)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_items, f, indent=2, ensure_ascii=False)
    print(f"\nSaved {len(all_items)} items to {out_path}", file=sys.stderr)
    for slug, n in per_category.items():
        print(f"  {slug}: {n}", file=sys.stderr)
    return all_items


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "data/equipment.json"
    run_all(out)
