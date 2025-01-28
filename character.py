import roll
import random
from fictional_names import name_generator
names = name_generator.generate_name


CHARACTER_CLASSES = {
    "Barbarian": {
        "hit_die": "d12"
    },
    "Fighter": {
        "hit_die": "d10"
    },
    "Monk": {
        "hit_die": "d8"
    },
    "Ranger": {
        "hit_die": "d10"
    }
}

EQUIPMENT = {
    "Longbow": {
        "attack": 2
    }
}


PROFICIENCIES = {
    "Stealth": {
        "dex": 2
    }
}


SPECIES = {
    "Human": {
        "fictional_names_race": "human"
    },
    "Elf": {
        "fictional_names_race": "elven"
    },
    "Halfling": {
        "fictional_names_race": "halfling"
    },
    "Orc": {
        "fictional_names_race": "orc"
    },
    "Drow": {
        "fictional_names_race": "drow"
    },
    "Dwarf": {
        "fictional_names_race": "dwarven"
    },
    "Gnome": {
        "fictional_names_race": "gnomish"
    }
}


class Character:
    def __init__(self, name, species, char_class, sex):
        self.name = name
        self.species = species
        self.sex = sex
        self.char_class = char_class
        self.strength = 0
        self.dexterity = 0
        self.constitution = 0
        self.intelligence = 0
        self.wisdom = 0
        self.charisma = 0
        self.hp = 0
        self.level = 1
        self.proficiencies = []
        self.equipment = []

    def roll_stats(self):
        self.strength = stat_generator()
        self.dexterity = stat_generator()
        self.constitution = stat_generator()
        self.intelligence = stat_generator()
        self.wisdom = stat_generator()
        self.charisma = stat_generator()
        self.hp = hp(level=self.level, character_class=self.char_class, constitution=self.constitution)
        pass

    def level_up(self):
        self.level += 1
        # Implement logic for increasing HP and other level-up benefits

    def add_proficiency(self, proficiency):
        self.proficiencies.append(proficiency)

    def add_equipment(self, equipment):
        self.equipment.append(equipment)

    def display_character_sheet(self):
        character_sheet = f"""
        Character Sheet:
        
        Name: {self.name}
        Sex: {self.sex}
        Species: {self.species}
        Class: {self.char_class}
        Level: {self.level}
        HP: {self.hp}
        Strength: {self.strength} Mod: {modifier(self.strength)}
        Dexterity: {self.dexterity} Mod: {modifier(self.dexterity)}
        Constitution: {self.constitution} Mod: {modifier(self.constitution)}
        Intelligence: {self.intelligence} Mod: {modifier(self.intelligence)}
        Wisdom: {self.wisdom} Mod: {modifier(self.wisdom)}
        Charisma: {self.charisma} Mod: {modifier(self.charisma)}
        Proficiencies: {self.proficiencies}
        Equipment: {self.equipment}
        """
        print(character_sheet)


def modifier(ability_score):
    return (ability_score - 10) // 2


def random_proficiency():
    return random.choice(list(PROFICIENCIES.keys()))


def random_equipment():
    return random.choice(list(EQUIPMENT.keys()))


def random_character_class():
    return random.choice(list(CHARACTER_CLASSES.keys()))


def random_species():
    return random.choice(list(SPECIES.keys()))


def hp(level, character_class, constitution):
    hit_die = CHARACTER_CLASSES[character_class]['hit_die']
    constitution_modifier = modifier(constitution)
    level_1_hp = int(hit_die.replace("d", "")) + constitution_modifier
    if level == 1:
        return level_1_hp
    char_hp = level_1_hp
    number_of_rolls = level - 1
    die_roll = f"{number_of_rolls}{hit_die}"
    hit_die_total = roll.dice(die_roll)
    char_hp += hit_die_total
    constitution_bonus = constitution_modifier * number_of_rolls
    char_hp += constitution_bonus
    return char_hp


def stat_generator():
    rolls = [roll.d6(), roll.d6(), roll.d6(), roll.d6()]
    rolls.sort()
    rolls.pop(0)
    stat = sum(rolls)
    if stat < 8:
        stat = stat_generator()
    return stat


def create_random_character():
    char_class = random_character_class()
    species = random_species()
    fictional_names_race = SPECIES[species]["fictional_names_race"]
    sex = random.choice(['male', 'female']).capitalize()
    name = names(gender=sex, style=fictional_names_race)
    my_character = Character(name=name, species=species, char_class=char_class, sex=sex)
    my_character.level = roll.d20()
    my_character.roll_stats()
    my_character.add_proficiency(random_proficiency())
    my_character.add_equipment(random_equipment())
    return my_character


def create_character(name, species, character_class, sex, level):
    if species not in list(SPECIES.keys()):
        raise Exception("Specified Species Not Supported")
    if character_class not in list(CHARACTER_CLASSES.keys()):
        raise Exception("Specified Character Class Not Supported")
    my_character = Character(name=name, char_class=character_class, sex=sex, species=species)
    my_character.level = level
    my_character.roll_stats()
    my_character.add_proficiency(random_proficiency())
    my_character.add_equipment(random_equipment())
    return my_character
