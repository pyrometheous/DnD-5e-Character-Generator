import character
import roll


def main():
    random_character = character.create_random_character()
    print(random_character.display_character_sheet())
    # print("Random Character:")
    # new_character = character.create_random_character()
    # new_character.display_character_sheet()
    # print("Custom Character:")
    # custom_character = character.create_character(name="Delgado", species="Human", character_class="Ranger", sex="Male", level=1)
    # custom_character.display_character_sheet()
    # print(roll.dice("3d8"))
    return


if __name__ == "__main__":
    main()