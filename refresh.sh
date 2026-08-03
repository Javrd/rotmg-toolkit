#!/usr/bin/env bash
# Re-scrape everything and regenerate the site + API from scratch.
# Safe to re-run any time; each step reads/writes data/*.json and is
# independently re-runnable too (see docs/ARCHITECTURE.md).
set -euo pipefail
cd "$(dirname "$0")"

echo "== Dungeons =="
python3 scraper.py all data/dungeon_potions.json

echo "== Setpiece Bosses / Encounters =="
python3 scraper.py quests data/quest_monster_potions.json

echo "== Equipment =="
python3 equipment_scraper.py data/equipment.json

echo "== HTML site =="
python3 build_html.py data/dungeon_potions.json index.html data/quest_monster_potions.json data/equipment.json

echo "== Static API =="
python3 build_api.py api

echo "Done."
