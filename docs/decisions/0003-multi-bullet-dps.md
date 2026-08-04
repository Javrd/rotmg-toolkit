# 0003 — DPS calculation for multi-bullet weapons

> **Revised by [[0005-thin-category-page-weapons]]:** the "leftover
> probability" model below for a bullet with no listed Rate of Fire was a
> guess that turned out wrong. Fetching more item pages (Shortbow's Main/
> Side arrows both omit Rate of Fire and both simply always fire) showed
> the wiki's actual convention is simpler: no listed RoF means the bullet
> fires on 100% of attacks, not "whatever's left over from the others."
> Kept below for the record of how the multi-bullet grouping itself works
> (still correct) — only the missing-RoF default changed.

## Context

The Equipment Compare DPS estimate (`computeDps()` in `build_html.py`)
originally read only the first "Bullet 1" damage segment for weapons whose
category-page cell lists more than one bullet group (e.g. Heartsteel
Claymore: `Bullet 1: 325-375 (350)` at 60% Rate of Fire, `Bullet 2:
150-200 (175)` at 20%), then multiplied that single average by the
weapon's *combined* `Shots` total (3, i.e. 1 shot from bullet 1 + 2 shots
from bullet 2) at bullet 1's Rate of Fire. That overcounts badly — it
treats all 3 shots as dealing bullet 1's higher damage at bullet 1's
attack speed, ignoring bullet 2 entirely.

Fetching each such weapon's own item page (not just the category listing)
shows the real per-bullet structure: one small table per projectile
definition, each with its own `Shots`/`Damage`/`Rate of Fire` row. For
Arcane Rapier, the "Arcane Lunge" (bullet 2) table's Notes explain the
mechanic directly: an Awakened enchant makes "the Rapier's Lunge trigger
every 3 shots instead of 5" — i.e. bullet 2's 20% Rate of Fire means it
replaces the normal swing on 1 out of every 5 attacks, not that it fires
as an independent, simultaneous attack-speed stream. This generalizes:
each bullet group's Rate of Fire is the probability that a given attack
(at the weapon's shared base attack speed) deals that bullet's damage
instead of the default swing.

Category pages don't reliably expose the per-bullet shot count needed to
weight each group correctly — some categories collapse it to one combined
total (Heartsteel Claymore's `Shots: 3`), others already split it
correctly per bullet (Arcane Rapier's `Shots` cell is `1<br><br>1`), and
at least one (`Blade of Fates`, daggers) mixes a combined summary `Shots`
row into the item's main info table in addition to its two real per-bullet
tables, making a naive count unreliable.

## Decision

- `equipment_scraper.py`'s `enrich_multi_bullet_shots()` fetches the
  item's own page for any Weapon with 2+ `Bullet N` damage groups, and
  adds a `Bullet N Shots` segment per group parsed from that page's
  per-projectile tables — but only when the number of `Shots`-bearing
  tables found matches the number of bullet groups exactly. A mismatch
  (e.g. Blade of Fates' extra summary row) means the page doesn't follow
  the expected layout, so it's skipped rather than risking a wrong count;
  that item's DPS falls back to 1 shot per bullet group.
- `computeDps()` in `build_html.py` sums each bullet group's own
  contribution — `avg * shots * DamageMultiplier * (baseAttacksPerSec *
  RoF/100)` — instead of reading only the first group. A group with no
  listed Rate of Fire (the default swing, e.g. Arcane Rapier's "Arcane
  Blade") gets whatever probability is left over from the other groups
  (100% minus their RoF).

## Consequences

- Multi-bullet weapon DPS is now a real weighted sum instead of reading
  one bullet's numbers as if they applied to every shot. Verified against
  Heartsteel Claymore (280 expected damage/attack from 0.6×350×1 +
  0.2×175×2, vs. the old calculation's 350×3 = 1050 — nearly 4x
  overcounted) and Arcane Rapier (RoF sums to exactly 100%: 80% base
  swing + 20% Lunge, matching the item page's own "every 5 shots"
  description).
- Items where the per-page layout doesn't match 1:1 with the category
  page's bullet count (currently just Blade of Fates) still assume 1 shot
  per bullet group — an improvement over the old single-bullet bug, but
  not exact. Fixing that would need a dedicated parser for daggers'
  layout, not a change to the generic multi-bullet path.
