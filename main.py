import character
import roll


def main():
    new_character = character.create_random_character()
    new_character.display_character_sheet()
    # new_character.create_pdf_file()
    return


if __name__ == "__main__":
    main()