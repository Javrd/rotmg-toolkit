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


def render_card(name, href, icon, blocks, difficulty=None, error=None):
    """blocks: list of (title_or_None, guaranteed_list, possible_list).
    Returns None if the card has no potions and no error (should be omitted)."""
    has_potions = any(g or e for _, g, e in blocks)
    if not error and not has_potions:
        return None
    classes = "card no-data" if error else "card"
    out = [f'<article class="{classes}" data-name="{esc(name.lower())}">']
    out.append(
        f'<h3>{img(icon, name, "card-icon")}'
        f'<a href="https://www.realmeye.com{esc(href)}" target="_blank" rel="noopener">{esc(name)}</a>'
        f'{render_difficulty(difficulty)}</h3>'
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


def render_category(title, card_htmls):
    if not card_htmls:
        return ""
    out = [f'<section class="cat" data-cat="{esc(title)}">',
           f'<h2 class="cat-title">{esc(title)}</h2>',
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


def build_quest_monster_section(title, entries):
    cards = []
    for e in entries:
        g = [dict(p, source_name=None) for p in e["potions"] if p["guaranteed"]]
        ex = [dict(p, source_name=None) for p in e["potions"] if not p["guaranteed"]]
        blocks = [(None, g, ex)]
        card = render_card(e["name"], e["href"], e.get("icon"), blocks)
        if card:
            cards.append(card)
    return render_category(title, cards)


def collect_types(dungeons, qm):
    types = set()

    def scan(entries):
        for p in entries:
            types.add(p.get("type", p["name"]))

    for d in dungeons:
        scan(d["main"]["garantizados"]); scan(d["main"]["extra"])
        scan(d["treasure"]["garantizados"]); scan(d["treasure"]["extra"])
    if qm:
        for k in ("setpiece", "encounters"):
            for e in qm.get(k, []):
                scan(e["potions"])
    return sorted(types)


def build(data_path, out_path, quest_path=None, equipment_path=None):
    with open(data_path, encoding="utf-8") as f:
        dungeons = json.load(f)

    def has_potions(d):
        return bool(d["main"]["garantizados"] or d["main"]["extra"] or
                    d["treasure"]["garantizados"] or d["treasure"]["extra"])

    dungeon_html = build_dungeon_sections(dungeons)
    n_total = len(dungeons)
    n_shown = sum(1 for d in dungeons if not d.get("error") and has_potions(d))
    n_no_data = sum(1 for d in dungeons if d.get("error"))

    quest_html = ""
    n_setpiece = n_encounters = 0
    qm = None
    if quest_path:
        try:
            with open(quest_path, encoding="utf-8") as f:
                qm = json.load(f)
            n_setpiece = len(qm.get("setpiece", []))
            n_encounters = len(qm.get("encounters", []))
            quest_html = (
                build_quest_monster_section("Setpiece Bosses (open world)", qm.get("setpiece", [])) +
                "\n" +
                build_quest_monster_section("Encounters (event bosses)", qm.get("encounters", []))
            )
        except FileNotFoundError:
            pass

    types = collect_types(dungeons, qm)
    type_options = "".join(f'<option value="{esc(t)}">{esc(t)}</option>' for t in types)

    n_equipment = 0
    if equipment_path:
        try:
            with open(equipment_path, encoding="utf-8") as f:
                n_equipment = len(json.load(f))
        except FileNotFoundError:
            pass

    page = TEMPLATE.replace("__DUNGEON_CARDS__", dungeon_html) \
                    .replace("__QUEST_CARDS__", quest_html) \
                    .replace("__TYPE_OPTIONS__", type_options) \
                    .replace("__N_SHOWN__", str(n_shown)) \
                    .replace("__N_NO_DATA__", str(n_no_data)) \
                    .replace("__N_SETPIECE__", str(n_setpiece)) \
                    .replace("__N_ENCOUNTERS__", str(n_encounters)) \
                    .replace("__N_EQUIPMENT__", str(n_equipment)) \
                    .replace("__FALLBACK_ICON_JSON__", json.dumps(FALLBACK_ICON))

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(page)
    print(f"Wrote {out_path} ({n_shown}/{n_total} dungeons with potions, {n_no_data} with no data, "
          f"{n_setpiece} setpiece + {n_encounters} encounter enemies, {len(types)} potion types, "
          f"{n_equipment} equipment items)")


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
    border-radius:12px; padding:.8rem; box-shadow: var(--shadow); }
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
  .eq-result-name { font-size:.88rem; }
  .eq-result-meta { font-size:.72rem; color:var(--muted); }
  .eq-empty { padding:.7rem; font-size:.85rem; color:var(--muted); }
  .eq-selected { display:flex; align-items:center; gap:.6rem; }
  .eq-selected img { width:36px; height:36px; object-fit:contain; flex-shrink:0; }
  .eq-selected-body { flex:1; min-width:0; }
  .eq-selected-name { font-weight:600; font-size:.95rem; }
  .eq-selected-meta { font-size:.75rem; color:var(--muted); }
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
</style>
</head>
<body>
<header>
  <h1><span class="emoji">🧪</span> RotMG Toolkit</h1>
  <nav class="pagenav">
    <button class="pagetab active" data-page="potions">Where to Find Stat Potions</button>
    <button class="pagetab" data-page="equipment">Equipment Compare</button>
  </nav>
</header>
<main>
  <section id="page-potions" class="page active">
    <p class="sub">Data from the <a href="https://www.realmeye.com/wiki/dungeons" target="_blank" rel="noopener">RealmEye wiki</a>
      (__N_SHOWN__ dungeons with potions of interest, __N_NO_DATA__ with no data, __N_SETPIECE__ setpiece bosses, __N_ENCOUNTERS__ encounters).
      <b>Guaranteed</b> = the enemy's own Drops table marks that potion with a G.
      <b>Possible</b> = it can drop there but isn't guaranteed.
      The skull next to a dungeon's name is its difficulty rating (0-10, in steps of 0.5).</p>
    <div class="controls">
      <input id="search" type="search" placeholder="Search dungeon or enemy…">
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
      <button class="tab" data-view="quests">Setpiece Bosses / Encounters</button>
    </div>
    <div id="view-dungeons" class="view active">
__DUNGEON_CARDS__
    </div>
    <div id="view-quests" class="view">
      <p class="sub">Open-world bosses not tied to a specific dungeon: <a href="https://www.realmeye.com/wiki/quest-monsters#setpiece" target="_blank" rel="noopener">Setpiece Bosses</a> and <a href="https://www.realmeye.com/wiki/quest-monsters#event" target="_blank" rel="noopener">Encounters</a>.</p>
__QUEST_CARDS__
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

function segmentRows(segsA, segsB) {
  const mapA = segsToMap(segsA), mapB = segsToMap(segsB);
  const labels = [];
  const seen = new Set();
  [mapA, mapB].forEach(m => m.forEach((_, k) => { if (!seen.has(k)) { seen.add(k); labels.push(k); } }));
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
     Attacks/sec (RoF 100%) = 1.5 + 6.5 * (DEX/75); actual = that * (RoF% / 100)
   ATT explicitly does not affect ability damage, so this only applies to weapons.
   Multi-bullet weapons (e.g. Heartsteel Claymore) only use the first bullet's
   average damage -- a known approximation. */
function parseDamageProfile(item) {
  if (item.category !== 'Weapon') return null;
  const segs = item.columns['Damage (Average)'] || item.columns['Damage'];
  if (!segs) return null;
  const primary = segs.find(s => s.label === 'Damage (Average)' || s.label === 'Damage' || s.label === 'Bullet 1');
  if (!primary) return null;
  const avgMatch = primary.value.match(/\(([\d.]+)\)/);
  if (!avgMatch) return null;
  const avg = parseFloat(avgMatch[1]);
  const shotsSegs = item.columns['Shots'];
  const shotsVal = (shotsSegs && shotsSegs[0]) ? shotsSegs[0].value : '1';
  const shotsMatch = shotsVal.match(/^(\d+)/);
  const shots = shotsMatch ? parseInt(shotsMatch[1], 10) : 1;
  const rofSeg = segs.find(s => s.label === 'Rate of Fire' || s.label === 'Bullet 1 Rate of Fire');
  const rofMatch = rofSeg ? rofSeg.value.match(/([\d.]+)/) : null;
  const rof = rofMatch ? parseFloat(rofMatch[1]) : 100;
  return { avg, shots, rof };
}

function computeDps(item, att, dex) {
  const p = parseDamageProfile(item);
  if (!p) return null;
  const dmgMult = 0.5 + att / 50;
  const aps = (1.5 + 6.5 * (dex / 75)) * (p.rof / 100);
  return Object.assign({}, p, { aps, dps: p.avg * p.shots * dmgMult * aps });
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
    out += textRow('Rate of Fire', dpsA.rof + '%', dpsB.rof + '%');
  }

  STAT_ORDER.forEach(k => {
    if (k in a.stats || k in b.stats) out += statRow(STAT_LABELS[k], a.stats[k], b.stats[k]);
  });

  out += textRow('Tier', a.tier + (a.soulbound ? ' (Soulbound)' : ''), b.tier + (b.soulbound ? ' (Soulbound)' : ''));

  const skip = new Set(STAT_ORDER);
  ['XP Bonus', 'Feed Power'].forEach(k => { skip.add(k); out += segmentRows(a.columns[k], b.columns[k]); });

  const otherKeys = Array.from(new Set([...Object.keys(a.columns), ...Object.keys(b.columns)]))
    .filter(k => !skip.has(k));
  otherKeys.forEach(k => { out += segmentRows(a.columns[k], b.columns[k]); });

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
    quest_path = sys.argv[3] if len(sys.argv) > 3 else "data/quest_monster_potions.json"
    equipment_path = sys.argv[4] if len(sys.argv) > 4 else "data/equipment.json"
    build(data_path, out_path, quest_path, equipment_path)
