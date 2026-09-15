#!/usr/bin/env python3
import json
import sys
import html as htmlmod

from scraper import DIFFICULTY_FULL_ICON, DIFFICULTY_HALF_ICON

CATEGORY_ORDER = [
    "Realm Dungeons", "Realm Event Dungeons", "Advanced Dungeons",
    "Oryx's Castle", "Oryx’s Castle", "Wormholes", "Heroic Dungeons",
    "Special Event Dungeons", "Other Dungeons",
]

FALLBACK_ICON = ("data:image/svg+xml;utf8,"
                  "<svg xmlns='http://www.w3.org/2000/svg' width='32' height='32'>"
                  "<rect width='32' height='32' rx='6' fill='%23888'/></svg>")


def esc(s):
    return htmlmod.escape(s, quote=True)


def img(src, alt, cls):
    src = src or FALLBACK_ICON
    return f'<img class="{cls}" src="{esc(src)}" alt="{esc(alt)}" loading="lazy">'


def render_pill(p):
    """p: dict with name, type, icon, label(optional), source_name/href/icon(optional)."""
    cls = "pill g" if p.get("guaranteed") else "pill e"
    label = f' <span class="pill-label">{esc(p["label"])}</span>' if p.get("label") else ""
    src_bit = ""
    if p.get("source_name"):
        src_icon = img(p.get("source_icon"), p["source_name"], "src-icon") if p.get("source_icon") else ""
        src_bit = f'<span class="pill-src">{src_icon}{esc(p["source_name"])}</span>'
    return (f'<span class="{cls}" data-type="{esc(p.get("type", p["name"]))}">'
            f'{img(p.get("icon"), p["name"], "pill-icon")}'
            f'<span class="pill-body"><span class="pill-name">{esc(p["name"])}</span>{label}{src_bit}</span>'
            f'</span>')


def render_rows(g, e):
    out = []
    if g:
        out.append('<div class="row g"><span class="label g">Guaranteed</span>'
                    '<span class="pills">' + "".join(render_pill(p) for p in g) + '</span></div>')
    if e:
        out.append('<div class="row e"><span class="label e">Possible</span>'
                    '<span class="pills">' + "".join(render_pill(p) for p in e) + '</span></div>')
    return out


def render_difficulty(value):
    if value is None:
        return ""
    full = int(value)
    half = (value - full) >= 0.5
    icons = (f'<img class="skull" src="{esc(DIFFICULTY_FULL_ICON)}" alt="">' * full)
    if half:
        icons += f'<img class="skull" src="{esc(DIFFICULTY_HALF_ICON)}" alt="">'
    label = f'{value:g}/10'
    return f'<span class="difficulty" title="Difficulty: {esc(label)}">{icons}</span>'


def render_card(name, href, icon, blocks, difficulty=None, error=None, search_name=None,
                 icon_class="card-icon", badge=None):
    """blocks: list of (title_or_None, guaranteed_list, possible_list).
    Returns None if the card has no potions and no error (should be omitted).
    search_name overrides what data-name search matches against (e.g. a biome
    monster card also matches its biome's name, not just the monster's own name).
    badge: optional small tag next to the name (e.g. an enemy's biome group)."""
    has_potions = any(g or e for _, g, e in blocks)
    if not error and not has_potions:
        return None
    classes = "card no-data" if error else "card"
    badge_html = f'<span class="badge">{esc(badge)}</span>' if badge else ""
    out = [f'<article class="{classes}" data-name="{esc((search_name or name).lower())}">']
    out.append(
        f'<h3>{img(icon, name, icon_class)}'
        f'<a href="https://www.realmeye.com{esc(href)}" target="_blank" rel="noopener">{esc(name)}</a>'
        f'{badge_html}{render_difficulty(difficulty)}</h3>'
    )
    if error:
        out.append(f'<p class="note">No data ({esc(error)})</p>')
    else:
        for title, g, e in blocks:
            if not (g or e):
                continue
            if title:
                out.append(f'<div class="block treasure"><h4>{esc(title)}</h4>')
            else:
                out.append('<div class="block">')
            out.extend(render_rows(g, e))
            out.append('</div>')
    out.append('</article>')
    return "\n".join(out)


def render_category(title, card_htmls, icon=None):
    if not card_htmls:
        return ""
    title_html = (img(icon, title, "cat-icon") if icon else "") + esc(title)
    out = [f'<section class="cat" data-cat="{esc(title)}">',
           f'<h2 class="cat-title">{title_html}</h2>',
           '<div class="cards">']
    out.extend(card_htmls)
    out.append('</div></section>')
    return "\n".join(out)


def build_dungeon_sections(dungeons):
    by_cat = {}
    for d in dungeons:
        by_cat.setdefault(d.get("category", "Other"), []).append(d)

    ordered_cats = [c for c in CATEGORY_ORDER if c in by_cat]
    for c in by_cat:
        if c not in ordered_cats:
            ordered_cats.append(c)

    sections = []
    for cat in ordered_cats:
        cards = []
        for d in by_cat[cat]:
            blocks = [
                (None, d["main"]["garantizados"], d["main"]["extra"]),
                ("Treasure Room", d["treasure"]["garantizados"], d["treasure"]["extra"]),
            ]
            card = render_card(d["name"], d["href"], d.get("icon"), blocks,
                                difficulty=d.get("difficulty"), error=d.get("error"))
            if card:
                cards.append(card)
        sections.append(render_category(cat, cards))
    return "\n".join(s for s in sections if s)


BIOME_TIER_ORDER = ["Rookie", "Adept", "Veteran", "Seasonal"]
BIOME_GROUP_ORDER = ["Regular Enemies", "Heroes of Oryx", "Heroes of Oryx Minions",
                     "Encounters", "Beacon Guardian"]
BIOME_GROUP_BADGE = {
    "Regular Enemies": None,
    "Heroes of Oryx": "Hero of Oryx",
    "Heroes of Oryx Minions": "Hero Minion",
    "Encounters": "Encounter",
    "Beacon Guardian": "Beacon Guardian",
}


def render_biome_monster_card(enemy, group_title, biome_name):
    g_list = [p for p in enemy["potions"] if p["guaranteed"]]
    e_list = [p for p in enemy["potions"] if not p["guaranteed"]]
    return render_card(enemy["name"], enemy["href"], enemy.get("icon"),
                        [(None, g_list, e_list)],
                        search_name=f'{enemy["name"]} {biome_name}',
                        icon_class="card-icon card-icon-lg",
                        badge=BIOME_GROUP_BADGE.get(group_title, group_title))


def build_biome_sections(biomes):
    ordered_biomes = sorted(
        biomes,
        key=lambda b: (BIOME_TIER_ORDER.index(b["tier"]) if b.get("tier") in BIOME_TIER_ORDER
                        else len(BIOME_TIER_ORDER), b["name"]))

    sections = []
    for b in ordered_biomes:
        groups = b.get("groups", {})
        ordered_groups = [g for g in BIOME_GROUP_ORDER if g in groups]
        ordered_groups += [g for g in groups if g not in ordered_groups]

        cards = []
        for group_title in ordered_groups:
            for e in groups[group_title]:
                card = render_biome_monster_card(e, group_title, b["name"])
                if card:
                    cards.append(card)

        title = f'{b["name"]} ({b["tier"]})' if b.get("tier") else b["name"]
        sections.append(render_category(title, cards, icon=b.get("icon")))
    return "\n".join(s for s in sections if s)


def render_fame_item(entry):
    """One checkbox in a fame collection. data-dungeon is the sync key: the same
    dungeon checked in one collection is checked in every other one."""
    name = entry["name"]
    link = (f'<a href="https://www.realmeye.com{esc(entry["href"])}" target="_blank" '
            f'rel="noopener" class="fame-wiki" title="Open on RealmEye">wiki</a>'
            if entry.get("href") else "")
    return (f'<label class="fame-item" data-dungeon="{esc(name)}">'
            f'<input type="checkbox" class="fame-check">'
            f'{img(entry.get("icon"), name, "fame-icon")}'
            f'<span class="fame-name">{esc(name)}</span>{link}</label>')


