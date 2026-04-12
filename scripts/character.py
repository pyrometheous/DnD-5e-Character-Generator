from scripts import roll
from scripts.feats import choose_feat_for_character, load_feat_config
from scripts.progression import ensure_progression

from tinys_srd import Classes, Equipment, Proficiencies, Levels
from tinys_srd import Races as Species

import json
import random
import re
import io
import os
import urllib.request
import zipfile
from fillpdf import fillpdfs
from fictional_names import name_generator
import fitz


names = name_generator.generate_name

AVAILABLE_CLASSES = Classes.entries

SPECIES_NAMES = {
    "Human": "human",
    "Elf": "elven",
    "Halfling": "halfling",
    "Dwarf": "dwarven",
    "Gnome": "gnomish",
    "Half_elf": "elven",
    "Dragonborn": "dragonborn",
    "Tiefling": "dragonborn",
    "Half_orc": "orc",
}

ABILITY_INDEX_MAP = {
    'str': 'strength',
    'dex': 'dexterity',
    'con': 'constitution',
    'int': 'intelligence',
    'wis': 'wisdom',
    'cha': 'charisma',
}

PDF_SAVING_THROWS = {
    'STR': {'checkbox': "Check Box 11", 'value': 'ST Strength', 'ability': 'strength'},
    'DEX': {'checkbox': "Check Box 18", 'value': 'ST Dexterity', 'ability': 'dexterity'},
    'CON': {'checkbox': "Check Box 19", 'value': "ST Constitution", 'ability': 'constitution'},
    'INT': {'checkbox': "Check Box 20", 'value': "ST Intelligence", 'ability': 'intelligence'},
    'WIS': {'checkbox': "Check Box 21", 'value': "ST Wisdom", 'ability': 'wisdom'},
    'CHA': {'checkbox': "Check Box 22", 'value': "ST Charisma", 'ability': 'charisma'},
}

SKILLS = {
    'Acrobatics':      {'ability': 'dexterity',     'field': 'Acrobatics',      'checkbox': 'Check Box 23'},
    'Animal Handling': {'ability': 'wisdom',         'field': 'Animal',          'checkbox': 'Check Box 24'},
    'Arcana':          {'ability': 'intelligence',   'field': 'Arcana',          'checkbox': 'Check Box 25'},
    'Athletics':       {'ability': 'strength',       'field': 'Athletics',       'checkbox': 'Check Box 26'},
    'Deception':       {'ability': 'charisma',       'field': 'Deception ',      'checkbox': 'Check Box 27'},
    'History':         {'ability': 'intelligence',   'field': 'History ',        'checkbox': 'Check Box 28'},
    'Insight':         {'ability': 'wisdom',         'field': 'Insight',         'checkbox': 'Check Box 29'},
    'Intimidation':    {'ability': 'charisma',       'field': 'Intimidation',    'checkbox': 'Check Box 30'},
    'Investigation':   {'ability': 'intelligence',   'field': 'Investigation ',  'checkbox': 'Check Box 31'},
    'Medicine':        {'ability': 'wisdom',         'field': 'Medicine',        'checkbox': 'Check Box 32'},
    'Nature':          {'ability': 'intelligence',   'field': 'Nature',          'checkbox': 'Check Box 33'},
    'Perception':      {'ability': 'wisdom',         'field': 'Perception ',     'checkbox': 'Check Box 34'},
    'Performance':     {'ability': 'charisma',       'field': 'Performance',     'checkbox': 'Check Box 35'},
    'Persuasion':      {'ability': 'charisma',       'field': 'Persuasion',      'checkbox': 'Check Box 36'},
    'Religion':        {'ability': 'intelligence',   'field': 'Religion',        'checkbox': 'Check Box 37'},
    'Sleight of Hand': {'ability': 'dexterity',      'field': 'SleightofHand',   'checkbox': 'Check Box 38'},
    'Stealth':         {'ability': 'dexterity',      'field': 'Stealth ',        'checkbox': 'Check Box 39'},
    'Survival':        {'ability': 'wisdom',         'field': 'Survival',        'checkbox': 'Check Box 40'},
}

SPELLCASTING_ABILITY = {
    'bard': 'charisma', 'cleric': 'wisdom', 'druid': 'wisdom',
    'paladin': 'charisma', 'ranger': 'wisdom', 'sorcerer': 'charisma',
    'warlock': 'charisma', 'wizard': 'intelligence',
}

DEFAULT_SPELLCASTING_GUIDANCE = {
    'global_rules': {
        'include_spell_use_basics': True,
        'include_species_trait_spellcasting_hint': True,
    },
    'class_rules': {
        'bard': {
            'prepared_formula': 'none',
            'resource_refresh': 'long_rest',
            'show_cantrips_known': True,
            'show_spells_known': True,
            'include_prepared_rest_reminder': False,
            'include_mystic_arcanum': False,
        },
        'cleric': {
            'prepared_formula': 'level_plus_mod',
            'resource_refresh': 'long_rest',
            'show_cantrips_known': True,
            'show_spells_known': False,
            'include_prepared_rest_reminder': True,
            'include_mystic_arcanum': False,
        },
        'druid': {
            'prepared_formula': 'level_plus_mod',
            'resource_refresh': 'long_rest',
            'show_cantrips_known': True,
            'show_spells_known': False,
            'include_prepared_rest_reminder': True,
            'include_mystic_arcanum': False,
        },
        'paladin': {
            'prepared_formula': 'half_level_plus_mod',
            'resource_refresh': 'long_rest',
            'show_cantrips_known': False,
            'show_spells_known': False,
            'include_prepared_rest_reminder': False,
            'include_mystic_arcanum': False,
        },
        'ranger': {
            'prepared_formula': 'none',
            'resource_refresh': 'long_rest',
            'show_cantrips_known': False,
            'show_spells_known': True,
            'include_prepared_rest_reminder': False,
            'include_mystic_arcanum': False,
        },
        'sorcerer': {
            'prepared_formula': 'none',
            'resource_refresh': 'long_rest',
            'show_cantrips_known': True,
            'show_spells_known': True,
            'include_prepared_rest_reminder': False,
            'include_mystic_arcanum': False,
        },
        'warlock': {
            'prepared_formula': 'none',
            'resource_refresh': 'warlock',
            'show_cantrips_known': True,
            'show_spells_known': True,
            'include_prepared_rest_reminder': False,
            'include_mystic_arcanum': True,
        },
        'wizard': {
            'prepared_formula': 'wizard',
            'resource_refresh': 'long_rest',
            'show_cantrips_known': True,
            'show_spells_known': False,
            'include_prepared_rest_reminder': False,
            'include_mystic_arcanum': False,
        },
    },
    'class_notes': {
        'bard': [
            'Spellcasting: slots refresh on long rest.',
            'Known-spell caster: choose spells learned on level-up.',
        ],
        'cleric': [
            'Spellcasting: slots refresh on long rest.',
            'Prepared caster: prepare spells each day from the cleric list.',
        ],
        'druid': [
            'Spellcasting: slots refresh on long rest.',
            'Prepared caster: prepare spells each day from the druid list.',
        ],
        'paladin': [
            'Spellcasting: slots refresh on long rest.',
            'Half-caster progression: fewer slots than full casters.',
        ],
        'ranger': [
            'Spellcasting: slots refresh on long rest.',
            'Half-caster progression: fewer slots than full casters.',
        ],
        'sorcerer': [
            'Spellcasting: slots refresh on long rest.',
            'Flexible Casting details are listed below based on current level resources.',
        ],
        'warlock': [
            'Pact Magic: slots refresh on short rest.',
            'At high levels, warlock uses 5th-level pact slots.',
            'Mystic Arcanum handles 6th-9th level spells (1/long rest each).',
        ],
        'wizard': [
            'Spellcasting: slots refresh on long rest.',
            'Arcane Recovery restores some slots on a short rest (once/day).',
        ],
    },
    'feat_note_rules': {
        'match_mode': 'exact_normalized',
        'use_contains_fallback': True,
        'aliases': {
            'Magic Initiate': [
                'Magic Initiate (Bard)',
                'Magic Initiate (Cleric)',
                'Magic Initiate (Druid)',
                'Magic Initiate (Sorcerer)',
                'Magic Initiate (Warlock)',
                'Magic Initiate (Wizard)',
            ],
            'War Caster': ['War-Caster', 'Warcaster'],
            'Spell Sniper': ['Spell-Sniper'],
        },
    },
    'feat_notes': {
        'Elemental Adept': [
            'Elemental Adept: choose and focus on one damage type from your feat.',
        ],
        'Magic Initiate': [
            'Magic Initiate: one 1st-level spell can be cast once per long rest.',
        ],
        'Ritual Caster': [
            'Ritual Caster: ritual spells can be cast without expending slots if prepared in your ritual book.',
        ],
        'Spell Sniper': [
            'Spell Sniper: doubled range for attack-roll spells and more reliable cover targeting.',
        ],
        'War Caster': [
            'War Caster: advantage on concentration checks and can cast in place of opportunity attacks.',
        ],
    },
    'species_notes': {
        'tiefling': [
            'Species magic: tieflings may gain innate spells from racial traits.',
        ],
    },
    'sorcerer_flexible_casting': {
        'font_of_magic_unlock_level': 2,
        'max_created_slot_level': 5,
        'slot_to_point_conversion': 'slot_level',
        'fallback_creation_costs': [
            {'spell_slot_level': 1, 'sorcery_point_cost': 2},
            {'spell_slot_level': 2, 'sorcery_point_cost': 3},
            {'spell_slot_level': 3, 'sorcery_point_cost': 5},
            {'spell_slot_level': 4, 'sorcery_point_cost': 6},
            {'spell_slot_level': 5, 'sorcery_point_cost': 7},
        ],
        'fallback_sorcery_points_by_level': {
            '1': 0, '2': 2, '3': 3, '4': 4, '5': 5,
            '6': 6, '7': 7, '8': 8, '9': 9, '10': 10,
            '11': 11, '12': 12, '13': 13, '14': 14, '15': 15,
            '16': 16, '17': 17, '18': 18, '19': 19, '20': 20,
        },
    },
    'templates': {
        'spell_use_basics_header': 'Spell Use Basics:',
        'spellcasting_ability_line': 'Spellcasting ability: {ability_name} ({ability_mod:+d}).',
        'spell_save_dc_line': 'Spell Save DC: {save_dc}.',
        'spell_attack_bonus_line': 'Spell Attack Bonus: +{attack_bonus}.',
        'cantrips_known_line': 'Cantrips known: {cantrips_known}.',
        'spells_known_line': 'Spells known from class: {spells_known}.',
        'prepared_spells_line_cleric_druid': (
            'Prepared spells each day: {prepared_count} ({level} + {ability_name_short} mod).'
        ),
        'prepared_spells_line_wizard': (
            'Prepared wizard spells each day: {prepared_count} ({level} + INT mod) from your spellbook.'
        ),
        'prepared_spells_line_paladin': (
            'Prepared paladin spells each day: {prepared_count} (level//2 + CHA mod).'
        ),
        'prepared_after_long_rest_line': (
            'After a long rest, choose prepared spells from your class list.'
        ),
        'warlock_slots_refresh_line': 'Pact slots refresh on a short or long rest.',
        'mystic_arcanum_line': 'Mystic Arcanum gained: {arcanum}.',
        'long_rest_slots_refresh_line': 'Class spell slots refresh on a long rest.',
        'species_spellcasting_traits_line': (
            'Species traits may grant additional spells; see your racial traits section.'
        ),
        'sorcery_points_unlock_line': (
            'Font of Magic unlocks at level {unlock_level}; no sorcery points yet.'
        ),
        'sorcery_points_available_line': (
            'Sorcery Points: {sorcery_points} available (max {sorcery_points_max}); regain all on a long rest.'
        ),
        'sorcery_points_to_slots_line': (
            'Flexible Casting (sorcery points -> spell slot): {creation_costs}. Cannot create slots above {max_slot_level}th level.'
        ),
        'sorcery_points_affordable_slots_line': (
            'Current point budget can create: {affordable_costs}.'
        ),
        'sorcery_points_no_affordable_slot_line': (
            'Current point budget cannot create a spell slot yet.'
        ),
        'slot_to_sorcery_points_line': (
            'Flexible Casting (spell slot -> sorcery points): expend one slot to gain points equal to slot level; available slot levels now: {slot_levels}.'
        ),
    },
}

