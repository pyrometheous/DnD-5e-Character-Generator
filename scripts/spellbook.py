from __future__ import annotations

import random
from pathlib import Path

from tinys_srd import Levels, Spells

from scripts.character import SPELLCASTING_ABILITY, modifier

PREPARED_SPELL_ABILITIES = {
    "cleric": "wisdom",
    "druid": "wisdom",
    "paladin": "charisma",
    "wizard": "intelligence",
}

HALF_CASTER_CLASSES = {"paladin", "ranger", "warlock"}


def _ordinal(level: int) -> str:
    if 10 <= level % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(level % 10, "th")
    return f"{level}{suffix}"


def _spell_to_dict(spell) -> dict:
    school = getattr(spell, "school", {}) or {}
    return {
        "name": spell.name,
        "level": int(spell.level),
        "school": school.get("name", "Unknown"),
    }


def _get_spell_pool(char_class: str) -> dict[int, list]:
    class_name = char_class.lower()
    pool: dict[int, list] = {level: [] for level in range(10)}

    for spell_index in Spells.entries:
        spell = getattr(Spells, spell_index)
        spell_classes = {
            class_info["name"].lower()
            for class_info in getattr(spell, "classes", [])
        }
        if class_name in spell_classes:
            pool.setdefault(int(spell.level), []).append(spell)

    for spells in pool.values():
        spells.sort(key=lambda entry: entry.name)

    return pool


def _get_spell_slots(spellcasting: dict) -> dict[int, int]:
    slot_map = {}
    for level in range(1, 10):
        slots = int(spellcasting.get(f"spell_slots_level_{level}", 0))
        if slots > 0:
            slot_map[level] = slots
    return slot_map


def _estimate_leveled_spell_count(character_obj, spellcasting: dict) -> int:
    char_class = character_obj.char_class

    if char_class == "wizard":
        return 6 + max(0, (character_obj.level - 1) * 2)

    if spellcasting.get("spells_known"):
        return int(spellcasting["spells_known"])

    ability_name = PREPARED_SPELL_ABILITIES.get(char_class)
    if ability_name:
        ability_mod = max(1, modifier(getattr(character_obj, ability_name)))
        if char_class == "paladin":
            return max(1, (character_obj.level // 2) + ability_mod)
        return max(1, character_obj.level + ability_mod)

    spell_slots = _get_spell_slots(spellcasting)
    return max(1, sum(spell_slots.values())) if spell_slots else 0


def _allocate_spells_by_level(
    known_spell_count: int,
    spell_slots: dict[int, int],
    spell_pool: dict[int, list],
    char_class: str,
) -> dict[int, int]:
    available_levels = sorted(spell_slots)
    allocation = {level: 0 for level in available_levels}

    if known_spell_count <= 0 or not available_levels:
        return allocation

    base_spells_per_level = 1 if char_class in HALF_CASTER_CLASSES else 2

    for level in available_levels:
        if known_spell_count <= 0:
            break
        picks = min(base_spells_per_level, len(spell_pool.get(level, [])), known_spell_count)
        allocation[level] += picks
        known_spell_count -= picks

    weighted_levels = [
        level for level in available_levels for _ in range(max(1, spell_slots[level]))
    ]
    stalled_attempts = 0

    while known_spell_count > 0 and weighted_levels:
        level = random.choice(weighted_levels)
        max_spells_at_level = len(spell_pool.get(level, []))
        if allocation[level] < max_spells_at_level:
            allocation[level] += 1
            known_spell_count -= 1
            stalled_attempts = 0
        else:
            stalled_attempts += 1
            if stalled_attempts > len(weighted_levels) * 3:
                break

    return allocation


def build_spellbook_for_character(character_obj) -> dict | None:
    char_class = character_obj.char_class.lower()
    if char_class not in SPELLCASTING_ABILITY:
        return None

    level_data = getattr(Levels, f"{char_class}_{character_obj.level}")
    spellcasting = getattr(level_data, "spellcasting", None)
    if not spellcasting:
        return None

    spell_pool = _get_spell_pool(char_class)
    cantrip_count = int(spellcasting.get("cantrips_known", 0))
    cantrip_pool = spell_pool.get(0, [])
    cantrips = random.sample(cantrip_pool, min(cantrip_count, len(cantrip_pool)))

    spell_slots = _get_spell_slots(spellcasting)
    known_spell_count = _estimate_leveled_spell_count(character_obj, spellcasting)
    level_allocations = _allocate_spells_by_level(
        known_spell_count=known_spell_count,
        spell_slots=spell_slots,
        spell_pool=spell_pool,
        char_class=char_class,
    )

    spells_by_level = {}
    for level, spell_count in level_allocations.items():
        picked_spells = random.sample(
            spell_pool.get(level, []),
            min(spell_count, len(spell_pool.get(level, []))),
        )
        spells_by_level[level] = sorted(picked_spells, key=lambda spell: spell.name)

    return {
        "name": character_obj.name,
        "class": char_class,
        "level": character_obj.level,
        "ability": SPELLCASTING_ABILITY[char_class],
        "cantrips": [_spell_to_dict(spell) for spell in sorted(cantrips, key=lambda spell: spell.name)],
        "spells_by_level": {
            level: [_spell_to_dict(spell) for spell in spells]
            for level, spells in sorted(spells_by_level.items())
        },
        "spell_slots": spell_slots,
    }


def format_spellbook(spellbook: dict) -> str:
    lines = [
        f"Spellbook for {spellbook['name']}",
        f"Class: {spellbook['class'].capitalize()} | Level: {spellbook['level']}",
        f"Spellcasting Ability: {spellbook['ability'].capitalize()}",
    ]

    if spellbook["cantrips"]:
        lines.append(f"\nCantrips ({len(spellbook['cantrips'])}):")
        for spell in spellbook["cantrips"]:
            lines.append(f"  - {spell['name']} ({spell['school']})")

    for level, spells in spellbook["spells_by_level"].items():
        slot_count = spellbook["spell_slots"].get(level, 0)
        lines.append(
            f"\n{_ordinal(level)}-level spells ({len(spells)} selected, {slot_count} slots):"
        )
        for spell in spells:
            lines.append(f"  - {spell['name']} ({spell['school']})")

    return "\n".join(lines)


def save_spellbook_to_file(spellbook: dict, output_dir: str | Path = ".") -> str:
    output_path = Path(output_dir) / f"{spellbook['name'].replace(' ', '_')}_Spellbook.txt"
    output_path.write_text(format_spellbook(spellbook) + "\n", encoding="utf-8")
    return str(output_path)