def render_fame_collection(col):
    total = len(col["dungeons"])
    items = "".join(render_fame_item(e) for e in col["dungeons"])
    subtitle = f'<span class="fame-sub">{esc(col["subtitle"])}</span>' if col.get("subtitle") else ""
    return (f'<section class="fame-collection" data-collection="{esc(col["name"])}" data-total="{total}" data-fame="{col.get("fame") or 0}">'
            f'<div class="fame-head">'
            f'<h2 class="fame-title">{esc(col["name"])}{subtitle}</h2>'
            f'<span class="fame-bonus">{esc(col["bonus"])}</span>'
            f'<span class="fame-progress"><span class="fame-count">0/{total}</span>'
            f'<span class="fame-bar"><span class="fame-bar-fill"></span></span></span>'
            f'</div>'
            f'<div class="fame-items">{items}</div>'
            f'</section>')


def build_fame_sections(collections):
    return "\n".join(render_fame_collection(c) for c in collections)


def collect_types(dungeons, biomes):
    types = set()

    def scan(entries):
        for p in entries:
            types.add(p.get("type", p["name"]))

    for d in dungeons:
        scan(d["main"]["garantizados"]); scan(d["main"]["extra"])
        scan(d["treasure"]["garantizados"]); scan(d["treasure"]["extra"])
    if biomes:
        for b in biomes:
            for entries in b.get("groups", {}).values():
                for e in entries:
                    scan(e["potions"])
    return sorted(types)


def build(data_path, out_path, biome_path=None, equipment_path=None, fame_path=None):
    with open(data_path, encoding="utf-8") as f:
        dungeons = json.load(f)

    def has_potions(d):
        return bool(d["main"]["garantizados"] or d["main"]["extra"] or
                    d["treasure"]["garantizados"] or d["treasure"]["extra"])

    dungeon_html = build_dungeon_sections(dungeons)
    n_total = len(dungeons)
    n_shown = sum(1 for d in dungeons if not d.get("error") and has_potions(d))
    n_no_data = sum(1 for d in dungeons if d.get("error"))

    biome_html = ""
    n_biomes = n_biome_enemies = 0
    biomes = None
    if biome_path:
        try:
            with open(biome_path, encoding="utf-8") as f:
                biomes = json.load(f)
            n_biomes = sum(1 for b in biomes if any(b.get("groups", {}).values()))
            n_biome_enemies = sum(len(es) for b in biomes for es in b.get("groups", {}).values())
            biome_html = build_biome_sections(biomes)
        except FileNotFoundError:
            pass

    types = collect_types(dungeons, biomes)
    type_options = "".join(f'<option value="{esc(t)}">{esc(t)}</option>' for t in types)

    fame_html = ""
    n_collections = n_fame_dungeons = n_fame_total = 0
    if fame_path:
        try:
            with open(fame_path, encoding="utf-8") as f:
                collections = json.load(f)
            n_collections = len(collections)
            n_fame_dungeons = len({d["name"] for c in collections for d in c["dungeons"]})
            n_fame_total = sum(c.get("fame") or 0 for c in collections)
            fame_html = build_fame_sections(collections)
        except FileNotFoundError:
            pass

    n_equipment = 0
    if equipment_path:
        try:
            with open(equipment_path, encoding="utf-8") as f:
                n_equipment = len(json.load(f))
        except FileNotFoundError:
            pass

    page = TEMPLATE.replace("__DUNGEON_CARDS__", dungeon_html) \
                    .replace("__BIOME_CARDS__", biome_html) \
                    .replace("__TYPE_OPTIONS__", type_options) \
                    .replace("__N_SHOWN__", str(n_shown)) \
                    .replace("__N_NO_DATA__", str(n_no_data)) \
                    .replace("__N_BIOMES__", str(n_biomes)) \
                    .replace("__N_BIOME_ENEMIES__", str(n_biome_enemies)) \
                    .replace("__N_EQUIPMENT__", str(n_equipment)) \
                    .replace("__FAME_SECTIONS__", fame_html) \
                    .replace("__N_COLLECTIONS__", str(n_collections)) \
                    .replace("__N_FAME_DUNGEONS__", str(n_fame_dungeons)) \
                    .replace("__N_FAME_TOTAL__", f"{n_fame_total:,}") \
                    .replace("__FALLBACK_ICON_JSON__", json.dumps(FALLBACK_ICON))

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(page)
    print(f"Wrote {out_path} ({n_shown}/{n_total} dungeons with potions, {n_no_data} with no data, "
          f"{n_biomes} biomes with {n_biome_enemies} potion-dropping enemies, {len(types)} potion types, "
          f"{n_equipment} equipment items, {n_collections} fame collections)")


TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>RotMG Toolkit</title>
<style>
  :root {
    color-scheme: light dark;
    --bg: #f4f5f7; --card-bg: #fff; --text: #1a1c20; --muted: #6b7280;
    --border: #e2e4e9; --accent: #2563eb;
    --g-bg: #dcfce7; --g-text: #166534; --g-border: #86efac;
    --e-bg: #eef0f3; --e-text: #444b57; --e-border: #cfd3da;
    --bad-bg: #fee2e2; --bad-text: #991b1b; --bad-border: #fca5a5;
    --shadow: 0 1px 2px rgba(16,24,40,.04), 0 1px 3px rgba(16,24,40,.06);
  }
  @media (prefers-color-scheme: dark) {
    :root { --bg:#15171c; --card-bg:#1d2027; --text:#e8e9ec; --muted:#9aa0ab;
      --border:#2b2f38; --accent:#60a5fa;
      --g-bg:#123421; --g-text:#86efac; --g-border:#1f5a38;
      --e-bg:#252932; --e-text:#c3c8d1; --e-border:#3a3f4a;
      --bad-bg:#3a1616; --bad-text:#fca5a5; --bad-border:#5c2323;
      --shadow: 0 1px 2px rgba(0,0,0,.3), 0 1px 3px rgba(0,0,0,.4); }
  }
  * { box-sizing: border-box; }
  body { margin:0; padding:0 0 3rem; background:var(--bg); color:var(--text);
    font-family: -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
  header { position: sticky; top:0; z-index:10; background:var(--bg);
    padding: 1.25rem 1.5rem 1rem; border-bottom:1px solid var(--border); }
  h1 { margin:0 0 .6rem; font-size:1.4rem; display:flex; align-items:center; gap:.5rem; }
  h1 .emoji { filter: drop-shadow(0 1px 1px rgba(0,0,0,.15)); }
  .sub { color:var(--muted); font-size:.85rem; margin:0 0 .75rem; max-width: 900px; }
  .pagenav { display:flex; gap:.5rem; flex-wrap:wrap; }
  .pagetab { font-size:.9rem; padding:.5rem 1rem; border-radius:10px; border:1px solid var(--border);
    background:var(--card-bg); color:var(--text); cursor:pointer; font-weight:600; }
  .pagetab.active { background:var(--accent); border-color:var(--accent); color:#fff; }
  .page { display:none; }
  .page.active { display:block; }
  .controls { display:flex; gap:.5rem; flex-wrap:wrap; align-items:center; margin-top: 1rem; }
  #search, #typeFilter { padding:.55rem .8rem; border-radius:8px;
    border:1px solid var(--border); background:var(--card-bg); color:var(--text); font-size:.9rem; }
  #search { flex: 1 1 260px; min-width: 180px; }
  #typeFilter { flex: 0 0 auto; }
  .toggles { margin-top:.6rem; font-size:.85rem; color:var(--muted); display:flex; gap:1rem; flex-wrap:wrap; align-items:center; }
  .toggles label { cursor:pointer; display:flex; align-items:center; gap:.35rem; }
  .toggles label.pill-toggle { padding:.3rem .7rem; border-radius:999px; border:1px solid var(--g-border);
    background:var(--g-bg); color:var(--g-text); font-weight:600; }
  .tabs { display:flex; gap:.4rem; margin-top:.8rem; flex-wrap:wrap; }
  .tab { font-size:.82rem; padding:.35rem .8rem; border-radius:999px; border:1px solid var(--border);
    background:var(--card-bg); color:var(--text); cursor:pointer; }
  .tab.active { background:var(--accent); border-color:var(--accent); color:#fff; font-weight:600; }
  main { padding: 1rem 1.5rem; max-width: 1200px; margin: 0 auto; }
  .view { display:none; }
  .view.active { display:block; }
  .cat-title { font-size:1.05rem; margin: 1.6rem 0 .8rem; color:var(--muted);
    text-transform:uppercase; letter-spacing:.04em; font-weight:600; }
  .cards { display:grid; grid-template-columns: repeat(auto-fill, minmax(290px,1fr)); gap:.85rem; }
  .card { background:var(--card-bg); border:1px solid var(--border); border-radius:12px;
    padding:.9rem 1rem 1rem; box-shadow: var(--shadow); transition: transform .12s ease, box-shadow .12s ease; }
  .card:hover { transform: translateY(-1px); box-shadow: 0 4px 14px rgba(16,24,40,.1); }
  .card h3 { margin:0 0 .6rem; font-size:1rem; display:flex; align-items:center; gap:.5rem; flex-wrap:wrap; }
  .card h3 a { color:var(--text); text-decoration:none; margin-right:auto; }
  .card h3 a:hover { color:var(--accent); text-decoration:underline; }
  .card-icon { width:28px; height:28px; object-fit:contain; border-radius:6px;
    background: rgba(127,127,127,.12); flex-shrink:0; }
  .card-icon-lg { width:52px; height:52px; border-radius:8px; }
  .cat-icon { width:24px; height:24px; object-fit:contain; border-radius:5px;
    vertical-align:middle; margin-right:.4rem; background: rgba(127,127,127,.12); }
  .badge { font-size:.68rem; font-weight:700; text-transform:uppercase; letter-spacing:.03em;
    padding:.15rem .5rem; border-radius:999px; background: rgba(127,127,127,.15);
    color:var(--muted); flex-shrink:0; }
  .difficulty { display:inline-flex; align-items:center; gap:1px; flex-shrink:0; cursor:help; }
  .difficulty .skull { width:13px; height:13px; object-fit:contain; opacity:.85; }
  .note { color:var(--muted); font-size:.85rem; margin:.2rem 0 0; }
  .block { margin-top:.35rem; }
  .block.treasure { margin-top:.6rem; padding-top:.5rem; border-top:1px dashed var(--border); }
  .block.treasure h4 { margin:0 0 .35rem; font-size:.8rem; color:var(--muted); font-weight:600;
    text-transform:uppercase; letter-spacing:.03em; }
  .row { display:flex; gap:.5rem; align-items:flex-start; margin:.3rem 0; flex-wrap:wrap; }
  .label { font-size:.72rem; font-weight:700; text-transform:uppercase; letter-spacing:.03em;
    padding:.3rem 0; min-width:5.2rem; flex-shrink:0; }
  .label.g { color: var(--g-text); }
  .label.e { color: var(--muted); }
  .pills { display:flex; flex-wrap:wrap; gap:.35rem; }
  .pill { display:inline-flex; align-items:center; gap:.4rem; font-size:.78rem;
    padding:.2rem .55rem .2rem .3rem; border-radius:999px; border:1px solid; line-height:1.35; }
  .pill.g { background:var(--g-bg); color:var(--g-text); border-color:var(--g-border); font-weight:600; }
  .pill.e { background:var(--e-bg); color:var(--e-text); border-color:var(--e-border); }
  .pill-icon { width:20px; height:20px; object-fit:contain; flex-shrink:0; }
  .pill-body { display:flex; flex-direction:column; line-height:1.25; }
  .pill-label { font-size:.68rem; opacity:.8; font-weight:600; }
  .pill-src { font-size:.68rem; opacity:.75; display:flex; align-items:center; gap:.25rem; font-weight:400; }
  .src-icon { width:14px; height:14px; object-fit:contain; border-radius:3px; flex-shrink:0; }
  .card.no-data { opacity:.5; }
  .hidden { display:none !important; }
  .pill.hidden { display:none !important; }

  /* Equipment compare */
  .eq-stats { display:flex; gap:1.5rem; flex-wrap:wrap; margin-top:1rem; background:var(--card-bg);
    border:1px solid var(--border); border-radius:12px; padding:.8rem 1rem; box-shadow: var(--shadow); }
  .eq-stat-slider { flex:1 1 200px; min-width:180px; }
  .eq-stat-slider label { display:flex; justify-content:space-between; font-size:.78rem; font-weight:700;
    color:var(--muted); margin-bottom:.3rem; }
  .eq-stat-slider label span { color:var(--text); }
  .eq-stat-slider input[type=range] { width:100%; accent-color: var(--accent); }
  .eq-pickers { display:grid; grid-template-columns: 1fr auto 1fr; gap:1rem; align-items:start; margin-top:1rem; }
  .eq-vs { align-self:center; font-weight:700; color:var(--muted); font-size:.85rem; }
  .eq-picker { position:relative; background:var(--card-bg); border:1px solid var(--border);
    border-radius:12px; padding:.8rem; box-shadow: var(--shadow); min-width:0; }
  .eq-picker > label { display:block; font-size:.72rem; font-weight:700; text-transform:uppercase;
    letter-spacing:.03em; color:var(--muted); margin-bottom:.4rem; }
  .eq-search { width:100%; padding:.55rem .7rem; border-radius:8px; border:1px solid var(--border);
    background:var(--bg); color:var(--text); font-size:.9rem; }
  .eq-search:disabled { opacity:.5; cursor:not-allowed; }
  .eq-results { position:absolute; left:.8rem; right:.8rem; top:100%; margin-top:.3rem;
    background:var(--card-bg); border:1px solid var(--border); border-radius:10px;
    box-shadow: 0 8px 24px rgba(16,24,40,.15); max-height:340px; overflow-y:auto; z-index:20; display:none; }
  .eq-results.open { display:block; }
  .eq-result { display:flex; align-items:center; gap:.6rem; padding:.5rem .7rem; cursor:pointer; }
  .eq-result:hover { background: rgba(127,127,127,.12); }
  .eq-result img { width:26px; height:26px; object-fit:contain; flex-shrink:0; }
  .eq-result-body { flex:1; min-width:0; }
  .eq-result-name { font-size:.88rem; overflow-wrap:anywhere; }
  .eq-result-meta { font-size:.72rem; color:var(--muted); overflow-wrap:anywhere; }
  .eq-empty { padding:.7rem; font-size:.85rem; color:var(--muted); }
  .eq-selected { display:flex; align-items:center; gap:.6rem; }
  .eq-selected img { width:36px; height:36px; object-fit:contain; flex-shrink:0; }
  .eq-selected-body { flex:1; min-width:0; }
  .eq-selected-name { font-weight:600; font-size:.95rem; overflow-wrap:anywhere; }
  .eq-selected-meta { font-size:.75rem; color:var(--muted); overflow-wrap:anywhere; }
  .eq-selected-classes { font-size:.72rem; color:var(--accent); margin-top:.15rem; }
  .eq-change { font-size:.75rem; padding:.3rem .6rem; border-radius:8px; border:1px solid var(--border);
    background:var(--bg); color:var(--text); cursor:pointer; flex-shrink:0; }
  #eq-compare { margin-top:1.5rem; }
  .eq-cmp-header { display:grid; grid-template-columns: 1fr auto 1fr; gap:1rem; align-items:center;
    margin-bottom: .75rem; }
  .eq-cmp-side { display:flex; align-items:center; gap:.6rem; }
  .eq-cmp-side:last-child { flex-direction:row-reverse; text-align:right; }
  .eq-cmp-side img { width:40px; height:40px; object-fit:contain; }
  .eq-cmp-name a { color:var(--text); font-weight:700; text-decoration:none; }
  .eq-cmp-name a:hover { color:var(--accent); text-decoration:underline; }
  .eq-cmp-meta { font-size:.75rem; color:var(--muted); }
  .eq-cmp-vslabel { font-weight:700; color:var(--muted); font-size:.8rem; }
  .eq-section-title { font-size:.75rem; font-weight:700; text-transform:uppercase; letter-spacing:.03em;
    color:var(--muted); margin: 1.1rem 0 .4rem; }
  .eq-row { display:grid; grid-template-columns: 1fr auto 1fr; gap:.75rem; align-items:center;
    padding:.4rem .6rem; border-radius:8px; }
  .eq-row:nth-child(odd) { background: rgba(127,127,127,.06); }
  .eq-row.diff { background: rgba(96,165,250,.1); }
  .eq-label { text-align:center; font-size:.72rem; color:var(--muted); font-weight:600; }
  .eq-val { font-size:.88rem; font-variant-numeric: tabular-nums; text-align:center; }
  .eq-val.text { text-align:left; font-size:.82rem; }
  .eq-cmp-header + .eq-row .eq-val.text, .eq-row .eq-val.text:last-child { text-align:right; }
  .eq-val.better { color:var(--g-text); font-weight:700; }
  .eq-val.worse { color:var(--bad-text); }
  .eq-val.has { color:var(--g-text); font-weight:700; }
  .eq-val.no { color:var(--muted); opacity:.5; }
  .eq-row.eq-dps-row { background: rgba(96,165,250,.14); border-radius:10px; }
  .eq-row.eq-dps-row .eq-val { font-size:1.15rem; font-weight:800; }
  .eq-row.eq-dps-row .eq-label { font-weight:800; color:var(--text); }

  /* Fame checklist */
  .fame-toolbar { display:flex; gap:.75rem; flex-wrap:wrap; align-items:center; margin-top:1rem;
    background:var(--card-bg); border:1px solid var(--border); border-radius:12px;
    padding:.75rem 1rem; box-shadow: var(--shadow); }
  .fame-summary { font-size:.88rem; color:var(--muted); margin-right:auto; }
  .fame-summary b { color:var(--text); font-variant-numeric: tabular-nums; }
  .fame-btn { font-size:.82rem; padding:.45rem .9rem; border-radius:8px; border:1px solid var(--border);
    background:var(--bg); color:var(--text); cursor:pointer; font-weight:600; }
  .fame-btn:hover { border-color:var(--accent); color:var(--accent); }
  .fame-collection { background:var(--card-bg); border:1px solid var(--border); border-radius:12px;
    padding:.9rem 1rem 1rem; box-shadow: var(--shadow); margin-top:1rem; }
  .fame-collection.done { border-color:var(--g-border); background:var(--g-bg); }
  .fame-head { display:flex; align-items:baseline; gap:.75rem; flex-wrap:wrap;
    padding-bottom:.6rem; border-bottom:1px solid var(--border); margin-bottom:.7rem; }
  .fame-collection.done .fame-head { border-bottom-color:var(--g-border); }
  .fame-title { margin:0; font-size:1.05rem; display:flex; align-items:baseline;
    gap:.5rem; flex-wrap:wrap; }
  .fame-sub { font-size:.78rem; font-weight:400; color:var(--muted); text-transform:lowercase; }
  .fame-collection.done .fame-title, .fame-collection.done .fame-sub { color:var(--g-text); }
  .fame-bonus { font-size:.78rem; font-weight:700; padding:.2rem .6rem; border-radius:999px;
    border:1px solid var(--g-border); background:var(--g-bg); color:var(--g-text); white-space:nowrap; }
  .fame-collection.done .fame-bonus { background:var(--g-text); color:var(--g-bg); border-color:var(--g-text); }
  .fame-progress { margin-left:auto; display:flex; align-items:center; gap:.5rem; }
  .fame-count { font-size:.8rem; color:var(--muted); font-variant-numeric: tabular-nums; font-weight:600; }
  .fame-collection.done .fame-count { color:var(--g-text); }
  .fame-bar { width:70px; height:6px; border-radius:999px; background:rgba(127,127,127,.25);
    overflow:hidden; flex-shrink:0; }
  .fame-bar-fill { display:block; height:100%; width:0; border-radius:999px;
    background:var(--accent); transition: width .15s ease; }
  .fame-collection.done .fame-bar-fill { background:var(--g-text); }
  .fame-items { display:grid; grid-template-columns: repeat(auto-fill, minmax(230px,1fr)); gap:.3rem; }
  .fame-item { display:flex; align-items:center; gap:.5rem; padding:.35rem .5rem; border-radius:8px;
    cursor:pointer; min-width:0; }
  .fame-item:hover { background: rgba(127,127,127,.12); }
  .fame-item input { accent-color: var(--accent); width:16px; height:16px; flex-shrink:0; cursor:pointer; }
  .fame-icon { width:24px; height:24px; object-fit:contain; border-radius:5px; flex-shrink:0;
    background: rgba(127,127,127,.12); }
  .fame-name { font-size:.85rem; overflow-wrap:anywhere; }
  .fame-item.checked .fame-name { color:var(--muted); text-decoration:line-through; }
  .fame-item.checked .fame-icon { opacity:.5; }
  .fame-wiki { margin-left:auto; font-size:.68rem; color:var(--muted); text-decoration:none;
    opacity:0; flex-shrink:0; }
  .fame-item:hover .fame-wiki { opacity:1; }
  .fame-wiki:hover { color:var(--accent); text-decoration:underline; }
  .fame-picker { position:relative; margin-top:1rem; }
  .fame-search { width:100%; padding:.6rem .85rem; border-radius:10px; border:1px solid var(--border);
    background:var(--card-bg); color:var(--text); font-size:.95rem; box-shadow: var(--shadow); }
  .fame-search:focus { outline:none; border-color:var(--accent); }
  .fame-results { position:absolute; left:0; right:0; top:100%; margin-top:.35rem;
    background:var(--card-bg); border:1px solid var(--border); border-radius:10px;
    box-shadow: 0 8px 24px rgba(16,24,40,.18); max-height:min(50vh,380px); overflow-y:auto;
    z-index:30; display:none; }
  .fame-results.open { display:block; }
  .fame-result { display:flex; align-items:center; gap:.6rem; padding:.45rem .7rem; cursor:pointer; }
  .fame-result:hover { background: rgba(127,127,127,.12); }
  .fame-result input { accent-color: var(--accent); width:16px; height:16px; flex-shrink:0; cursor:pointer; }
  .fame-result.checked .fame-name { color:var(--muted); text-decoration:line-through; }
  .fame-result.checked .fame-icon { opacity:.5; }
  .fame-result-meta { margin-left:auto; font-size:.7rem; color:var(--muted); white-space:nowrap;
    flex-shrink:0; }
  .fame-empty { padding:.75rem; font-size:.85rem; color:var(--muted); }
</style>
</head>
<body>
<header>
  <h1><span class="emoji">🧪</span> RotMG Toolkit</h1>
  <nav class="pagenav">
    <button class="pagetab active" data-page="potions">Where to Find Stat Potions</button>
    <button class="pagetab" data-page="equipment">Equipment Compare</button>
    <button class="pagetab" data-page="fame">Fame Checklist</button>
  </nav>
</header>
<main>
  <section id="page-potions" class="page active">
    <p class="sub">Data from the <a href="https://www.realmeye.com/wiki/dungeons" target="_blank" rel="noopener">RealmEye wiki</a>
      (__N_SHOWN__ dungeons with potions of interest, __N_NO_DATA__ with no data, __N_BIOMES__ open-world biomes with __N_BIOME_ENEMIES__ potion-dropping enemies).
      <b>Guaranteed</b> = the enemy's own Drops table marks that potion with a G.
      <b>Possible</b> = it can drop there but isn't guaranteed.
      The skull next to a dungeon's name is its difficulty rating (0-10, in steps of 0.5).</p>
    <div class="controls">
      <input id="search" type="search" placeholder="Search dungeon, biome or enemy…">
      <select id="typeFilter">
        <option value="">All potion types</option>
        __TYPE_OPTIONS__
      </select>
    </div>
    <div class="toggles">
      <label class="pill-toggle"><input type="checkbox" id="onlyGuaranteed"> Guaranteed only</label>
      <label><input type="checkbox" id="hideNoData"> Hide missing data</label>
    </div>
    <div class="tabs">
      <button class="tab active" data-view="dungeons">Dungeons</button>
      <button class="tab" data-view="biomes">Open-World Biomes</button>
    </div>
    <div id="view-dungeons" class="view active">
__DUNGEON_CARDS__
    </div>
    <div id="view-biomes" class="view">
      <p class="sub">Every biome of the <a href="https://www.realmeye.com/wiki/the-realm" target="_blank" rel="noopener">open-world Realm</a> map, with the regular enemies, Heroes of Oryx, encounters and beacon guardians in it that can drop potions.</p>
__BIOME_CARDS__
    </div>
  </section>

  <section id="page-equipment" class="page">
    <p class="sub">Data from the <a href="https://www.realmeye.com/wiki/equipment" target="_blank" rel="noopener">RealmEye equipment wiki</a>
      (__N_EQUIPMENT__ weapons/abilities/armor items; rings aren't included yet — the source page mixes
      several inconsistent table layouts). Pick two items that are equippable by the exact same set of
      classes to compare their stats and effects side by side. When both items are weapons, a live DPS
      estimate is shown too — drag your character's ATT/DEX below.</p>
    <div class="eq-stats">
      <div class="eq-stat-slider">
        <label for="eqAtt">ATT <span id="eqAttVal">75</span></label>
        <input type="range" id="eqAtt" min="0" max="100" value="75">
      </div>
      <div class="eq-stat-slider">
        <label for="eqDex">DEX <span id="eqDexVal">75</span></label>
        <input type="range" id="eqDex" min="0" max="100" value="75">
      </div>
    </div>
    <div class="eq-pickers">
      <div class="eq-picker" data-side="a">
        <label>Item A</label>
        <input type="search" class="eq-search" placeholder="Search item…" autocomplete="off">
        <div class="eq-results"></div>
        <div class="eq-selected"></div>
      </div>
      <div class="eq-vs">VS</div>
      <div class="eq-picker" data-side="b">
        <label>Item B</label>
        <input type="search" class="eq-search" placeholder="Pick Item A first" autocomplete="off" disabled>
        <div class="eq-results"></div>
        <div class="eq-selected"></div>
      </div>
    </div>
    <div id="eq-compare"></div>
  </section>

  <section id="page-fame" class="page">
    <p class="sub">The <b>Dungeon Collection</b> bonuses from the
      <a href="https://www.realmeye.com/wiki/fame-bonuses" target="_blank" rel="noopener">RealmEye fame-bonuses wiki</a>
      (__N_COLLECTIONS__ collections over __N_FAME_DUNGEONS__ distinct dungeons). Each one pays out once,
      the first time you have completed every dungeon in it on a single character. Tick the dungeons you
      have cleared — a dungeon that appears in several collections is ticked in all of them at once, and
      your progress is kept in this browser.</p>
    <div class="fame-picker">
      <input id="fameSearch" class="fame-search" type="search" autocomplete="off"
             placeholder="Search any dungeon to tick it off — click to see all __N_FAME_DUNGEONS__">
      <div id="fameResults" class="fame-results"></div>
    </div>
    <div class="fame-toolbar">
      <span class="fame-summary"><b id="fameDone">0</b>/__N_FAME_DUNGEONS__ dungeons ticked ·
        <b id="fameCollections">0</b>/__N_COLLECTIONS__ collections complete ·
        <b id="fameFame">0</b> of __N_FAME_TOTAL__ bonus Fame</span>
      <button class="fame-btn" id="fameClear">Clear all</button>
    </div>
__FAME_SECTIONS__
  </section>
</main>
<script>
const search = document.getElementById('search');
const typeFilter = document.getElementById('typeFilter');
const onlyGuaranteed = document.getElementById('onlyGuaranteed');
const hideNoData = document.getElementById('hideNoData');
const tabs = Array.from(document.querySelectorAll('.tab'));
const views = Array.from(document.querySelectorAll('.view'));
const pagetabs = Array.from(document.querySelectorAll('.pagetab'));
const pages = Array.from(document.querySelectorAll('.page'));

function applyFilters() {
  const q = search.value.trim().toLowerCase();
  const type = typeFilter.value;
  const onlyG = onlyGuaranteed.checked;
  const filtersActive = !!type || onlyG;
  const activeView = document.querySelector('.view.active');
  const cards = Array.from(activeView.querySelectorAll('.card'));

  cards.forEach(c => {
    const nameMatch = !q || c.dataset.name.includes(q);
    let anyPillVisible = false;

    c.querySelectorAll('.row').forEach(row => {
      let rowHasVisible = false;
      row.querySelectorAll('.pill').forEach(pill => {
        let visible = true;
        if (type && pill.dataset.type !== type) visible = false;
        if (onlyG && pill.classList.contains('e')) visible = false;
        pill.classList.toggle('hidden', !visible);
        if (visible) rowHasVisible = true;
      });
      row.classList.toggle('hidden', !rowHasVisible);
      if (rowHasVisible) anyPillVisible = true;
    });
    c.querySelectorAll('.block').forEach(block => {
      const anyRow = Array.from(block.querySelectorAll('.row')).some(r => !r.classList.contains('hidden'));
      block.classList.toggle('hidden', !anyRow);
    });

    let show = nameMatch;
    if (filtersActive) {
      show = show && anyPillVisible;
    }
    if (hideNoData.checked && c.classList.contains('no-data')) show = false;
    c.classList.toggle('hidden', !show);
  });

  activeView.querySelectorAll('.cat').forEach(cat => {
    const anyVisible = Array.from(cat.querySelectorAll('.card')).some(c => !c.classList.contains('hidden'));
    cat.classList.toggle('hidden', !anyVisible);
  });
}

[search, typeFilter].forEach(el => el.addEventListener('input', applyFilters));
[onlyGuaranteed, hideNoData].forEach(el => el.addEventListener('change', applyFilters));
tabs.forEach(tab => tab.addEventListener('click', () => {
  tabs.forEach(t => t.classList.remove('active'));
  tab.classList.add('active');
  views.forEach(v => v.classList.toggle('active', v.id === 'view-' + tab.dataset.view));
  applyFilters();
}));
applyFilters();

pagetabs.forEach(tab => tab.addEventListener('click', () => {
  pagetabs.forEach(t => t.classList.remove('active'));
  tab.classList.add('active');
  pages.forEach(p => p.classList.toggle('active', p.id === 'page-' + tab.dataset.page));
}));

/* ---- Fame checklist ---- */
const FAME_KEY = 'rotmg-toolkit:fame-dungeons';
const fameItems = Array.from(document.querySelectorAll('.fame-item'));
const fameCollections = Array.from(document.querySelectorAll('.fame-collection'));

function fameLoad() {
  try {
    const raw = localStorage.getItem(FAME_KEY);
    return new Set(raw ? JSON.parse(raw) : []);
  } catch (e) { return new Set(); }
}

function fameSave(done) {
  try { localStorage.setItem(FAME_KEY, JSON.stringify([...done])); } catch (e) { /* private mode */ }
}

let fameDone = fameLoad();

/* The quick picker's list is derived from the sections themselves, so there is
   only ever one copy of the data: every distinct dungeon, A-Z, with the icon
   and the collections it belongs to. */
const famePicker = document.querySelector('.fame-picker');
const fameSearchInput = document.getElementById('fameSearch');
const fameResults = document.getElementById('fameResults');

const fameCatalog = (() => {
  const byName = new Map();
  fameItems.forEach(item => {
    const name = item.dataset.dungeon;
    let rec = byName.get(name);
    if (!rec) {
      rec = { name, icon: item.querySelector('.fame-icon').getAttribute('src'), collections: 0 };
      byName.set(name, rec);
    }
    rec.collections++;
  });
  return [...byName.values()].sort((a, b) => a.name.localeCompare(b.name, 'en'));
})();

/* Typing "oryx's" should find "Oryx’s Castle": the wiki uses typographic
   apostrophes, keyboards produce straight ones. */
function fameNorm(s) {
  return s.toLowerCase().replace(/[\u2018\u2019]/g, "'").trim();
}

const fameRows = fameCatalog.map(d => {
  const row = document.createElement('label');
  row.className = 'fame-result';
  row.dataset.dungeon = d.name;
  row.dataset.needle = fameNorm(d.name);

  const box = document.createElement('input');
  box.type = 'checkbox';
  box.className = 'fame-result-check';

  const icon = document.createElement('img');
  icon.className = 'fame-icon';
  icon.src = d.icon;
  icon.alt = '';
  icon.loading = 'lazy';

  const label = document.createElement('span');
  label.className = 'fame-name';
  label.textContent = d.name;

  const meta = document.createElement('span');
  meta.className = 'fame-result-meta';
  meta.textContent = d.collections + (d.collections === 1 ? ' collection' : ' collections');

  row.append(box, icon, label, meta);
  box.addEventListener('change', () => fameSet(d.name, box.checked));
  fameResults.append(row);
  return row;
});

const fameEmpty = document.createElement('div');
fameEmpty.className = 'fame-empty';
fameEmpty.hidden = true;
fameEmpty.textContent = 'No dungeon matches that.';
fameResults.append(fameEmpty);

function fameRender() {
  fameItems.forEach(item => {
    const on = fameDone.has(item.dataset.dungeon);
    item.querySelector('.fame-check').checked = on;
    item.classList.toggle('checked', on);
  });
  fameRows.forEach(row => {
    const on = fameDone.has(row.dataset.dungeon);
    row.querySelector('.fame-result-check').checked = on;
    row.classList.toggle('checked', on);
  });
  let completed = 0, earned = 0;
  fameCollections.forEach(sec => {
    const total = Number(sec.dataset.total);
    const n = Array.from(sec.querySelectorAll('.fame-item'))
      .filter(i => fameDone.has(i.dataset.dungeon)).length;
    const full = total > 0 && n === total;
    if (full) { completed++; earned += Number(sec.dataset.fame) || 0; }
    sec.classList.toggle('done', full);
    sec.querySelector('.fame-count').textContent = n + '/' + total;
    sec.querySelector('.fame-bar-fill').style.width = total ? (100 * n / total) + '%' : '0';
  });
  const ticked = fameCatalog.filter(d => fameDone.has(d.name)).length;
  document.getElementById('fameDone').textContent = ticked;
  document.getElementById('fameCollections').textContent = completed;
  document.getElementById('fameFame').textContent = earned.toLocaleString('en-US');
}

function fameSet(name, on) {
  if (on) fameDone.add(name); else fameDone.delete(name);
  fameSave(fameDone);
  fameRender();
}

fameItems.forEach(item => {
  item.querySelector('.fame-check').addEventListener('change', ev => {
    fameSet(item.dataset.dungeon, ev.target.checked);
  });
});

function fameFilter() {
  const q = fameNorm(fameSearchInput.value);
  let shown = 0;
  fameRows.forEach(row => {
    const hit = !q || row.dataset.needle.includes(q);
    row.hidden = !hit;
    if (hit) shown++;
  });
  fameEmpty.hidden = shown > 0;
}

function famePickerOpen(open) {
  fameResults.classList.toggle('open', open);
}

fameSearchInput.addEventListener('focus', () => { fameFilter(); famePickerOpen(true); });
fameSearchInput.addEventListener('input', () => { fameFilter(); famePickerOpen(true); });
fameSearchInput.addEventListener('keydown', ev => {
  if (ev.key !== 'Escape') return;
  if (fameSearchInput.value) { fameSearchInput.value = ''; fameFilter(); }
  else { famePickerOpen(false); fameSearchInput.blur(); }
});
/* Close on a click outside the picker, but never on a click inside it -- ticking
   several dungeons in a row should not dismiss the list. */
document.addEventListener('mousedown', ev => {
  if (!famePicker.contains(ev.target)) famePickerOpen(false);
});

document.getElementById('fameClear').addEventListener('click', () => {
  if (!fameDone.size) return;
  if (!confirm('Untick every dungeon in the fame checklist?')) return;
  fameDone = new Set();
  fameSave(fameDone);
  fameRender();
});

fameFilter();
fameRender();

/* ---- Equipment compare ---- */
const FALLBACK_ICON = __FALLBACK_ICON_JSON__;
let eqData = null;
let eqByHref = {};
const eqSelected = { a: null, b: null };

fetch('data/equipment.json').then(r => r.json()).then(data => {
  eqData = data;
  data.forEach(it => { eqByHref[it.href] = it; });
  document.querySelectorAll('.eq-search').forEach(input => {
    const side = input.closest('.eq-picker').dataset.side;
    if (document.activeElement === input) eqSearch(side, input.value);
  });
});

function escHtml(s) {
  return (s ?? '').toString().replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}
function classKey(it) { return it.classes.slice().sort().join('|'); }

function eqSearch(side, query) {
  const resultsEl = document.querySelector('.eq-picker[data-side="' + side + '"] .eq-results');
  if (!eqData) {
    resultsEl.innerHTML = '<div class="eq-empty">Loading…</div>';
    resultsEl.classList.add('open');
    return;
  }
  let pool = eqData;
  if (side === 'b' && eqSelected.a) {
    const key = classKey(eqSelected.a);
    pool = pool.filter(it => classKey(it) === key);
  }
  const q = query.trim().toLowerCase();
  const results = (q ? pool.filter(it => it.name.toLowerCase().includes(q)) : pool).slice(0, 40);
  if (!results.length) {
    resultsEl.innerHTML = '<div class="eq-empty">No matches</div>';
  } else {
    resultsEl.innerHTML = results.map(it =>
      '<div class="eq-result" data-href="' + escHtml(it.href) + '">' +
        '<img src="' + escHtml(it.icon || FALLBACK_ICON) + '" alt="">' +
        '<div class="eq-result-body">' +
          '<div class="eq-result-name">' + escHtml(it.name) + '</div>' +
          '<div class="eq-result-meta">' + escHtml(it.category) + ' · ' + escHtml(it.family || '') +
            ' · Tier ' + escHtml(it.tier || '—') + '</div>' +
        '</div>' +
      '</div>'
    ).join('');
  }
  resultsEl.classList.add('open');
}

function renderEqSelected(side) {
  const picker = document.querySelector('.eq-picker[data-side="' + side + '"]');
  const input = picker.querySelector('.eq-search');
  const resultsEl = picker.querySelector('.eq-results');
  const selEl = picker.querySelector('.eq-selected');
  const item = eqSelected[side];
  resultsEl.classList.remove('open');
  if (item) {
    input.style.display = 'none';
    selEl.innerHTML =
      '<img src="' + escHtml(item.icon || FALLBACK_ICON) + '" alt="">' +
      '<div class="eq-selected-body">' +
        '<div class="eq-selected-name">' + escHtml(item.name) + '</div>' +
        '<div class="eq-selected-meta">' + escHtml(item.category) + ' · Tier ' + escHtml(item.tier || '—') +
          (item.soulbound ? ' · Soulbound' : '') + '</div>' +
        '<div class="eq-selected-classes">' + item.classes.map(escHtml).join(', ') + '</div>' +
      '</div>' +
      '<button class="eq-change" type="button">Change</button>';
    selEl.querySelector('.eq-change').addEventListener('click', () => {
      eqSelected[side] = null;
      if (side === 'a') { eqSelected.b = null; renderEqSelected('b'); }
      renderEqSelected(side);
      renderEqCompare();
      const inp = picker.querySelector('.eq-search');
      inp.value = '';
      inp.focus();
    });
  } else {
    selEl.innerHTML = '';
    input.style.display = '';
    input.disabled = (side === 'b' && !eqSelected.a);
    input.placeholder = (side === 'b' && !eqSelected.a) ? 'Pick Item A first' : 'Search item…';
  }
}

function selectEqItem(side, href) {
  const item = eqByHref[href];
  if (!item) return;
  eqSelected[side] = item;
  if (side === 'a' && eqSelected.b && classKey(eqSelected.b) !== classKey(item)) {
    eqSelected.b = null;
  }
  renderEqSelected('a');
  renderEqSelected('b');
  renderEqCompare();
}

const STAT_ORDER = ['ATT', 'DEF', 'SPD', 'DEX', 'VIT', 'WIS', 'HP', 'MP'];
const STAT_LABELS = { ATT: 'Attack', DEF: 'Defense', SPD: 'Speed', DEX: 'Dexterity',
                       VIT: 'Vitality', WIS: 'Wisdom', HP: 'HP', MP: 'MP' };

function fmtSigned(n) { return (n > 0 ? '+' : '') + n; }

function statRow(label, va, vb) {
  if (va == null && vb == null) return '';
  const na = va || 0, nb = vb || 0;
  let ca = '', cb = '';
  if (na !== nb) {
    const aWins = na > nb;
    ca = aWins ? 'better' : 'worse';
    cb = aWins ? 'worse' : 'better';
  }
  return '<div class="eq-row">' +
    '<div class="eq-val ' + ca + '">' + (va != null ? fmtSigned(va) : '—') + '</div>' +
    '<div class="eq-label">' + escHtml(label) + '</div>' +
    '<div class="eq-val ' + cb + '">' + (vb != null ? fmtSigned(vb) : '—') + '</div>' +
  '</div>';
}

function textRow(label, va, vb) {
  if (!va && !vb) return '';
  const differs = (va || '') !== (vb || '');
  return '<div class="eq-row ' + (differs ? 'diff' : '') + '">' +
    '<div class="eq-val text">' + (va ? escHtml(va) : '—') + '</div>' +
    '<div class="eq-label">' + escHtml(label) + '</div>' +
    '<div class="eq-val text">' + (vb ? escHtml(vb) : '—') + '</div>' +
  '</div>';
}

/* A column's value is a list of {label, value} bits (e.g. a weapon's
   "Damage (Average)" column splits into a Damage bit, a Projectile Speed
   bit, an embedded effect + its description, and a Rate of Fire bit) --
   one row per bit, matched by label between the two items being compared. */
function segsToMap(segs) {
  const map = new Map();
  (segs || []).forEach(s => { if (!map.has(s.label)) map.set(s.label, s.value); });
  return map;
}

function segmentRows(segsA, segsB, skipLabels) {
  const mapA = segsToMap(segsA), mapB = segsToMap(segsB);
  const labels = [];
  const seen = new Set();
  [mapA, mapB].forEach(m => m.forEach((_, k) => {
    if (!seen.has(k) && !(skipLabels && skipLabels.has(k))) { seen.add(k); labels.push(k); }
  }));
  return labels.map(label => textRow(label, mapA.get(label), mapB.get(label))).join('');
}

function numRow(label, va, vb, extraClass) {
  if (va == null && vb == null) return '';
  const na = va || 0, nb = vb || 0;
  let ca = '', cb = '';
  if (na !== nb) {
    const aWins = na > nb;
    ca = aWins ? 'better' : 'worse';
    cb = aWins ? 'worse' : 'better';
  }
  return '<div class="eq-row ' + (extraClass || '') + '">' +
    '<div class="eq-val ' + ca + '">' + (va != null ? va : '—') + '</div>' +
    '<div class="eq-label">' + escHtml(label) + '</div>' +
    '<div class="eq-val ' + cb + '">' + (vb != null ? vb : '—') + '</div>' +
  '</div>';
}

/* DPS = avg damage per shot * shots * Damage Multiplier(ATT) * Attacks/sec(DEX, RoF).
   Verified against realmeye.com/wiki/character-stats:
     Damage Multiplier = 0.5 + ATT/50
     Attacks/sec (RoF 100%) = 1.5 + 6.5 * (DEX/75)
   ATT explicitly does not affect ability damage, so this only applies to weapons.

   Multi-shot weapons show up in three different shapes on the wiki (see
   docs/decisions/0003-multi-bullet-dps.md and 0004-fire-rate-column.md);
   in all three, each shot/bullet's own Rate of Fire is the probability it
   fires on a given attack at the weapon's shared base attack speed, not an
   independent attack-speed stream -- so DPS is always the sum of each
   group's own avg * shots * DamageMultiplier * (baseAttacksPerSec * RoF%):
     A. "Bullet N" damage groups inside the Damage cell itself, each with
        its own optional "Bullet N Rate of Fire" (Heartsteel Claymore,
        Arcane Rapier). A bullet with no listed RoF fires on every attack
        (100%) -- that's the wiki's convention for "always fires" (e.g.
        Shortbow's Main/Side arrows both omit it and both always fire
        together), not "whatever's left over from the other bullets".
     B. A labeled "Fire Rate" column with one shared label per group
        (e.g. "Main"/"Side" -- Hama Yumi), matched by label against the
        Damage and Shots columns.
     C. A single "Fire Rate" segment listing N comma-separated percentages
        that all share one avg damage value, one shot each (e.g. Morning
        Star of Harrowing Memories' "15%, 50%, 90%, 50%, 15%"). */
function parseDamageProfile(item) {
  if (item.category !== 'Weapon') return null;
  const segs = item.columns['Damage (Average)'] || item.columns['Damage'];
  if (!segs) return null;

  const readAvg = v => { const m = v.match(/\(([\d.]+)\)/) || v.match(/^([\d.]+)$/); return m ? parseFloat(m[1]) : null; };
  const readPct = v => { const m = v.match(/([\d.]+)/); return m ? parseFloat(m[1]) : null; };
  const readPctList = v => (v.match(/[\d.]+/g) || []).map(parseFloat);

  const bulletNums = Array.from(new Set(segs
    .map(s => { const m = s.label.match(/^Bullet (\d+)$/); return m ? parseInt(m[1], 10) : null; })
    .filter(n => n !== null))).sort((a, b) => a - b);

  if (bulletNums.length >= 2) {
    const groups = [];
    bulletNums.forEach(n => {
      const primary = segs.find(s => s.label === 'Bullet ' + n);
      if (!primary) return;
      const avg = readAvg(primary.value);
      if (avg == null) return;
      const shotsSeg = segs.find(s => s.label === 'Bullet ' + n + ' Shots');
      const shots = shotsSeg ? (parseInt(shotsSeg.value, 10) || 1) : 1;
      const rofSeg = segs.find(s => s.label === 'Bullet ' + n + ' Rate of Fire');
      const rofVal = rofSeg ? readPct(rofSeg.value) : null;
      const rof = rofVal != null ? rofVal : 100;
      groups.push({ avg, shots, rof });
    });
    if (groups.length) return groups;
  }

  const fireRateSegs = item.columns['Fire Rate'];
  const shotsSegs = item.columns['Shots'];
  if (fireRateSegs && fireRateSegs.length) {
    const labeled = fireRateSegs.filter(s => s.label !== 'Fire Rate');
    if (labeled.length >= 2) {
      const groups = [];
      labeled.forEach(frSeg => {
        const dmgSeg = segs.find(s => s.label === frSeg.label);
        const shotSeg = shotsSegs && shotsSegs.find(s => s.label === frSeg.label);
        if (!dmgSeg || !shotSeg) return;
        const avg = readAvg(dmgSeg.value);
        const rof = readPct(frSeg.value);
        if (avg == null || rof == null) return;
        groups.push({ avg, shots: parseInt(shotSeg.value, 10) || 1, rof });
      });
      if (groups.length) return groups;
    } else if (fireRateSegs.length === 1 && fireRateSegs[0].label === 'Fire Rate') {
      const primary = segs.find(s => s.label === 'Damage (Average)' || s.label === 'Damage');
      const avg = primary ? readAvg(primary.value) : null;
      const pctList = readPctList(fireRateSegs[0].value);
      if (avg != null && pctList.length) {
        return pctList.map(rof => ({ avg, shots: 1, rof }));
      }
    }
  }

  const primary = segs.find(s => s.label === 'Damage (Average)' || s.label === 'Damage');
  if (!primary) return null;
  const avg = readAvg(primary.value);
  if (avg == null) return null;
  const rofSeg = segs.find(s => s.label === 'Rate of Fire');
  const rofVal = rofSeg ? readPct(rofSeg.value) : null;
  const rof = rofVal != null ? rofVal : 100;
  const shotsVal = (shotsSegs && shotsSegs[0]) ? shotsSegs[0].value : '1';
  const shotsMatch = shotsVal.match(/^(\d+)/);
  const shots = shotsMatch ? parseInt(shotsMatch[1], 10) : 1;
  return [{ avg, shots, rof }];
}

function computeDps(item, att, dex) {
  const groups = parseDamageProfile(item);
  if (!groups) return null;
  const dmgMult = 0.5 + att / 50;
  const baseAps = 1.5 + 6.5 * (dex / 75);
  let dps = 0, aps = 0;
  groups.forEach(g => {
    const groupAps = baseAps * (g.rof / 100);
    dps += g.avg * g.shots * dmgMult * groupAps;
    aps += groupAps;
  });
  const rofDisplay = groups.map(g => g.rof + '%').join(' / ');
  return { dps, aps, rofDisplay, groups };
}

function renderEqCompare() {
  const el = document.getElementById('eq-compare');
  const a = eqSelected.a, b = eqSelected.b;
  if (!a || !b) { el.innerHTML = ''; return; }

  let out = '<div class="eq-cmp-header">' +
    '<div class="eq-cmp-side"><img src="' + escHtml(a.icon || FALLBACK_ICON) + '" alt="">' +
      '<div><div class="eq-cmp-name"><a href="https://www.realmeye.com' + escHtml(a.href) +
        '" target="_blank" rel="noopener">' + escHtml(a.name) + '</a></div>' +
      '<div class="eq-cmp-meta">' + escHtml(a.category) + ' · ' + escHtml(a.family || '') + '</div></div></div>' +
    '<div class="eq-cmp-vslabel">VS</div>' +
    '<div class="eq-cmp-side"><img src="' + escHtml(b.icon || FALLBACK_ICON) + '" alt="">' +
      '<div><div class="eq-cmp-name"><a href="https://www.realmeye.com' + escHtml(b.href) +
        '" target="_blank" rel="noopener">' + escHtml(b.name) + '</a></div>' +
      '<div class="eq-cmp-meta">' + escHtml(b.category) + ' · ' + escHtml(b.family || '') + '</div></div></div>' +
  '</div>';

  const att = parseInt(document.getElementById('eqAtt').value, 10);
  const dex = parseInt(document.getElementById('eqDex').value, 10);
  const dpsA = computeDps(a, att, dex);
  const dpsB = computeDps(b, att, dex);
  if (dpsA && dpsB) {
    out += '<div class="eq-section-title">Estimated DPS (ATT ' + att + ', DEX ' + dex + ')</div>';
    out += numRow('DPS', Math.round(dpsA.dps), Math.round(dpsB.dps), 'eq-dps-row');
    out += textRow('Attacks/sec', dpsA.aps.toFixed(2), dpsB.aps.toFixed(2));
    out += textRow('Rate of Fire', dpsA.rofDisplay, dpsB.rofDisplay);
  }

  STAT_ORDER.forEach(k => {
    if (k in a.stats || k in b.stats) out += statRow(STAT_LABELS[k], a.stats[k], b.stats[k]);
  });

  out += textRow('Tier', a.tier + (a.soulbound ? ' (Soulbound)' : ''), b.tier + (b.soulbound ? ' (Soulbound)' : ''));

  const skip = new Set(STAT_ORDER);
  ['XP Bonus', 'Feed Power'].forEach(k => { skip.add(k); out += segmentRows(a.columns[k], b.columns[k]); });

  const otherKeys = Array.from(new Set([...Object.keys(a.columns), ...Object.keys(b.columns)]))
    .filter(k => !skip.has(k));
  otherKeys.forEach(k => {
    // The DPS section above already shows a combined "Rate of Fire" row
    // (dpsA/dpsB.rofDisplay) when it renders, so skip the same label(s)
    // here to avoid showing "Rate of Fire" twice for the same weapon.
    let skipLabels = null;
    if (dpsA && dpsB && (k === 'Damage (Average)' || k === 'Damage')) {
      skipLabels = new Set();
      (a.columns[k] || []).concat(b.columns[k] || []).forEach(s => {
        if (s.label === 'Rate of Fire' || /\bRate of Fire$/.test(s.label)) skipLabels.add(s.label);
      });
    }
    out += segmentRows(a.columns[k], b.columns[k], skipLabels);
  });

  const allEffects = Array.from(new Set([...a.effects, ...b.effects])).sort();
  if (allEffects.length) {
    out += '<div class="eq-section-title">Effects</div>';
    out += allEffects.map(eff => {
      const hasA = a.effects.includes(eff), hasB = b.effects.includes(eff);
      return '<div class="eq-row ' + (hasA !== hasB ? 'diff' : '') + '">' +
        '<div class="eq-val ' + (hasA ? 'has' : 'no') + '">' + (hasA ? '✓' : '—') + '</div>' +
        '<div class="eq-label">' + escHtml(eff) + '</div>' +
        '<div class="eq-val ' + (hasB ? 'has' : 'no') + '">' + (hasB ? '✓' : '—') + '</div>' +
      '</div>';
    }).join('');
  }

  el.innerHTML = out;
}

document.querySelectorAll('.eq-search').forEach(input => {
  const side = input.closest('.eq-picker').dataset.side;
  input.addEventListener('input', () => eqSearch(side, input.value));
  input.addEventListener('focus', () => eqSearch(side, input.value));
});
document.addEventListener('click', e => {
  const resEl = e.target.closest('.eq-result');
  if (resEl) {
    const side = resEl.closest('.eq-picker').dataset.side;
    selectEqItem(side, resEl.dataset.href);
    return;
  }
  if (!e.target.closest('.eq-picker')) {
    document.querySelectorAll('.eq-results').forEach(r => r.classList.remove('open'));
  }
});
const eqAttSlider = document.getElementById('eqAtt');
const eqDexSlider = document.getElementById('eqDex');
const eqAttVal = document.getElementById('eqAttVal');
const eqDexVal = document.getElementById('eqDexVal');
[eqAttSlider, eqDexSlider].forEach(sl => sl.addEventListener('input', () => {
  eqAttVal.textContent = eqAttSlider.value;
  eqDexVal.textContent = eqDexSlider.value;
  renderEqCompare();
}));
renderEqSelected('a');
renderEqSelected('b');
</script>
</body>
</html>
"""

if __name__ == "__main__":
    data_path = sys.argv[1] if len(sys.argv) > 1 else "data/dungeon_potions.json"
    out_path = sys.argv[2] if len(sys.argv) > 2 else "index.html"
    biome_path = sys.argv[3] if len(sys.argv) > 3 else "data/biome_potions.json"
    equipment_path = sys.argv[4] if len(sys.argv) > 4 else "data/equipment.json"
    fame_path = sys.argv[5] if len(sys.argv) > 5 else "data/fame_bonuses.json"
    build(data_path, out_path, biome_path, equipment_path, fame_path)
