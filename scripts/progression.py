from __future__ import annotations

import json
import random
from pathlib import Path

from tinys_srd import Classes, Features, Levels, Spells, Subclasses

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "progression_rules.json"
SPELLBOOK_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "spellbook_rules.json"

SPELLCASTING_ABILITY = {
    'bard': 'charisma',
    'cleric': 'wisdom',
    'druid': 'wisdom',
    'paladin': 'charisma',
    'ranger': 'wisdom',
    'sorcerer': 'charisma',
    'warlock': 'charisma',
    'wizard': 'intelligence',
}

KNOWN_SPELL_CLASSES = {'bard', 'ranger', 'sorcerer', 'warlock'}
PREPARED_SPELL_CLASSES = {'cleric', 'druid', 'paladin'}
REPLACEMENT_CLASSES = {'bard', 'ranger', 'sorcerer', 'warlock'}
ALWAYS_PREPARED_SUBCLASS_CLASSES = {'cleric', 'paladin'}

DEFAULT_PROGRESS = {
    'built_to_level': 0,
    'cantrips': [],
    'known_spells': [],
    'always_prepared_spells': [],
    'prepared_spells': [],
    'prepared_formula': 'none',
    'spell_slots': {},
    'mystic_arcanum': {},
    'replacement_log': [],
    'decision_log': [],
    'spell_focus': {},
}


def load_progression_config(config_path: str | Path | None = None) -> dict:
    target_path = Path(config_path) if config_path else CONFIG_PATH
    with target_path.open('r', encoding='utf-8') as handle:
        return json.load(handle)


def load_spellbook_config(config_path: str | Path | None = None) -> dict:
    target_path = Path(config_path) if config_path else SPELLBOOK_CONFIG_PATH
    with target_path.open('r', encoding='utf-8') as handle:
        return json.load(handle)


def ensure_progression(
    character_obj,
    config: dict | None = None,
    spellbook_config: dict | None = None,
    rng=None,
):
    config = config or load_progression_config()
    spellbook_config = spellbook_config or load_spellbook_config()
    rng = rng or getattr(character_obj, 'rng', random)

    _ensure_progression_fields(character_obj)
    if character_obj.progression_built_to_level >= character_obj.level:
        return character_obj.spellcasting_profile

    for current_level in range(character_obj.progression_built_to_level + 1, character_obj.level + 1):
        _process_level(character_obj, current_level, config, spellbook_config, rng)

    character_obj.progression_built_to_level = character_obj.level
    _finalize_spellcasting_profile(character_obj, spellbook_config)
    return character_obj.spellcasting_profile


def export_spellbook(character_obj) -> dict | None:
    profile = getattr(character_obj, 'spellcasting_profile', None)
    if not profile:
        return None

    return {
        'name': character_obj.name,
        'class': character_obj.char_class,
        'level': character_obj.level,
        'subclass': character_obj.subclass,
        'ability': SPELLCASTING_ABILITY[character_obj.char_class],
        'cantrips': [_spell_to_dict(spell) for spell in profile['cantrips']],
        'spells_by_level': {
            level: [_spell_to_dict(spell) for spell in spells]
            for level, spells in sorted(profile['spells_by_level'].items())
        },
        'prepared_spells': {
            level: [_spell_to_dict(spell) for spell in spells]
            for level, spells in sorted(profile.get('prepared_by_level', {}).items())
        },
        'spell_slots': dict(profile['spell_slots']),
        'always_prepared': [_spell_to_dict(spell) for spell in profile['always_prepared_spells']],
        'mystic_arcanum': {
            level: _spell_to_dict(spell)
            for level, spell in sorted(profile['mystic_arcanum'].items())
        },
        'replacement_log': list(profile['replacement_log']),
        'decision_log': list(profile['decision_log']),
        'spell_focus': dict(profile['spell_focus']),
    }


def _ensure_progression_fields(character_obj):
    if not hasattr(character_obj, 'feature_annotations'):
        character_obj.feature_annotations = {}
    if not hasattr(character_obj, 'bonus_features_by_level'):
        character_obj.bonus_features_by_level = {}
    if not hasattr(character_obj, 'class_feature_choices'):
        character_obj.class_feature_choices = []
    if not hasattr(character_obj, 'progression_choices'):
        character_obj.progression_choices = []
    if not hasattr(character_obj, 'class_specific_by_level'):
        character_obj.class_specific_by_level = {}
    if not hasattr(character_obj, 'class_specific_current'):
        character_obj.class_specific_current = {}
    if not hasattr(character_obj, 'progression_built_to_level'):
        character_obj.progression_built_to_level = 0
    if not hasattr(character_obj, 'subclass'):
        character_obj.subclass = None
    if not hasattr(character_obj, 'subclass_index'):
        character_obj.subclass_index = None
    if not hasattr(character_obj, 'applied_subclass_feature_levels'):
        character_obj.applied_subclass_feature_levels = set()
    if not hasattr(character_obj, 'spellcasting_profile') or not character_obj.spellcasting_profile:
        character_obj.spellcasting_profile = {
            key: (value.copy() if isinstance(value, dict) else list(value) if isinstance(value, list) else value)
            for key, value in DEFAULT_PROGRESS.items()
        }


