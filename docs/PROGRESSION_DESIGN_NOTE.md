# Progression Design Note

## Goal

Character progression is PHB-aligned and deterministic while remaining practical with the data exposed by `tinys_srd`.

## Source of Truth Policy

Progression follows this precedence order:

1. PHB rules are the authority for expected behavior.
2. `tinys_srd` is used first when it exposes complete structured data for a rule.
3. Project config files supplement missing or incomplete `tinys_srd` data.

This keeps behavior correct to PHB intent while still benefiting from the SRD data model.

## Where Supplementation Happens

Primary progression logic is in `scripts/progression.py`.

Config supplementation points:

- `config/progression_rules.json`
  - `subclass_fallbacks`: subclass milestone hooks when subclass features are not exposed inline by `tinys_srd`.
  - `feature_selection`: weighted class feature option selection and mechanical grants.
  - `spellcasting.slot_fallbacks`: PHB spell slot table fallback by class and level.
  - `spellcasting.class_strategies`: spell choice heuristics (learned, replacement, prepared loadout).

- `config/spellbook_rules.json`
  - capability and redundancy filtering used during spell pool construction.

## Spell Slot Resolution Strategy

`_get_spell_slots` in `scripts/progression.py` resolves each slot level as follows:

1. Read `spell_slots_level_N` from `tinys_srd` level spellcasting data.
2. If missing or zero, use `spellcasting.slot_fallbacks[class][level]` from `config/progression_rules.json`.
3. Keep only positive slot counts.

This ensures PHB-correct slots remain available even if SRD slot fields are sparse.

## Progression Pipeline Order

Per level, progression runs in this order:

1. Class/subclass milestone handling.
2. Class feature choice resolution.
3. ASI or feat resolution.
4. Spell progression (learn, replace, prepare).
5. Derived/mechanical updates and exported profile refresh.

## Determinism

A seeded character RNG is used so weighted choices are reproducible for tests and debugging.

## Mechanical Coherence

Chosen progression options can update concrete sheet-impacting fields where the model supports it, such as:

- armor class bonus
- ranged attack bonus
- hp bonus per level
- proficiencies and skill proficiencies

Non-numeric or situational class features are preserved as explicit feature annotations and guidance notes.
