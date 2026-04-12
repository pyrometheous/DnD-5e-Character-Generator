# Config Guide

This folder uses strict JSON files. JSON does not support comments (`//` or `/* ... */`).
To keep files self-documented without breaking parsers, each config file includes a top-level `_meta` section.

## General Rules
- Keep all executable settings in their existing keys.
- Keep documentation in `_meta` only.
- Avoid renaming core keys unless code is updated to match.
- Class keys are lowercase in most configs.
- Species keys follow each config's existing conventions.

## Standard `_meta` Schema
All config files should use the same `_meta` shape:
- `version`: schema/info version for that config
- `owner`: team/project owner label
- `last_updated`: ISO date string (`YYYY-MM-DD`)
- `purpose`: one-line summary of what the file controls
- `examples`: short practical tuning examples
- `notes`: key semantics and guardrails

## Validation Script
Run this from project root to validate all JSON config `_meta` blocks:

```bash
python scripts/validate_config_meta.py
```

Optional custom directory:

```bash
python scripts/validate_config_meta.py --config-dir config
```

## Files

### ability_score_weights.json
Controls ASI target selection and aggressive recovery behavior.
- `global`: scoring multipliers and floor-recovery controls
- `class_priorities`: primary/secondary abilities per class
- `species_modifiers`: species-based ability weighting

### feats_rules.json
Controls feat-vs-ASI probability and feat effects.
- `selection`: global feat selection multipliers
- `feats`: feat definitions, prerequisites, and grants

### spellcasting_notes.json
Controls spellcaster guidance text rendered into page 2.
- `global_rules`: global inclusion toggles
- `class_rules`: per-class formula and inclusion logic
- `class_notes`, `feat_notes`, `species_notes`: guidance lines
- `feat_note_rules`: feat matching mode and aliases
- `templates`: dynamic text templates with placeholders

### progression_rules.json
Controls the end-to-end level-up pipeline and weighted class feature choices.
- `subclass_selection`: weighted subclass picks by class
- `feature_selection`: weighted option picks and mechanical grants for exposed class features
- `subclass_fallbacks`: config-driven subclass feature hooks when tinys_srd lacks inline milestone data
- `spellcasting.slot_fallbacks`: PHB slot tables by class/level used when tinys_srd slot data is missing or incomplete
- `spellcasting.class_strategies`: heuristics for learned spells, replacements, preparation, and loadout balance

### spellbook_rules.json
Controls spellbook generation and capability-based redundancy filtering.
- `prepared_spellcasting_abilities`
- `species_capabilities`, `trait_capability_map`, `feature_capability_map`
- `level_based_capabilities`
- `spell_redundancy_rules`

### party_balance_rules.json
Controls class/role composition logic for balanced parties.
- `party_size_roles`, `overflow_role_cycle`
- `role_definitions`, `capability_requirements`
- `species_preferences`, `default_species_pool`, `class_synergy`
