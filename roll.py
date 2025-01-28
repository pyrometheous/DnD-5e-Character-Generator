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


def attack(dice_to_roll, modifier=None):
    num_rolls, die = dice_to_roll.split('d')
    die = f"d{die}"
    if die in DICE:
        roll = dice(dice_to_roll)
    else:
        raise Exception(f"Invalid dice_to_roll={dice_to_roll}. Good Example: 1d6 or 3d8")
    if modifier:
        roll = roll + modifier
    # print(f"Roll: {roll}")
    return roll


def to_hit(armor_class, modifier=None):
    if modifier:
        roll = d20() + modifier
    else:
        roll = d20()
    # print(f"Roll: {roll}")
    if roll >= armor_class:
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