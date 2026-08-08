# 0008 — Classify open-world potion drops by biome, not Setpiece/Encounter

## Context

The "Where to Find Stat Potions" page had two tabs: Dungeons, and
"Setpiece Bosses / Encounters" (`data/quest_monster_potions.json`,
scraped from `/wiki/quest-monsters`'s two sections). That split answers
"what kind of enemy is this" but not the question a player farming
potions actually has: "where in the open-world Realm do I go to find
this potion". It also silently excluded regular (non-boss, non-setpiece)
open-world enemies entirely — only "leaders" listed in a `Leader(s)`
table column on `/wiki/quest-monsters` were scraped, even though regular
enemies can drop stat potions too (confirmed once biome pages were
scraped: e.g. Carboniferous's own regular enemies each drop 2-3 potion
types).

RealmEye's `/wiki/the-realm` describes the Realm as being made of
**biomes** (Rookie/Adept/Veteran/Seasonal tiers), and each biome's own
wiki page (e.g. `/wiki/carboniferous`) lists **every** enemy that spawns
there — Regular Enemies, Heroes of Oryx (+ Minions on some biomes),
Encounters, Beacon Guardian, occasionally NPCs — under one `<h2>Enemies</h2>`
(or `<h2>Monsters</h2>` on a few pages) block, structurally identical
across all 23 implemented biomes (Low Desert is listed on `/wiki/the-realm`
but has no link to its own page — not implemented in-game yet — and is
skipped automatically since its name isn't wrapped in `<b><a href=...>`
like every implemented biome's is).

## Decision

- Replaced `data/quest_monster_potions.json` (`{setpiece: [...], encounters: [...]}`)
  with `data/biome_potions.json`: one entry per biome (`name`, `href`,
  `icon`, `tier`, `groups`), where `groups` maps each biome-page
  subsection title (`Regular Enemies`, `Heroes of Oryx`, `Heroes of Oryx
  Minions`, `Encounters`, `Beacon Guardian`, ...) to the enemies in it
  that drop at least one stat potion.
- `scraper.py`: `get_biome_list()` reads `/wiki/the-realm`'s four tier
  tables; `scrape_biome()` slices each biome page's Enemies/Monsters `<h2>`
  block, splits it by h3/h4 subheadings (content before the first
  subheading — some biomes list their base monster grid with no
  subheading at all — is labelled `Regular Enemies`), and for every
  enemy found calls the *existing* `get_enemy_potion_drops()` (unchanged
  — it was already how quest-monster leaders were scraped: read that
  enemy's own "Drops" table directly, no need to cross-reference a
  biome-level "Drops of Interest" table, which has an inconsistent
  format anyway — seasonal biomes like Eternal Frost use a completely
  different loot-bag layout for that table that has nothing to do with
  potions).
- Deleted `get_quest_monster_groups()` / `scrape_quest_monster_group()` /
  `run_quest_monsters()` and the `quest-monsters` API resource
  (`api/quest-monsters.json`, `api/quest-monsters/*.json`) entirely
  rather than keeping both — bumped `API_VERSION` to `"2"` for the
  removed resource. `build_html.py`'s "Setpiece Bosses / Encounters" tab
  became "Open-World Biomes", grouped by tier the same way dungeons are
  grouped by category; `render_card()` gained an optional `search_name`
  override so a biome card's search-by-text still matches its enemies'
  names, not just the biome's own name (dungeon cards never needed this
  since their boss names were never searchable either).

## Consequences

- Every open-world enemy that can drop a stat potion is now covered, not
  just setpiece/encounter leaders — regular biome enemies are new
  coverage this scrape didn't have before.
- Rookie biomes end up contributing nothing (empty `groups`, or a `1`-
  or `2`-enemy dungeon-portal-only page like Nature Ruins) since they're
  meant for leveling, not potion farming — this matches `/wiki/the-realm`'s
  own description and isn't a scraping gap; `build_html.py` already
  omits any card with zero potions (`render_card` returns `None`), so
  those biomes simply don't produce a card.
- Scrape cost grew from ~150 quest-monster leader fetches to ~300+
  individual enemy fetches across 23 biome pages (~3-4 min vs ~1-2 min),
  but most enemies overlap with ones already cached from dungeon
  scraping or a previous biome run, so re-runs are cheap.