def _process_level(character_obj, current_level: int, config: dict, spellbook_config: dict, rng):
    level_data = getattr(Levels, f'{character_obj.char_class}_{current_level}')

    _record_class_specific_variables(character_obj, current_level, level_data)

    for feature in getattr(level_data, 'features', []):
        feature_index = feature.get('index', '')
        if feature['name'] == 'Ability Score Improvement':
            character_obj.apply_asi_level(current_level)
            continue

        if _is_subclass_feature(feature_index):
            _choose_subclass(character_obj, current_level, feature, config, rng)
            continue

        _resolve_feature_choice(character_obj, current_level, feature_index, feature['name'], config, rng)

    _resolve_class_specific_growth(character_obj, current_level, config, rng)
    _apply_subclass_level_features(character_obj, current_level, config, rng)
    _process_spellcasting_level(character_obj, current_level, spellbook_config, config, rng)


def _record_class_specific_variables(character_obj, current_level: int, level_data):
    class_specific = dict(getattr(level_data, 'class_specific', None) or {})
    character_obj.class_specific_by_level[current_level] = class_specific

    for key, value in class_specific.items():
        previous = character_obj.class_specific_current.get(key)
        character_obj.class_specific_current[key] = value
        if previous != value:
            character_obj.progression_choices.append({
                'type': 'class_specific',
                'level': current_level,
                'key': key,
                'value': value,
            })


def _resolve_class_specific_growth(character_obj, current_level: int, config: dict, rng):
    level_data = getattr(Levels, f'{character_obj.char_class}_{current_level}')
    class_specific = getattr(level_data, 'class_specific', None) or {}

    if character_obj.char_class == 'warlock':
        target = int(class_specific.get('invocations_known', 0) or 0)
        current = len([
            entry for entry in character_obj.class_feature_choices
            if entry.get('feature_index') == 'eldritch-invocations'
        ])
        if target > current:
            _resolve_feature_choice(
                character_obj,
                current_level,
                'eldritch-invocations',
                'Eldritch Invocations',
                config,
                rng,
                as_bonus_feature=current_level > 2,
            )

    if character_obj.char_class == 'sorcerer':
        target = int(class_specific.get('metamagic_known', 0) or 0)
        current = len([
            entry for entry in character_obj.class_feature_choices
            if entry.get('feature_index', '').startswith('metamagic-')
        ])
        if target > current:
            feature_index = 'metamagic-1'
            if current >= 2:
                feature_index = 'metamagic-2'
            if current >= 3:
                feature_index = 'metamagic-3'
            _resolve_feature_choice(
                character_obj,
                current_level,
                feature_index,
                'Metamagic',
                config,
                rng,
                as_bonus_feature=current_level > 3,
            )


def _is_subclass_feature(feature_index: str) -> bool:
    return feature_index in {
        'martial-archetype',
        'sacred-oath',
        'ranger-archetype',
        'otherworldly-patron',
        'sorcerous-origin',
        'divine-domain',
        'bard-college',
        'druid-circle',
        'monastic-tradition',
        'primal-path',
        'roguish-archetype',
        'arcane-tradition',
    }


def _choose_subclass(character_obj, current_level: int, feature: dict, config: dict, rng):
    if character_obj.subclass_index:
        return

    subclass_refs = list(getattr(getattr(Classes, character_obj.char_class), 'subclasses', []) or [])
    configured = config.get('subclass_selection', {}).get(character_obj.char_class, {})
    subclass_fallbacks = config.get('subclass_fallbacks', {}).get(character_obj.char_class, {})

    options = []
    for subclass_ref in subclass_refs:
        subclass_index = subclass_ref['index']
        options.append({
            'index': subclass_index,
            'name': subclass_fallbacks.get(subclass_index, {}).get('name', subclass_ref['name']),
            'weight': float(configured.get(subclass_index, 1.0)),
        })

    if not options:
        for subclass_index, subclass_data in subclass_fallbacks.items():
            options.append({
                'index': subclass_index,
                'name': subclass_data.get('name', subclass_index.replace('_', ' ').title()),
                'weight': float(configured.get(subclass_index, 1.0)),
            })

    selected = _weighted_choice(options, rng, unique_key='index')
    if not selected:
        return

    character_obj.subclass_index = selected['index']
    character_obj.subclass = selected['name']
    _annotate_feature(character_obj, current_level, feature.get('index', feature['name']), f"{feature['name']} ({selected['name']})")
    character_obj.progression_choices.append({
        'type': 'subclass',
        'level': current_level,
        'feature': feature['name'],
        'subclass_index': selected['index'],
        'subclass_name': selected['name'],
    })


