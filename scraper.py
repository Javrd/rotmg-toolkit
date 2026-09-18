#!/usr/bin/env python3
"""RealmEye dungeon potion-drop scraper (stdlib only, no bs4/pip available)."""
import re
import html as htmlmod
import os
import sys
import json
import time
import urllib.request
import urllib.error

BASE = "https://www.realmeye.com"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

HEADING_RE = re.compile(r'<h([23])(?:\s+id="([^"]*)")?>([^<]*)</h\1>')
TD_RE = re.compile(r'<td[^>]*>(.*?)</td>', re.S)
TR_RE = re.compile(r'<tr[^>]*>(.*?)</tr>', re.S)
LINK_RE = re.compile(r'<a href="(/wiki/[^"#]+)">(.*?)</a>', re.S)
ALT_RE = re.compile(r'alt="([^"]+)"')
TAG_RE = re.compile(r'<[^>]+>')
ICON_RE = re.compile(r'<a href="(/wiki/[^"#]+)"><img[^>]*src="([^"]+)"')
GREAT_RE = re.compile(r'(?i)\bgreat(?:er)?\b\s*')
POTION_OF_RE = re.compile(r'(?i)^potion of (.+)$')


def build_icon_map(html_fragment):
    """href -> absolute icon URL, first occurrence wins."""
    m = {}
    for href, src in ICON_RE.findall(html_fragment):
        if href not in m:
            m[href] = BASE + src if src.startswith("/") else src
    return m


SB_SUFFIX_RE = re.compile(r'(?i)\s*\(sb\)\s*$')


def potion_type(name):
    """Normalize a potion name to its stat/category, ignoring 'Greater'/'(SB)'."""
    stripped = GREAT_RE.sub("", name).strip()
    stripped = SB_SUFFIX_RE.sub("", stripped).strip()
    low = stripped.lower()
    if low == "health potion":
        return "Life"
    if low == "magic potion":
        return "Mana"
    m = POTION_OF_RE.match(stripped)
    if m:
        return m.group(1).title()
    return stripped


def cache_path(url):
    slug = re.sub(r'[^a-zA-Z0-9]+', '_', url)
    return os.path.join(CACHE_DIR, slug + ".html")


def fetch(url, force=False):
    path = cache_path(url)
    if not force and os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return f.read()
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = resp.read().decode("utf-8", errors="replace")
            if len(data) < 500:
                raise ValueError("suspiciously short response (%d bytes)" % len(data))
            with open(path, "w", encoding="utf-8") as f:
                f.write(data)
            time.sleep(0.35)
            return data
        except (urllib.error.URLError, ValueError, TimeoutError) as e:
            wait = 1.5 * (attempt + 1)
            print(f"  ! fetch failed ({e}), retrying in {wait}s...", file=sys.stderr)
            time.sleep(wait)
    raise RuntimeError(f"Could not fetch {url}")


def split_sections(html):
    """Return list of (level, id, title, content) for top-level h2/h3 headings."""
    matches = list(HEADING_RE.finditer(html))
    sections = []
    for i, m in enumerate(matches):
        level, hid, title = m.group(1), m.group(2), m.group(3).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(html)
        sections.append((level, hid, title, html[start:end]))
    return sections


def extract_links(cell_html):
    """Return [(href, name), ...] for every /wiki/... link in a table cell,
    whether the name comes from an <img alt="..."> or plain link text."""
    out = []
    for href, inner in LINK_RE.findall(cell_html):
        m = ALT_RE.search(inner)
        name = m.group(1) if m else TAG_RE.sub("", inner).strip()
        if name:
            out.append((href, name))
    return out


DUNGEON_LIST_LINK_RE = re.compile(
    r'<a href="(/wiki/[a-z0-9-]+)">([^<]+)</a><a id="[^"]*"></a>')


