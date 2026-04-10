# D&D 5e Character Generator

A command-line tool that generates random, rules-legal D&D 5th Edition characters (levels 1–20) and outputs filled PDF character sheets with fantasy fonts.

## Setup

### Requirements

- Python 3.10+

### Installation

```bash
git clone https://github.com/pyrometheous/dnd_5e_character_generator.git
cd dnd_5e_character_generator
pip install -r requirements.txt
```

## Usage

```bash
python3 main.py [OPTIONS]
```

Running with no arguments generates a single character with a random class, species, level, and font.

### Arguments

| Argument | Type | Default | Description |
|---|---|---|---|
| `--level` | int (1–20) | Random | Character level. |
| `--class` | string | Random | Character class. |
| `--species` | string | Random | Character species/race. |
| `--font` | string | Random | Fantasy font for the PDF. |
| `--characters` | int | 1 | Number of characters to generate. |
| `--balance` | flag | Off | Build a theoretically balanced party for the requested group size. |
| `--spellbook` | flag | Off | Generate a random class-appropriate spellbook for spellcasting classes. |

### Valid Values

**Classes:** `barbarian`, `bard`, `cleric`, `druid`, `fighter`, `monk`, `paladin`, `ranger`, `rogue`, `sorcerer`, `warlock`, `wizard`

**Species:** `Dwarf`, `Elf`, `Halfling`, `Human`, `Dragonborn`, `Gnome`, `Half_elf`, `Half_orc`, `Tiefling`

**Fonts:**

| Font | Description |
|---|---|
| [`cinzel`](https://fonts.google.com/specimen/Cinzel) | Elegant serif, great readability |
| [`medievalsharp`](https://fonts.google.com/specimen/MedievalSharp) | Whimsical medieval script |
| [`almendra`](https://fonts.google.com/specimen/Almendra) | Fantasy serif inspired by calligraphy |
| [`metamorphous`](https://fonts.google.com/specimen/Metamorphous) | Dark fantasy display font |
| [`pirataone`](https://fonts.google.com/specimen/Pirata+One) | Pirate/adventure theme |
| [`imfell`](https://fonts.google.com/specimen/IM+Fell+English+SC) | Historic English printing style |
| [`uncialantiqua`](https://fonts.google.com/specimen/Uncial+Antiqua) | Celtic/uncial manuscript style |

### Examples

```bash
# Generate a single random character
python3 main.py

# Level 1 Human Fighter with a specific font
python3 main.py --level 1 --class fighter --species Human --font cinzel

# 5 level-1 characters with random classes and species
python3 main.py --level 1 --characters 5

# A balanced 5-person level-10 party
python3 main.py --level 10 --characters 5 --balance

# A balanced party built around a fighter and wizard
python3 main.py --level 8 --characters 4 --balance --class fighter,wizard

# A level-10 wizard with a random spellbook
python3 main.py --class wizard --level 10 --spellbook

# 3 random-level Wizards
python3 main.py --class wizard --characters 3
```

### Output

Each character produces:
- A character sheet printed to the terminal
- A filled PDF saved to the current directory as `<Name>_Character_Sheet.pdf`

The PDF is based on the official WotC D&D 5E form-fillable character sheet and includes ability scores, saving throws, skills, equipment, proficiencies, languages, features, traits, and spell slots (for caster classes).

If you use `--spellbook`, the generator also writes a plain-text spellbook file with random class-appropriate 5e spells for the generated caster.

Balanced party templates and class-role tuning live in `config/party_balance_rules.json`, so you can manually fine-tune what combinations the generator prefers.