SPELL_SLOT_FIELD_MAP = {
    1: 'SlotsTotal 19',
    2: 'SlotsTotal 20',
    3: 'SlotsTotal 21',
    4: 'SlotsTotal 22',
    5: 'SlotsTotal 23',
    6: 'SlotsTotal 24',
    7: 'SlotsTotal 25',
    8: 'SlotsTotal 26',
    9: 'SlotsTotal 27',
}

ALL_ABILITIES = [
    'strength', 'dexterity', 'constitution',
    'intelligence', 'wisdom', 'charisma',
]

# Feature indices that grant Expertise (double proficiency on chosen skills)
# and how many skill choices each grants.
EXPERTISE_FEATURE_INDICES = {
    'rogue-expertise-1': 2,
    'rogue-expertise-2': 2,
    'bard-expertise-1': 2,
    'bard-expertise-2': 2,
}

AVAILABLE_FONTS = {
    'cinzel':        {'css': 'Cinzel:wght@400;700',         'desc': 'Elegant serif, great readability'},
    'medievalsharp': {'css': 'MedievalSharp',                'desc': 'Whimsical medieval script'},
    'almendra':      {'css': 'Almendra:wght@400;700',        'desc': 'Fantasy serif inspired by calligraphy'},
    'metamorphous':  {'css': 'Metamorphous',                 'desc': 'Dark fantasy display font'},
    'pirataone':     {'css': 'Pirata+One',                   'desc': 'Pirate/adventure theme'},
    'imfell':        {'css': 'IM+Fell+English+SC',           'desc': 'Historic English printing style'},
    'uncialantiqua': {'css': 'Uncial+Antiqua',               'desc': 'Celtic/uncial manuscript style'},
}

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS_DIR = os.path.join(BASE_DIR, '.fonts')
SPELLCARD_BACKGROUND_PATH = os.path.join(BASE_DIR, 'GUI', 'parchment_bg.jpg')


def load_spellcasting_notes(config_path=None):
    """Load spellcasting guidance (class/feat/species notes) from JSON config.

    Backward compatible with legacy format where the JSON is a plain
    class->notes mapping.
    """
    target_path = config_path or os.path.join(BASE_DIR, 'config', 'spellcasting_notes.json')
    notes = {
        'global_rules': dict(DEFAULT_SPELLCASTING_GUIDANCE['global_rules']),
        'class_rules': {k: dict(v) for k, v in DEFAULT_SPELLCASTING_GUIDANCE['class_rules'].items()},
        'class_notes': {k: list(v) for k, v in DEFAULT_SPELLCASTING_GUIDANCE['class_notes'].items()},
        'feat_note_rules': {
            'match_mode': DEFAULT_SPELLCASTING_GUIDANCE['feat_note_rules']['match_mode'],
            'use_contains_fallback': DEFAULT_SPELLCASTING_GUIDANCE['feat_note_rules']['use_contains_fallback'],
            'aliases': {
                k: list(v)
                for k, v in DEFAULT_SPELLCASTING_GUIDANCE['feat_note_rules']['aliases'].items()
            },
        },
        'feat_notes': {k: list(v) for k, v in DEFAULT_SPELLCASTING_GUIDANCE['feat_notes'].items()},
        'species_notes': {k: list(v) for k, v in DEFAULT_SPELLCASTING_GUIDANCE['species_notes'].items()},
        'sorcerer_flexible_casting': {
            'font_of_magic_unlock_level': int(
                DEFAULT_SPELLCASTING_GUIDANCE['sorcerer_flexible_casting']['font_of_magic_unlock_level']
            ),
            'max_created_slot_level': int(
                DEFAULT_SPELLCASTING_GUIDANCE['sorcerer_flexible_casting']['max_created_slot_level']
            ),
            'slot_to_point_conversion': str(
                DEFAULT_SPELLCASTING_GUIDANCE['sorcerer_flexible_casting']['slot_to_point_conversion']
            ),
            'fallback_creation_costs': [
                {
                    'spell_slot_level': int(entry['spell_slot_level']),
                    'sorcery_point_cost': int(entry['sorcery_point_cost']),
                }
                for entry in DEFAULT_SPELLCASTING_GUIDANCE['sorcerer_flexible_casting']['fallback_creation_costs']
            ],
            'fallback_sorcery_points_by_level': {
                str(level): int(value)
                for level, value in (
                    DEFAULT_SPELLCASTING_GUIDANCE['sorcerer_flexible_casting']['fallback_sorcery_points_by_level'].items()
                )
            },
        },
        'templates': dict(DEFAULT_SPELLCASTING_GUIDANCE['templates']),
    }

    if not os.path.exists(target_path):
        return notes

    try:
        with open(target_path, 'r', encoding='utf-8') as handle:
            loaded = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return notes

    if not isinstance(loaded, dict):
        return notes

    # Legacy format: {"wizard": ["..."]}
    legacy_mode = all(isinstance(value, list) for value in loaded.values())
    if legacy_mode:
        loaded = {'class_notes': loaded}

    global_rule_data = loaded.get('global_rules', {})
    if isinstance(global_rule_data, dict):
        for key, value in global_rule_data.items():
            if key in notes['global_rules'] and isinstance(value, bool):
                notes['global_rules'][key] = value

    class_rule_data = loaded.get('class_rules', {})
    if isinstance(class_rule_data, dict):
        for class_name, class_rules in class_rule_data.items():
            if not isinstance(class_name, str) or not isinstance(class_rules, dict):
                continue
            normalized_class = class_name.strip().lower()
            base_rules = dict(notes['class_rules'].get(
                normalized_class,
                DEFAULT_SPELLCASTING_GUIDANCE['class_rules'].get('wizard', {}),
            ))
            for key, value in class_rules.items():
                if key in (
                    'prepared_formula',
                    'resource_refresh',
                ) and isinstance(value, str):
                    base_rules[key] = value.strip().lower()
                elif key in (
                    'show_cantrips_known',
                    'show_spells_known',
                    'include_prepared_rest_reminder',
                    'include_mystic_arcanum',
                ) and isinstance(value, bool):
                    base_rules[key] = value
            notes['class_rules'][normalized_class] = base_rules

    feat_rule_data = loaded.get('feat_note_rules', {})
    if isinstance(feat_rule_data, dict):
        mode = feat_rule_data.get('match_mode')
        if isinstance(mode, str) and mode.strip().lower() in ('exact_normalized', 'contains_normalized'):
            notes['feat_note_rules']['match_mode'] = mode.strip().lower()

        contains_fallback = feat_rule_data.get('use_contains_fallback')
        if isinstance(contains_fallback, bool):
            notes['feat_note_rules']['use_contains_fallback'] = contains_fallback

        alias_data = feat_rule_data.get('aliases', {})
        if isinstance(alias_data, dict):
            cleaned_aliases = {}
            for feat_name, aliases in alias_data.items():
                if not isinstance(feat_name, str) or not isinstance(aliases, list):
                    continue
                cleaned = [
                    alias.strip()
                    for alias in aliases
                    if isinstance(alias, str) and alias.strip()
                ]
                if cleaned:
                    cleaned_aliases[feat_name.strip()] = cleaned
            if cleaned_aliases:
                notes['feat_note_rules']['aliases'].update(cleaned_aliases)

    for section_name in ('class_notes', 'feat_notes', 'species_notes'):
        section_data = loaded.get(section_name, {})
        if not isinstance(section_data, dict):
            continue
        for key, value in section_data.items():
            if not isinstance(key, str) or not isinstance(value, list):
                continue
            cleaned_lines = [
                line.strip()
                for line in value
                if isinstance(line, str) and line.strip()
            ]
            if cleaned_lines:
                normalized_key = key.strip()
                if section_name in ('class_notes', 'species_notes'):
                    normalized_key = normalized_key.lower()
                notes[section_name][normalized_key] = cleaned_lines

    sorcerer_data = loaded.get('sorcerer_flexible_casting', {})
    if isinstance(sorcerer_data, dict):
        unlock_level = sorcerer_data.get('font_of_magic_unlock_level')
        if isinstance(unlock_level, (int, float)) and int(unlock_level) >= 1:
            notes['sorcerer_flexible_casting']['font_of_magic_unlock_level'] = int(unlock_level)

        max_created_slot_level = sorcerer_data.get('max_created_slot_level')
        if isinstance(max_created_slot_level, (int, float)) and int(max_created_slot_level) >= 1:
            notes['sorcerer_flexible_casting']['max_created_slot_level'] = int(max_created_slot_level)

        slot_to_point_conversion = sorcerer_data.get('slot_to_point_conversion')
        if isinstance(slot_to_point_conversion, str) and slot_to_point_conversion.strip():
            notes['sorcerer_flexible_casting']['slot_to_point_conversion'] = slot_to_point_conversion.strip()

        fallback_creation_costs = sorcerer_data.get('fallback_creation_costs')
        if isinstance(fallback_creation_costs, list):
            cleaned_creation_costs = []
            for entry in fallback_creation_costs:
                if not isinstance(entry, dict):
                    continue
                slot_level = entry.get('spell_slot_level')
                point_cost = entry.get('sorcery_point_cost')
                if not isinstance(slot_level, (int, float)) or not isinstance(point_cost, (int, float)):
                    continue
                slot_level = int(slot_level)
                point_cost = int(point_cost)
                if slot_level < 1 or point_cost < 1:
                    continue
                cleaned_creation_costs.append({
                    'spell_slot_level': slot_level,
                    'sorcery_point_cost': point_cost,
                })
            if cleaned_creation_costs:
                notes['sorcerer_flexible_casting']['fallback_creation_costs'] = cleaned_creation_costs

        fallback_points = sorcerer_data.get('fallback_sorcery_points_by_level')
        if isinstance(fallback_points, dict):
            cleaned_points = {}
            for level_key, points in fallback_points.items():
                if not isinstance(points, (int, float)):
                    continue
                try:
                    normalized_level = int(str(level_key).strip())
                except ValueError:
                    continue
                if normalized_level < 1:
                    continue
                cleaned_points[str(normalized_level)] = int(points)
            if cleaned_points:
                notes['sorcerer_flexible_casting']['fallback_sorcery_points_by_level'] = cleaned_points

    template_data = loaded.get('templates', {})
    if isinstance(template_data, dict):
        for key, value in template_data.items():
            if isinstance(key, str) and isinstance(value, str) and value.strip():
                notes['templates'][key.strip()] = value.strip()

    return notes


