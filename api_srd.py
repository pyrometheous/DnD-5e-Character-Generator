import requests

BASE_URL = "https://www.dnd5eapi.co/api/"

ABILITIES = {
    'Charisma': "cha",
    'Constitution': "con",
    'Dexterity': 'dex',
    'Intelligence': 'int',
    'Strength': 'str',
    'Wisdom': 'wis'
}


class Ability:
    def __init__(self, name, description, skills):
        self.name = name
        self.description = description
        self.skills = skills

        def ability_card():
            print(f"""
            Name: {self.name}
            Description: \n{self.description}
            Skills:\n
            """)


def get_request(index):
    url = BASE_URL + index
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
    else:
        raise Exception(f"Request for {index} failed")
    return data


def get_skill(skill_name):
    index = f"skills/{skill_name}"
    data = get_request(index)
    return data


def convert_description_to_string(description_list):
    description_string = ''
    for i in description_list:
        description_string += f"{i}"
        description_string += "\n"
    return description_string


def get_ability_data(ability):
    ability_abbreviated = ABILITIES[ability]
    if ability_abbreviated in list(ABILITIES.values()):
        index = f"ability-scores/{ability_abbreviated}"
        data = get_request(index)
        ability_data = {
            "full_name": data['full_name'],
            "description": convert_description_to_string(data['desc']),
            "skills": {
            }
        }
        for skill in data['skills']:
            skill_name = skill['index']
            skill_data = get_skill(skill_name)
            ability_data['skills'][skill_name] = {
                "name": skill_data['name'],
                "description": convert_description_to_string(skill_data['desc'])
            }
        return ability_data
    else:
        raise Exception(f"{ability_abbreviated} is an invalid ability.")


def create_abilities():
    abilities = []
    for ability in ABILITIES:
        ability_data = get_ability_data(ability)
        ability_class = Ability(name=ability_data['full_name'], description=ability_data['description'], skills=ability_data['skills'])
        abilities.append(ability_class)
    return abilities


ABILITIES_DATA = create_abilities()


def get_ability(ability_name):
    for i in ABILITIES_DATA:
        if ability_name == i.name:
            return {
                "name": i.name,
                "description": i.description,
                "skills": i.skills
            }


print(get_ability("Strength"))