def _apply_subclass_level_features(character_obj, current_level: int, config: dict, rng):
    if not character_obj.subclass_index:
        return
    level_key = str(current_level)
    applied_key = (character_obj.subclass_index, current_level)
    if applied_key in character_obj.applied_subclass_feature_levels:
        return

    subclass_data = config.get('subclass_fallbacks', {}).get(character_obj.char_class, {}).get(character_obj.subclass_index, {})
    for feature_index in subclass_data.get('choice_features_by_level', {}).get(level_key, []):
        feature_obj = _get_feature_object(feature_index)
        if feature_obj is None:
            continue
        _resolve_feature_choice(
            character_obj,
            current_level,
            getattr(feature_obj, 'index', feature_index).replace('_', '-'),
            getattr(feature_obj, 'name', feature_index.replace('_', ' ').title()),
            config,
            rng,
            as_bonus_feature=True,
        )

    for feature_entry in subclass_data.get('features_by_level', {}).get(level_key, []):
        feature_name = feature_entry['name']
        _add_bonus_feature(character_obj, current_level, feature_name)
        _apply_grants(character_obj, feature_entry.get('grants', {}))

    character_obj.applied_subclass_feature_levels.add(applied_key)


def _resolve_feature_choice(
    character_obj,
    current_level: int,
    feature_index: str,
    feature_name: str,
    config: dict,
    rng,
    as_bonus_feature: bool = False,
):
    feature_obj = _get_feature_object(feature_index)
    if feature_obj is None:
        return

    normalized_index = getattr(feature_obj, 'index', feature_index).replace('_', '-')
    feature_specific = getattr(feature_obj, 'feature_specific', None) or {}

    if normalized_index == 'eldritch-invocations':
        _resolve_eldritch_invocations(character_obj, current_level, feature_obj, config, rng, as_bonus_feature)
        return

    if not isinstance(feature_specific, dict):
        return

    if 'subfeature_options' in feature_specific:
        subfeature_options = feature_specific['subfeature_options']
        options = [
            option.get('item', {})
            for option in subfeature_options.get('from', {}).get('options', [])
            if option.get('item')
        ]
        choose_count = int(subfeature_options.get('choose', 1) or 1)
        picks = _pick_feature_options(
            character_obj,
            normalized_index,
            feature_name,
            options,
            choose_count,
            config,
            rng,
        )
        if not picks:
            return

        display_names = [_clean_choice_name(option['name']) for option in picks]
        if as_bonus_feature:
            for name in display_names:
                _add_bonus_feature(character_obj, current_level, name)
        else:
            _annotate_feature(
                character_obj,
                current_level,
                normalized_index,
                f"{feature_name} ({', '.join(display_names)})",
            )

        for option in picks:
            _record_class_feature_choice(
                character_obj,
                current_level,
                normalized_index,
                feature_name,
                option,
                config,
            )


def _resolve_eldritch_invocations(character_obj, current_level: int, feature_obj, config: dict, rng, as_bonus_feature: bool):
    profile = character_obj.spellcasting_profile
    level_data = getattr(Levels, f'{character_obj.char_class}_{current_level}')
    class_specific = getattr(level_data, 'class_specific', None) or {}
    target_count = int(class_specific.get('invocations_known', 0) or 0)
    existing = [
        entry for entry in character_obj.class_feature_choices
        if entry.get('feature_index') == 'eldritch-invocations'
    ]
    selected_indices = {entry['choice_index'] for entry in existing}
    available = []
    for option in feature_obj.feature_specific.get('invocations', []):
        option_obj = {
            'index': option['index'],
            'name': option['name'],
        }
        if option_obj['index'] in selected_indices:
            continue
        if not _meets_invocation_prerequisites(character_obj, current_level, option_obj['index'], profile):
            continue
        available.append(option_obj)

    replacement_rules = config.get('feature_selection', {}).get('eldritch-invocations', {}).get('replacement', {})
    if current_level > 2 and existing and available and replacement_rules.get('enabled', True):
        chance = float(replacement_rules.get('chance', 0.45))
        if rng.random() <= chance:
            weakest = min(
                existing,
                key=lambda entry: _option_weight('eldritch-invocations', entry['choice_index'], config),
            )
            candidate = max(
                available,
                key=lambda option: _option_weight('eldritch-invocations', option['index'], config),
            )
            if _option_weight('eldritch-invocations', candidate['index'], config) > _option_weight('eldritch-invocations', weakest['choice_index'], config):
                weakest['replaced_by'] = candidate['name']
                weakest['replaced_at_level'] = current_level
                selected_indices.remove(weakest['choice_index'])
                selected_indices.add(candidate['index'])
                character_obj.class_feature_choices = [
                    entry for entry in character_obj.class_feature_choices
                    if entry is not weakest
                ]
                character_obj.spellcasting_profile['decision_log'].append(
                    f"Level {current_level}: replaced invocation {weakest['choice_name']} with {candidate['name']}."
                )
                _record_class_feature_choice(
                    character_obj,
                    current_level,
                    'eldritch-invocations',
                    'Eldritch Invocations',
                    candidate,
                    config,
                    force_bonus_feature=True,
                )

    while len(selected_indices) < target_count:
        available = []
        for option in feature_obj.feature_specific.get('invocations', []):
            option_obj = {
                'index': option['index'],
                'name': option['name'],
            }
            if option_obj['index'] in selected_indices:
                continue
            if not _meets_invocation_prerequisites(character_obj, current_level, option_obj['index'], profile):
                continue
            available.append(option_obj)
        pick = _weighted_choice(
            [
                {
                    'index': option['index'],
                    'name': option['name'],
                    'weight': _option_weight('eldritch-invocations', option['index'], config),
                }
                for option in available
            ],
            rng,
            unique_key='index',
        )
        if not pick:
            break
        selected_indices.add(pick['index'])
        _record_class_feature_choice(
            character_obj,
            current_level,
            'eldritch-invocations',
            'Eldritch Invocations',
            pick,
            config,
            force_bonus_feature=True,
        )

    if current_level == 2 and not as_bonus_feature:
        names = [
            _clean_choice_name(entry['choice_name'])
            for entry in character_obj.class_feature_choices
            if entry.get('feature_index') == 'eldritch-invocations'
        ]
        if names:
            _annotate_feature(
                character_obj,
                current_level,
                'eldritch-invocations',
                f"Eldritch Invocations ({', '.join(names[:target_count])})",
            )