def get_dungeon_list():
    html = fetch(BASE + "/wiki/dungeons")
    icon_map = build_icon_map(html)
    sections = split_sections(html)
    seen = set()
    dungeons = []
    for level, hid, title, content in sections:
        if title.strip().lower() == "history":
            continue
        for href, name in DUNGEON_LIST_LINK_RE.findall(content):
            if href in seen:
                continue
            seen.add(href)
            dungeons.append({"name": name, "href": href, "category": title.strip(),
                              "icon": icon_map.get(href)})
    for d in dungeons:
        if not d["icon"]:
            d["icon"] = get_portal_icon(d["href"])
    return dungeons


PORTAL_IMG_RE = re.compile(r'<img[^>]*\btitle="[^"]*\bPortal"[^>]*>')
IMG_SRC_RE = re.compile(r'src="([^"]+)"')


def get_portal_icon(href):
    """Icon for a dungeon that /wiki/dungeons lists without one (Oryx's Castle
    is entered from the realm, so it has no portal thumbnail in that table).

    Its own page always shows the portal as `<img ... title="X Portal">`, which
    is the one image on the page guaranteed to be the portal and not a boss,
    a layout map or a screenshot. Used only as a fallback: where the list does
    have an icon that one wins, because a few pages show a different (often
    animated .gif) variant and the list is what the rest of the site already
    displays."""
    try:
        html = fetch(BASE + href)
    except Exception:
        return None
    m = PORTAL_IMG_RE.search(html)
    if not m:
        return None
    src = IMG_SRC_RE.search(m.group(0))
    if not src:
        return None
    url = src.group(1)
    return BASE + url if url.startswith("/") else url


def parse_dungeon_page(html):
    sections = split_sections(html)

    boss_hrefs = set()
    treasure_hrefs = set()
    drops_content = None

    for level, hid, title, content in sections:
        tl = title.lower()
        if tl == "drops of interest":
            drops_content = content
        elif "treasure room" in tl and "boss" in tl:
            for href, name in extract_links(content):
                treasure_hrefs.add(href)
        elif "boss" in tl:
            for href, name in extract_links(content):
                boss_hrefs.add(href)

    if drops_content is None:
        return None, boss_hrefs, treasure_hrefs

    rows = []
    for tr in TR_RE.findall(drops_content):
        if "<th" in tr:
            continue
        cells = TD_RE.findall(tr)
        if len(cells) < 2:
            continue
        item_cell, source_cell = cells[0], cells[1]
        items = extract_links(item_cell)
        sources = extract_links(source_cell)
        rows.append((items, sources))

    return rows, boss_hrefs, treasure_hrefs


DROP_SUP_TMPL = r'<a href="{href}">([^<]+)</a>(<sup><abbr title="([^"]*)">([^<]*)</abbr></sup>)?'


def get_enemy_drop_status(enemy_href, item_href):
    """Return (guaranteed: bool|None, label: str|None)."""
    url = BASE + enemy_href
    html = fetch(url)
    sections = split_sections(html)
    drops_content = None
    for level, hid, title, content in sections:
        if title.strip().lower() == "drops":
            drops_content = content
            break
    if drops_content is None:
        return None, None
    pattern = re.compile(DROP_SUP_TMPL.format(href=re.escape(item_href)))
    m = pattern.search(drops_content)
    if not m:
        return None, None
    if m.group(2):
        return True, m.group(4)
    return False, None


EXCLUDED_POTIONS = {
    "health potion", "magic potion", "loot drop potion",
    "potion of max level", "loot tier potion",
}


def is_potion(name):
    low = name.lower()
    if "potion" not in low:
        return False
    stripped = GREAT_RE.sub("", name).strip().lower()
    if stripped in EXCLUDED_POTIONS:
        return False
    return True


DIFFICULTY_RE = re.compile(r'Difficulty:\s*([\d.]+)')
DIFFICULTY_FULL_ICON = BASE + "/s/a/img/wiki/i/gKMdCOG.png"
DIFFICULTY_HALF_ICON = BASE + "/s/a/img/wiki/i/4tJF9j9.png"


