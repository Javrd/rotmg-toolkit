#!/usr/bin/env python3
"""RealmEye dungeon potion-drop scraper (stdlib only, no bs4/pip available)."""
import re
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
    return dungeons


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


TABLE_RE = re.compile(r'<table[^>]*>(.*?)</table>', re.S)
THEAD_RE = re.compile(r'<thead>(.*?)</thead>', re.S)
TH_RE = re.compile(r'<th[^>]*>(.*?)</th>', re.S)
DROP_ITEM_RE = re.compile(
    r'<a href="(/wiki/[^"#]+)">([^<]+)</a>(<sup><abbr title="([^"]*)">([^<]*)</abbr></sup>)?')


def leader_column_index(table_html):
    m = THEAD_RE.search(table_html)
    header_html = m.group(1) if m else table_html
    headers = TH_RE.findall(header_html)
    for idx, h in enumerate(headers):
        if "leader" in TAG_RE.sub("", h).strip().lower():
            return idx
    return None


def extract_leaders_from_section(section_html):
    leaders, seen = [], set()
    for table_html in TABLE_RE.findall(section_html):
        idx = leader_column_index(table_html)
        if idx is None:
            continue
        body = THEAD_RE.sub("", table_html)
        for tr in TR_RE.findall(body):
            if "<th" in tr:
                continue
            cells = TD_RE.findall(tr)
            if idx >= len(cells):
                continue
            for href, name in extract_links(cells[idx]):
                if href not in seen:
                    seen.add(href)
                    leaders.append((href, name))
    return leaders


def get_quest_monster_groups():
    """Return (setpiece_leaders, encounter_leaders, icon_map) from /wiki/quest-monsters."""
    html = fetch(BASE + "/wiki/quest-monsters")
    icon_map = build_icon_map(html)
    i = html.find('id="setpiece"')
    j = html.find('id="event"')
    if i == -1 or j == -1:
        raise RuntimeError("quest-monsters page layout changed: couldn't find setpiece/event headings")
    setpiece_html = html[i:j]
    encounters_html = html[j:]
    return (extract_leaders_from_section(setpiece_html),
            extract_leaders_from_section(encounters_html),
            icon_map)


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


def scrape_quest_monster_group(leaders, icon_map):
    results = []
    for href, name in leaders:
        try:
            potions = get_enemy_potion_drops(href)
        except Exception as e:
            print(f"    ! {name} ({href}) failed: {e}", file=sys.stderr)
            continue
        if potions:
            results.append({"name": name, "href": href, "icon": icon_map.get(href),
                             "potions": potions})
    return results


def run_quest_monsters(out_path):
    setpiece_leaders, encounter_leaders, icon_map = get_quest_monster_groups()
    print(f"Setpiece Bosses: {len(setpiece_leaders)} leaders, "
          f"Encounters: {len(encounter_leaders)} leaders", file=sys.stderr)

    print("Scanning Setpiece Bosses...", file=sys.stderr)
    setpiece = scrape_quest_monster_group(setpiece_leaders, icon_map)
    print("Scanning Encounters...", file=sys.stderr)
    encounters = scrape_quest_monster_group(encounter_leaders, icon_map)

    data = {"setpiece": setpiece, "encounters": encounters}
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"\nSaved {len(setpiece)} setpiece + {len(encounters)} encounter "
          f"enemies with potions to {out_path}", file=sys.stderr)
    return data


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
    elif len(sys.argv) > 1 and sys.argv[1] == "quests":
        out = sys.argv[2] if len(sys.argv) > 2 else "data/quest_monster_potions.json"
        run_quest_monsters(out)
    else:
        r = scrape_dungeon("Woodland Labyrinth", "/wiki/woodland-labyrinth")
        print_result(r)
        print()
        print(json.dumps(r, indent=2, ensure_ascii=False))