def _pick_feature_options(character_obj, feature_index: str, feature_name: str, options: list[dict], choose_count: int, config: dict, rng) -> list[dict]:
    existing = {
        entry['choice_index']
        for entry in character_obj.class_feature_choices
        if entry.get('feature_index') == feature_index
    }
    picked: list[dict] = []
    for _ in range(max(0, choose_count)):
        weighted_options = []
        for option in options:
            option_index = option.get('index')
            if option_index in existing:
                continue
            weighted_options.append({
                'index': option_index,
                'name': option.get('name', option_index),
                'weight': _option_weight(feature_index, option_index, config),
            })
        pick = _weighted_choice(weighted_options, rng, unique_key='index')
        if not pick:
            break
        existing.add(pick['index'])
        picked.append(pick)
    return picked


def _record_class_feature_choice(
    character_obj,
    current_level: int,
    feature_index: str,
    feature_name: str,
    option: dict,
    config: dict,
    force_bonus_feature: bool = False,
):
    grants = (
        config.get('feature_selection', {})
        .get(feature_index, {})
        .get('grants', {})
        .get(option['index'], {})
    )
    choice_name = option.get('name', option['index'])
    record = {
        'type': 'class_feature',
        'level': current_level,
        'feature_index': feature_index,
        'feature_name': feature_name,
        'choice_index': option['index'],
        'choice_name': choice_name,
    }
    character_obj.class_feature_choices.append(record)
    character_obj.progression_choices.append(record)
    _apply_grants(character_obj, grants)
    clean_name = _clean_choice_name(choice_name)
    if force_bonus_feature or feature_index in {'eldritch-invocations', 'metamagic-2', 'metamagic-3', 'additional-fighting-style'}:
        _add_bonus_feature(character_obj, current_level, clean_name)


def _apply_grants(character_obj, grants: dict):
    if not grants:
        return

    for skill_name in grants.get('skill_proficiencies', []):
        if skill_name not in character_obj.skill_proficiencies:
            character_obj.skill_proficiencies.append(skill_name)
    for proficiency_name in grants.get('proficiencies', []):
        if proficiency_name not in character_obj.proficiencies:
            character_obj.proficiencies.append(proficiency_name)
    for save_name in grants.get('saving_throw_proficiencies', []):
        if save_name not in character_obj.saving_throw_proficiencies:
            character_obj.saving_throw_proficiencies.append(save_name)

    character_obj.speed_bonus += int(grants.get('speed_bonus', 0))
    character_obj.initiative_bonus += int(grants.get('initiative_bonus', 0))
    character_obj.passive_perception_bonus += int(grants.get('passive_perception_bonus', 0))
    character_obj.hp_bonus_per_level += int(grants.get('hp_per_level_bonus', 0))
    character_obj.armor_class_bonus += int(grants.get('ac_bonus', 0))
    character_obj.ranged_attack_bonus += int(grants.get('ranged_attack_bonus', 0))


def _annotate_feature(character_obj, current_level: int, feature_index: str, label: str):
    character_obj.feature_annotations[(current_level, feature_index)] = label


def _add_bonus_feature(character_obj, current_level: int, feature_name: str):
    entries = character_obj.bonus_features_by_level.setdefault(current_level, [])
    if feature_name not in entries:
        entries.append(feature_name)


def _get_feature_object(feature_index: str):
    attr_name = feature_index.replace('-', '_')
    return getattr(Features, attr_name, None)


def _get_subclass_object(subclass_index: str):
    attr_name = subclass_index.replace('-', '_')
    return getattr(Subclasses, attr_name, None)


def _option_weight(feature_index: str, option_index: str, config: dict) -> float:
    feature_cfg = config.get('feature_selection', {}).get(feature_index, {})
    return float(feature_cfg.get('weights', {}).get(option_index, 1.0))


def _weighted_choice(options: list[dict], rng, unique_key: str | None = None):
    filtered = [option for option in options if float(option.get('weight', 1.0)) > 0]
    if not filtered:
        return None
    total = sum(float(option.get('weight', 1.0)) for option in filtered)
    roll = rng.uniform(0, total)
    upto = 0.0
    for option in filtered:
        upto += float(option.get('weight', 1.0))
        if roll <= upto:
            return option
    return filtered[-1]


def _clean_choice_name(name: str) -> str:
    if ': ' in name:
        return name.split(': ', 1)[1]
    return name


def _normalize_name(value: str) -> str:
    return value.strip().lower().replace('_', ' ').replace('-', ' ')