def get_difficulty(html):
    m = DIFFICULTY_RE.search(html)
    return float(m.group(1)) if m else None


def scrape_dungeon(name, href):
    url = BASE + href
    html = fetch(url)
    rows, boss_hrefs, treasure_hrefs = parse_dungeon_page(html)
    icon_map = build_icon_map(html)

    result = {
        "name": name, "href": href, "icon": icon_map.get(href),
        "difficulty": get_difficulty(html),
        "main": {"garantizados": [], "extra": []},
        "treasure": {"garantizados": [], "extra": []},
        "error": None,
    }

    if rows is None:
        result["error"] = "No 'Drops of Interest' section found"
        return result

    seen_main = {"garantizados": set(), "extra": set()}
    seen_treasure = {"garantizados": set(), "extra": set()}

    for items, sources in rows:
        source_map = dict(sources)
        source_hrefs = set(source_map)
        boss_matches = source_hrefs & boss_hrefs
        treasure_matches = source_hrefs & treasure_hrefs

        for item_href, item_name in items:
            if not is_potion(item_name):
                continue
            item_icon = icon_map.get(item_href)
            ptype = potion_type(item_name)

            if boss_matches:
                for bh in sorted(boss_matches):
                    guaranteed, label = get_enemy_drop_status(bh, item_href)
                    bucket = "garantizados" if guaranteed else "extra"
                    if item_name not in seen_main[bucket]:
                        seen_main[bucket].add(item_name)
                        result["main"][bucket].append({
                            "name": item_name, "type": ptype, "icon": item_icon,
                            "guaranteed": bool(guaranteed), "label": label,
                            "source_name": source_map.get(bh, bh),
                            "source_href": bh, "source_icon": icon_map.get(bh),
                        })

            if treasure_matches:
                for th in sorted(treasure_matches):
                    guaranteed, label = get_enemy_drop_status(th, item_href)
                    bucket = "garantizados" if guaranteed else "extra"
                    if item_name not in seen_treasure[bucket]:
                        seen_treasure[bucket].add(item_name)
                        result["treasure"][bucket].append({
                            "name": item_name, "type": ptype, "icon": item_icon,
                            "guaranteed": bool(guaranteed), "label": label,
                            "source_name": source_map.get(th, th),
                            "source_href": th, "source_icon": icon_map.get(th),
                        })

            if not boss_matches and not treasure_matches:
                if item_name not in seen_main["extra"]:
                    seen_main["extra"].add(item_name)
                    first_href, first_name = sources[0] if sources else (None, "Enemigos variables")
                    extra_n = len(sources) - 1
                    src_name = first_name + (f" +{extra_n}" if extra_n > 0 else "")
                    result["main"]["extra"].append({
                        "name": item_name, "type": ptype, "icon": item_icon,
                        "guaranteed": False, "label": None, "source_name": src_name,
                        "source_href": first_href,
                        "source_icon": icon_map.get(first_href) if first_href else None,
                    })

    return result


def _fmt_entry(e):
    return e["name"] + (f" ({e['label']})" if e.get("label") else "")


def print_result(result):
    print(f"\n=== {result['name']} ===")
    if result["error"]:
        print(f"  (sin datos: {result['error']})")
        return
    if result["main"]["garantizados"]:
        print("Garantizados:")
        for x in result["main"]["garantizados"]:
            print(f"  {_fmt_entry(x)}  [{x['source_name']}]")
    if result["main"]["extra"]:
        print("Extra:")
        for x in result["main"]["extra"]:
            print(f"  {_fmt_entry(x)}  [{x['source_name']}]")
    if result["treasure"]["garantizados"] or result["treasure"]["extra"]:
        print("Treasure Room:")
        if result["treasure"]["garantizados"]:
            print("  Garantizados:")
            for x in result["treasure"]["garantizados"]:
                print(f"    {_fmt_entry(x)}  [{x['source_name']}]")
        if result["treasure"]["extra"]:
            print("  Extra:")
            for x in result["treasure"]["extra"]:
                print(f"    {_fmt_entry(x)}  [{x['source_name']}]")


