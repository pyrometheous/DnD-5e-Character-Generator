import random


def d6():
    return random.randint(1, 6)


def d8():
    return random.randint(1, 8)


def d10():
    return random.randint(1, 10)


def d12():
    return random.randint(1, 12)


def d20():
    return random.randint(1, 20)


def d100():
    return random.randint(1, 100)


DICE = {
    "d6": d6,
    "d8": d8,
    "d10": d10,
    "d12": d12,
    "d20": d20,
    "d100": d100
}


def attack(die, modifier=None):
    if die in DICE:
        roll = DICE[die]()
    else:
        return "Invalid Die"

    if modifier:
        roll = roll + modifier

    return roll


def to_hit(armor_class, modifier=None):
    if modifier:
        roll = d20() + modifier
    else:
        roll = d20()
    if roll <= armor_class:
        return True
    else:
        return False


def dice(dice_to_roll):
    number_of_rolls, die = int(dice_to_roll.split('d')[0]), f"d{dice_to_roll.split('d')[1]}"
    roll_total = 0
    if die in DICE:
        for roll_number in range(number_of_rolls):
            roll_total += DICE[die]()
        return roll_total
    else:
        return "Invalid Die"