def _lookup_capabilities(name: str, mapping: dict[str, list[str]]) -> set[str]:
    normalized = _normalize_name(name)
    capabilities: set[str] = set()
    for key, values in mapping.items():
        normalized_key = _normalize_name(key)
        if normalized == normalized_key or normalized.startswith(f'{normalized_key} ('):
            capabilities.update(values)
    return capabilities


def _collect_character_capabilities(character_obj, config: dict) -> set[str]:
    capabilities: set[str] = set()
    for species_name, species_capabilities in config.get('species_capabilities', {}).items():
        if _normalize_name(species_name) == _normalize_name(character_obj.species):
            capabilities.update(species_capabilities)

    for trait in character_obj.get_traits():
        capabilities.update(_lookup_capabilities(trait, config.get('trait_capability_map', {})))

    for feature in character_obj.get_features():
        capabilities.update(_lookup_capabilities(feature, config.get('feature_capability_map', {})))

    return capabilities


def _spell_is_redundant(spell, capabilities: set[str], config: dict) -> bool:
    normalized_spell = _normalize_name(spell.name)
    for rule in config.get('spell_redundancy_rules', []):
        if _normalize_name(rule.get('spell', '')) != normalized_spell:
            continue
        blocked_by_any = set(rule.get('blocked_by_any_capabilities', []))
        blocked_by_all = set(rule.get('blocked_by_all_capabilities', []))
        if blocked_by_any and capabilities.intersection(blocked_by_any):
            return True
        if blocked_by_all and blocked_by_all.issubset(capabilities):
            return True
    return False


def _get_spell_pool(character_obj, spellbook_config: dict) -> dict[int, list]:
    class_name = character_obj.char_class.lower()
    capabilities = _collect_character_capabilities(character_obj, spellbook_config)
    pool: dict[int, list] = {level: [] for level in range(10)}
    for spell_index in Spells.entries:
        spell = getattr(Spells, spell_index)
        classes = {entry['name'].lower() for entry in getattr(spell, 'classes', [])}
        if class_name not in classes:
            continue
        if _spell_is_redundant(spell, capabilities, spellbook_config):
            continue
        pool.setdefault(int(spell.level), []).append(spell)

    for level_spells in pool.values():
        level_spells.sort(key=lambda spell: spell.name)
    return pool


def _process_spellcasting_level(character_obj, current_level: int, spellbook_config: dict, config: dict, rng):
    if character_obj.char_class not in SPELLCASTING_ABILITY:
        return

    level_data = getattr(Levels, f'{character_obj.char_class}_{current_level}')
    spellcasting = getattr(level_data, 'spellcasting', None) or {}
    if not spellcasting:
        return

    profile = character_obj.spellcasting_profile
    class_name = character_obj.char_class
    pool = _get_spell_pool(character_obj, spellbook_config)
    max_spell_level = max(
        _get_spell_slots(
            spellcasting,
            character_obj.char_class,
            current_level,
            config,
        ).keys(),
        default=0,
    )
    strategy = config.get('spellcasting', {}).get('class_strategies', {}).get(
        class_name,
        config.get('spellcasting', {}).get('class_strategies', {}).get('default', {}),
    )

    _learn_cantrips(profile, spellcasting, pool, max_spell_level, strategy, current_level, rng)

    if class_name in KNOWN_SPELL_CLASSES:
        _advance_known_spellcaster(profile, character_obj, current_level, spellcasting, pool, max_spell_level, strategy, rng)
    elif class_name == 'wizard':
        _advance_wizard(profile, current_level, spellcasting, pool, max_spell_level, strategy, rng)

    _learn_mystic_arcanum(profile, character_obj, current_level, pool, strategy, rng)
    _refresh_prepared_spells(
        profile,
        character_obj,
        current_level,
        spellcasting,
        pool,
        max_spell_level,
        strategy,
        rng,
        config,
    )


def _learn_cantrips(profile: dict, spellcasting: dict, pool: dict[int, list], max_spell_level: int, strategy: dict, current_level: int, rng):
    target = int(spellcasting.get('cantrips_known', 0) or 0)
    while len(profile['cantrips']) < target:
        pick = _choose_best_spell(
            candidates=[spell for spell in pool.get(0, []) if spell not in profile['cantrips']],
            selected=profile['cantrips'],
            strategy=strategy,
            current_level=current_level,
            max_spell_level=max_spell_level,
            rng=rng,
        )
        if pick is None:
            break
        profile['cantrips'].append(pick)
        profile['decision_log'].append(f'Level {current_level}: learned cantrip {pick.name}.')


def _advance_known_spellcaster(profile: dict, character_obj, current_level: int, spellcasting: dict, pool: dict[int, list], max_spell_level: int, strategy: dict, rng):
    target = int(spellcasting.get('spells_known', 0) or 0)
    expanded = _expanded_spell_indices(character_obj, current_level)
    while len(profile['known_spells']) < target:
        pick = _choose_best_spell(
            candidates=_available_leveled_spells(pool, profile['known_spells'], max_spell_level),
            selected=profile['known_spells'],
            strategy=strategy,
            current_level=current_level,
            max_spell_level=max_spell_level,
            rng=rng,
            expanded_spell_indices=expanded,
        )
        if pick is None:
            break
        profile['known_spells'].append(pick)
        profile['decision_log'].append(f'Level {current_level}: learned spell {pick.name}.')

    if current_level > 1 and character_obj.char_class in REPLACEMENT_CLASSES and profile['known_spells']:
        replacement = _choose_replacement(profile, pool, strategy, current_level, max_spell_level, rng, expanded)
        if replacement:
            old_spell, new_spell = replacement
            profile['known_spells'] = [new_spell if spell == old_spell else spell for spell in profile['known_spells']]
            profile['replacement_log'].append({
                'level': current_level,
                'replaced': old_spell.name,
                'new_spell': new_spell.name,
            })
            profile['decision_log'].append(
                f'Level {current_level}: replaced {old_spell.name} with {new_spell.name}.'
            )


