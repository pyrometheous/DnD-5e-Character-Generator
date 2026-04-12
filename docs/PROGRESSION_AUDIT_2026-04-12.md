# Progression Audit 2026-04-12

## Scope

Audit target: progression from fresh level 1 through level 20 for all core classes present in `tinys_srd`.

Classes audited:

- barbarian
- bard
- cleric
- druid
- fighter
- monk
- paladin
- ranger
- rogue
- sorcerer
- warlock
- wizard

## PHB Alignment Baseline

PHB is treated as authoritative, with `tinys_srd` used first and config fallback used when `tinys_srd` data is missing or incomplete.

Validated PHB-derived supplementation in config:

- `spellcasting.slot_fallbacks`: full 1-20 spell-slot fallback tables by class.
- `subclass_fallbacks`: base PHB subclass milestone scaffolding for all classes represented in `tinys_srd`.

## Validation Method

1. Subclass coverage check:
- Verified every class in `Classes.entries` has both:
  - `subclass_selection[class]`
  - `subclass_fallbacks[class]`

2. Full-level progression execution check:
- Executed progression for each class at each level 1..20 (240 builds total).
- For each build, asserted no progression exceptions.

3. Class-specific variable accounting check:
- For each class/level, compared `Levels.<class>_<level>.class_specific` to runtime tracked state:
  - `character.class_specific_by_level[level]`
- Result required exact dict equality.

4. Feature-choice resolution check:
- Built required choice-surface set from level features with:
  - `feature_specific.subfeature_options`
  - explicit `eldritch-invocations`
- Verified each required choice surface produced runtime choice records in:
  - `character.class_feature_choices`

## Results

Status: PASS

Measured outcomes:

- Subclass config coverage gaps: 0
- Progression smoke checks: 240 passed / 240 total
- Class-specific variable mismatches: 0
- Missing required choice-resolution records: 0 classes

## What Is Accounted For Per Level

For each level-up step, system now accounts for:

1. Class feature list and milestone events from `Levels`.
2. Subclass selection and subclass milestone fallback features.
3. Choice-bearing class features (fighting styles, invocations, metamagic, pact boon, and configured subclass choices).
4. ASI vs feat decisions at ASI levels.
5. Spell progression (known, prepared, replacement, mystic arcanum) and PHB slot fallback if needed.
6. All class-specific progression variables (`class_specific`) via tracked runtime state.

## Remaining Intentional Boundaries

- Some PHB features are non-numeric/situational and therefore represented as annotations/guidance rather than hard numeric sheet fields.
- This audit validates progression accounting and data coverage, not gameplay simulation of every activated feature effect.
