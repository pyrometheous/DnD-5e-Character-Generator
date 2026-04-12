from __future__ import annotations

import copy
import json
import random
from pathlib import Path

from tinys_srd import Languages, Proficiencies

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "feats_rules.json"

ABILITY_NAMES = [
    'strength', 'dexterity', 'constitution',
    'intelligence', 'wisdom', 'charisma',
]

SPELLCASTER_CLASSES = {
    'bard', 'cleric', 'druid', 'paladin',
    'ranger', 'sorcerer', 'warlock', 'wizard',
}


def load_feat_config(config_path: str | Path | None = None) -> dict:
    target_path = Path(config_path) if config_path else CONFIG_PATH
    with target_path.open('r', encoding='utf-8') as handle:
        return json.load(handle)


def choose_feat_for_character(character_obj, asi_level: int, config: dict | None = None):
    config = config or load_feat_config()
    selection = config.get('selection', {})
    max_feats = selection.get('max_feats_per_character')
    if max_feats is not None and len(character_obj.feats) >= int(max_feats):
        return None

    options = [('asi', _asi_weight(character_obj, asi_level, selection))]
    for feat in config.get('feats', []):
        if not _can_take_feat(character_obj, feat):
            continue
        weight = _feat_weight(character_obj, feat, asi_level, config)
        if weight > 0:
            options.append((feat, weight))

    total_weight = sum(weight for _, weight in options if weight > 0)
    if total_weight <= 0:
        return None

    roll = random.uniform(0, total_weight)
    upto = 0.0
    for option, weight in options:
        if weight <= 0:
            continue
        upto += weight
        if roll <= upto:
            if option == 'asi':
                return None
            return resolve_feat_selection(character_obj, option, asi_level, config)
    return None


def resolve_feat_selection(character_obj, feat: dict, asi_level: int, config: dict | None = None) -> dict:
    config = config or load_feat_config()
    resolved = copy.deepcopy(feat)
    resolved['_applied'] = False

    selected_ability_bonuses = {}
    for ability_name, bonus in resolved.get('ability_bonuses', {}).items():
        if ability_name in ABILITY_NAMES and int(bonus) > 0:
            selected_ability_bonuses[ability_name] = selected_ability_bonuses.get(ability_name, 0) + int(bonus)

    ability_options = [
        ability for ability in resolved.get('ability_bonus_options', [])
        if ability in ABILITY_NAMES and getattr(character_obj, ability) < 20
    ]
    if ability_options:
        chosen_ability = _choose_ability_option(character_obj, ability_options, asi_level)
        if chosen_ability:
            selected_ability_bonuses[chosen_ability] = selected_ability_bonuses.get(chosen_ability, 0) + 1
    resolved['selected_ability_bonuses'] = selected_ability_bonuses

    grants = resolved.get('grants', {})
    resolved['selected_languages'] = _choose_languages(
        character_obj,
        int(grants.get('language_choices', 0)),
    )
    resolved['selected_proficiencies'] = _choose_proficiencies(character_obj, grants)
    resolved['selected_saving_throw'] = _choose_saving_throw(character_obj, grants, asi_level)
    resolved['selected_magic_class'] = _choose_magic_class(character_obj, grants)
    resolved['selected_damage_type'] = _choose_damage_type(grants)
    resolved['summary'] = describe_feat_selection(resolved)
    return resolved


def describe_feat_selection(feat: dict) -> str:
    parts = []

    bonuses = feat.get('selected_ability_bonuses', {})
    if bonuses:
        bonus_parts = [f"+{value} {ability[:3].upper()}" for ability, value in bonuses.items()]
        parts.append(', '.join(bonus_parts))

    selected_save = feat.get('selected_saving_throw')
    if selected_save:
        parts.append(f"save {selected_save[:3].upper()}")

    selected_languages = feat.get('selected_languages', [])
    if selected_languages:
        preview = ', '.join(selected_languages[:2])
        if len(selected_languages) > 2:
            preview += ', ...'
        parts.append(f"langs {preview}")

    selected_proficiencies = feat.get('selected_proficiencies', [])
    if selected_proficiencies:
        preview = ', '.join(selected_proficiencies[:2])
        if len(selected_proficiencies) > 2:
            preview += ', ...'
        parts.append(preview)

    if feat.get('selected_magic_class'):
        parts.append(feat['selected_magic_class'].capitalize())
    if feat.get('selected_damage_type'):
        parts.append(feat['selected_damage_type'])

    if not parts:
        return feat['name']
    return f"{feat['name']} ({'; '.join(parts)})"


