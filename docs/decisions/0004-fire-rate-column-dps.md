# 0004 — DPS for weapons with a separate "Fire Rate" column

## Context

[[0003-multi-bullet-dps]] fixed DPS for weapons that pack multiple
"Bullet N" damage groups into the Damage cell itself (Heartsteel Claymore,
Arcane Rapier). That left a second, larger group of weapons unhandled:
~31 items (mostly Longbows, e.g. Anteros Longbow, Harpoon Longbow, Morning
Star of Harrowing Memories) whose category-page row has a *separate*
`Fire Rate` column instead, distinct in both name and shape from the
`Rate of Fire` sub-segment normal weapons carry inside their Damage cell.

`computeDps()`'s fallback path only ever looked for a segment literally
labeled `Rate of Fire`, so for these items it silently defaulted to 100%
and used the full `Shots` count at that rate — e.g. Morning Star of
Harrowing Memories (avg 95, 5 shots, individual fire rates `15%, 50%,
90%, 50%, 15%`) computed as `95 * 5 shots * 100% RoF` = 7600 DPS at
ATT/DEX 75, when the wiki's own per-shot rates give `95 * (15+50+90+50+
15)% = 95 * 220%` = 3344 DPS at the shared base attack speed — more than
double the real number, the same shape of bug as 0003 with a different
root cause.

Inspecting the `Fire Rate` column across all weapon categories that have
it turned up two shapes:

1. **Single shared avg + a comma-separated percentage list** (28 of 31
   items, e.g. the Morning Star above, Anteros Longbow): one `Damage
   (Average)` value applies to every shot in the burst, and `Fire Rate`
   holds one percentage per shot, positionally.
2. **Labeled groups mirrored across three columns** (Hama Yumi, Longbow
   of Spirits and Shadows): `Damage (Average)`, `Shots`, and `Fire Rate`
   each carry `Main`/`Side` labeled segments instead of a flat list —
   structurally the same idea as `Bullet N` groups, just named
   differently.

One item (Morning Square) doesn't cleanly fit either shape — its `Fire
Rate` column has 3 segments that each collapsed to the literal header
label `Fire Rate` (not real per-group labels) because it's actually 3
separate projectile definitions, each itself potentially multi-shot
(`"45%, 40%"` inside a single segment). Building a bespoke parser for one
item wasn't worth it here.

## Decision

`parseDamageProfile()` in `build_html.py` tries, in order:

1. The existing `Bullet N` grouping from 0003.
2. A labeled `Fire Rate` match (shape 2 above): for every non-generic
   label in the `Fire Rate` column, look up the same label in `Damage
   (Average)` and `Shots` to build a group.
3. A single `Fire Rate` segment holding a percentage list (shape 1
   above): pair each percentage with the item's one shared avg damage,
   1 shot per group.
4. The original single-group fallback (plain `Rate of Fire` sub-segment
   or 100%, plain `Shots` count) — now only reached by weapons that
   genuinely have neither a `Bullet N` nor a `Fire Rate` shape, which
   also happens to be where Morning Square lands (undercounts its real
   shot volume — a known gap, not a crash).

## Consequences

- The ~30 affected Longbow-family weapons now compute a real weighted-sum
  DPS instead of silently assuming 100% RoF on every shot.
- Morning Square's DPS is still an underestimate (1 of its ~5 real shots
  counted). Fixing it needs a dedicated parser for its nested
  projectile-definition layout, not a generalization of the paths above.
