# 0005 — Backfilling weapons whose category-page row omits most fields

## Context

A user comparing basic Tiered bows/wands/daggers/etc. in Equipment
Compare noticed several fields simply weren't there: no Piercing effect,
no Shots count, no Projectile Speed. Checking the source confirmed it's
not a parsing bug — RealmEye's category-listing pages (e.g. `/wiki/bows`'
"Tiered Bows" table) genuinely only expose `Name`/`Damage (Average)`/`XP
Bonus`/`Feed Power`/`Projectile` for these basic T0-T13 weapon lines. No
`Shots`, `Rate of Fire`, or `Effect(s)` column exists on the category
page at all for ~170 weapons across every weapon family's "Tiered"
sub-table (Daggers, Bows, Staves, Wands, Swords, Katanas, Longbows,
Dual Blades, Spellblades, Flails, Tachis) plus a chunk of Untiered/
Limited Edition/Set Tiered daggers. `computeDps()`'s fallback silently
defaulted to 1 shot at 100% RoF for all of them, and Equipment Compare's
effects section never showed e.g. Shortbow's Piercing at all.

The item's own page has the missing data (one small table per projectile
definition, each with `Shots`/`Damage`/`Projectile Speed`/`Range`/
`Rate of Fire`(if not 100%)/`Effect(s)`), the same shape
[[0003-multi-bullet-dps]] already fetches for multi-bullet weapons — so
the fix is to fetch it for these "thin" weapons too, generalizing that
existing per-item fetch into `fetch_projectile_groups()`.

Two additional wiki page-layout quirks turned up while building this:

1. **Malformed `<tr>` rows break naive `<th>...</th><td>...</td>` row
   regexes.** Every item page's "Tier" row is actually `<tr><th>Tier</th>
   <th class="...">VALUE</th></tr>` — two `<th>`s, no `<td>` at all. A
   lazy `.*?` capture group for the row label doesn't stop at the first
   `</th>`when the rest of the pattern fails to match there; it keeps
   expanding across `</tr>` and into the *next* row looking for a `<td>`
   that satisfies the pattern, corrupting the label of the row after it
   (observed: Steel Dagger's captured "Shots" label came back as the
   entire blob `"Tier</th>\n<th class=\"\">0</th>\n\n\n</tr><tr>\n<th>
   Shots"`). This silently produced 0 parsed groups for ~139 of the ~170
   affected weapons on the first attempt at this fix, before it was
   caught by re-checking coverage numbers after the run rather than
   trusting the "no errors" exit status.
2. **A weapon's Main/Side (or similarly-named) damage groups don't
   correspond 1:1 with the category page's own labels for those groups**
   (positionally they do, by name they often don't — Shortbow's category
   cell says "Main"/"Side (2)", the item page's tables are titled "Large
   Standard Arrow"/"Small T0 Arrow"). Rebuilding by *position* into the
   `Bullet N` shape already avoids needing them to match by name.

## Decision

- `fetch_projectile_groups(href)` in `equipment_scraper.py` fetches an
  item's own page and returns one dict per projectile-definition table
  (`Shots`, `Damage`, `Rate of Fire`, `Projectile Speed`, `Range`,
  `_effects`, `_effect_descriptions`), used by both
  `enrich_multi_bullet_shots()` (0003) and the new
  `enrich_thin_weapons()`.
- `enrich_thin_weapons()` runs for any Weapon with no `Shots` column, no
  `Fire Rate` column, and no existing `Bullet N` grouping. It rebuilds
  `columns['Damage (Average)']` from scratch: a single group becomes a
  normal `Damage (Average)`/`Rate of Fire`/`Projectile Speed`/`Range` set
  plus a top-level `Shots` column (matching every other single-shot
  weapon's shape); 2+ groups become `Bullet 1`/`Bullet 2`/... by
  position, reusing the exact shape [[0003-multi-bullet-dps]]'s DPS
  reader already understands. Effects and their descriptions are merged
  into the item's existing `effects`/`effect_descriptions`.
- The row regex requires the label capture to stop at the next `<` (`
  [^<]*` instead of `.*?`) so a malformed two-`<th>` row fails to match
  cleanly instead of bleeding into the following row.
- `parseDamageProfile()` in `build_html.py`: a `Bullet N` group with no
  listed Rate of Fire now defaults to 100% (see the note atop 0003)
  instead of the old "100% minus the other groups' RoF" — matching how
  Shortbow's Main and Side arrows both always fire together.

## Consequences

- 556 of 557 weapons now carry real Shots/Rate of Fire data (up from
  ~380); the one holdout, Blade of Fates, is the known [[0003-multi-bullet-dps]]
  fail-safe skip (its own page mixes a combined summary Shots row with
  its two real per-bullet tables, so the count doesn't match cleanly and
  it's left alone rather than guessed at).
- Arcane Rapier's DPS estimate changed from 2784 to 3240 (ATT/DEX 75) as
  a result of the missing-RoF model correction — its "Arcane Blade" base
  swing now correctly assumed to fire on 100% of attacks rather than 80%.
- 38 weapons still compute no DPS at all — bespoke multi-phase attacks
  with custom, non-generic label pairs the parser doesn't recognize (e.g.
  Damnation's "Shot 1"/"Shots 2-3", Shaman's Staff's "Wisp"/"Bolt",
  Fiery Katana's "Has two attacks, see here"). These need one-off
  handling per weapon, not a generalization of the paths above, and are
  left as a known gap rather than guessed at.
- equipment_scraper.py's full run now takes ~2.5 minutes instead of a
  few seconds (fetches ~170 additional item pages beyond the 34 category
  pages), but every fetch is disk-cached via `fetch()` like everything
  else, so re-running without deleting `data/cache/` is still fast.