def _advance_wizard(profile: dict, current_level: int, spellcasting: dict, pool: dict[int, list], max_spell_level: int, strategy: dict, rng):
    additions = 6 if current_level == 1 and not profile['known_spells'] else 2
    for _ in range(additions):
        pick = _choose_best_spell(
            candidates=_available_leveled_spells(pool, profile['known_spells'], max_spell_level),
            selected=profile['known_spells'],
            strategy=strategy,
            current_level=current_level,
            max_spell_level=max_spell_level,
            rng=rng,
        )
        if pick is None:
            break
        profile['known_spells'].append(pick)
        profile['decision_log'].append(f'Level {current_level}: copied {pick.name} into the spellbook.')


def _learn_mystic_arcanum(profile: dict, character_obj, current_level: int, pool: dict[int, list], strategy: dict, rng):
    if character_obj.char_class != 'warlock':
        return
    class_specific = getattr(getattr(Levels, f'warlock_{current_level}'), 'class_specific', None) or {}
    for spell_level in range(6, 10):
        key = f'mystic_arcanum_level_{spell_level}'
        target = int(class_specific.get(key, 0) or 0)
        if target <= 0 or spell_level in profile['mystic_arcanum']:
            continue
        pick = _choose_best_spell(
            candidates=[spell for spell in pool.get(spell_level, []) if spell not in profile['mystic_arcanum'].values()],
            selected=list(profile['mystic_arcanum'].values()),
            strategy=strategy,
            current_level=current_level,
            max_spell_level=spell_level,
            rng=rng,
        )
        if pick is None:
            continue
        profile['mystic_arcanum'][spell_level] = pick
        profile['decision_log'].append(f'Level {current_level}: learned Mystic Arcanum {pick.name}.')


def _refresh_prepared_spells(
    profile: dict,
    character_obj,
    current_level: int,
    spellcasting: dict,
    pool: dict[int, list],
    max_spell_level: int,
    strategy: dict,
    rng,
    config: dict,
):
    class_name = character_obj.char_class
    always_prepared = _always_prepared_subclass_spells(character_obj, current_level)
    profile['always_prepared_spells'] = always_prepared

    if class_name in PREPARED_SPELL_CLASSES:
        prepared_target = _prepared_spell_count(character_obj, current_level, spellcasting, spellbook_config=None)
        available = _available_leveled_spells(pool, always_prepared, max_spell_level)
        prepared = list(always_prepared)
        while len(prepared) < prepared_target + len(always_prepared):
            pick = _choose_best_spell(
                candidates=[spell for spell in available if spell not in prepared],
                selected=prepared,
                strategy=strategy,
                current_level=current_level,
                max_spell_level=max_spell_level,
                rng=rng,
            )
            if pick is None:
                break
            prepared.append(pick)
        profile['prepared_spells'] = prepared
    elif class_name == 'wizard':
        prepared_target = _prepared_spell_count(character_obj, current_level, spellcasting, spellbook_config=None)
        prepared = []
        while len(prepared) < prepared_target:
            pick = _choose_best_spell(
                candidates=[spell for spell in profile['known_spells'] if spell not in prepared],
                selected=prepared,
                strategy=strategy,
                current_level=current_level,
                max_spell_level=max_spell_level,
                rng=rng,
            )
            if pick is None:
                break
            prepared.append(pick)
        profile['prepared_spells'] = prepared
    else:
        profile['prepared_spells'] = list(profile['known_spells'])

    profile['prepared_formula'] = _prepared_formula_for_class(class_name)
    profile['spell_slots'] = _get_spell_slots(
        spellcasting,
        character_obj.char_class,
        current_level,
        config,
    )


