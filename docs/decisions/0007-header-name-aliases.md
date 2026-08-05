# 0007 — Aliasing category-page header text that varies by family

## Context

Comparing Spirit Dagger against a T12 dagger in Equipment Compare showed
two things twice: a "Rate of Fire" row appeared both in the DPS section
and again from the generic column rendering, and Spirit Dagger's Shots/
Range showed as `Shots(Arc Gap)`/`Range(True Range)` rows separate from
the T12 dagger's plain `Shots`/`Range` rows (one side always blank on
each), instead of one shared row per field.

The second issue is a different root cause than
[[0006-duplicate-range-rows]]: that ADR covers the same field stored
top-level on one item and embedded in the Damage cell on another. Here
both are top-level *columns*, just under different key strings — the
Daggers and Dual Blades category pages literally use `<th>Shots(Arc
Gap)</th>` and `<th>Range(True Range)</th>` where every other weapon
category just uses `Shots`/`Range`. `normalize_collision_labels()`
(0006) can't catch this: it only reconciles a label that's top-level on
one item and embedded on another, not two different top-level label
strings for the same concept.

## Decision

- `parse_item_tables()` now runs each parsed `<th>` header through a
  `HEADER_ALIASES` dict (`equipment_scraper.py`) before using it as a
  column key: `"Shots(Arc Gap)"` → `"Shots"`, `"Range(True Range)"` →
  `"Range"`. The qualifier isn't lost — the cell *values* for those
  columns already carry it inline when relevant (e.g. `"2 (arc gap:
  14°)"`, `"5.6 tiles (true range: 2.84 tiles)"`), so renaming just the
  header key doesn't drop information, and this also means
  `enrich_thin_weapons()` ([[0005-thin-category-page-weapons]]) correctly
  recognizes these items already have Shots data and skips the redundant
  per-item fetch it would otherwise make.
- `renderEqCompare()` in `build_html.py` now skips a `Rate of Fire` (or
  `Bullet N Rate of Fire`) row from the generic per-column rendering
  whenever the DPS section above it is already showing (i.e. both
  compared items are weapons with a computed DPS profile) — that section
  already displays a combined `rofDisplay` for the same information, so
  showing it again as a raw segment was always redundant, not just for
  daggers. `segmentRows()` takes an optional `skipLabels` set for this.

## Consequences

- Comparing any dagger or dual-blade against a weapon from another
  family (or another dagger) no longer produces disconnected `Shots(Arc
  Gap)`/`Shots` or `Range(True Range)`/`Range` row pairs.
- Any weapon-vs-weapon comparison where DPS is shown no longer repeats
  the Rate of Fire row.
- `HEADER_ALIASES` is a small hardcoded map rather than a fuzzy-matching
  scheme, since the known cases are an exact, closed set (2 entries, both
  confirmed by re-fetching the daggers/dual-blades category pages) — if
  RealmEye introduces another oddly-named header for a common field,
  it'll need a new entry here, same as any other wiki-layout-quirk fix in
  this codebase.