DROP_ITEM_RE = re.compile(
    r'<a href="(/wiki/[^"#]+)">([^<]+)</a>(<sup><abbr title="([^"]*)">([^<]*)</abbr></sup>)?')


def get_enemy_potion_drops(enemy_href):
    """All potions in enemy_href's own 'Drops' table: [{name, type, icon, guaranteed, label}]."""
    html = fetch(BASE + enemy_href)
    sections = split_sections(html)
    drops_content = None
    for level, hid, title, content in sections:
        if title.strip().lower() == "drops":
            drops_content = content
            break
    if drops_content is None:
        return []
    icon_map = build_icon_map(drops_content)
    out, seen = [], set()
    for href, name, sup, title_attr, label in DROP_ITEM_RE.findall(drops_content):
        if not is_potion(name) or name in seen:
            continue
        seen.add(name)
        out.append({"name": name, "type": potion_type(name), "icon": icon_map.get(href),
                     "guaranteed": bool(sup), "label": label if sup else None})
    return out


BIOME_TIER_HEADINGS = {
    "rookie biomes": "Rookie", "adept biomes": "Adept",
    "veteran biomes": "Veteran", "seasonal biomes": "Seasonal",
}
BIOME_ROW_RE = re.compile(
    r'<td><img[^>]*src="([^"]+)"[^>]*></td>\s*'
    r'<td[^>]*><img[^>]*src="[^"]+"[^>]*></td>\s*'
    r'<td.*?<a href="(/wiki/[^"#]+)">([^<]+)</a>', re.S)


def get_biome_list():
    """Return [{name, href, icon, tier}] from /wiki/the-realm, skipping unimplemented
    biomes like Low Desert (no link to their own page in the summary table)."""
    html = fetch(BASE + "/wiki/the-realm")
    sections = split_sections(html)
    biomes, seen = [], set()
    for level, hid, title, content in sections:
        tier = BIOME_TIER_HEADINGS.get(title.strip().lower())
        if not tier:
            continue
        for icon_src, href, name in BIOME_ROW_RE.findall(content):
            if href in seen:
                continue
            seen.add(href)
            biomes.append({"name": name, "href": href, "tier": tier,
                            "icon": BASE + icon_src if icon_src.startswith("/") else icon_src})
    return biomes


H2_RE = re.compile(r'<h2(?:\s+id="[^"]*")?>([^<]*)</h2>')
SUBHEAD_RE = re.compile(r'<h([34])(?:\s+id="[^"]*")?>([^<]*)</h\1>')


def get_biome_enemies_block(html):
    """Slice out the HTML between the 'Enemies'/'Monsters' h2 and the next h2."""
    matches = list(H2_RE.finditer(html))
    for i, m in enumerate(matches):
        if m.group(1).strip().lower() in ("enemies", "monsters"):
            start = m.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(html)
            return html[start:end]
    return None


def split_enemy_groups(block_html):
    """Split an Enemies/Monsters block into [(group_title, content), ...] by h3/h4
    subheadings (Regular Enemies, Heroes of Oryx, Heroes of Oryx Minions, Encounters,
    Beacon Guardian, NPCs...). Content preceding the first subheading (some biome
    pages list the base monster grid directly under the h2, no subheading) is
    labelled 'Regular Enemies'."""
    matches = list(SUBHEAD_RE.finditer(block_html))
    groups = []
    if not matches or matches[0].start() > 0:
        head = block_html[:matches[0].start()] if matches else block_html
        groups.append(("Regular Enemies", head))
    for i, m in enumerate(matches):
        title = m.group(2).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(block_html)
        groups.append((title, block_html[start:end]))
    return groups


