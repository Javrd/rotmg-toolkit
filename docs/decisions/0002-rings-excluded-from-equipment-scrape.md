# 0002 — Rings excluded from the equipment scrape (v1)

## Context

`equipment_scraper.py` scrapes 34 RealmEye category pages (12 weapon
lines, 19 ability lines, 3 armor lines) using one generic parser: find
each `<table class="table table-striped">` with a "Name" header, then read
one item per `<tr>`, matching `<td>` cells positionally to `<th>` headers.
Every one of those 34 pages follows this same one-row-per-item shape.

`/wiki/rings` does not. Inspecting it turned up at least four different,
mutually-inconsistent table layouts on that single page:

1. The basic single-stat tiered rings (T0-T7) are packed 2-6 items into a
   single visual "row" via a 3-physical-`<tr>` grid (name-row, a
   mid-table `<tr>` of bare `<th>` sub-labels ATT/DEF/SPD/DEX/VIT/WIS,
   then a stat-row) — nothing like the list format everywhere else.
2. An "Untiered Rings" section (`<h2 id="untiered">`, not even the `<h4>`
   the other sub-sections use) has a `<th colspan="2">Name</th>` header
   but the body splits that into **two** separate `<td>` elements (one
   `align="right"` text-link, one icon-link) — a header/body tag-count
   mismatch that silently corrupts positional column mapping.
3. A T0 singleton table (Ring of Minor Defense) uses yet another header
   set (`Defense`/`Stat Bonus`/`XP Bonus`/`Feed Power`) with no `Name`
   column at all.

A first attempt at a dedicated grid-parser for shape (1) also
mis-consumed rows from shape (2) because both live under h4/h2 headings
that can't be told apart by heading text alone, and produced garbage
`stats` (e.g. treating a ring's own icon `alt` text as a stat value).

## Decision

Drop `rings` from `CATEGORY_SLUGS` entirely for v1. Ship correct data for
weapons/abilities/armor (1316 items) rather than incorrect data for
everything. `extract_classes()` and `parse_item_tables()` are otherwise
generic and don't need to change if rings are tackled later.

## Consequences

- The equipment comparison tool has no ring entries yet.
- If rings are wanted later, they need their own parser per layout
  (grid / untiered-split-name / T0-singleton), not a reuse of
  `parse_item_tables`. Re-fetch `/wiki/rings` fresh when doing this — the
  page is large (~270KB) and worth inspecting section-by-section rather
  than assuming the shapes above are exhaustive.