def _asi_weight(character_obj, asi_level: int, selection_config: dict) -> float:
    weight = float(selection_config.get('asi_base_weight', 4.0))
    if asi_level < 10 and any(getattr(character_obj, ability) < 10 for ability in ABILITY_NAMES):
        weight *= float(selection_config.get('asi_sub_ten_multiplier', 1.7))
    preferred_spell_ability = _preferred_spellcasting_ability(character_obj, asi_level)
    if preferred_spell_ability and getattr(character_obj, preferred_spell_ability) < 20:
        weight *= float(selection_config.get('asi_spellcasting_multiplier', 1.25))
    if any(getattr(character_obj, ability) % 2 == 1 and getattr(character_obj, ability) < 20 for ability in ABILITY_NAMES):
        weight *= float(selection_config.get('asi_odd_score_multiplier', 1.2))
    weight *= float(selection_config.get('level_multipliers', {}).get(str(asi_level), 1.0))
    return max(weight, 0.0)


def _feat_weight(character_obj, feat: dict, asi_level: int, config: dict) -> float:
    selection = config.get('selection', {})
    weight = float(feat.get('weight', 1.0))
    weight *= float(selection.get('level_multipliers', {}).get(str(asi_level), 1.0))

    class_name = character_obj.char_class.lower()
    species_name = _normalize_name(character_obj.species)
    feat_tags = set(feat.get('tags', []))

    class_affinity = set(feat.get('class_affinity', []))

    if class_name in class_affinity:
        weight *= float(selection.get('class_affinity_multiplier', 1.6))
    elif class_affinity:
        weight *= float(selection.get('class_mismatch_multiplier', 0.55))
    if species_name in [_normalize_name(name) for name in feat.get('species_affinity', [])]:
        weight *= float(selection.get('species_affinity_multiplier', 1.25))

    if _is_spellcaster(character_obj) and 'magic' in feat_tags:
        weight *= float(selection.get('magic_feat_multiplier', 1.8))
    if _is_martial(character_obj) and 'martial' in feat_tags:
        weight *= float(selection.get('martial_feat_multiplier', 1.45))
    if _is_spellcaster(character_obj) and 'martial' in feat_tags and class_name not in class_affinity:
        weight *= float(selection.get('spellcaster_martial_penalty', 0.2))
    if _is_martial(character_obj) and 'magic' in feat_tags and class_name not in class_affinity:
        weight *= float(selection.get('martial_magic_penalty', 0.6))
    if class_name in {'rogue', 'ranger', 'monk'} and 'stealth' in feat_tags:
        weight *= float(selection.get('stealth_feat_multiplier', 1.3))

    if _feat_addresses_sub_ten(character_obj, feat) and asi_level < 10:
        weight *= float(selection.get('under_ten_alignment_multiplier', 1.8))
    elif _feat_aligns_with_preferred_ability(character_obj, feat, asi_level):
        weight *= float(selection.get('ability_alignment_multiplier', 1.5))

    if _feat_has_redundant_grants(character_obj, feat):
        weight *= float(selection.get('redundant_grant_multiplier', 0.35))

    return max(weight, 0.0)


def _can_take_feat(character_obj, feat: dict) -> bool:
    if not feat.get('repeatable', False):
        taken_names = {_normalize_name(existing.get('name', '')) for existing in character_obj.feats}
        if _normalize_name(feat.get('name', '')) in taken_names:
            return False
    return _meets_prerequisites(character_obj, feat)


def _meets_prerequisites(character_obj, feat: dict) -> bool:
    prerequisites = feat.get('prerequisites', {})

    for ability_name, minimum in prerequisites.get('ability', {}).items():
        if getattr(character_obj, ability_name, 0) < int(minimum):
            return False

    ability_any_of = prerequisites.get('ability_any_of', {})
    if ability_any_of:
        if not any(getattr(character_obj, ability_name, 0) >= int(minimum)
                   for ability_name, minimum in ability_any_of.items()):
            return False

    if prerequisites.get('spellcasting') and not _is_spellcaster(character_obj):
        return False

    for proficiency_name in prerequisites.get('proficiencies_all', []):
        if not _character_has_proficiency(character_obj, proficiency_name):
            return False

    return True