def extract_biome_enemy_entries(group_html):
    """One (href, name) per <td> cell, taking only the first link (the enemy itself,
    not the dungeon-portal icon some cells append after a <br>)."""
    entries, seen = [], set()
    for td in TD_RE.findall(group_html):
        links = LINK_RE.findall(td)
        if not links:
            continue
        href, inner = links[0]
        m = ALT_RE.search(inner)
        name = m.group(1) if m else TAG_RE.sub("", inner).strip()
        if not name or href in seen:
            continue
        seen.add(href)
        entries.append((href, name))
    return entries


def scrape_biome(name, href, tier):
    url = BASE + href
    html = fetch(url)
    icon_map = build_icon_map(html)
    block = get_biome_enemies_block(html)
    groups = {}
    if block is not None:
        for group_title, group_html in split_enemy_groups(block):
            entries = extract_biome_enemy_entries(group_html)
            enemies = []
            for ehref, ename in entries:
                try:
                    potions = get_enemy_potion_drops(ehref)
                except Exception as e:
                    print(f"    ! {ename} ({ehref}) failed: {e}", file=sys.stderr)
                    continue
                if potions:
                    enemies.append({"name": ename, "href": ehref,
                                     "icon": icon_map.get(ehref), "potions": potions})
            if enemies:
                groups.setdefault(group_title, []).extend(enemies)
    return {"name": name, "href": href, "icon": icon_map.get(href) or None,
            "tier": tier, "groups": groups}


FAME_URL = BASE + "/wiki/fame-bonuses"
COLLECTION_HEADING = "<h4>Dungeon Collection</h4>"
COMPLETION_HEADING = '<h4 id="completion">'
BR_RE = re.compile(r'<br\s*/?>', re.I)
FAME_AMOUNT_RE = re.compile(r'\+([\d,]+)\s*Fame')
FAME_PERCENT_RE = re.compile(r'\+([\d.]+)%')

# The wiki's "Realm of the Mad God" row still lists the pre-rename "Ice Cave";
# every other row (and /wiki/dungeons) calls it "Ice Citadel", and /wiki/ice-cave
# is a dead page -- see docs/decisions/0009-fame-collection-dungeon-aliases.md.
DUNGEON_NAME_ALIASES = {
    "Ice Cave": "Ice Citadel",
}


def cell_text(cell_html):
    """Plain text of a table cell, with entities and stray whitespace tidied."""
    return htmlmod.unescape(TAG_RE.sub("", cell_html)).strip()


def scrape_fame_collections():
    """Parse the "Dungeon Collection" table of /wiki/fame-bonuses.

    One row per collection bonus (Tunnel Rat, Explosive Journey, ...). The
    "Threshold" cell packs the requirement, the set's label and the dungeon
    names into a single <br>-separated blob, e.g.
    "<b>Complete each 1 time:<br>Wild Shadow era dungeons:</b><br>Pirate Cave<br>...".
    The "Repeatable" column is dropped: it is False for every row of this table.
    """
    page = fetch(FAME_URL)
    start = page.find(COLLECTION_HEADING)
    end = page.find(COMPLETION_HEADING)
    if start < 0 or end < 0:
        raise RuntimeError("Dungeon Collection table not found on " + FAME_URL)
    block = page[start:end]

    dungeons = {d["name"]: d for d in get_dungeon_list()}
    collections = []
    for row in TR_RE.findall(block):
        cells = TD_RE.findall(row)
        if len(cells) < 3:
            continue  # header row (<th>)
        parts = [cell_text(p) for p in BR_RE.split(cells[1])]
        parts = [p for p in parts if p]
        requirement = parts[0].rstrip(":") if parts else ""
        subtitle = parts[1].rstrip(":") if len(parts) > 1 else ""
        entries = []
        seen = set()
        for raw in parts[2:]:
            name = DUNGEON_NAME_ALIASES.get(raw, raw)
            if name in seen:
                continue
            seen.add(name)
            known = dungeons.get(name, {})
            href = known.get("href")
            # Seasonal dungeons (Santa's Workshop, Rainbow Road, Beachzone)
            # have no "Difficulty" box on their page: they stay None.
            difficulty = get_difficulty(fetch(BASE + href)) if href else None
            entries.append({"name": name, "href": href,
                            "icon": known.get("icon"), "difficulty": difficulty})
        bonus = cell_text(cells[2])
        fame = FAME_AMOUNT_RE.search(bonus)
        percent = FAME_PERCENT_RE.search(bonus)
        collections.append({
            "name": cell_text(cells[0]),
            "requirement": requirement,
            "subtitle": subtitle,
            "bonus": bonus,
            "fame": int(fame.group(1).replace(",", "")) if fame else None,
            "percent": float(percent.group(1)) if percent else None,
            "dungeons": entries,
        })
    return collections


