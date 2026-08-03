# RotMG Toolkit API

A static, read-only JSON API scraped from the [RealmEye wiki](https://www.realmeye.com/wiki/realm-of-the-mad-god).
No server, no database — every file here is a plain JSON file, regenerated
from scratch by [`build_api.py`](../build_api.py) whenever the underlying
data is re-scraped. Fetch whatever you need directly, e.g.:

```
curl https://<your-pages-domain>/api/dungeons/woodland-labyrinth.json
```

Or from JS in a browser/Node:

```js
const res = await fetch('https://<your-pages-domain>/api/equipment/indomptable.json');
const item = await res.json();
```

## Start here

`GET /api/index.json` — a manifest listing every resource below, its list
endpoint, its per-item endpoint template, and current item counts. Fetch
this first if you're building something generic; it's the only endpoint
whose shape is a contract you should rely on staying stable across
re-scrapes (item counts and `generatedAt` will change, the field names
won't).

## Resources

Each resource has a **list** endpoint (one big JSON array, everything) and
an **item** endpoint (`{slug}` = the last segment of the item's RealmEye
wiki URL, e.g. `/wiki/woodland-labyrinth` → `woodland-labyrinth`).

### Dungeons — `dungeons.json`, `dungeons/{slug}.json`

What potions each dungeon can drop, and whether they're guaranteed.

```jsonc
{
  "slug": "woodland-labyrinth",
  "name": "Woodland Labyrinth",
  "wikiUrl": "https://www.realmeye.com/wiki/woodland-labyrinth",
  "icon": "https://www.realmeye.com/s/a/img/wiki/i/jyKYlZg.gif",
  "category": "Realm Dungeons",       // matches RealmEye's own grouping on /wiki/dungeons
  "difficulty": 5.5,                  // 0-10, steps of 0.5; null if not listed
  "hasData": true,                    // false for non-combat pages (Chess, Admin Arena, ...)
  "error": null,                      // reason, when hasData is false
  "potions": {
    "guaranteed": [ /* potion entries, see below */ ],
    "possible": [ /* can drop, but not guaranteed */ ]
  },
  "treasureRoomPotions": {
    "guaranteed": [ /* ... */ ],
    "possible": [ /* ... */ ]
  }
}
```

A **potion entry**:

```jsonc
{
  "name": "Greater Potion of Vitality",
  "type": "Vitality",                 // normalized: "Greater "/"(SB)" stripped, "Health Potion"->"Life", "Magic Potion"->"Mana"
  "icon": "https://www.realmeye.com/s/a/img/wiki/i/sYB43YR.png",
  "guaranteedLabel": "G - 2",          // the wiki's own guarantee condition text, null if not guaranteed
  "source": {                          // the specific enemy whose own Drops table this came from
    "name": "Murderous Megamoth",
    "wikiUrl": "https://www.realmeye.com/wiki/murderous-megamoth",
    "icon": "https://www.realmeye.com/s/a/img/wiki/i/NM0J5Kq.png"
  }
}
```

`guaranteed` means that specific enemy's own Drops table marks the potion
with RealmEye's "G" marker. `possible` covers everything else the potion
can drop from (including "Various Enemies" spawns with no guarantee at
all). A potion can legitimately appear in both `dungeons[].potions` and
`dungeons[].treasureRoomPotions` with different guarantee status in each,
if a regular boss and the treasure-room boss both drop it but only one
guarantees it.

Only "stat" potions are included — Health Potion, Magic Potion, Loot Drop
Potion, Loot Tier Potion, and Potion of Max Level are filtered out (not
useful for stat-farming). Dungeons/enemies left with zero potions after
that filter aren't included in the dataset at all.

Dungeons without a `hasData: true` still get an entry (e.g. `chess`,
`admin-arena`) so you can tell "no drops here" apart from "not scraped".

### Quest monsters — `quest-monsters.json`, `quest-monsters/{slug}.json`

Same potion shape as dungeons, but for open-world bosses not tied to any
dungeon — RealmEye's [Setpiece Bosses and Heroes of Oryx](https://www.realmeye.com/wiki/quest-monsters#setpiece)
and [Encounters](https://www.realmeye.com/wiki/quest-monsters#event).

```jsonc
{
  "slug": "murderous-megamoth",
  "name": "Murderous Megamoth",
  "wikiUrl": "https://www.realmeye.com/wiki/...",
  "icon": "https://www.realmeye.com/s/a/img/wiki/i/...",
  "group": "setpiece",                 // "setpiece" | "encounter"
  "potions": { "guaranteed": [...], "possible": [...] }
}
```

### Equipment — `equipment.json`, `equipment/{slug}.json`

Weapons, ability items, and armor (**rings are not included** — see
[`docs/decisions/0002-rings-excluded-from-equipment-scrape.md`](../docs/decisions/0002-rings-excluded-from-equipment-scrape.md)
in the main repo for why).

```jsonc
{
  "slug": "indomptable",
  "name": "Indomptable",
  "wikiUrl": "https://www.realmeye.com/wiki/indomptable",
  "icon": "https://www.realmeye.com/s/a/img/wiki/i/F1N1mS0.png",
  "category": "Weapon",                // "Weapon" | "Ability" | "Armor"
  "categorySlug": "swords",            // the RealmEye category page it came from
  "family": "Set Tiered Swords",       // the subsection heading on that page
  "tier": "ST",                        // a tier number as a string, or "UT"/"ST"
  "soulbound": true,
  "classes": ["Warrior", "Knight", "Paladin"],  // exact equip-class set; see note below
  "stats": { "ATT": 5 },               // parsed {ATT,DEF,SPD,DEX,VIT,WIS,HP,MP: number}, only keys present on the item
  "columns": {
    "Damage (Average)": [
      { "label": "Damage (Average)", "value": "550-600 (575)" },
      { "label": "Projectile Speed", "value": "8" },
      { "label": "Piercing", "value": "Shots hit multiple targets" },
      { "label": "Rate of Fire", "value": "33%" }
    ],
    "Shots": [ { "label": "Shots", "value": "1" } ],
    "...": "one array entry per distinct fact packed into that RealmEye table cell"
  },
  "effects": ["Piercing"],             // effect names found anywhere in columns
  "effectDescriptions": { "Piercing": "Shots hit multiple targets" }
}
```

`columns` holds *every* stat/fact column from the item's row on its
RealmEye category page, split into one `{label, value}` entry per distinct
fact (a cell like `"550-600 (575) | Projectile Speed: 8 | [Piercing]
Shots hit multiple targets | Rate of Fire: 33%"` becomes 4 entries). The
label is either the sub-fact's own name (`Projectile Speed`, `Rate of
Fire`, an effect name) or, for the one unlabeled bit (usually the primary
damage range), the column header itself. Column names vary by item
category since they mirror RealmEye's own tables verbatim (weapons get
`Damage (Average)`/`Shots`/`Range`/`Projectile`, armor gets
`ATT`/`DEF`/...— already duplicated into `stats` as numbers —, abilities
get `Cost`/`Stat Bonus`/`Effect(s)`, etc.) — there's no fixed schema
across categories, iterate the object.

**"Same type" for comparing two items** = identical `classes` array
(order-independent). This is deliberately *not* `category`/`categorySlug`
— e.g. Bows and Longbows are both `["Archer", "Huntress", "Bard"]` and are
considered the same type even though they're different weapon lines,
because anyone equippable by exactly that class set can use either.
`classes` is read once from each RealmEye category page's intro text and
applied to every item on that page — a handful of Set-Tier items are
actually restricted to a single class within a multi-class family even
though the page covers several classes; see
[`docs/decisions/0001-headings-without-id-attribute.md`](../docs/decisions/0001-headings-without-id-attribute.md)-adjacent
notes in `docs/ARCHITECTURE.md` for the full caveat list.

DPS is *not* precomputed here since it depends on the consuming
character's live ATT/DEX — see `docs/ARCHITECTURE.md` in the main repo
for the exact formulas (verified against RealmEye's own worked examples)
if you want to compute it yourself from `columns`/`stats`.

### Potion types — `potion-types.json`

A flat sorted array of every normalized potion `type` string that appears
anywhere in `dungeons.json` or `quest-monsters.json` (e.g. `["Attack",
"Defense", ..., "Vitality"]`). Handy for building a type filter without
having to scan every dungeon yourself.

## Stability / versioning

`index.json`'s `apiVersion` bumps on any breaking field rename or removal.
Nothing here is guaranteed to be byte-stable across scrapes (RealmEye's
own data changes — new items, balance patches, tier reworks), but the
*shape* described above is the contract.

## CORS

Served as plain static files via GitHub Pages, which serves all assets
with permissive CORS by default — cross-origin `fetch()` from another
site should work without extra configuration, but isn't something GitHub
guarantees contractually, so don't build anything that breaks badly if it
ever doesn't.

## Regenerating

This whole directory is generated, never hand-edited:

```
python3 build_api.py            # reads data/*.json, writes api/
```

See `docs/ARCHITECTURE.md` in the repo root for how `data/*.json` itself
gets (re-)scraped.
