from __future__ import annotations

import json
import random
from pathlib import Path

from tinys_srd import Levels, Spells

from scripts.character import SPELLCASTING_ABILITY, modifier
from scripts.progression import ensure_progression, export_spellbook

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "spellbook_rules.json"


def load_spellbook_config(config_path: str | Path | None = None) -> dict:
    target_path = Path(config_path) if config_path else CONFIG_PATH
    with target_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _normalize_name(value: str) -> str:
    return value.strip().lower().replace("_", " ").replace("-", " ")


def _lookup_capabilities(name: str, mapping: dict[str, list[str]]) -> set[str]:
    normalized = _normalize_name(name)
    capabilities: set[str] = set()
    for key, values in mapping.items():
        normalized_key = _normalize_name(key)
        if normalized == normalized_key or normalized.startswith(f"{normalized_key} ("):
            capabilities.update(values)
    return capabilities


def _collect_character_capabilities(character_obj, config: dict) -> set[str]:
    capabilities: set[str] = set()
    for species_name, species_capabilities in config.get("species_capabilities", {}).items():
        if _normalize_name(species_name) == _normalize_name(character_obj.species):
            capabilities.update(species_capabilities)

    for trait in character_obj.get_traits():
        capabilities.update(
            _lookup_capabilities(trait, config.get("trait_capability_map", {}))
        )

    for feature in character_obj.get_features():
        capabilities.update(
            _lookup_capabilities(feature, config.get("feature_capability_map", {}))
        )

    for rule in config.get("level_based_capabilities", []):
        min_level = int(rule.get("min_level", 1))
        if character_obj.level < min_level:
            continue
        if (
            rule.get("species")
            and _normalize_name(rule["species"]) != _normalize_name(character_obj.species)
        ):
            continue
        if (
            rule.get("class")
            and _normalize_name(rule["class"]) != _normalize_name(character_obj.char_class)
        ):
            continue
        capabilities.update(rule.get("capabilities", []))

    return capabilities


def _spell_is_redundant(spell, character_capabilities: set[str], config: dict) -> bool:
    normalized_spell = _normalize_name(spell.name)
    for rule in config.get("spell_redundancy_rules", []):
        if _normalize_name(rule.get("spell", "")) != normalized_spell:
            continue

        blocked_by_any = set(rule.get("blocked_by_any_capabilities", []))
        blocked_by_all = set(rule.get("blocked_by_all_capabilities", []))

        if blocked_by_any and character_capabilities.intersection(blocked_by_any):
            return True
        if blocked_by_all and blocked_by_all.issubset(character_capabilities):
            return True

    return False


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


def _get_spell_pool(
    char_class: str,
    character_capabilities: set[str],
    config: dict,
) -> dict[int, list]:
    class_name = char_class.lower()
    pool: dict[int, list] = {level: [] for level in range(10)}

    for spell_index in Spells.entries:
        spell = getattr(Spells, spell_index)
        spell_classes = {
            class_info["name"].lower()
            for class_info in getattr(spell, "classes", [])
        }
        if class_name in spell_classes and not _spell_is_redundant(
            spell, character_capabilities, config
        ):
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


def _get_castable_levels(spell_slots: dict[int, int], spell_pool: dict[int, list]) -> list[int]:
    if not spell_slots:
        return []

    highest_spell_level = max(spell_slots)
    return [
        level
        for level in range(1, highest_spell_level + 1)
        if spell_pool.get(level)
    ]