def load_asi_weight_config(config_path=None):
    """Load class/species ASI weighting rules from JSON config."""
    default_config = {
        'global': {
            'class_primary_weight': 220,
            'class_secondary_weight': 95,
            'spellcasting_weight': 115,
            'species_weight_scale': 20,
            'under_cap_weight': 1,
            'odd_score_weight': 14,
            'sub_ten_weight': 90,
            'important_below_floor_weight': 130,
            'important_floor_target': 14,
            'important_floor_trigger': 10,
            'force_asi_when_important_below_floor': True,
        },
        'class_priorities': {},
        'species_modifiers': {},
    }

    target_path = config_path or os.path.join(BASE_DIR, 'config', 'ability_score_weights.json')
    if not os.path.exists(target_path):
        return default_config

    try:
        with open(target_path, 'r', encoding='utf-8') as handle:
            loaded = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return default_config

    if not isinstance(loaded, dict):
        return default_config

    config = {
        'global': dict(default_config['global']),
        'class_priorities': dict(default_config['class_priorities']),
        'species_modifiers': dict(default_config['species_modifiers']),
    }

    global_cfg = loaded.get('global', {})
    if isinstance(global_cfg, dict):
        for key, value in global_cfg.items():
            if key in config['global'] and isinstance(value, (int, float, bool)):
                config['global'][key] = value

    class_cfg = loaded.get('class_priorities', {})
    if isinstance(class_cfg, dict):
        for class_name, priority_data in class_cfg.items():
            if not isinstance(class_name, str) or not isinstance(priority_data, dict):
                continue
            normalized = class_name.strip().lower()
            config['class_priorities'][normalized] = {
                'primary': [a for a in priority_data.get('primary', []) if a in ALL_ABILITIES],
                'secondary': [a for a in priority_data.get('secondary', []) if a in ALL_ABILITIES],
            }

    species_cfg = loaded.get('species_modifiers', {})
    if isinstance(species_cfg, dict):
        for species_name, weights in species_cfg.items():
            if not isinstance(species_name, str) or not isinstance(weights, dict):
                continue
            normalized_species = species_name.strip().lower()
            cleaned = {}
            for ability, weight in weights.items():
                if ability in ALL_ABILITIES and isinstance(weight, (int, float)):
                    cleaned[ability] = float(weight)
            if cleaned:
                config['species_modifiers'][normalized_species] = cleaned

    return config


SPELLCASTING_GUIDANCE = load_spellcasting_notes()
SPELLCASTING_NOTES = SPELLCASTING_GUIDANCE['class_notes']
ASI_WEIGHT_CONFIG = load_asi_weight_config()
FEAT_CONFIG = load_feat_config()



