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
SHOTS_TABLE_RE = re.compile(
    r'<div class="table-responsive"><table>\s*<tbody>(.*?)</tbody></table></div>', re.S)
SHOTS_ROW_RE = re.compile(r'<th>Shots</th>\s*<td>(\d+)</td>')


def fetch_bullet_shot_counts(href):
    """Category-page cells often can't say how many shots belong to each
    'Bullet N' group in a weapon's Damage column -- some categories collapse
    it to a single combined total (e.g. Heartsteel Claymore's Shots: 3, for
    bullet groups of 1 and 2 shots respectively). The item's own page has
    one small table per projectile definition, each starting with its own
    'Shots' row, in the same order the bullets are listed on the category
    page. Returns the ordered per-bullet shot counts, or [] if the page
    doesn't follow that layout (e.g. it also has a combined summary 'Shots'
    row mixed into the main info table, which throws the count off and
    means we bail out rather than guess)."""
    try:
        detail_html = fetch(BASE + href)
    except Exception as e:
        print(f"    ! bullet-shots fetch failed for {href}: {e}", file=sys.stderr)
        return []
    counts = []
    for tbl in SHOTS_TABLE_RE.findall(detail_html):
        m = SHOTS_ROW_RE.search(tbl)
        if m:
            counts.append(int(m.group(1)))
    return counts


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
        counts = fetch_bullet_shot_counts(it["href"])
        if len(counts) != len(bullet_ns):
            continue
        for n, count in zip(bullet_ns, counts):
            segs.append({"label": f"Bullet {n} Shots", "value": str(count)})
    return items


def scrape_category(slug, category):
    html_doc = fetch(BASE + "/wiki/" + slug)
    classes = extract_classes(html_doc)
    items = parse_item_tables(html_doc, category)
    items = enrich_multi_bullet_shots(items)
    for it in items:
        it["classes"] = classes
        it["category_slug"] = slug
    return items, classes


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

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_items, f, indent=2, ensure_ascii=False)
    print(f"\nSaved {len(all_items)} items to {out_path}", file=sys.stderr)
    for slug, n in per_category.items():
        print(f"  {slug}: {n}", file=sys.stderr)
    return all_items


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "data/equipment.json"
    run_all(out)