def _choose_ability_option(character_obj, options: list[str], asi_level: int):
    weighted_options = []
    preferred_spell_ability = _preferred_spellcasting_ability(character_obj, asi_level)
    for ability_name in options:
        score = 1
        current = getattr(character_obj, ability_name)
        if asi_level < 10 and current < 10:
            score += 120
        if preferred_spell_ability == ability_name:
            score += 90
        if current % 2 == 1:
            score += 45
        if current >= 20:
            score = 0
        weighted_options.append((ability_name, score))

    total = sum(weight for _, weight in weighted_options if weight > 0)
    if total <= 0:
        return None

    roll = random.uniform(0, total)
    upto = 0.0
    for ability_name, weight in weighted_options:
        if weight <= 0:
            continue
        upto += weight
        if roll <= upto:
            return ability_name
    return weighted_options[-1][0]


def _choose_languages(character_obj, count: int) -> list[str]:
    if count <= 0:
        return []
    known_languages = {_normalize_name(language) for language in character_obj.get_languages()}
    available = []
    for language_index in Languages.entries:
        language_name = getattr(Languages, language_index).name
        if _normalize_name(language_name) not in known_languages:
            available.append(language_name)
    random.shuffle(available)
    return available[:count]


def _choose_proficiencies(character_obj, grants: dict) -> list[str]:
    selected = []

    for proficiency_name in grants.get('proficiencies', []):
        if not _character_has_proficiency(character_obj, proficiency_name):
            selected.append(proficiency_name)

    skill_choices = int(grants.get('skill_choices', 0))
    if skill_choices > 0:
        available_skills = [
            skill_name for skill_name in _all_skill_names()
            if skill_name not in character_obj.skill_proficiencies
        ]
        random.shuffle(available_skills)
        selected.extend(available_skills[:skill_choices])

    tool_choices = int(grants.get('tool_choices', 0))
    if tool_choices > 0:
        available_tools = [
            tool_name for tool_name in _all_tool_names()
            if not _character_has_proficiency(character_obj, tool_name)
        ]
        random.shuffle(available_tools)
        selected.extend(available_tools[:tool_choices])

    skill_or_tool_choices = int(grants.get('skill_or_tool_choices', 0))
    if skill_or_tool_choices > 0:
        mixed_pool = [
            *[skill_name for skill_name in _all_skill_names() if skill_name not in character_obj.skill_proficiencies],
            *[tool_name for tool_name in _all_tool_names() if not _character_has_proficiency(character_obj, tool_name)],
        ]
        unique_pool = list(dict.fromkeys(mixed_pool))
        random.shuffle(unique_pool)
        selected.extend(unique_pool[:skill_or_tool_choices])

    weapon_choices = int(grants.get('weapon_choices', 0))
    if weapon_choices > 0:
        available_weapons = [
            weapon_name for weapon_name in _all_weapon_names()
            if not _character_has_proficiency(character_obj, weapon_name)
        ]
        random.shuffle(available_weapons)
        selected.extend(available_weapons[:weapon_choices])

    return list(dict.fromkeys(selected))


def _choose_saving_throw(character_obj, grants: dict, asi_level: int):
    if not grants.get('saving_throw_choice'):
        return None
    available = [
        ability_name for ability_name in ABILITY_NAMES
        if ability_name[:3].upper() not in character_obj.saving_throw_proficiencies
    ]
    if not available:
        return None
    return _choose_ability_option(character_obj, available, asi_level)


def _choose_magic_class(character_obj, grants: dict):
    choices = grants.get('magic_class_choices', [])
    if not choices:
        return None
    if character_obj.char_class in choices:
        return character_obj.char_class
    if _is_spellcaster(character_obj):
        preferred = _spellcasting_family_choice(character_obj)
        if preferred in choices:
            return preferred
    return random.choice(choices)


def _choose_damage_type(grants: dict):
    choices = grants.get('damage_type_choices', [])
    if not choices:
        return None
    return random.choice(choices)