def _prepared_spell_count(character_obj, current_level: int, spellcasting: dict, spellbook_config=None) -> int:
    ability_name = SPELLCASTING_ABILITY.get(character_obj.char_class)
    ability_mod = max(1, (getattr(character_obj, ability_name) - 10) // 2) if ability_name else 1
    if character_obj.char_class in {'cleric', 'druid'}:
        return max(1, current_level + ability_mod)
    if character_obj.char_class == 'paladin':
        return max(1, (current_level // 2) + ability_mod)
    if character_obj.char_class == 'wizard':
        return max(1, current_level + ability_mod)
    return int(spellcasting.get('spells_known', 0) or 0)


def _prepared_formula_for_class(class_name: str) -> str:
    if class_name in {'cleric', 'druid'}:
        return 'level_plus_mod'
    if class_name == 'paladin':
        return 'half_level_plus_mod'
    if class_name == 'wizard':
        return 'wizard'
    return 'known_spells'


def _available_leveled_spells(pool: dict[int, list], selected: list, max_spell_level: int) -> list:
    candidates = []
    for spell_level in range(1, max_spell_level + 1):
        for spell in pool.get(spell_level, []):
            if spell not in selected:
                candidates.append(spell)
    return candidates


def _choose_best_spell(candidates: list, selected: list, strategy: dict, current_level: int, max_spell_level: int, rng, expanded_spell_indices: set[str] | None = None):
    if not candidates:
        return None
    weighted = []
    for spell in candidates:
        score = _spell_score(spell, selected, strategy, current_level, max_spell_level)
        if expanded_spell_indices and spell.index in expanded_spell_indices:
            score += float(strategy.get('expanded_spell_bonus', 2.0))
        weighted.append({'spell': spell, 'weight': max(score, 0.01)})

    total = sum(item['weight'] for item in weighted)
    roll = rng.uniform(0, total)
    upto = 0.0
    for item in weighted:
        upto += item['weight']
        if roll <= upto:
            return item['spell']
    return weighted[-1]['spell']


def _choose_replacement(profile: dict, pool: dict[int, list], strategy: dict, current_level: int, max_spell_level: int, rng, expanded_spell_indices: set[str]) -> tuple | None:
    if not profile['known_spells']:
        return None
    current_scores = {
        spell: _spell_score(spell, profile['known_spells'], strategy, current_level, max_spell_level)
        for spell in profile['known_spells']
    }
    replaceable = sorted(profile['known_spells'], key=lambda spell: (current_scores[spell], spell.level, spell.name))
    candidates = _available_leveled_spells(pool, profile['known_spells'], max_spell_level)
    if not candidates:
        return None
    best_candidate = max(
        candidates,
        key=lambda spell: _spell_score(spell, profile['known_spells'], strategy, current_level, max_spell_level)
        + (float(strategy.get('expanded_spell_bonus', 2.0)) if spell.index in expanded_spell_indices else 0.0),
    )
    worst_known = replaceable[0]
    best_score = _spell_score(best_candidate, profile['known_spells'], strategy, current_level, max_spell_level)
    if best_candidate.index in expanded_spell_indices:
        best_score += float(strategy.get('expanded_spell_bonus', 2.0))
    if best_score <= current_scores[worst_known] + float(strategy.get('replacement_threshold', 1.5)):
        return None
    return worst_known, best_candidate


def _spell_score(spell, selected: list, strategy: dict, current_level: int, max_spell_level: int) -> float:
    tags = _spell_tags(spell)
    counts = _selected_tag_counts(selected)
    weights = strategy.get('category_weights', {})
    score = float(strategy.get('base_weight', 1.0))
    score += float(strategy.get('prefer_highest_level_weight', 0.6)) * int(spell.level)

    for tag in tags:
        score += float(weights.get(tag, 0.0))

    if 'concentration' in tags and counts.get('concentration', 0) == 0:
        score += float(strategy.get('first_concentration_bonus', 2.4))
    elif 'concentration' in tags:
        score -= counts.get('concentration', 0) * float(strategy.get('extra_concentration_penalty', 0.9))

    if 'healing' in tags and counts.get('healing', 0) == 0:
        score += float(strategy.get('missing_healing_bonus', 2.2))
    if 'control' in tags and counts.get('control', 0) == 0:
        score += float(strategy.get('missing_control_bonus', 1.6))
    if 'ritual' in tags and counts.get('ritual', 0) == 0:
        score += float(strategy.get('first_ritual_bonus', 1.1))
    if spell.level and spell.level < max_spell_level:
        score -= float(strategy.get('low_level_penalty', 0.15)) * max(0, max_spell_level - int(spell.level))
    return score


def _spell_tags(spell) -> set[str]:
    desc_text = ' '.join(getattr(spell, 'desc', []) or []).lower()
    tags = {'utility'}
    if getattr(spell, 'concentration', False):
        tags.add('concentration')
    if getattr(spell, 'damage', None):
        tags.add('damage')
    if getattr(spell, 'attack_type', None):
        tags.add('attack')
    if getattr(spell, 'heal_at_slot_level', None) or 'regains hit points' in desc_text:
        tags.add('healing')
    if getattr(spell, 'dc', None):
        tags.add('save')
    if getattr(spell, 'ritual', False):
        tags.add('ritual')
    if any(keyword in desc_text for keyword in ('paralyzed', 'restrained', 'charmed', 'frightened', 'incapacitated', 'stunned', 'banished', 'speed is halved', "can't move")):
        tags.add('control')
    return tags


def _selected_tag_counts(selected: list) -> dict[str, int]:
    counts: dict[str, int] = {}
    for spell in selected:
        for tag in _spell_tags(spell):
            counts[tag] = counts.get(tag, 0) + 1
    return counts


def _get_spell_slots(spellcasting: dict, class_name: str, class_level: int, config: dict) -> dict[int, int]:
    slots = {}
    fallback = _phb_slot_fallback(class_name, class_level, config)
    for level in range(1, 10):
        value = int(spellcasting.get(f'spell_slots_level_{level}', 0) or 0)
        if value <= 0:
            value = int(fallback.get(level, 0) or 0)
        if value > 0:
            slots[level] = value
    return slots


def _phb_slot_fallback(class_name: str, class_level: int, config: dict) -> dict[int, int]:
    table = (
        config.get('spellcasting', {})
        .get('slot_fallbacks', {})
        .get(class_name, {})
    )
    row = table.get(str(class_level), [])
    if not isinstance(row, list):
        return {}
    return {
        idx + 1: int(value)
        for idx, value in enumerate(row)
        if int(value) > 0
    }


def _always_prepared_subclass_spells(character_obj, current_level: int) -> list:
    if not character_obj.subclass_index:
        return []
    if character_obj.char_class not in ALWAYS_PREPARED_SUBCLASS_CLASSES:
        return []
    subclass_obj = _get_subclass_object(character_obj.subclass_index)
    if subclass_obj is None:
        return []
    spells = []
    for entry in getattr(subclass_obj, 'spells', []) or []:
        if not _spell_prerequisites_met(entry.get('prerequisites', []), current_level):
            continue
        spell_index = entry['spell']['index'].replace('-', '_')
        spell_obj = getattr(Spells, spell_index, None)
        if spell_obj is not None and spell_obj not in spells:
            spells.append(spell_obj)
    return spells


def _expanded_spell_indices(character_obj, current_level: int) -> set[str]:
    if not character_obj.subclass_index:
        return set()
    subclass_obj = _get_subclass_object(character_obj.subclass_index)
    if subclass_obj is None:
        return set()
    indices = set()
    for entry in getattr(subclass_obj, 'spells', []) or []:
        if _spell_prerequisites_met(entry.get('prerequisites', []), current_level):
            indices.add(entry['spell']['index'])
    return indices


def _spell_prerequisites_met(prerequisites: list[dict], current_level: int) -> bool:
    for prerequisite in prerequisites:
        if prerequisite.get('type') == 'level':
            name = prerequisite.get('name', '')
            pieces = name.split()
            try:
                level_value = int(pieces[-1])
            except (IndexError, ValueError):
                level_value = current_level
            if current_level < level_value:
                return False
    return True


def _meets_invocation_prerequisites(character_obj, current_level: int, invocation_index: str, profile: dict) -> bool:
    invocation_obj = _get_feature_object(invocation_index)
    if invocation_obj is None:
        return False
    for prerequisite in getattr(invocation_obj, 'prerequisites', []) or []:
        prerequisite_type = prerequisite.get('type')
        if prerequisite_type == 'level' and current_level < int(prerequisite.get('level', 0) or 0):
            return False
        if prerequisite_type == 'feature':
            feature_url = prerequisite.get('feature', '')
            feature_index = feature_url.rstrip('/').split('/')[-1]
            if feature_index not in {
                entry.get('choice_index') for entry in character_obj.class_feature_choices
            }:
                return False
        if prerequisite_type == 'spell':
            spell_index = prerequisite.get('spell', '').rstrip('/').split('/')[-1]
            known_spell_indices = {spell.index for spell in profile.get('cantrips', []) + profile.get('known_spells', [])}
            if spell_index not in known_spell_indices:
                return False
    return True


def _finalize_spellcasting_profile(character_obj, spellbook_config: dict):
    profile = character_obj.spellcasting_profile
    if character_obj.char_class not in SPELLCASTING_ABILITY:
        character_obj.spellcasting_profile = None
        return

    if profile['prepared_spells']:
        display_spells = list(profile['prepared_spells'])
    else:
        display_spells = list(profile['known_spells'])
    for spell in profile['always_prepared_spells']:
        if spell not in display_spells:
            display_spells.append(spell)
    for spell in profile['mystic_arcanum'].values():
        if spell not in display_spells:
            display_spells.append(spell)

    spells_by_level: dict[int, list] = {}
    prepared_by_level: dict[int, list] = {}
    for spell in sorted(display_spells, key=lambda item: (int(item.level), item.name)):
        spells_by_level.setdefault(int(spell.level), []).append(spell)
    for spell in sorted(profile['prepared_spells'], key=lambda item: (int(item.level), item.name)):
        prepared_by_level.setdefault(int(spell.level), []).append(spell)
    profile['spells_by_level'] = spells_by_level
    profile['prepared_by_level'] = prepared_by_level
    profile['spell_focus'] = _selected_tag_counts(display_spells)


def _spell_to_dict(spell) -> dict:
    school = getattr(spell, 'school', {}) or {}
    desc = list(getattr(spell, 'desc', []) or [])
    higher_level = list(getattr(spell, 'higher_level', []) or [])
    return {
        'index': getattr(spell, 'index', ''),
        'name': spell.name,
        'level': int(spell.level),
        'school': school.get('name', 'Unknown'),
        'casting_time': getattr(spell, 'casting_time', ''),
        'range': getattr(spell, 'range', ''),
        'components': list(getattr(spell, 'components', []) or []),
        'material': getattr(spell, 'material', ''),
        'duration': getattr(spell, 'duration', ''),
        'ritual': bool(getattr(spell, 'ritual', False)),
        'concentration': bool(getattr(spell, 'concentration', False)),
        'desc': desc,
        'higher_level': higher_level,
    }