import roll

from tinys_srd import Classes, Equipment, Proficiencies, Levels
from tinys_srd import Races as Species

import random
import urllib.request
from fillpdf import fillpdfs
from fictional_names import name_generator


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
        class_levels = getattr(Levels, f"{self.char_class}_{self.level}")
        return class_levels.ability_score_bonuses

    def get_features(self):
        features = []
        for lvl in range(1, self.level + 1):
            level_data = getattr(Levels, f"{self.char_class}_{lvl}")
            for feat in level_data.features:
                features.append(feat['name'])
        return features

    def get_speed(self):
        species_key = self.species.lower()
        race_data = getattr(Species, species_key)
        return race_data.speed

    def get_languages(self):
        species_key = self.species.lower()
        race_data = getattr(Species, species_key)
        return [lang['name'] for lang in race_data.languages]

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
        num_asi = self.ability_score_improvements()
        for _ in range(num_asi):
            # Each ASI gives +2 total, typically +2 to one or +1 to two
            # Randomly boost two different abilities by +1 each
            abilities = ['strength', 'dexterity', 'constitution',
                         'intelligence', 'wisdom', 'charisma']
            chosen = random.sample(abilities, 2)
            for ability in chosen:
                current = getattr(self, ability)
                if current < 20:
                    setattr(self, ability, current + 1)

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
        if skill_name in self.skill_proficiencies:
            mod += self.proficiency_bonus()
        return mod

    def roll_stats(self):
        self.strength = stat_generator()
        self.dexterity = stat_generator()
        self.constitution = stat_generator()
        self.intelligence = stat_generator()
        self.wisdom = stat_generator()
        self.charisma = stat_generator()
        self.apply_racial_bonuses()
        self.choose_skill_proficiencies()
        self.apply_asi()
        self.hp = hp(level=self.level, constitution=self.constitution,
                     hit_die=self.hit_die)

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
        Features: {', '.join(self.get_features())}
        """
        print(character_sheet)

    def create_pdf_file(self):
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
            "HPCurrent": self.hp,
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
            "Initiative": modifier(self.dexterity),
            "Speed": self.get_speed(),
            "Passive": 10 + self.skill_modifier('Perception'),
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

        # Equipment list
        equip_names = []
        for eq in self.equipment:
            try:
                equip_names.append(self.equipment_name(eq))
            except AttributeError:
                equip_names.append(eq)
        # Also add starting equipment from class
        cls = getattr(Classes, self.char_class)
        for item in cls.starting_equipment:
            name = item['equipment']['name']
            qty = item['quantity']
            equip_names.append(f"{name} x{qty}" if qty > 1 else name)
        fields['Equipment'] = '\n'.join(equip_names)

        # Proficiencies and Languages
        prof_list = []
        for p in self.proficiencies:
            try:
                prof_data = getattr(Proficiencies, p)
                prof_list.append(prof_data.name)
            except AttributeError:
                prof_list.append(p)
        languages = self.get_languages()
        traits = self.get_traits()
        fields['ProficienciesLang'] = (
            "Proficiencies: " + ', '.join(prof_list) + '\n' +
            "Languages: " + ', '.join(languages)
        )

        # Features and Traits
        features = self.get_features()
        fields['Features and Traits'] = '\n'.join(features)
        fields['Feat+Traits'] = '\n'.join(traits)

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

        # Spell slots for casters
        if self.char_class in SPELLCASTING_ABILITY:
            level_data = getattr(Levels, f"{self.char_class}_{self.level}")
            if hasattr(level_data, 'spellcasting') and level_data.spellcasting:
                sc = level_data.spellcasting
                spell_ability = SPELLCASTING_ABILITY[self.char_class]
                spell_mod = modifier(getattr(self, spell_ability))
                fields['SpellcastingAbility 2'] = spell_ability.capitalize()[:3].upper()
                fields['SpellSaveDC  2'] = 8 + prof_bonus + spell_mod
                fields['SpellAtkBonus 2'] = f"+{prof_bonus + spell_mod}"
                fields['Spellcasting Class 2'] = self.char_class.capitalize()

                slot_field_map = {
                    'spell_slots_level_1': 'SlotsTotal 19',
                    'spell_slots_level_2': 'SlotsTotal 20',
                    'spell_slots_level_3': 'SlotsTotal 21',
                    'spell_slots_level_4': 'SlotsTotal 22',
                    'spell_slots_level_5': 'SlotsTotal 23',
                    'spell_slots_level_6': 'SlotsTotal 24',
                    'spell_slots_level_7': 'SlotsTotal 25',
                    'spell_slots_level_8': 'SlotsTotal 26',
                    'spell_slots_level_9': 'SlotsTotal 27',
                }
                for slot_key, field_name in slot_field_map.items():
                    slots = sc.get(slot_key, 0)
                    if slots > 0:
                        fields[field_name] = slots

        fillpdfs.write_fillable_pdf(input_pdf_filename, output_pdf_filename, fields)
        print(f"Character sheet saved to: {output_pdf_filename}")
        return


def modifier(ability_score):
    return (ability_score - 10) // 2


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
    