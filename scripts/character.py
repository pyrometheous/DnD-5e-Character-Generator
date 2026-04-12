from scripts import roll
from scripts.feats import choose_feat_for_character, load_feat_config

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

DEFAULT_SPELLCASTING_NOTES = {
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
        'Flexible Casting: sorcery points can create or convert spell slots.',
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


def load_spellcasting_notes(config_path=None):
    """Load class spellcasting notes from JSON config with safe defaults."""
    target_path = config_path or os.path.join(BASE_DIR, 'config', 'spellcasting_notes.json')
    notes = {k: list(v) for k, v in DEFAULT_SPELLCASTING_NOTES.items()}

    if not os.path.exists(target_path):
        return notes

    try:
        with open(target_path, 'r', encoding='utf-8') as handle:
            loaded = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return notes

    if not isinstance(loaded, dict):
        return notes

    for class_name, class_notes in loaded.items():
        if not isinstance(class_name, str) or not isinstance(class_notes, list):
            continue
        normalized_class = class_name.strip().lower()
        normalized_notes = [
            note.strip()
            for note in class_notes
            if isinstance(note, str) and note.strip()
        ]
        if normalized_notes:
            notes[normalized_class] = normalized_notes

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


SPELLCASTING_NOTES = load_spellcasting_notes()
ASI_WEIGHT_CONFIG = load_asi_weight_config()
FEAT_CONFIG = load_feat_config()



class Character:
    def __init__(self, name, species, char_class, sex, level):
        self.name = name
        self.species = species
        self.sex = sex
        self.char_class = char_class
        self.level = int(level)
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
        self.feats = []                  # optional selected feats (dict/object/string)
        self.speed_bonus = 0
        self.initiative_bonus = 0
        self.passive_perception_bonus = 0
        self.hp_bonus_per_level = 0
        self.aggressive_asi_focus = set()
        self.proficiencies = []
        self.equipment = []
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

    def get_features(self):
        features = []
        for lvl in range(1, self.level + 1):
            level_data = getattr(Levels, f"{self.char_class}_{lvl}")
            for feat in level_data.features:
                features.append(feat['name'])
        return features

    def get_features_annotated(self):
        """Return features with ASI entries replaced by ASI or feat choices."""
        features = []
        advancement_index = 0
        for lvl in range(1, self.level + 1):
            level_data = getattr(Levels, f"{self.char_class}_{lvl}")
            for feat in level_data.features:
                name = feat['name']
                if name == 'Ability Score Improvement' and advancement_index < len(self.advancement_log):
                    record = self.advancement_log[advancement_index]
                    if record.get('type') == 'feat':
                        name = record['feat'].get('summary', record['feat'].get('name', name))
                    else:
                        bonuses = record.get('ability_bonuses', {})
                        parts = [f"+{v} {k[:3].upper()}" for k, v in bonuses.items() if v > 0]
                        if parts:
                            name = f"Ability Score Improvement ({', '.join(parts)})"
                    advancement_index += 1
                features.append(name)
        return features

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

    def apply_asi(self):
        """Apply all Ability Score Improvements earned up to the current level.

        Each ASI distributes +2 points using the following priority:

                For any character at ASI levels < 10
                    1. Any ability below 10 (reduce/remove negative modifiers early)
                    2. Then continue with the class-based rules below

        For spellcasters at ASI levels ≤ 15
          1. Spellcasting ability (regardless of current parity)
          2. Any other ability currently at an odd score  (odd → even = +1 modifier)
          3. Any other ability < 20

        For non-casters, or ASI levels > 15
          1. Any ability currently at an odd score  (odd → even = +1 modifier)
          2. Any ability < 20

        ASI levels are discovered from class feature names rather than the
        ability_score_bonuses field, which has a known data error for Rogue.
        """
        spellcast_ability = SPELLCASTING_ABILITY.get(self.char_class)

        # Collect the character level at which each ASI is granted, in order.
        asi_levels = []
        for lvl in range(1, self.level + 1):
            level_data = getattr(Levels, f"{self.char_class}_{lvl}")
            for feat in level_data.features:
                if feat['name'] == 'Ability Score Improvement':
                    asi_levels.append(lvl)

        for asi_level in asi_levels:
            aggressive_focus = self._refresh_aggressive_asi_focus()
            force_asi = bool(
                ASI_WEIGHT_CONFIG['global'].get('force_asi_when_important_below_floor', True)
                and aggressive_focus
            )

            if not force_asi:
                selected_feat = choose_feat_for_character(self, asi_level, FEAT_CONFIG)
                if selected_feat is not None:
                    self._apply_selected_feat(selected_feat)
                    self.advancement_log.append({'type': 'feat', 'feat': selected_feat})
                    continue

            prefer_sc = (spellcast_ability
                         if (spellcast_ability and asi_level <= 15)
                         else None)
            prioritize_sub_ten = asi_level < 10
            first, second = self._rank_asi_candidates(
                prefer_spellcast_ability=prefer_sc,
                prioritize_sub_ten=prioritize_sub_ten,
                aggressive_focus=aggressive_focus,
            )

            asi_record = {}
            for ability in (a for a in (first, second) if a is not None):
                s = getattr(self, ability)
                if s < 20:
                    setattr(self, ability, s + 1)
                    asi_record[ability] = asi_record.get(ability, 0) + 1
            self.asi_log.append(asi_record)
            self.advancement_log.append({'type': 'asi', 'ability_bonuses': asi_record})

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
                    self.skill_proficiencies = random.sample(skill_options, num_choose)

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
                            random.sample(eligible, num_pick)
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
            chosen = random.sample(options, num_choose)
            for opt in chosen:
                lang_name = opt['item']['name']
                if lang_name not in self.extra_languages:
                    self.extra_languages.append(lang_name)

        # Extra proficiency choices (Dwarf: artisan tool, Half-Elf: 2 skills)
        if hasattr(race_data, 'starting_proficiency_options') and race_data.starting_proficiency_options:
            prof_opts = race_data.starting_proficiency_options
            options = prof_opts['from']['options']
            num_choose = min(prof_opts['choose'], len(options))
            chosen = random.sample(options, num_choose)
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
        self.choose_expertise()             # Expertise from class features
        self.apply_jack_of_all_trades()     # JOAT half-prof flag
        self.apply_asi()
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
        AC: {10 + modifier(self.dexterity)}
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

    def create_pdf_file(self, font_name=None, spellbook=None):
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
            "AC": 10 + modifier(self.dexterity),
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
        features = self.get_features_annotated()
        fields['Features and Traits'] = '\n'.join(features)
        trait_lines = list(traits)
        class_notes = SPELLCASTING_NOTES.get(self.char_class, [])
        if class_notes:
            trait_lines.extend([''] + class_notes)
        fields['Feat+Traits'] = '\n'.join(trait_lines)

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
            font_name = random.choice(list(AVAILABLE_FONTS.keys()))
        apply_custom_font(output_pdf_filename, font_name,
                          expertise_skills=self.expertise_skills)

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


def create_random_character(level=None, char_class=None, species=None):
    if char_class is None:
        char_class = random_character_class()
    if species is None:
        species = random_species()
    if level is None:
        level = roll.d20()

    level = max(1, min(20, int(level)))

    fictional_names_species = SPECIES_NAMES.get(species, "human")
    sex = random.choice(['male', 'female']).capitalize()
    name = names(gender=sex, style=fictional_names_species)

    my_character = Character(name=name, species=species, char_class=char_class,
                             sex=sex, level=level)
    my_character.roll_stats()

    # Add starting equipment from class
    cls = getattr(Classes, char_class)
    for item in cls.starting_equipment:
        eq_index = item['equipment']['index'].replace('-', '_')
        if eq_index in Equipment.entries:
            my_character.add_equipment(eq_index)

    return my_character


def create_character(name, species, character_class, sex, level):
    if species not in list(SPECIES_NAMES.keys()):
        raise ValueError(f"Specified Species Not Supported. Choose from: {list(SPECIES_NAMES.keys())}")
    if character_class not in AVAILABLE_CLASSES:
        raise ValueError(f"Specified Character Class Not Supported. Choose from: {AVAILABLE_CLASSES}")
    level = max(1, min(20, int(level)))
    my_character = Character(name=name, char_class=character_class, sex=sex,
                             species=species, level=level)
    my_character.roll_stats()

    cls = getattr(Classes, character_class)
    for item in cls.starting_equipment:
        eq_index = item['equipment']['index'].replace('-', '_')
        if eq_index in Equipment.entries:
            my_character.add_equipment(eq_index)

    return my_character
    