def run_fame(out_path):
    collections = scrape_fame_collections()
    unknown = sorted({d["name"] for c in collections for d in c["dungeons"]
                      if not d["href"]})
    for c in collections:
        print(f"{c['name']}: {len(c['dungeons'])} dungeons, {c['bonus']}",
              file=sys.stderr)
    if unknown:
        print(f"\nNot found in /wiki/dungeons (no icon/link): {', '.join(unknown)}",
              file=sys.stderr)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(collections, f, indent=2, ensure_ascii=False)
    print(f"\nSaved {len(collections)} fame collections to {out_path}", file=sys.stderr)
    return collections


def run_biomes(out_path):
    biomes = get_biome_list()
    print(f"Biomes: {len(biomes)}", file=sys.stderr)
    results = []
    for i, b in enumerate(biomes, 1):
        print(f"[{i}/{len(biomes)}] {b['name']} ({b['href']})", file=sys.stderr)
        r = scrape_biome(b["name"], b["href"], b["tier"])
        r["icon"] = b.get("icon") or r.get("icon")
        n_enemies = sum(len(v) for v in r["groups"].values())
        print(f"    -> {n_enemies} enemies with potions across {len(r['groups'])} groups",
              file=sys.stderr)
        results.append(r)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nSaved {len(results)} biomes to {out_path}", file=sys.stderr)
    return results


def run_all(out_path):
    dungeons = get_dungeon_list()
    results = []
    total = len(dungeons)
    for i, d in enumerate(dungeons, 1):
        print(f"[{i}/{total}] {d['name']} ({d['href']})", file=sys.stderr)
        try:
            r = scrape_dungeon(d["name"], d["href"])
        except Exception as e:
            r = {"name": d["name"], "href": d["href"], "icon": None, "difficulty": None,
                 "main": {"garantizados": [], "extra": []},
                 "treasure": {"garantizados": [], "extra": []},
                 "error": f"scrape failed: {e}"}
        r["category"] = d["category"]
        r["icon"] = d.get("icon") or r.get("icon")
        results.append(r)
        if r["error"]:
            print(f"    -> {r['error']}", file=sys.stderr)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nSaved {len(results)} dungeons to {out_path}", file=sys.stderr)
    return results


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "all":
        out = sys.argv[2] if len(sys.argv) > 2 else "data/dungeon_potions.json"
        run_all(out)
    elif len(sys.argv) > 1 and sys.argv[1] == "biomes":
        out = sys.argv[2] if len(sys.argv) > 2 else "data/biome_potions.json"
        run_biomes(out)
    elif len(sys.argv) > 1 and sys.argv[1] == "fame":
        out = sys.argv[2] if len(sys.argv) > 2 else "data/fame_bonuses.json"
        run_fame(out)
    else:
        r = scrape_dungeon("Woodland Labyrinth", "/wiki/woodland-labyrinth")
        print_result(r)
        print()
        print(json.dumps(r, indent=2, ensure_ascii=False))
