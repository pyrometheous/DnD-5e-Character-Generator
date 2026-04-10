import argparse
import random

from tinys_srd import Classes
from tinys_srd import Races as Species

from scripts import character
from scripts.party_balance import build_balanced_party, format_party_summary
from scripts.spellbook import build_spellbook_for_character, format_spellbook, save_spellbook_to_file


def parse_requested_values(raw_value, valid_values, label):
    if raw_value is None:
        return []

    lookup = {}
    for value in valid_values:
        normalized = value.replace('_', ' ').strip().lower()
        lookup[normalized] = value
        lookup[value.lower()] = value

    tokens = [token.strip() for token in raw_value.split(',') if token.strip()]
    resolved = []
    invalid = []

    for token in tokens:
        normalized = token.replace('_', ' ').strip().lower()
        match = lookup.get(normalized)
        if match is None:
            invalid.append(token)
            continue
        if match not in resolved:
            resolved.append(match)

    if invalid:
        raise ValueError(
            f"Invalid {label}(s): {', '.join(invalid)}. "
            f"Valid options: {', '.join(valid_values)}"
        )

    return resolved


def choose_requested_value(values, index):
    if not values:
        return None
    if index < len(values):
        return values[index]
    return random.choice(values)


def maybe_generate_spellbook(new_character, should_generate):
    if not should_generate:
        return

    spellbook = build_spellbook_for_character(new_character)
    if spellbook is None:
        print(
            f"{new_character.name} the {new_character.char_class.capitalize()} "
            "does not have a class spellbook to generate."
        )
        return

    print()
    print(format_spellbook(spellbook))
    output_path = save_spellbook_to_file(spellbook)
    print(f"Spellbook saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="D&D 5e Random Character, Party, and Spellbook Generator"
    )
    parser.add_argument(
        '--level', type=int, default=None,
        help="Character level (1-20). Random if not specified."
    )
    parser.add_argument(
        '--class', dest='char_class', type=str, default=None,
        help=(
            "Character class, or a comma-separated class list. "
            "With --balance, these act as party anchors/preferences."
        )
    )
    parser.add_argument(
        '--species', type=str, default=None,
        help=(
            "Character species, or a comma-separated species list. "
            "Random if not specified."
        )
    )
    font_names = list(character.AVAILABLE_FONTS.keys())
    parser.add_argument(
        '--font', type=str, default=None,
        choices=font_names,
        help="Fantasy font for the PDF. Choices: " + ', '.join(font_names)
    )
    parser.add_argument(
        '--characters', type=int, default=1,
        help="Number of characters to generate (default: 1)."
    )
    parser.add_argument(
        '--balance', action='store_true',
        help=(
            "Generate a theoretically balanced party using the rules in "
            "config/party_balance_rules.json."
        )
    )
    parser.add_argument(
        '--spellbook', action='store_true',
        help=(
            "Generate a random class-appropriate spellbook for each "
            "spellcasting character."
        )
    )
    args = parser.parse_args()

    valid_species = [s.capitalize() for s in Species.entries]

    try:
        selected_classes = parse_requested_values(args.char_class, Classes.entries, 'class')
        selected_species = parse_requested_values(args.species, valid_species, 'species')
    except ValueError as exc:
        parser.error(str(exc))

    if args.balance:
        party_members = build_balanced_party(
            party_size=args.characters,
            level=args.level,
            preferred_classes=selected_classes or None,
            preferred_species=selected_species or None,
        )
        print(format_party_summary(party_members))

        for index, party_member in enumerate(party_members, start=1):
            if args.characters > 1:
                print(f"\n--- Character {index} of {args.characters} ---")
            new_character = party_member['character']
            new_character.display_character_sheet()
            maybe_generate_spellbook(new_character, args.spellbook)
            new_character.create_pdf_file(font_name=args.font)
        return

    for index in range(args.characters):
        if args.characters > 1:
            print(f"\n--- Character {index + 1} of {args.characters} ---")
        new_character = character.create_random_character(
            level=args.level,
            char_class=choose_requested_value(selected_classes, index),
            species=choose_requested_value(selected_species, index),
        )
        new_character.display_character_sheet()
        maybe_generate_spellbook(new_character, args.spellbook)
        new_character.create_pdf_file(font_name=args.font)


if __name__ == "__main__":
    main()