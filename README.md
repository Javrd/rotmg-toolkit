# RotMG Toolkit

A static site + JSON API scraped from the [RealmEye wiki](https://www.realmeye.com/wiki/realm-of-the-mad-god)
for two things I kept wanting while playing *Realm of the Mad God*:

- **Where to Find Stat Potions** — every dungeon and open-world
  boss/encounter, which stat potions they can drop, and whether each one
  is actually *guaranteed* (per the wiki's own drop tables) or just
  possible.
- **Equipment Compare** — pick two items equippable by the exact same set
  of classes and see their stats/effects diffed side by side, with a
  live weapon-DPS estimate driven by ATT/DEX sliders (using the game's
  own published attack-speed/damage formulas).

🔗 **Live site:** https://javrd.github.io/rotmg-toolkit/
🔗 **JSON API:** [`api/README.md`](api/README.md) — no server, plain
static JSON files, fetch whatever you need.

No database, no build step beyond static file generation, no external
runtime dependencies — the site is one self-contained `index.html`
(vanilla JS/CSS) and the scrapers are stdlib-only Python.

## Repo layout

```
scraper.py             dungeons + open-world boss potion drops -> data/*.json
equipment_scraper.py   weapons/abilities/armor -> data/equipment.json
build_html.py          data/*.json -> index.html (the site)
build_api.py           data/*.json -> api/ (the static JSON API)
refresh.sh             re-run all of the above in order
data/*.json            scraped data (checked in; data/cache/ raw HTML is not)
api/                   generated static API (see api/README.md)
docs/                  architecture notes + decision log (in Spanish; my own working notes)
```

## Running it yourself

Everything is stdlib-only Python 3 — no `pip install` needed.

```
git clone https://github.com/javrd/rotmg-toolkit.git
cd rotmg-toolkit
./refresh.sh                 # re-scrapes everything from realmeye.com, ~10 min
python3 -m http.server 8000  # serve index.html + api/ + data/ locally
```

Then open `http://localhost:8000/`.

## Data source & attribution

All game data comes from [RealmEye.com](https://www.realmeye.com), an
unofficial, community-run wiki and stat-tracking site for *Realm of the
Mad God* (published by Deca Games). This project isn't affiliated with
RealmEye or Deca Games; it's a personal tool that re-shapes publicly
visible wiki data into a more convenient form. If you're RealmEye and
would rather this didn't exist in its current form, open an issue.

Known gaps are documented as they're found — see
[`docs/decisions/`](docs/decisions/) (e.g. rings aren't scraped yet; the
source page mixes several inconsistent table layouts).

## License

Code in this repo is [MIT-licensed](LICENSE). The underlying game data
belongs to Deca Games / RealmEye's contributors, not to this repo.
