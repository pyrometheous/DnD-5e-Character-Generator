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


def get_request(index):
    url = BASE_URL + index
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        print(f"Type: {type(data)}\nValue:\n\n")
    else:
        raise Exception(f"Request for {index} failed")
    return data


def get_skill(skill):
    index = f""
    data = get_request(index)
    return data


def get_ability_score(ability):
    ability_abbreviated = ABILITIES[ability]
    if ability_abbreviated in list(ABILITIES.values()):
        index = f"ability-scores/{ability_abbreviated}"
        data = get_request(index)
        print(data)
        url = data['url']
        index = url.replace("/api/", "")

        ability_data = {
            "full_name": data['full_name'],
            "description": data['desc'],
            "skills": {
            }
        }
        for skill in data['skills']:
            skill_name = skill['name']

            get_skill(skill_name)
        return
    else:
        raise Exception(f"{ability_abbreviated} is an invalid ability.")



ability = get_ability_score("Charisma")