class Character:
    def __init__(self, name, species, char_class, sex, level, seed=None):
        self.name = name
        self.species = species
        self.sex = sex
        self.char_class = char_class
        self.level = int(level)
        self.seed = seed
        self.rng = random.Random(seed) if seed is not None else random
        self.strength = 0
        self.dexterity = 0
        self.constitution = 0
        self.intelligence = 0
        self.wisdom = 0
        self.charisma = 0
        self.hp = 0
        char_class_attribute = getattr(Classes, self.char_class)
        self.hit_die = f'd{char_class_attribute.hit_die}'
        self.skill_proficiencies = []
        self.expertise_skills = []    # skills with doubled proficiency bonus
        self.jack_of_all_trades = False  # bard: half prof on non-proficient skills
        self.extra_languages = []        # from racial language choices
        self.asi_log = []                # track each ASI taken {ability: bonus}
        self.advancement_log = []        # ordered ASI-vs-feat selections
        self.progression_choices = []    # ordered subclass/feature/spell decisions
        self.feats = []                  # optional selected feats (dict/object/string)
        self.speed_bonus = 0
        self.initiative_bonus = 0
        self.passive_perception_bonus = 0
        self.hp_bonus_per_level = 0
        self.armor_class_bonus = 0
        self.ranged_attack_bonus = 0
        self.aggressive_asi_focus = set()
        self.proficiencies = []
        self.equipment = []
        self.subclass = None
        self.subclass_index = None
        self.feature_annotations = {}
        self.bonus_features_by_level = {}
        self.class_feature_choices = []
        self.class_specific_by_level = {}
        self.class_specific_current = {}
        self.progression_built_to_level = 0
        self.applied_subclass_feature_levels = set()
        self.spellcasting_profile = None
        self.saving_throw_proficiencies = [
            st['name'] for st in char_class_attribute.saving_throws
        ]

    def hit_die_total(self):
        return f"{self.level}{self.hit_die}"

    def proficiency_bonus(self):
        class_levels = getattr(Levels, f"{self.char_class}_{self.level}")
        return class_levels.prof_bonus

    def ability_score_improvements(self):
        """Return the total number of ASIs granted at the current level.

        Uses feature scanning rather than the ability_score_bonuses field from
        tinys_srd, which is known to report an incorrect value of 5 (instead of
        6) for the Rogue at level 20.
        """
        count = 0
        for lvl in range(1, self.level + 1):
            level_data = getattr(Levels, f"{self.char_class}_{lvl}")
            for feat in level_data.features:
                if feat['name'] == 'Ability Score Improvement':
                    count += 1
        return count

    def _feature_label(self, level, feature, annotated=False, advancement_index=None):
        feature_index = feature.get('index', feature['name'])
        if (
            annotated
            and feature['name'] == 'Ability Score Improvement'
            and advancement_index is not None
            and advancement_index < len(self.advancement_log)
        ):
            record = self.advancement_log[advancement_index]
            if record.get('type') == 'feat':
                return record['feat'].get('summary', record['feat'].get('name', feature['name']))
            bonuses = record.get('ability_bonuses', {})
            parts = [f"+{value} {ability[:3].upper()}" for ability, value in bonuses.items() if value > 0]
            if parts:
                return f"Ability Score Improvement ({', '.join(parts)})"
        return self.feature_annotations.get((level, feature_index), feature['name'])

    def _collect_feature_names(self, annotated=False):
        features = []
        advancement_index = 0
        for lvl in range(1, self.level + 1):
            level_data = getattr(Levels, f"{self.char_class}_{lvl}")
            for feature in level_data.features:
                features.append(
                    self._feature_label(
                        lvl,
                        feature,
                        annotated=annotated,
                        advancement_index=advancement_index,
                    )
                )
                if feature['name'] == 'Ability Score Improvement':
                    advancement_index += 1
            features.extend(self.bonus_features_by_level.get(lvl, []))
        return features

    def _collect_feature_entries(self, annotated=False):
        """Return ordered (level, label) entries for class/subclass features."""
        entries = []
        advancement_index = 0
        for lvl in range(1, self.level + 1):
            level_data = getattr(Levels, f"{self.char_class}_{lvl}")
            for feature in level_data.features:
                entries.append((
                    lvl,
                    self._feature_label(
                        lvl,
                        feature,
                        annotated=annotated,
                        advancement_index=advancement_index,
                    ),
                ))
                if feature['name'] == 'Ability Score Improvement':
                    advancement_index += 1
            for bonus_feature in self.bonus_features_by_level.get(lvl, []):
                entries.append((lvl, bonus_feature))
        return entries

    def _condense_feature_entries(self, entries):
        """Collapse repeated features into one line with counts and levels."""
        order = []
        levels_by_label = {}
        for level, label in entries:
            if label not in levels_by_label:
                levels_by_label[label] = []
                order.append(label)
            levels_by_label[label].append(level)

        condensed = []
        for label in order:
            levels = levels_by_label[label]
            if len(levels) <= 1:
                condensed.append(label)
                continue
            level_text = ', '.join(f"lv {lvl}" for lvl in levels)
            condensed.append(f"{label} ({len(levels)}x: {level_text})")
        return condensed

    def get_features(self):
        return self._collect_feature_names(annotated=False)

    def get_features_annotated(self):
        """Return features with progression choices and ASI entries annotated."""
        return self._collect_feature_names(annotated=True)

    def get_features_annotated_condensed(self):
        """Return annotated features with repeated items collapsed by level."""
        return self._condense_feature_entries(self._collect_feature_entries(annotated=True))

    def armor_class(self):
        return 10 + modifier(self.dexterity) + self.armor_class_bonus

    def get_speed(self):
        species_key = self.species.lower()
        race_data = getattr(Species, species_key)
        return race_data.speed + self.speed_bonus

    def get_languages(self):
        species_key = self.species.lower()
        race_data = getattr(Species, species_key)
        languages = [lang['name'] for lang in race_data.languages]
        languages.extend(self.extra_languages)
        # Rogues learn Thieves' Cant as a secret language at level 1
        if "Thieves' Cant" in self.get_features() and "Thieves' Cant" not in languages:
            languages.append("Thieves' Cant")
        return list(dict.fromkeys(languages))

    def selected_feat_names(self):
        return [feat.get('name', str(feat)) for feat in self.feats if isinstance(feat, dict)]

    def passive_perception(self):
        return 10 + self.skill_modifier('Perception') + self.passive_perception_bonus

    def _spellcaster_notes(self, prof_bonus, spellbook=None):
        if self.char_class not in SPELLCASTING_ABILITY:
            return []

        notes = []

        def append_unique(line):
            if line and line not in notes:
                notes.append(line)

        templates = SPELLCASTING_GUIDANCE.get('templates', {})
        global_rules = SPELLCASTING_GUIDANCE.get('global_rules', {})
        class_rules = SPELLCASTING_GUIDANCE.get('class_rules', {}).get(self.char_class, {})
        feat_note_rules = SPELLCASTING_GUIDANCE.get('feat_note_rules', {})

        def render(template_key, default, **values):
            template = templates.get(template_key, default)
            try:
                return template.format(**values)
            except (KeyError, ValueError):
                return default.format(**values)

        def normalize_feat_name(value):
            return ''.join(ch.lower() for ch in str(value) if ch.isalnum())

        def feat_note_applies(note_key, selected_names):
            normalized_selected = [normalize_feat_name(name) for name in selected_names]
            normalized_note = normalize_feat_name(note_key)

            aliases = feat_note_rules.get('aliases', {}).get(note_key, [])
            normalized_aliases = [normalize_feat_name(alias) for alias in aliases]
            candidates = [normalized_note] + [alias for alias in normalized_aliases if alias]

            match_mode = str(feat_note_rules.get('match_mode', 'exact_normalized')).lower()
            use_contains_fallback = bool(feat_note_rules.get('use_contains_fallback', True))

            def exact_match():
                return any(candidate and candidate in normalized_selected for candidate in candidates)

            def contains_match():
                for selected in normalized_selected:
                    if not selected:
                        continue
                    for candidate in candidates:
                        if candidate and (candidate in selected or selected in candidate):
                            return True
                return False

            if match_mode == 'contains_normalized':
                return contains_match()
            if exact_match():
                return True
            if use_contains_fallback:
                return contains_match()
            return False

        ability = SPELLCASTING_ABILITY[self.char_class]
        ability_mod = modifier(getattr(self, ability))
        save_dc = 8 + prof_bonus + ability_mod
        attack_bonus = prof_bonus + ability_mod

        include_basics = bool(global_rules.get('include_spell_use_basics', True))
        if include_basics:
            append_unique(render(
                'spell_use_basics_header',
                'Spell Use Basics:'
            ))
            append_unique(render(
                'spellcasting_ability_line',
                'Spellcasting ability: {ability_name} ({ability_mod:+d}).',
                ability_name=ability.capitalize(),
                ability_mod=ability_mod,
            ))
            append_unique(render(
                'spell_save_dc_line',
                'Spell Save DC: {save_dc}.',
                save_dc=save_dc,
            ))
            append_unique(render(
                'spell_attack_bonus_line',
                'Spell Attack Bonus: +{attack_bonus}.',
                attack_bonus=attack_bonus,
            ))

        level_data = getattr(Levels, f"{self.char_class}_{self.level}")
        spellcasting = getattr(level_data, 'spellcasting', None) or {}
        cantrips_known = int(spellcasting.get('cantrips_known', 0) or 0)
        spells_known = int(spellcasting.get('spells_known', 0) or 0)
        if class_rules.get('show_cantrips_known', True) and cantrips_known > 0:
            append_unique(render(
                'cantrips_known_line',
                'Cantrips known: {cantrips_known}.',
                cantrips_known=cantrips_known,
            ))
        if class_rules.get('show_spells_known', True) and spells_known > 0:
            append_unique(render(
                'spells_known_line',
                'Spells known from class: {spells_known}.',
                spells_known=spells_known,
            ))

        if self.char_class == 'sorcerer':
            sorcerer_rules = SPELLCASTING_GUIDANCE.get('sorcerer_flexible_casting', {})
            unlock_level = int(sorcerer_rules.get('font_of_magic_unlock_level', 2) or 2)
            max_created_slot_level = int(sorcerer_rules.get('max_created_slot_level', 5) or 5)

            class_specific = getattr(level_data, 'class_specific', None) or {}

            fallback_points = sorcerer_rules.get('fallback_sorcery_points_by_level', {})
            fallback_points_by_level = {
                str(level): int(points)
                for level, points in fallback_points.items()
                if isinstance(level, str) and isinstance(points, (int, float))
            }

            sorcery_points_max = int(class_specific.get('sorcery_points', 0) or 0)
            if sorcery_points_max <= 0:
                sorcery_points_max = int(
                    fallback_points_by_level.get(str(self.level), max(0, self.level if self.level >= unlock_level else 0))
                )

            if self.level < unlock_level:
                append_unique(render(
                    'sorcery_points_unlock_line',
                    'Font of Magic unlocks at level {unlock_level}; no sorcery points yet.',
                    unlock_level=unlock_level,
                ))
            else:
                append_unique(render(
                    'sorcery_points_available_line',
                    'Sorcery Points: {sorcery_points} available (max {sorcery_points_max}); regain all on a long rest.',
                    sorcery_points=sorcery_points_max,
                    sorcery_points_max=sorcery_points_max,
                ))

                creation_options = class_specific.get('creating_spell_slots', [])
                if not isinstance(creation_options, list) or not creation_options:
                    creation_options = sorcerer_rules.get('fallback_creation_costs', [])

                cleaned_creation_options = []
                for entry in creation_options:
                    if not isinstance(entry, dict):
                        continue
                    slot_level = entry.get('spell_slot_level')
                    point_cost = entry.get('sorcery_point_cost')
                    if not isinstance(slot_level, (int, float)) or not isinstance(point_cost, (int, float)):
                        continue
                    slot_level = int(slot_level)
                    point_cost = int(point_cost)
                    if slot_level < 1 or point_cost < 1 or slot_level > max_created_slot_level:
                        continue
                    cleaned_creation_options.append((slot_level, point_cost))

                cleaned_creation_options.sort(key=lambda pair: pair[0])
                if cleaned_creation_options:
                    creation_costs = ', '.join(
                        f"{_ordinal(slot_level)} ({point_cost} SP)"
                        for slot_level, point_cost in cleaned_creation_options
                    )
                    append_unique(render(
                        'sorcery_points_to_slots_line',
                        'Flexible Casting (sorcery points -> spell slot): {creation_costs}. Cannot create slots above {max_slot_level}th level.',
                        creation_costs=creation_costs,
                        max_slot_level=max_created_slot_level,
                    ))

                    affordable_options = [
                        (slot_level, point_cost)
                        for slot_level, point_cost in cleaned_creation_options
                        if point_cost <= sorcery_points_max
                    ]
                    if affordable_options:
                        affordable_costs = ', '.join(
                            f"{_ordinal(slot_level)} ({point_cost} SP)"
                            for slot_level, point_cost in affordable_options
                        )
                        append_unique(render(
                            'sorcery_points_affordable_slots_line',
                            'Current point budget can create: {affordable_costs}.',
                            affordable_costs=affordable_costs,
                        ))
                    else:
                        append_unique(render(
                            'sorcery_points_no_affordable_slot_line',
                            'Current point budget cannot create a spell slot yet.',
                        ))

                slot_levels = []
                for slot_level in range(1, 10):
                    slot_count = int(spellcasting.get(f'spell_slots_level_{slot_level}', 0) or 0)
                    if slot_count <= 0:
                        continue
                    slot_levels.append(f"{_ordinal(slot_level)} x{slot_count}")

                if slot_levels:
                    append_unique(render(
                        'slot_to_sorcery_points_line',
                        'Flexible Casting (spell slot -> sorcery points): expend one slot to gain points equal to slot level; available slot levels now: {slot_levels}.',
                        slot_levels=', '.join(slot_levels),
                    ))

        prepared_formula = class_rules.get('prepared_formula', 'none')
        if prepared_formula == 'level_plus_mod':
            prepare_count = max(1, self.level + ability_mod)
            append_unique(render(
                'prepared_spells_line_cleric_druid',
                'Prepared spells each day: {prepared_count} ({level} + {ability_name_short} mod).',
                prepared_count=prepare_count,
                level=self.level,
                ability_name_short=ability.capitalize(),
            ))
            if class_rules.get('include_prepared_rest_reminder', False):
                append_unique(render(
                    'prepared_after_long_rest_line',
                    'After a long rest, choose prepared spells from your class list.'
                ))
        elif prepared_formula == 'wizard':
            prepare_count = max(1, self.level + ability_mod)
            append_unique(render(
                'prepared_spells_line_wizard',
                'Prepared wizard spells each day: {prepared_count} ({level} + INT mod) from your spellbook.',
                prepared_count=prepare_count,
                level=self.level,
            ))
        elif prepared_formula == 'half_level_plus_mod':
            prepare_count = max(1, (self.level // 2) + ability_mod)
            append_unique(render(
                'prepared_spells_line_paladin',
                'Prepared paladin spells each day: {prepared_count} (level//2 + CHA mod).',
                prepared_count=prepare_count,
            ))

        resource_refresh = class_rules.get('resource_refresh', 'long_rest')
        if resource_refresh == 'warlock':
            append_unique(render(
                'warlock_slots_refresh_line',
                'Pact slots refresh on a short or long rest.'
            ))
        else:
            append_unique(render(
                'long_rest_slots_refresh_line',
                'Class spell slots refresh on a long rest.'
            ))

        if class_rules.get('include_mystic_arcanum', False):
            arcanum = [
                feature['name'] for feature in level_data.features
                if 'Mystic Arcanum' in feature.get('name', '')
            ]
            if arcanum:
                append_unique(render(
                    'mystic_arcanum_line',
                    'Mystic Arcanum gained: {arcanum}.',
                    arcanum=', '.join(arcanum),
                ))

        for line in SPELLCASTING_GUIDANCE.get('class_notes', {}).get(self.char_class, []):
            append_unique(line)

        for line in SPELLCASTING_GUIDANCE.get('species_notes', {}).get(self.species.lower(), []):
            append_unique(line)

        selected_feats = self.selected_feat_names()
        for feat_name, feat_lines in SPELLCASTING_GUIDANCE.get('feat_notes', {}).items():
            if feat_note_applies(feat_name, selected_feats):
                for line in feat_lines:
                    append_unique(line)

        include_species_hint = bool(global_rules.get('include_species_trait_spellcasting_hint', True))
        if include_species_hint and any('Spellcasting' in trait for trait in self.get_traits()):
            append_unique(render(
                'species_spellcasting_traits_line',
                'Species traits may grant additional spells; see your racial traits section.'
            ))

        if self.subclass:
            append_unique(f'Subclass: {self.subclass}.')

        if spellbook:
            focus = spellbook.get('spell_focus', {})
            if focus:
                summary_parts = []
                for key in ('concentration', 'control', 'healing', 'ritual', 'damage'):
                    count = int(focus.get(key, 0) or 0)
                    if count > 0:
                        summary_parts.append(f'{count} {key}')
                if summary_parts:
                    append_unique(f"Current spell focus: {', '.join(summary_parts)}.")

            replacements = spellbook.get('replacement_log', [])
            if replacements:
                latest = replacements[-1]
                append_unique(
                    f"Latest spell swap: {latest['replaced']} -> {latest['new_spell']} at level {latest['level']}."
                )

        return notes

    def _progression_notes(self):
        notes = []
        if self.subclass:
            notes.append(f'Subclass: {self.subclass}.')

        grouped = {}
        for record in self.class_feature_choices:
            feature_name = record.get('feature_name', 'Feature')
            choice_name = record.get('choice_name', '')
            if ': ' in choice_name:
                choice_name = choice_name.split(': ', 1)[1]
            grouped.setdefault(feature_name, [])
            if choice_name and choice_name not in grouped[feature_name]:
                grouped[feature_name].append(choice_name)

        for feature_name, choice_names in grouped.items():
            notes.append(f"{feature_name}: {', '.join(choice_names)}.")

        return notes

    def _split_feature_trait_lines(self, lines, first_page_max_lines=30):
        """Split one feature/trait stream into page 1 then page 2 continuation."""
        if len(lines) <= first_page_max_lines:
            return lines, []

        page_one = list(lines[:first_page_max_lines])
        page_two = list(lines[first_page_max_lines:])

        # Avoid awkward duplicate blank boundary when splitting.
        while page_one and page_two and page_one[-1] == '' and page_two[0] == '':
            page_two.pop(0)

        return page_one, page_two

    def get_traits(self):
        species_key = self.species.lower()
        race_data = getattr(Species, species_key)
        return [trait['name'] for trait in race_data.traits]

    def apply_racial_bonuses(self):
        species_key = self.species.lower()
        race_data = getattr(Species, species_key)
        for bonus in race_data.ability_bonuses:
            ability = ABILITY_INDEX_MAP[bonus['ability_score']['index']]
            current = getattr(self, ability)
            setattr(self, ability, current + bonus['bonus'])

    def apply_asi_level(self, asi_level):
        spellcast_ability = SPELLCASTING_ABILITY.get(self.char_class)

        aggressive_focus = self._refresh_aggressive_asi_focus()
        force_asi = bool(
            ASI_WEIGHT_CONFIG['global'].get('force_asi_when_important_below_floor', True)
            and aggressive_focus
        )

        if not force_asi:
            selected_feat = choose_feat_for_character(self, asi_level, FEAT_CONFIG, rng=self.rng)
            if selected_feat is not None:
                self._apply_selected_feat(selected_feat)
                self.advancement_log.append({'type': 'feat', 'feat': selected_feat})
                return

        prefer_sc = (spellcast_ability if (spellcast_ability and asi_level <= 15) else None)
        prioritize_sub_ten = asi_level < 10
        first, second = self._rank_asi_candidates(
            prefer_spellcast_ability=prefer_sc,
            prioritize_sub_ten=prioritize_sub_ten,
            aggressive_focus=aggressive_focus,
        )

        asi_record = {}
        for ability in (entry for entry in (first, second) if entry is not None):
            score = getattr(self, ability)
            if score < 20:
                setattr(self, ability, score + 1)
                asi_record[ability] = asi_record.get(ability, 0) + 1
        self.asi_log.append(asi_record)
        self.advancement_log.append({'type': 'asi', 'ability_bonuses': asi_record})

    def apply_asi(self):
        """Apply all Ability Score Improvements earned up to the current level."""
        for lvl in range(1, self.level + 1):
            level_data = getattr(Levels, f"{self.char_class}_{lvl}")
            for feat in level_data.features:
                if feat['name'] == 'Ability Score Improvement':
                    self.apply_asi_level(lvl)

    def _rank_asi_candidates(self, prefer_spellcast_ability, prioritize_sub_ten=False, aggressive_focus=None):
        """Return (first, second) ability names for one ASI (+2 points total).

        first  — highest-priority target for the first +1 point
        second — highest-priority target for the second +1 point (may equal
                 first only when every other ability is already at 20)

        Priority order for each point:
          1) abilities below 10 (when prioritize_sub_ten=True)
          2) spellcasting ability (when preferred)
          3) odd abilities (odd+1 = even -> +1 modifier step)
          4) any ability below cap
        """
        under_cap = [a for a in ALL_ABILITIES if getattr(self, a) < 20]
        if not under_cap:
            return None, None

        first = self._best_asi_ability(
            candidates=under_cap,
            prefer_spellcast_ability=prefer_spellcast_ability,
            prioritize_sub_ten=prioritize_sub_ten,
            aggressive_focus=aggressive_focus,
        )

        if first is None:
            return None, None

        setattr(self, first, getattr(self, first) + 1)
        try:
            still_under_cap = [a for a in ALL_ABILITIES if getattr(self, a) < 20]
            second_pool = still_under_cap or [first]
            second = self._best_asi_ability(
                candidates=second_pool,
                prefer_spellcast_ability=prefer_spellcast_ability,
                prioritize_sub_ten=prioritize_sub_ten,
                aggressive_focus=aggressive_focus,
            )
        finally:
            setattr(self, first, getattr(self, first) - 1)

        if second is None:
            second = first

        return first, second

    def _important_abilities(self, prefer_spellcast_ability=None, primary_only=False):
        class_cfg = ASI_WEIGHT_CONFIG.get('class_priorities', {}).get(self.char_class, {})
        primary = class_cfg.get('primary', [])
        secondary = [] if primary_only else class_cfg.get('secondary', [])

        ordered = []
        for ability in primary + secondary:
            if ability in ALL_ABILITIES and ability not in ordered:
                ordered.append(ability)
        if prefer_spellcast_ability and prefer_spellcast_ability in ALL_ABILITIES and prefer_spellcast_ability not in ordered:
            ordered.append(prefer_spellcast_ability)
        return ordered

    def _refresh_aggressive_asi_focus(self):
        cfg = ASI_WEIGHT_CONFIG.get('global', {})
        trigger = int(cfg.get('important_floor_trigger', 10))
        floor = int(cfg.get('important_floor_target', 14))
        important = self._important_abilities(
            SPELLCASTING_ABILITY.get(self.char_class),
            primary_only=True,
        )

        if not self.aggressive_asi_focus:
            for ability in important:
                if getattr(self, ability) < trigger:
                    self.aggressive_asi_focus.add(ability)

        self.aggressive_asi_focus = {
            ability for ability in self.aggressive_asi_focus
            if getattr(self, ability) < floor and getattr(self, ability) < 20
        }
        return set(self.aggressive_asi_focus)

    def _ability_investment_score(self, ability, prefer_spellcast_ability, prioritize_sub_ten, aggressive_focus):
        cfg = ASI_WEIGHT_CONFIG.get('global', {})
        class_cfg = ASI_WEIGHT_CONFIG.get('class_priorities', {}).get(self.char_class, {})
        species_cfg = ASI_WEIGHT_CONFIG.get('species_modifiers', {}).get(self.species.lower(), {})

        current = getattr(self, ability)
        score = 0.0

        if ability in class_cfg.get('primary', []):
            score += float(cfg.get('class_primary_weight', 0))
        if ability in class_cfg.get('secondary', []):
            score += float(cfg.get('class_secondary_weight', 0))
        if prefer_spellcast_ability and ability == prefer_spellcast_ability:
            score += float(cfg.get('spellcasting_weight', 0))

        score += float(species_cfg.get(ability, 0)) * float(cfg.get('species_weight_scale', 0))
        score += max(0, 20 - current) * float(cfg.get('under_cap_weight', 0))

        if current % 2 == 1:
            score += float(cfg.get('odd_score_weight', 0))
        if prioritize_sub_ten and current < 10:
            score += float(cfg.get('sub_ten_weight', 0))

        floor = int(cfg.get('important_floor_target', 14))
        if ability in aggressive_focus and current < floor:
            score += float(cfg.get('important_below_floor_weight', 0)) * (floor - current)

        return score

    def _best_asi_ability(self, candidates, prefer_spellcast_ability, prioritize_sub_ten, aggressive_focus):
        if not candidates:
            return None

        aggressive_focus = aggressive_focus or set()

        best = None
        best_score = None
        for ability in ALL_ABILITIES:
            if ability not in candidates:
                continue
            score = self._ability_investment_score(
                ability=ability,
                prefer_spellcast_ability=prefer_spellcast_ability,
                prioritize_sub_ten=prioritize_sub_ten,
                aggressive_focus=aggressive_focus,
            )
            if best is None or score > best_score:
                best = ability
                best_score = score
        return best

    def apply_feat_ability_bonuses(self):
        """Apply any feat effects that were injected but not yet applied.

        This method is intentionally permissive because feat payloads can come
        from different sources. Supported feat shapes include:
          - dict with key `ability_bonuses`
          - object with attribute `ability_bonuses`

        Each bonus entry should provide ability metadata with index/name and a
        numeric `bonus`. Unknown shapes are ignored safely.
        """
        for feat in self.feats:
            if isinstance(feat, dict) and feat.get('_applied'):
                continue
            bonuses = []
            if isinstance(feat, dict):
                if (
                    feat.get('selected_ability_bonuses')
                    or feat.get('selected_languages')
                    or feat.get('selected_proficiencies')
                    or feat.get('selected_saving_throw')
                ):
                    self._apply_feat_effects(feat)
                    feat['_applied'] = True
                    continue
                bonuses = feat.get('ability_bonuses', []) or []
            elif hasattr(feat, 'ability_bonuses'):
                bonuses = getattr(feat, 'ability_bonuses') or []

            for bonus in bonuses:
                ability_ref = bonus.get('ability_score', {}) if isinstance(bonus, dict) else {}
                ability_key = self._normalize_ability_key(ability_ref)
                bonus_value = bonus.get('bonus', 0) if isinstance(bonus, dict) else 0
                if ability_key and isinstance(bonus_value, int) and bonus_value > 0:
                    current = getattr(self, ability_key)
                    setattr(self, ability_key, min(20, current + bonus_value))

    def _apply_selected_feat(self, feat):
        self._apply_feat_effects(feat)
        feat['_applied'] = True
        self.feats.append(feat)

    def _apply_feat_effects(self, feat):
        for ability_name, bonus in feat.get('selected_ability_bonuses', {}).items():
            current = getattr(self, ability_name)
            setattr(self, ability_name, min(20, current + int(bonus)))

        for language_name in feat.get('selected_languages', []):
            if language_name not in self.extra_languages:
                self.extra_languages.append(language_name)

        for proficiency_name in feat.get('selected_proficiencies', []):
            if proficiency_name in SKILLS and proficiency_name not in self.skill_proficiencies:
                self.skill_proficiencies.append(proficiency_name)
            elif proficiency_name.startswith('Skill: '):
                skill_name = proficiency_name.replace('Skill: ', '')
                if skill_name not in self.skill_proficiencies:
                    self.skill_proficiencies.append(skill_name)
            elif proficiency_name not in self.proficiencies:
                self.proficiencies.append(proficiency_name)

        selected_save = feat.get('selected_saving_throw')
        if selected_save:
            save_name = selected_save[:3].upper()
            if save_name not in self.saving_throw_proficiencies:
                self.saving_throw_proficiencies.append(save_name)

        grants = feat.get('grants', {})
        self.speed_bonus += int(grants.get('speed_bonus', 0))
        self.initiative_bonus += int(grants.get('initiative_bonus', 0))
        self.passive_perception_bonus += int(grants.get('passive_perception_bonus', 0))
        self.hp_bonus_per_level += int(grants.get('hp_per_level_bonus', 0))

    def _normalize_ability_key(self, ability_ref):
        """Normalize SRD-like ability references to internal attribute names."""
        if isinstance(ability_ref, dict):
            index = str(ability_ref.get('index', '')).lower()
            name = str(ability_ref.get('name', '')).lower()
            if index in ABILITY_INDEX_MAP:
                return ABILITY_INDEX_MAP[index]
            if index in ABILITY_INDEX_MAP.values():
                return index
            if name in ABILITY_INDEX_MAP:
                return ABILITY_INDEX_MAP[name]
            if name in ABILITY_INDEX_MAP.values():
                return name
            return None
        if isinstance(ability_ref, str):
            key = ability_ref.lower().strip()
            if key in ABILITY_INDEX_MAP:
                return ABILITY_INDEX_MAP[key]
            if key in ABILITY_INDEX_MAP.values():
                return key
        return None

    def choose_skill_proficiencies(self):
        cls = getattr(Classes, self.char_class)
        for choice in cls.proficiency_choices:
            if choice['type'] == 'proficiencies':
                options = choice['from']['options']
                skill_options = []
                for o in options:
                    if (o.get('option_type') == 'reference' and
                            o.get('item', {}).get('name', '').startswith('Skill:')):
                        skill_name = o['item']['name'].replace('Skill: ', '')
                        skill_options.append(skill_name)
                if skill_options:
                    num_choose = min(choice['choose'], len(skill_options))
                    self.skill_proficiencies = self.rng.sample(skill_options, num_choose)

    def skill_modifier(self, skill_name):
        skill_info = SKILLS[skill_name]
        ability = skill_info['ability']
        ability_score = getattr(self, ability)
        mod = modifier(ability_score)
        prof = self.proficiency_bonus()
        if skill_name in self.expertise_skills:
            mod += prof * 2
        elif skill_name in self.skill_proficiencies:
            mod += prof
        elif self.jack_of_all_trades:
            # Half proficiency bonus (floor) on non-proficient skills
            mod += prof // 2
        return mod

    def choose_expertise(self):
        """Randomly assign Expertise skills from existing skill proficiencies."""
        for lvl in range(1, self.level + 1):
            level_data = getattr(Levels, f"{self.char_class}_{lvl}")
            for feat in level_data.features:
                feat_index = feat.get('index', '')
                if feat_index in EXPERTISE_FEATURE_INDICES:
                    num_pick = EXPERTISE_FEATURE_INDICES[feat_index]
                    eligible = [s for s in self.skill_proficiencies
                                if s not in self.expertise_skills]
                    num_pick = min(num_pick, len(eligible))
                    if num_pick > 0:
                        self.expertise_skills.extend(
                            self.rng.sample(eligible, num_pick)
                        )

    def apply_jack_of_all_trades(self):
        """Set the JOAT flag if the character has the Jack of All Trades feature."""
        self.jack_of_all_trades = 'Jack of All Trades' in self.get_features()

    def choose_racial_options(self):
        """Pick additional languages and proficiencies granted by racial traits."""
        species_key = self.species.lower()
        race_data = getattr(Species, species_key)

        # Extra language choices (Human: +1, Half-Elf: +1)
        if hasattr(race_data, 'language_options') and race_data.language_options:
            lang_opts = race_data.language_options
            options = lang_opts['from']['options']
            num_choose = min(lang_opts['choose'], len(options))
            chosen = self.rng.sample(options, num_choose)
            for opt in chosen:
                lang_name = opt['item']['name']
                if lang_name not in self.extra_languages:
                    self.extra_languages.append(lang_name)

        # Extra proficiency choices (Dwarf: artisan tool, Half-Elf: 2 skills)
        if hasattr(race_data, 'starting_proficiency_options') and race_data.starting_proficiency_options:
            prof_opts = race_data.starting_proficiency_options
            options = prof_opts['from']['options']
            num_choose = min(prof_opts['choose'], len(options))
            chosen = self.rng.sample(options, num_choose)
            for opt in chosen:
                prof_name = opt['item']['name']
                if prof_name.startswith('Skill: '):
                    skill_name = prof_name.replace('Skill: ', '')
                    if skill_name not in self.skill_proficiencies:
                        self.skill_proficiencies.append(skill_name)
                else:
                    if prof_name not in self.proficiencies:
                        self.proficiencies.append(prof_name)

    def populate_proficiencies(self):
        """Add class armor/weapon/tool proficiencies and racial proficiencies."""
        cls = getattr(Classes, self.char_class)
        for p in cls.proficiencies:
            name = p['name']
            # Skip saving throws (tracked separately)
            if name.startswith('Saving Throw:'):
                continue
            if name not in self.proficiencies:
                self.proficiencies.append(name)
        # Racial starting proficiencies
        species_key = self.species.lower()
        race_data = getattr(Species, species_key)
        for p in race_data.starting_proficiencies:
            name = p['name']
            if name not in self.proficiencies:
                self.proficiencies.append(name)

    def roll_stats(self):
        self.strength = stat_generator()
        self.dexterity = stat_generator()
        self.constitution = stat_generator()
        self.intelligence = stat_generator()
        self.wisdom = stat_generator()
        self.charisma = stat_generator()
        self.apply_racial_bonuses()
        self.choose_skill_proficiencies()
        self.populate_proficiencies()
        self.choose_racial_options()        # racial language & proficiency picks
        ensure_progression(self)
        self.choose_expertise()             # Expertise from class features
        self.apply_jack_of_all_trades()     # JOAT half-prof flag
        self.apply_feat_ability_bonuses()   # apply any externally injected pending feats
        self.hp = hp(level=self.level, constitution=self.constitution,
                 hit_die=self.hit_die) + (self.hp_bonus_per_level * self.level)

    def level_up(self):
        self.level += 1

    def add_proficiency(self, proficiency):
        self.proficiencies.append(proficiency)

    def add_equipment(self, equipment):
        self.equipment.append(equipment)

    def equipment_name(self, equipment):
        equipment_index = getattr(Equipment, equipment)
        return equipment_index.name

    def display_character_sheet(self):
        character_sheet = f"""
        Character Sheet:

        Name: {self.name}
        Sex: {self.sex}
        Species: {self.species}
        Class: {self.char_class.capitalize()}
        Level: {self.level}
        HP: {self.hp}
        AC: {self.armor_class()}
        Speed: {self.get_speed()} ft
        Strength: {self.strength} ({modifier(self.strength):+d})
        Dexterity: {self.dexterity} ({modifier(self.dexterity):+d})
        Constitution: {self.constitution} ({modifier(self.constitution):+d})
        Intelligence: {self.intelligence} ({modifier(self.intelligence):+d})
        Wisdom: {self.wisdom} ({modifier(self.wisdom):+d})
        Charisma: {self.charisma} ({modifier(self.charisma):+d})
        Hit Dice: {self.hit_die_total()}
        Proficiency Bonus: +{self.proficiency_bonus()}
        Skill Proficiencies: {', '.join(self.skill_proficiencies)}
        Languages: {', '.join(self.get_languages())}
        Features: {', '.join(self.get_features_annotated())}
        """
        print(character_sheet)

    def create_pdf_file(self, font_name=None, spellbook=None, spellcards=False):
        input_pdf_filename = "./Character Sheet.pdf"
        output_pdf_filename = f"./{self.name.replace(' ', '_')}_Character_Sheet.pdf"
        urllib.request.urlretrieve(
            "https://media.wizards.com/2022/dnd/downloads/DnD_5E_CharacterSheet_FormFillable.pdf",
            input_pdf_filename
        )

        prof_bonus = self.proficiency_bonus()

        # Core identity and ability scores
        fields = {
            "CharacterName": self.name,
            "CharacterName 2": self.name,
            "ClassLevel": f"{self.char_class.capitalize()}  {self.level}",
            "Race ": self.species.replace('_', '-'),
            "HPMax": self.hp,
            "STR": self.strength,
            "STRmod": modifier(self.strength),
            "DEX": self.dexterity,
            "DEXmod ": modifier(self.dexterity),
            "CON": self.constitution,
            "CONmod": modifier(self.constitution),
            "INT": self.intelligence,
            "INTmod": modifier(self.intelligence),
            "WIS": self.wisdom,
            "WISmod": modifier(self.wisdom),
            "CHA": self.charisma,
            "CHamod": modifier(self.charisma),
            "ProfBonus": prof_bonus,
            "HD": self.hit_die,
            "HDTotal": str(self.hit_die_total()),
            "AC": self.armor_class(),
            "Initiative": modifier(self.dexterity) + self.initiative_bonus,
            "Speed": self.get_speed(),
            "Passive": self.passive_perception(),
        }

        # Saving throws - checkboxes and values
        for st_key, st_info in PDF_SAVING_THROWS.items():
            ability_score = getattr(self, st_info['ability'])
            st_mod = modifier(ability_score)
            if st_key in self.saving_throw_proficiencies:
                st_mod += prof_bonus
                fields[st_info['checkbox']] = 'Yes'
            fields[st_info['value']] = st_mod

        # Skills - checkboxes and values
        for skill_name, skill_info in SKILLS.items():
            mod = self.skill_modifier(skill_name)
            fields[skill_info['field']] = mod
            if skill_name in self.skill_proficiencies:
                fields[skill_info['checkbox']] = 'Yes'

        # Equipment list (deduplicated, with quantities)
        equip_counts = {}
        for eq in self.equipment:
            try:
                name = self.equipment_name(eq)
            except AttributeError:
                name = eq
            equip_counts[name] = equip_counts.get(name, 0) + 1
        equip_lines = []
        for name, qty in equip_counts.items():
            equip_lines.append(f"{name} x{qty}" if qty > 1 else name)
        fields['Equipment'] = '\n'.join(equip_lines)

        # Proficiencies and Languages (one per line)
        prof_list = []
        for p in self.proficiencies:
            prof_list.append(p)
        languages = self.get_languages()
        traits = self.get_traits()
        prof_lines = ['Proficiencies:']
        for p in prof_list:
            prof_lines.append(f'  {p}')
        if not prof_list:
            prof_lines.extend(['  ', '  ', '  '])
        prof_lines.append('')
        prof_lines.append('Languages:')
        for lang in languages:
            prof_lines.append(f'  {lang}')
        fields['ProficienciesLang'] = '\n'.join(prof_lines)

        # Features and Traits (ASI entries include parenthetical ability notes)
        features = self.get_features_annotated_condensed()
        all_feature_trait_lines = list(features)
        if traits:
            all_feature_trait_lines.extend([''] + list(traits))

        progression_notes = self._progression_notes()
        if progression_notes:
            all_feature_trait_lines.extend([''] + progression_notes)

        spellcaster_notes = self._spellcaster_notes(prof_bonus, spellbook=spellbook)
        if spellcaster_notes:
            all_feature_trait_lines.extend([''] + spellcaster_notes)

        page_one_lines, page_two_lines = self._split_feature_trait_lines(all_feature_trait_lines)
        fields['Features and Traits'] = '\n'.join(page_one_lines)
        fields['Feat+Traits'] = '\n'.join(page_two_lines)

        # Weapon attacks (populate first weapon slot from equipment if applicable)
        weapon_equipped = False
        for eq in self.equipment:
            try:
                eq_data = getattr(Equipment, eq)
                if hasattr(eq_data, 'damage') and eq_data.damage:
                    str_mod = modifier(self.strength)
                    dex_mod = modifier(self.dexterity)
                    is_finesse = any(p.get('index') == 'finesse' for p in getattr(eq_data, 'properties', []))
                    is_ranged = getattr(eq_data, 'weapon_range', '') == 'Ranged'
                    atk_mod = dex_mod if (is_ranged or is_finesse) else str_mod
                    atk_bonus = atk_mod + prof_bonus
                    if is_ranged:
                        atk_bonus += self.ranged_attack_bonus
                    dmg_dice = eq_data.damage['damage_dice']
                    dmg_type = eq_data.damage['damage_type']['name']
                    if not weapon_equipped:
                        fields['Wpn Name'] = eq_data.name
                        fields['Wpn1 AtkBonus'] = f"+{atk_bonus}"
                        fields['Wpn1 Damage'] = f"{dmg_dice}+{atk_mod} {dmg_type}"
                        weapon_equipped = True
            except AttributeError:
                pass

        # Spell sheet fields.
        # Populate slot totals from level spellcasting data whenever present,
        # even if the class is not in our spellcasting-ability map.
        level_data = getattr(Levels, f"{self.char_class}_{self.level}")
        sc = getattr(level_data, 'spellcasting', None)
        if sc:
            fields.update(build_spell_slot_fields(sc, spellbook=spellbook))

            # Only set ability/DC/attack bonus when we know the class's
            # spellcasting ability mapping.
            if self.char_class in SPELLCASTING_ABILITY:
                spell_ability = SPELLCASTING_ABILITY[self.char_class]
                spell_mod = modifier(getattr(self, spell_ability))
                fields['SpellcastingAbility 2'] = spell_ability.capitalize()[:3].upper()
                fields['SpellSaveDC  2'] = 8 + prof_bonus + spell_mod
                fields['SpellAtkBonus 2'] = f"+{prof_bonus + spell_mod}"
                fields['Spellcasting Class 2'] = self.char_class.capitalize()

        apply_spellbook_fields(fields, spellbook)

        fillpdfs.write_fillable_pdf(input_pdf_filename, output_pdf_filename, fields)

        if font_name is None:
            font_name = self.rng.choice(list(AVAILABLE_FONTS.keys()))
        apply_custom_font(output_pdf_filename, font_name,
                          expertise_skills=self.expertise_skills)

        if self.char_class not in SPELLCASTING_ABILITY:
            remove_spell_sheet_page(output_pdf_filename)

        if spellcards:
            cards_written = append_spell_cards(
                output_pdf_filename,
                spellbook=spellbook,
                font_name=font_name,
            )
            if cards_written == 0:
                print(
                    "Spell cards requested, but no spells were available for this character."
                )

        print(f"Character sheet saved to: {output_pdf_filename}")
        return


def modifier(ability_score):
    return (ability_score - 10) // 2


def build_spell_slot_fields(spellcasting, spellbook=None):
    """Map class spell slot progression to page 3 slot fields.

    The spell sheet has both total and expended slot columns. We fill
    total slots only, and always leave expended slots blank.
    """
    fields = {}
    for level, total_field in SPELL_SLOT_FIELD_MAP.items():
        slot_key = f"spell_slots_level_{level}"
        slots = int(spellcasting.get(slot_key, 0) or 0)
        remaining_field = total_field.replace('SlotsTotal', 'SlotsRemaining')

        # Keep SLOTS EXPENDED blank on generated sheets.
        fields[remaining_field] = ''

        # SLOTS TOTAL should reflect available slots even if no spells were selected.
        fields[total_field] = str(slots) if slots > 0 else ''
    return fields


def download_font(font_name):
    """Download a Google Font and return the path to the .ttf file."""
    font_name = font_name.lower()
    if font_name not in AVAILABLE_FONTS:
        raise ValueError(
            f"Unknown font '{font_name}'. Available: {', '.join(AVAILABLE_FONTS.keys())}"
        )

    os.makedirs(FONTS_DIR, exist_ok=True)
    cached = os.path.join(FONTS_DIR, f"{font_name}.ttf")
    if os.path.exists(cached):
        return cached

    css_family = AVAILABLE_FONTS[font_name]['css']
    css_url = f"https://fonts.googleapis.com/css2?family={css_family}"
    req = urllib.request.Request(
        css_url, headers={'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64)'}
    )
    css = urllib.request.urlopen(req).read().decode('utf-8')
    ttf_urls = re.findall(r'url\((https://fonts\.gstatic\.com/[^)]+\.ttf)\)', css)
    if not ttf_urls:
        raise RuntimeError(f"Could not find .ttf URL for font '{font_name}'")

    # Prefer the bold variant if available (index 1 for weight@400;700 families)
    # otherwise take the first/only variant
    ttf_url = ttf_urls[-1] if len(ttf_urls) > 1 else ttf_urls[0]
    urllib.request.urlretrieve(ttf_url, cached)
    return cached


# Fields where we want larger text rendered (ability scores, big numbers)
LARGE_FIELDS = {
    'STR', 'DEX', 'CON', 'INT', 'WIS', 'CHA',
    'AC', 'HPMax', 'Speed', 'Passive',
}

# Fields that need medium text (modifiers, bonuses)
MEDIUM_FIELDS = {
    'STRmod', 'DEXmod ', 'CONmod', 'INTmod', 'WISmod', 'CHamod',
    'ProfBonus', 'Initiative',
}

# Saving throw and skill value fields - need readable sizing
SMALL_VALUE_FIELDS = set()
for _st_info in PDF_SAVING_THROWS.values():
    SMALL_VALUE_FIELDS.add(_st_info['value'])
for _sk_info in SKILLS.values():
    SMALL_VALUE_FIELDS.add(_sk_info['field'])

# Text box fields that need larger readable text
TEXTBOX_FIELDS = {
    'Features and Traits', 'Feat+Traits', 'ProficienciesLang',
    'Equipment', 'AttacksSpellcasting',
}

# Spell sheet (page 3) field prefixes — render at nearly full field height
SPELL_SHEET_PREFIXES = (
    'Spells 10', 'SlotsTotal', 'SlotsRemaining',
    'Spellcasting Class 2', 'SpellcastingAbility 2',
    'SpellSaveDC', 'SpellAtkBonus',
)

SPELLBOOK_FIELD_MAP = {
    0: [
        'Spells 1014', 'Spells 1016', 'Spells 1017', 'Spells 1018',
        'Spells 1019', 'Spells 1020', 'Spells 1021', 'Spells 1022',
    ],
    1: [
        'Spells 1015', 'Spells 1023', 'Spells 1024', 'Spells 1025',
        'Spells 1026', 'Spells 1027', 'Spells 1028', 'Spells 1029',
        'Spells 1030', 'Spells 1031', 'Spells 1032', 'Spells 1033',
    ],
    2: [
        'Spells 1046', 'Spells 1034', 'Spells 1035', 'Spells 1036',
        'Spells 1037', 'Spells 1038', 'Spells 1039', 'Spells 1040',
        'Spells 1041', 'Spells 1042', 'Spells 1043', 'Spells 1044',
        'Spells 1045',
    ],
    3: [
        'Spells 1048', 'Spells 1047', 'Spells 1049', 'Spells 1050',
        'Spells 1051', 'Spells 1052', 'Spells 1053', 'Spells 1054',
        'Spells 1055', 'Spells 1056', 'Spells 1057', 'Spells 1058',
        'Spells 1059',
    ],
    4: [
        'Spells 1061', 'Spells 1060', 'Spells 1062', 'Spells 1063',
        'Spells 1064', 'Spells 1065', 'Spells 1066', 'Spells 1067',
        'Spells 1068', 'Spells 1069', 'Spells 1070', 'Spells 1071',
        'Spells 1072',
    ],
    5: [
        'Spells 1074', 'Spells 1073', 'Spells 1075', 'Spells 1076',
        'Spells 1077', 'Spells 1078', 'Spells 1079', 'Spells 1080',
        'Spells 1081',
    ],
    6: [
        'Spells 1083', 'Spells 1082', 'Spells 1084', 'Spells 1085',
        'Spells 1086', 'Spells 1087', 'Spells 1088', 'Spells 1089',
        'Spells 1090',
    ],
    7: [
        'Spells 1092', 'Spells 1091', 'Spells 1093', 'Spells 1094',
        'Spells 1095', 'Spells 1096', 'Spells 1097', 'Spells 1098',
        'Spells 1099',
    ],
    8: [
        'Spells 10101', 'Spells 10100', 'Spells 10102', 'Spells 10103',
        'Spells 10104', 'Spells 10105', 'Spells 10106',
    ],
    9: [
        'Spells 10108', 'Spells 10107', 'Spells 10109', 'Spells 101010',
        'Spells 101011', 'Spells 101012', 'Spells 101013',
    ],
}


def apply_spellbook_fields(fields, spellbook):
    """Populate page 3 spell-name fields without marking spells as prepared."""
    if not spellbook:
        return

    for field_name, spell in zip(SPELLBOOK_FIELD_MAP[0], spellbook.get('cantrips', [])):
        fields[field_name] = spell['name']

    for level, spells in spellbook.get('spells_by_level', {}).items():
        level = int(level)
        available_fields = SPELLBOOK_FIELD_MAP.get(level, [])
        if not available_fields:
            continue

        for field_name, spell in zip(available_fields, spells):
            fields[field_name] = spell['name']


def remove_spell_sheet_page(pdf_path):
    """Remove page 3 spell sheet for non-spellcaster output files."""
    temp_path = f"{pdf_path}.tmp"
    wrote_temp = False
    doc = fitz.open(pdf_path)
    try:
        if len(doc) >= 3:
            doc.delete_page(2)
            doc.save(temp_path)
            wrote_temp = True
    finally:
        doc.close()

    if wrote_temp:
        os.replace(temp_path, pdf_path)


def _ordinal(level):
    if 10 <= level % 100 <= 20:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(level % 10, 'th')
    return f"{level}{suffix}"


def _spell_level_label(level):
    if level <= 0:
        return 'Cantrip'
    return f"{_ordinal(level)}-level"


def _spell_components_text(spell):
    components = [str(value) for value in (spell.get('components') or [])]
    if not components:
        return ''

    value = ', '.join(components)
    material = str(spell.get('material', '') or '').strip()
    if material and 'M' in components:
        value = f"{value} ({material})"
    return value


def _wrap_text(text, font_obj, fontsize, max_width):
    words = [part for part in str(text or '').split() if part]
    if not words:
        return []

    lines = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if font_obj.text_length(candidate, fontsize=fontsize) <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def _spell_card_lines(spell, font_obj, fontsize, max_width):
    lines = []

    level = int(spell.get('level', 0) or 0)
    school = str(spell.get('school', 'Unknown') or 'Unknown')
    tags = []
    if bool(spell.get('ritual', False)):
        tags.append('Ritual')
    if bool(spell.get('concentration', False)):
        tags.append('Concentration')

    subtitle = f"{_spell_level_label(level)} {school}".strip()
    if tags:
        subtitle = f"{subtitle} | {' | '.join(tags)}"
    lines.append({'segments': [(subtitle, True)]})

    casting_time = str(spell.get('casting_time', '') or '').strip()
    spell_range = str(spell.get('range', '') or '').strip()
    components_text = _spell_components_text(spell)
    duration = str(spell.get('duration', '') or '').strip()

    metadata = [
        ('Casting Time', casting_time),
        ('Range', spell_range),
        ('Components', components_text),
        ('Duration', duration),
    ]

    for label, value in metadata:
        if not value:
            continue
        label_text = f"{label}: "
        label_width = font_obj.text_length(label_text, fontsize=fontsize)
        first_width = max(20, max_width - label_width)
        wrapped = _wrap_text(value, font_obj, fontsize, first_width)
        if not wrapped:
            continue
        lines.append({'segments': [(label_text, True), (wrapped[0], False)]})
        for continuation in wrapped[1:]:
            lines.append({'segments': [(continuation, False)]})

    descriptions = [
        str(paragraph).strip()
        for paragraph in (spell.get('desc') or [])
        if str(paragraph).strip()
    ]
    if descriptions:
        lines.append({'segments': []})
        for paragraph in descriptions:
            for wrapped_line in _wrap_text(paragraph, font_obj, fontsize, max_width):
                lines.append({'segments': [(wrapped_line, False)]})

    higher_level = [
        str(paragraph).strip()
        for paragraph in (spell.get('higher_level') or [])
        if str(paragraph).strip()
    ]
    if higher_level:
        lines.append({'segments': []})
        lines.append({'segments': [('At Higher Levels:', True)]})
        for paragraph in higher_level:
            for wrapped_line in _wrap_text(paragraph, font_obj, fontsize, max_width):
                lines.append({'segments': [(wrapped_line, False)]})

    return lines


def _spell_card_height(lines, fontsize):
    blank_height = fontsize * 0.7
    total = 0.0
    for line in lines:
        if not line['segments']:
            total += blank_height
        else:
            line_size = fontsize
            if any(is_emphasized for _, is_emphasized in line['segments']):
                line_size += 0.5
            line_height = line_size * 1.25
            total += line_height
    return total


def _draw_card_text(page, point, text, font_path, fontsize):
    page.insert_text(
        point,
        text,
        fontname='custom',
        fontfile=font_path,
        fontsize=fontsize,
    )


def _draw_spell_card_body(page, body_rect, spell, font_path, font_obj):
    emphasis_size_delta = 1.5
    chosen_size = None
    chosen_lines = None
    for body_size in [10, 9.5, 9, 8.5, 8, 7.5, 7, 6.5, 6, 5.5, 5]:
        lines = _spell_card_lines(spell, font_obj, body_size, body_rect.width)
        if _spell_card_height(lines, body_size) <= body_rect.height:
            chosen_size = body_size
            chosen_lines = lines
            break

    if chosen_lines is None:
        chosen_size = 5
        chosen_lines = _spell_card_lines(spell, font_obj, chosen_size, body_rect.width)

    y = body_rect.y0
    blank_height = chosen_size * 0.7
    for line in chosen_lines:
        segments = line['segments']
        if not segments:
            y += blank_height
            continue

        line_size = chosen_size
        if any(is_emphasized for _, is_emphasized in segments):
            line_size += emphasis_size_delta

        x = body_rect.x0
        baseline = y + line_size
        for segment_text, is_emphasized in segments:
            if not segment_text:
                continue
            segment_size = chosen_size + (emphasis_size_delta if is_emphasized else 0)
            _draw_card_text(
                page,
                fitz.Point(x, baseline),
                segment_text,
                font_path,
                segment_size,
            )
            x += font_obj.text_length(segment_text, fontsize=segment_size)
        y += line_size * 1.25


def _collect_spell_cards(spellbook):
    if not spellbook:
        return []

    seen = set()
    cards = []

    def add_spell(spell):
        if not isinstance(spell, dict):
            return
        key = str(spell.get('index') or spell.get('name') or '').strip().lower()
        if not key or key in seen:
            return
        seen.add(key)
        cards.append(spell)

    for spell in spellbook.get('cantrips', []):
        add_spell(spell)

    for spell in spellbook.get('always_prepared', []):
        add_spell(spell)

    spells_by_level = spellbook.get('spells_by_level', {})
    for _, spells in sorted(
        spells_by_level.items(),
        key=lambda item: int(item[0]),
    ):
        for spell in spells:
            add_spell(spell)

    mystic_arcanum = spellbook.get('mystic_arcanum', {})
    for _, spell in sorted(
        mystic_arcanum.items(),
        key=lambda item: int(item[0]),
    ):
        add_spell(spell)

    cards.sort(key=lambda entry: (int(entry.get('level', 0) or 0), entry.get('name', '')))
    return cards


def append_spell_cards(pdf_path, spellbook, font_name):
    cards = _collect_spell_cards(spellbook)
    if not cards:
        return 0

    font_path = download_font(font_name)
    font_obj = fitz.Font(fontfile=font_path)

    page_width = 612
    page_height = 792
    card_width = 216
    card_height = 360
    cols = page_width // card_width
    rows = page_height // card_height
    cards_per_page = int(cols * rows)
    if cards_per_page <= 0:
        return 0

    grid_width = cols * card_width
    grid_height = rows * card_height
    grid_x0 = (page_width - grid_width) / 2
    grid_y0 = (page_height - grid_height) / 2

    doc = fitz.open(pdf_path)
    try:
        page = None
        for index, spell in enumerate(cards):
            slot = index % cards_per_page
            if slot == 0:
                page = doc.new_page(width=page_width, height=page_height)
                if os.path.exists(SPELLCARD_BACKGROUND_PATH):
                    page.insert_image(
                        page.rect,
                        filename=SPELLCARD_BACKGROUND_PATH,
                        keep_proportion=False,
                        overlay=False,
                    )

            row = slot // cols
            col = slot % cols
            x0 = grid_x0 + (col * card_width)
            y0 = grid_y0 + (row * card_height)
            card_rect = fitz.Rect(x0, y0, x0 + card_width, y0 + card_height)

            page.draw_rect(card_rect, color=(0, 0, 0), width=0.8)

            inner = fitz.Rect(
                card_rect.x0 + 12,
                card_rect.y0 + 12,
                card_rect.x1 - 12,
                card_rect.y1 - 12,
            )
            title_rect = fitz.Rect(inner.x0, inner.y0, inner.x1, inner.y0 + 26)
            body_rect = fitz.Rect(inner.x0, title_rect.y1 + 6, inner.x1, inner.y1)

            title = str(spell.get('name', 'Unknown Spell') or 'Unknown Spell').strip()
            title_size = 14
            title_emphasis_delta = 1.0
            rendered_title_size = title_size + title_emphasis_delta
            while title_size >= 8:
                rendered_title_size = title_size + title_emphasis_delta
                title_width = font_obj.text_length(title, fontsize=rendered_title_size)
                if title_width <= title_rect.width:
                    break
                title_size -= 0.5

            title_x = title_rect.x0 + ((title_rect.width - title_width) / 2)
            title_y = title_rect.y0 + ((title_rect.height + rendered_title_size) / 2) - 1
            _draw_card_text(
                page,
                fitz.Point(title_x, title_y),
                title,
                font_path,
                rendered_title_size,
            )

            _draw_spell_card_body(page, body_rect, spell, font_path, font_obj)

        temp_path = f"{pdf_path}.tmp"
        doc.save(temp_path, deflate=True)
    finally:
        doc.close()

    os.replace(temp_path, pdf_path)
    return len(cards)


def apply_custom_font(pdf_path, font_name, expertise_skills=None):
    """Replace form field text with custom-font rendered text via pymupdf.

    expertise_skills: iterable of skill names (keys in SKILLS) that have
    Expertise.  An "E" is rendered just left of each matching proficiency
    checkbox on the character sheet.
    """
    font_path = download_font(font_name)
    font_obj = fitz.Font(fontfile=font_path)

    # Build the set of checkbox field names for expertise-marked skills
    expertise_cbs = set()
    if expertise_skills:
        for sname in expertise_skills:
            if sname in SKILLS:
                expertise_cbs.add(SKILLS[sname]['checkbox'])

    # The official WotC character sheet emits noisy, non-fatal MuPDF
    # diagnostics ("argument error: not a dict (string)") whenever we
    # inspect and save the AcroForm widgets. Suppress those library messages
    # here so the CLI stays clean while we render the custom font overlay.
    previous_error_state = fitz.TOOLS.mupdf_display_errors(False)
    previous_warning_state = fitz.TOOLS.mupdf_display_warnings(False)

    try:
        # Collect all filled widget data across all pages; also record
        # the checkbox rect for every expertise-marked skill.
        doc = fitz.open(pdf_path)
        all_page_data = []
        expertise_cb_rects = {}   # page_num -> {field_name: fitz.Rect}
        for page in doc:
            widgets_data = []
            cb_rects_on_page = {}
            for w in page.widgets():
                if w.field_type == fitz.PDF_WIDGET_TYPE_TEXT and w.field_value:
                    widgets_data.append({
                        'name': w.field_name,
                        'value': str(w.field_value),
                        'rect': w.rect,
                    })
                elif w.field_name in expertise_cbs:
                    cb_rects_on_page[w.field_name] = w.rect
            all_page_data.append(widgets_data)
            if cb_rects_on_page:
                expertise_cb_rects[page.number] = cb_rects_on_page
        doc.close()

        # Process one page at a time, saving and reopening between pages
        # to avoid cross-page widget corruption
        for page_num in range(len(all_page_data)):
            widgets_data = all_page_data[page_num]
            page_cb_rects = expertise_cb_rects.get(page_num, {})
            if not widgets_data and not page_cb_rects:
                continue

            doc = fitz.open(pdf_path)
            page = doc[page_num]

            # Delete filled text widgets on this page only
            filled = [w for w in page.widgets()
                      if w.field_type == fitz.PDF_WIDGET_TYPE_TEXT and w.field_value]
            for w in filled:
                page.delete_widget(w)

            # Render custom font text at each field position
            for wd in widgets_data:
                rect = wd['rect']
                value = wd['value']
                height = rect.height
                name = wd['name']

                # Scale font size based on field type
                is_spell_sheet = any(name.startswith(p) for p in SPELL_SHEET_PREFIXES)
                if name in LARGE_FIELDS:
                    fontsize = height * 0.75
                elif name in MEDIUM_FIELDS:
                    fontsize = height * 0.85
                elif name in SMALL_VALUE_FIELDS:
                    # Saving throws and skill values - maximize readability
                    fontsize = height * 0.95
                elif name in TEXTBOX_FIELDS:
                    fontsize = 9
                elif is_spell_sheet:
                    # Spell sheet fields — use nearly full height for readability
                    fontsize = height * 0.95
                else:
                    fontsize = min(height * 0.75, 11)

                # Textbox fields and multiline values use insert_textbox
                # (positions text at top-left of the rect)
                if name in TEXTBOX_FIELDS or '\n' in value:
                    if name in TEXTBOX_FIELDS:
                        fontsize = 9
                    # Shrink font until text fits; overflow drops all content
                    while fontsize > 4:
                        rc = page.insert_textbox(
                            rect, value,
                            fontname="custom", fontfile=font_path,
                            fontsize=fontsize, align=fitz.TEXT_ALIGN_LEFT,
                        )
                        if rc >= 0:
                            break
                        fontsize -= 0.5
                    continue

                # Calculate position for single-line text
                text_width = font_obj.text_length(value, fontsize=fontsize)

                # Shrink to fit if text overflows the rect
                if text_width > rect.width - 2:
                    fontsize = fontsize * (rect.width - 2) / text_width
                    text_width = font_obj.text_length(value, fontsize=fontsize)

                is_spell_numeric = is_spell_sheet and not name.startswith('Spells 10')
                if name in LARGE_FIELDS or name in MEDIUM_FIELDS or name in SMALL_VALUE_FIELDS or is_spell_numeric:
                    x = rect.x0 + (rect.width - text_width) / 2
                else:
                    x = rect.x0 + 1

                y = rect.y0 + (rect.height + fontsize) / 2 - 1

                page.insert_text(
                    fitz.Point(x, y), value,
                    fontname="custom", fontfile=font_path,
                    fontsize=fontsize,
                )

            # Overlay "E" to the left of each expertise skill checkbox
            for cb_rect in page_cb_rects.values():
                e_size = cb_rect.height * 0.85
                text_w = font_obj.text_length("E", fontsize=e_size)
                ex = cb_rect.x0 - text_w - 1
                ey = cb_rect.y0 + (cb_rect.height + e_size) / 2 - 1
                page.insert_text(
                    fitz.Point(ex, ey), "E",
                    fontname="custom", fontfile=font_path,
                    fontsize=e_size,
                )

            # Save this page's changes before processing the next page
            tmp_path = pdf_path + '.tmp'
            doc.save(tmp_path, deflate=True)
            doc.close()
            os.replace(tmp_path, pdf_path)
    finally:
        fitz.TOOLS.mupdf_display_errors(previous_error_state)
        fitz.TOOLS.mupdf_display_warnings(previous_warning_state)
        fitz.TOOLS.reset_mupdf_warnings()


def random_character_class():
    return random.choice(Classes.entries)


def random_species():
    return random.choice(Species.entries).capitalize()


def hp(level, constitution, hit_die):
    constitution_modifier = modifier(constitution)
    hit_dice = int(hit_die.replace('d', ''))
    # Level 1: max hit die + CON modifier
    char_hp = hit_dice + constitution_modifier
    if level == 1:
        return max(char_hp, 1)
    # Levels 2+: roll hit dice and add CON modifier per level
    for _ in range(level - 1):
        roll_result = roll.dice(f"1{hit_die}")
        # Minimum 1 HP per level
        char_hp += max(roll_result + constitution_modifier, 1)
    return char_hp


def stat_generator():
    rolls = [roll.d6(), roll.d6(), roll.d6(), roll.d6()]
    rolls.sort()
    rolls.pop(0)
    stat = sum(rolls)
    if stat < 8:
        stat = stat_generator()
    return stat


def create_random_character(level=None, char_class=None, species=None, seed=None):
    rng = random.Random(seed) if seed is not None else random
    if char_class is None:
        char_class = rng.choice(Classes.entries)
    if species is None:
        species = rng.choice(Species.entries).capitalize()
    if level is None:
        level = roll.d20()

    level = max(1, min(20, int(level)))

    fictional_names_species = SPECIES_NAMES.get(species, "human")
    sex = rng.choice(['male', 'female']).capitalize()
    name = names(gender=sex, style=fictional_names_species)

    my_character = Character(name=name, species=species, char_class=char_class,
                             sex=sex, level=level, seed=seed)
    my_character.roll_stats()

    # Add starting equipment from class
    cls = getattr(Classes, char_class)
    for item in cls.starting_equipment:
        eq_index = item['equipment']['index'].replace('-', '_')
        if eq_index in Equipment.entries:
            my_character.add_equipment(eq_index)

    return my_character


def create_character(name, species, character_class, sex, level, seed=None):
    if species not in list(SPECIES_NAMES.keys()):
        raise ValueError(f"Specified Species Not Supported. Choose from: {list(SPECIES_NAMES.keys())}")
    if character_class not in AVAILABLE_CLASSES:
        raise ValueError(f"Specified Character Class Not Supported. Choose from: {AVAILABLE_CLASSES}")
    level = max(1, min(20, int(level)))
    my_character = Character(name=name, char_class=character_class, sex=sex,
                             species=species, level=level, seed=seed)
    my_character.roll_stats()

    cls = getattr(Classes, character_class)
    for item in cls.starting_equipment:
        eq_index = item['equipment']['index'].replace('-', '_')
        if eq_index in Equipment.entries:
            my_character.add_equipment(eq_index)

    return my_character
    