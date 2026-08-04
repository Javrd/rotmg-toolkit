# 0006 — Consolidating fields stored two different ways

## Context

A user comparing two Wands in Equipment Compare saw two separate "Range"
rows instead of one, with one side blank in each. Cause: some Wand
category-page rows have their own dedicated `Range` `<th>` column
(Crystal Wand, Sprite Wand, and every other Untiered/Set-Tiered/Limited
Edition wand), while the "Tiered" wands backfilled by
[[0005-thin-category-page-weapons]]' `enrich_thin_weapons()` stored Range
as a segment embedded inside the `Damage (Average)` cell instead. Since
`renderEqCompare()` renders one row per distinct label found across
*either* item's segments for a given column, and these two items didn't
share the same column for that field, the UI produced two independent
rows that never lined up.

Auditing every Weapon/Ability/Armor item's columns for the same
top-level-vs-embedded split turned up two more, pre-existing and
unrelated to 0005's backfill: some Ability lines expose `Shots` as its
own column while a few Maces (e.g. "Mace of the Celestial Forest")
fold `Shots: 3-6` into the Damage cell instead, and `Life Steal` is a
column on some Maces but an embedded bit on "Mace of the Depths".

## Decision

- `enrich_thin_weapons()` now sets a single-group item's `Range` as its
  own top-level column (matching the majority convention: 357 items had
  it top-level vs. 190 embedded before this fix) instead of embedding it
  in `Damage (Average)`, mirroring how `Shots` was already handled.
- A new `normalize_collision_labels()`, run once across the full scraped
  item list in `run_all()` (after every category page and per-item
  enrichment fetch), finds any label used *both* as a top-level column
  and as an embedded (non-`Bullet N`-prefixed) Damage-cell segment
  anywhere in the dataset, and hoists every embedded occurrence to a
  top-level column. This is dataset-driven rather than a hardcoded field
  list, so it also catches collisions like `Shots`/`Life Steal` that
  don't come from `enrich_thin_weapons()` at all, and will keep catching
  new ones if RealmEye's category pages change layout again.
- `Bullet N`-prefixed segments (e.g. `Bullet 2 Range`) are left alone —
  a top-level column can only hold one scalar value, so per-bullet
  variants have nowhere else to go and don't collide with anything
  anyway (no naturally-occurring item exposes per-bullet fields as
  top-level columns).

## Consequences

- Comparing any two items no longer produces a duplicate row for the
  same conceptual field just because one item's category page happened
  to lay it out differently than another's.
- `normalize_collision_labels()` runs after `enrich_thin_weapons()` and
  `enrich_multi_bullet_shots()` (both per-category), so it sees the
  final, fully-enriched column shape before deciding what counts as a
  collision — a field only counts if it's *actually* inconsistent across
  the shipped dataset, not a transient mid-scrape state.
