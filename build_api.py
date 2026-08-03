#!/usr/bin/env python3
"""Turn the scraped data/*.json files into a static, documented, no-DB JSON
API under api/ -- one big array per resource plus one small file per item,
so a consumer can either download everything or fetch a single dungeon /
enemy / equipment item by slug. Pure derived output: re-run any time after
re-scraping, never hand-edit anything under api/.

Field names here are the public contract (English, stable) and
deliberately diverge from the internal data/*.json field names (Spanish
leftovers like "garantizados", or UI-shaped ones): this script is the one
place that translation happens.
"""
import json
import os
import re
import sys
import datetime

WIKI_BASE = "https://www.realmeye.com"
API_VERSION = "1"


def slugify(href_or_name):
    if href_or_name.startswith("/wiki/"):
        return href_or_name[len("/wiki/"):]
    return re.sub(r"[^a-z0-9]+", "-", href_or_name.lower()).strip("-")


def wiki_url(href):
    return href and (WIKI_BASE + href)


def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def potion_entry(p):
    entry = {
        "name": p["name"], "type": p["type"], "icon": p["icon"],
        "guaranteedLabel": p.get("label"),
    }
    if p.get("source_name"):
        entry["source"] = {
            "name": p["source_name"], "wikiUrl": wiki_url(p.get("source_href")),
            "icon": p.get("source_icon"),
        }
    return entry


def build_dungeons(src_path, out_dir):
    with open(src_path, encoding="utf-8") as f:
        dungeons = json.load(f)

    api_items = []
    for d in dungeons:
        slug = slugify(d["href"])
        item = {
            "slug": slug,
            "name": d["name"],
            "wikiUrl": wiki_url(d["href"]),
            "icon": d.get("icon"),
            "category": d.get("category"),
            "difficulty": d.get("difficulty"),
            "hasData": not d.get("error"),
            "error": d.get("error"),
            "potions": {
                "guaranteed": [potion_entry(p) for p in d["main"]["garantizados"]],
                "possible": [potion_entry(p) for p in d["main"]["extra"]],
            },
            "treasureRoomPotions": {
                "guaranteed": [potion_entry(p) for p in d["treasure"]["garantizados"]],
                "possible": [potion_entry(p) for p in d["treasure"]["extra"]],
            },
        }
        api_items.append(item)
        write_json(f"{out_dir}/dungeons/{slug}.json", item)

    write_json(f"{out_dir}/dungeons.json", api_items)
    return api_items


def build_quest_monsters(src_path, out_dir):
    with open(src_path, encoding="utf-8") as f:
        qm = json.load(f)

    api_items = []
    for group, entries in (("setpiece", qm.get("setpiece", [])),
                            ("encounter", qm.get("encounters", []))):
        for e in entries:
            slug = slugify(e["href"])
            item = {
                "slug": slug,
                "name": e["name"],
                "wikiUrl": wiki_url(e["href"]),
                "icon": e.get("icon"),
                "group": group,
                "potions": {
                    "guaranteed": [potion_entry(p) for p in e["potions"] if p["guaranteed"]],
                    "possible": [potion_entry(p) for p in e["potions"] if not p["guaranteed"]],
                },
            }
            api_items.append(item)
            write_json(f"{out_dir}/quest-monsters/{slug}.json", item)

    write_json(f"{out_dir}/quest-monsters.json", api_items)
    return api_items


def build_equipment(src_path, out_dir):
    with open(src_path, encoding="utf-8") as f:
        equipment = json.load(f)

    api_items = []
    for e in equipment:
        slug = slugify(e["href"])
        item = {
            "slug": slug,
            "name": e["name"],
            "wikiUrl": wiki_url(e["href"]),
            "icon": e.get("icon"),
            "category": e["category"],
            "categorySlug": e["category_slug"],
            "family": e.get("family"),
            "tier": e.get("tier"),
            "soulbound": e.get("soulbound", False),
            "classes": e["classes"],
            "stats": e.get("stats", {}),
            "columns": e.get("columns", {}),
            "effects": e.get("effects", []),
            "effectDescriptions": e.get("effect_descriptions", {}),
        }
        api_items.append(item)
        write_json(f"{out_dir}/equipment/{slug}.json", item)

    write_json(f"{out_dir}/equipment.json", api_items)
    return api_items


def build_potion_types(dungeons, quest_monsters):
    types = set()
    for d in dungeons:
        for bucket in (d["potions"], d["treasureRoomPotions"]):
            for lst in bucket.values():
                types.update(p["type"] for p in lst)
    for e in quest_monsters:
        for lst in e["potions"].values():
            types.update(p["type"] for p in lst)
    return sorted(types)


def build(out_dir="api",
          dungeons_path="data/dungeon_potions.json",
          quest_monsters_path="data/quest_monster_potions.json",
          equipment_path="data/equipment.json"):
    dungeons = build_dungeons(dungeons_path, out_dir)
    quest_monsters = build_quest_monsters(quest_monsters_path, out_dir)
    equipment = build_equipment(equipment_path, out_dir)
    potion_types = build_potion_types(dungeons, quest_monsters)
    write_json(f"{out_dir}/potion-types.json", potion_types)

    manifest = {
        "apiVersion": API_VERSION,
        "generatedAt": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "https://www.realmeye.com/wiki",
        "resources": {
            "dungeons": {"list": "dungeons.json", "item": "dungeons/{slug}.json", "count": len(dungeons)},
            "questMonsters": {"list": "quest-monsters.json", "item": "quest-monsters/{slug}.json",
                               "count": len(quest_monsters)},
            "equipment": {"list": "equipment.json", "item": "equipment/{slug}.json", "count": len(equipment)},
            "potionTypes": {"list": "potion-types.json", "count": len(potion_types)},
        },
    }
    write_json(f"{out_dir}/index.json", manifest)

    print(f"Wrote api/ : {len(dungeons)} dungeons, {len(quest_monsters)} quest monsters, "
          f"{len(equipment)} equipment items, {len(potion_types)} potion types", file=sys.stderr)
    return manifest


if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else "api")