def _estimate_leveled_spell_count(
    character_obj,
    spellcasting: dict,
    config: dict,
) -> int:
    char_class = character_obj.char_class
    spell_slots = _get_spell_slots(spellcasting)
    slot_total = sum(spell_slots.values())

    if char_class == "wizard":
        return max(slot_total, 6 + max(0, (character_obj.level - 1) * 2))

    if spellcasting.get("spells_known"):
        return max(slot_total, int(spellcasting["spells_known"]))

    ability_name = config.get("prepared_spellcasting_abilities", {}).get(char_class)
    if ability_name:
        ability_mod = max(1, modifier(getattr(character_obj, ability_name)))
        if char_class == "paladin":
            prepared_spells = max(1, (character_obj.level // 2) + ability_mod)
        else:
            prepared_spells = max(1, character_obj.level + ability_mod)
        return max(slot_total, prepared_spells)

    return max(1, slot_total) if spell_slots else 0


def _allocate_spells_by_level(
    known_spell_count: int,
    spell_slots: dict[int, int],
    spell_pool: dict[int, list],
    char_class: str,
    config: dict,
) -> dict[int, int]:
    available_levels = _get_castable_levels(spell_slots, spell_pool)
    allocation = {level: 0 for level in available_levels}

    if known_spell_count <= 0 or not available_levels:
        return allocation

    slot_targets = {
        level: max(1, int(spell_slots.get(level, 0)))
        for level in available_levels
    }

    for level in available_levels:
        if known_spell_count <= 0:
            break
        if not spell_pool.get(level):
            continue
        allocation[level] += 1
        known_spell_count -= 1

    for level in available_levels:
        if known_spell_count <= 0:
            break
        max_spells_at_level = len(spell_pool.get(level, []))
        desired_count = min(slot_targets[level], max_spells_at_level)
        if allocation[level] >= desired_count:
            continue

        additional_spells = min(desired_count - allocation[level], known_spell_count)
        allocation[level] += additional_spells
        known_spell_count -= additional_spells

    weighted_levels = [
        level for level in available_levels for _ in range(max(1, slot_targets[level]))
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


def build_spellbook_for_character(
    character_obj,
    config_path: str | Path | None = None,
) -> dict | None:
    char_class = character_obj.char_class.lower()
    if char_class not in SPELLCASTING_ABILITY:
        return None

    ensure_progression(character_obj, spellbook_config=load_spellbook_config(config_path))
    return export_spellbook(character_obj)


def format_spellbook(spellbook: dict) -> str:
    lines = [
        f"Spellbook for {spellbook['name']}",
        f"Class: {spellbook['class'].capitalize()} | Level: {spellbook['level']}",
        f"Spellcasting Ability: {spellbook['ability'].capitalize()}",
    ]

    if spellbook.get('subclass'):
        lines.append(f"Subclass: {spellbook['subclass']}")

    if spellbook["cantrips"]:
        lines.append(f"\nCantrips ({len(spellbook['cantrips'])}):")
        for spell in spellbook["cantrips"]:
            lines.append(f"  - {spell['name']} ({spell['school']})")

    always_prepared = spellbook.get('always_prepared', [])
    if always_prepared:
        lines.append(f"\nAlways prepared / bonus spells ({len(always_prepared)}):")
        for spell in always_prepared:
            lines.append(f"  - {spell['name']} ({spell['school']})")

    for level, spells in spellbook["spells_by_level"].items():
        slot_count = spellbook["spell_slots"].get(level, 0)
        lines.append(
            f"\n{_ordinal(level)}-level spells ({len(spells)} selected, {slot_count} slots):"
        )
        for spell in spells:
            lines.append(f"  - {spell['name']} ({spell['school']})")

    prepared_spells = spellbook.get('prepared_spells', {})
    if prepared_spells:
        lines.append("\nPrepared loadout:")
        for level, spells in prepared_spells.items():
            lines.append(f"  {_ordinal(level)} level:")
            for spell in spells:
                lines.append(f"    - {spell['name']} ({spell['school']})")

    mystic_arcanum = spellbook.get('mystic_arcanum', {})
    if mystic_arcanum:
        lines.append("\nMystic Arcanum:")
        for level, spell in mystic_arcanum.items():
            lines.append(f"  - {level}th: {spell['name']} ({spell['school']})")

    replacement_log = spellbook.get('replacement_log', [])
    if replacement_log:
        lines.append("\nSpell replacements:")
        for entry in replacement_log:
            lines.append(
                f"  - Level {entry['level']}: {entry['replaced']} -> {entry['new_spell']}"
            )

    return "\n".join(lines)


def save_spellbook_to_file(spellbook: dict, output_dir: str | Path = ".") -> str:
    output_path = Path(output_dir) / f"{spellbook['name'].replace(' ', '_')}_Spellbook.txt"
    output_path.write_text(format_spellbook(spellbook) + "\n", encoding="utf-8")
    return str(output_path)
