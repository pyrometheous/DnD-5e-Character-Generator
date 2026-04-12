# CLI Usage (main.py)

The command-line generator is the standalone tool and remains fully supported.

## Setup

1. Install Python 3.10+.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

## Run On Linux

```bash
python3 main.py [OPTIONS]
```

## Run On macOS

```bash
python3 main.py [OPTIONS]
```

## Run On Windows

```powershell
py main.py [OPTIONS]
```

## Common Arguments

- `--level` int (1-20), random if omitted
- `--class` class name or comma-separated class list
- `--species` species name or comma-separated species list
- `--font` fantasy font key
- `--characters` number of characters
- `--balance` build theoretically balanced party
- `--spellbook` build class-appropriate spellbook for caster classes
- `--spellcards` append 3x5 spell cards to the output PDF for caster classes

## Examples

```bash
# Single random character
python3 main.py

# Level 1 Human Fighter in Cinzel
python3 main.py --level 1 --class fighter --species Human --font cinzel

# Balanced 4-character level-8 party, anchored around fighter+wizard
python3 main.py --level 8 --characters 4 --balance --class fighter,wizard

# Wizard with spellbook
python3 main.py --class wizard --level 10 --spellbook

# Wizard with spell cards (also builds spellbook data)
python3 main.py --class wizard --level 10 --spellcards --font cinzel
```