def _character_has_proficiency(character_obj, proficiency_name: str) -> bool:
    normalized = _normalize_name(proficiency_name)
    known = {_normalize_name(name) for name in character_obj.proficiencies}
    known.update(_normalize_name(skill) for skill in character_obj.skill_proficiencies)
    known.update(_normalize_name(name) for name in character_obj.saving_throw_proficiencies)
    if normalized in known:
        return True
    if normalized.startswith('skill: '):
        skill_name = normalized.replace('skill: ', '')
        return skill_name in {_normalize_name(skill) for skill in character_obj.skill_proficiencies}
    return False


def _feat_addresses_sub_ten(character_obj, feat: dict) -> bool:
    for ability_name in feat.get('ability_bonus_options', []):
        if ability_name in ABILITY_NAMES and getattr(character_obj, ability_name) < 10:
            return True
    for ability_name in feat.get('ability_bonuses', {}):
        if ability_name in ABILITY_NAMES and getattr(character_obj, ability_name) < 10:
            return True
    return False


def _feat_aligns_with_preferred_ability(character_obj, feat: dict, asi_level: int) -> bool:
    preferred_spell_ability = _preferred_spellcasting_ability(character_obj, asi_level)
    feat_abilities = list(feat.get('ability_bonus_options', [])) + list(feat.get('ability_bonuses', {}).keys())
    for ability_name in feat_abilities:
        if ability_name not in ABILITY_NAMES:
            continue
        if preferred_spell_ability == ability_name:
            return True
        if getattr(character_obj, ability_name) % 2 == 1 and getattr(character_obj, ability_name) < 20:
            return True
    return False


def _feat_has_redundant_grants(character_obj, feat: dict) -> bool:
    grants = feat.get('grants', {})
    fixed_proficiencies = grants.get('proficiencies', [])
    if fixed_proficiencies and all(_character_has_proficiency(character_obj, name) for name in fixed_proficiencies):
        return True
    if grants.get('language_choices') and len(_choose_languages(character_obj, 1)) == 0:
        return True
    return False


def _preferred_spellcasting_ability(character_obj, asi_level: int):
    if asi_level > 15:
        return None
    spellcasting_map = {
        'bard': 'charisma', 'cleric': 'wisdom', 'druid': 'wisdom',
        'paladin': 'charisma', 'ranger': 'wisdom', 'sorcerer': 'charisma',
        'warlock': 'charisma', 'wizard': 'intelligence',
    }
    return spellcasting_map.get(character_obj.char_class)


def _is_spellcaster(character_obj) -> bool:
    return character_obj.char_class in SPELLCASTER_CLASSES


def _is_martial(character_obj) -> bool:
    return character_obj.char_class in {
        'barbarian', 'fighter', 'monk', 'paladin', 'ranger', 'rogue',
    }


def _spellcasting_family_choice(character_obj) -> str:
    spellcasting_ability = _preferred_spellcasting_ability(character_obj, 1)
    if spellcasting_ability == 'intelligence':
        return 'wizard'
    if spellcasting_ability == 'wisdom':
        return 'cleric'
    if spellcasting_ability == 'charisma':
        return 'warlock'
    return 'wizard'


def _all_skill_names() -> list[str]:
    names = []
    for proficiency_index in Proficiencies.entries:
        proficiency = getattr(Proficiencies, proficiency_index)
        if getattr(proficiency, 'type', '') == 'Skills' and proficiency.name.startswith('Skill: '):
            names.append(proficiency.name.replace('Skill: ', ''))
    return sorted(names)


def _all_tool_names() -> list[str]:
    tool_types = {
        "Artisan's Tools", "Gaming Sets", 'Musical Instruments',
        'Tools', 'Other', "Thieves' Tools",
    }
    names = []
    for proficiency_index in Proficiencies.entries:
        proficiency = getattr(Proficiencies, proficiency_index)
        if getattr(proficiency, 'type', '') in tool_types:
            names.append(proficiency.name)
    return sorted(set(names))


def _all_weapon_names() -> list[str]:
    names = []
    for proficiency_index in Proficiencies.entries:
        proficiency = getattr(Proficiencies, proficiency_index)
        if getattr(proficiency, 'type', '') == 'Weapons':
            names.append(proficiency.name)
    return sorted(set(names))


def _normalize_name(value: str) -> str:
    return value.strip().lower().replace('_', ' ').replace('-', ' ')