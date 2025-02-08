import roll
from tinys_srd import Classes, Equipment, Proficiencies
from tinys_srd import Races as Species
import random
from fictional_names import name_generator
names = name_generator.generate_name


# print(Classes.entries)
# print(Equipment.entries)
#
# print(Proficiencies.entries)
print(Classes.bard)
print(Classes.bard.hit_die)
#
# print(Equipment.trident)



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


# HALF_SPECIES = {
#     el
# }



SPECIES = {
    "Human": {
        "fictional_names_species": "human"
    },
    "Elf": {
        "fictional_names_species": "elven"
    },
    "Halfling": {
        "fictional_names_species": "halfling"
    },
    "Orc": {
        "fictional_names_species": "orc"
    },
    "Drow": {
        "fictional_names_species": "drow"
    },
    "Dwarf": {
        "fictional_names_species": "dwarven"
    },
    "Gnome": {
        "fictional_names_species": "gnomish"
    },
    "Half_elf": {
        "fictional_names_species": random.choice(["human", "elven"])
    },
    "Dragonborn": {
        "fictional_names_species": 'dragonborn'
    },
    "Tiefling": {
        "fictional_names_species": 'dragonborn'
    },
    "Half_orc": {
        "fictional_names_species": random.choice(["human", "orc"])
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

    def get_equipment_name(self, equipment):
        equipment_index = getattr(Equipment, equipment)
        return equipment_index.name

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
        Equipment: {self.get_equipment_name(self.equipment[0])}
        """
        print(character_sheet)


def modifier(ability_score):
    return (ability_score - 10) // 2


def random_proficiency():
    return random.choice(Proficiencies.entries)


def random_equipment():
    return random.choice(Equipment.entries)


def random_character_class():
    return random.choice(Classes.entries)


def random_species():
    return random.choice(Species.entries).capitalize()



def hp(level, character_class, constitution):
    char_class = getattr(Classes, character_class)
    hit_die = char_class.hit_die
    constitution_modifier = modifier(constitution)
    level_1_hp = hit_die + constitution_modifier
    if level == 1:
        return level_1_hp
    char_hp = level_1_hp
    number_of_rolls = level - 1
    die_roll = f"{number_of_rolls}d{hit_die}"
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
    print(species)
    fictional_names_species = SPECIES[species]["fictional_names_species"]
    sex = random.choice(['male', 'female']).capitalize()
    name = names(gender=sex, style=fictional_names_species)
    my_character = Character(name=name, species=species, char_class=char_class, sex=sex)
    my_character.level = roll.d20()
    my_character.roll_stats()
    my_character.add_proficiency(random_proficiency())
    my_character.add_equipment(random_equipment())
    return my_character


# def create_character(name, species, character_class, sex, level):
#     if species not in list(SPECIES.keys()):
#         raise Exception("Specified Species Not Supported")
#     if character_class not in list(CHARACTER_CLASSES.keys()):
#         raise Exception("Specified Character Class Not Supported")
#     my_character = Character(name=name, char_class=character_class, sex=sex, species=species)
#     my_character.level = level
#     my_character.roll_stats()
#     my_character.add_proficiency(random_proficiency())
#     my_character.add_equipment(random_equipment())
#     return my_character
