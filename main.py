import argparse
import character

from tinys_srd import Classes
from tinys_srd import Races as Species


def main():
    parser = argparse.ArgumentParser(
        description="D&D 5e Random Character Generator"
    )
    parser.add_argument(
        '--level', type=int, default=None,
        help="Character level (1-20). Random if not specified."
    )
    parser.add_argument(
        '--class', dest='char_class', type=str, default=None,
        choices=Classes.entries,
        help="Character class. Random if not specified."
    )
    parser.add_argument(
        '--species', type=str, default=None,
        choices=[s.capitalize() for s in Species.entries],
        help="Character species/race. Random if not specified."
    )
    font_names = list(character.AVAILABLE_FONTS.keys())
    font_help_lines = [f"  {k}: {v['desc']}" for k, v in character.AVAILABLE_FONTS.items()]
    parser.add_argument(
        '--font', type=str, default=None,
        choices=font_names,
        help="Fantasy font for the PDF. Choices: " + ', '.join(font_names)
    )
    args = parser.parse_args()

    new_character = character.create_random_character(
        level=args.level,
        char_class=args.char_class,
        species=args.species,
    )
    new_character.display_character_sheet()
    new_character.create_pdf_file(font_name=args.font)


if __name__ == "__main__":
    main()