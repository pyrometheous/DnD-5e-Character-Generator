from __future__ import annotations

import json
import random
from pathlib import Path

from tinys_srd import Levels, Spells

from scripts.character import SPELLCASTING_ABILITY, modifier

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


def _estimate_leveled_spell_count(
    character_obj,
    spellcasting: dict,
    config: dict,
) -> int:
    char_class = character_obj.char_class

    if char_class == "wizard":
        return 6 + max(0, (character_obj.level - 1) * 2)

    if spellcasting.get("spells_known"):
        return int(spellcasting["spells_known"])

    ability_name = config.get("prepared_spellcasting_abilities", {}).get(char_class)
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
    config: dict,
) -> dict[int, int]:
    available_levels = sorted(spell_slots)
    allocation = {level: 0 for level in available_levels}

    if known_spell_count <= 0 or not available_levels:
        return allocation

    limited_caster_classes = set(config.get("limited_caster_classes", []))
    if char_class in limited_caster_classes:
        base_spells_per_level = int(config.get("limited_caster_base_spells_per_level", 1))
    else:
        base_spells_per_level = int(config.get("default_base_spells_per_level", 2))

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


def build_spellbook_for_character(
    character_obj,
    config_path: str | Path | None = None,
) -> dict | None:
    config = load_spellbook_config(config_path)
    char_class = character_obj.char_class.lower()
    if char_class not in SPELLCASTING_ABILITY:
        return None

    level_data = getattr(Levels, f"{char_class}_{character_obj.level}")
    spellcasting = getattr(level_data, "spellcasting", None)
    if not spellcasting:
        return None

    character_capabilities = _collect_character_capabilities(character_obj, config)
    spell_pool = _get_spell_pool(char_class, character_capabilities, config)
    cantrip_count = int(spellcasting.get("cantrips_known", 0))
    cantrip_pool = spell_pool.get(0, [])
    cantrips = random.sample(cantrip_pool, min(cantrip_count, len(cantrip_pool)))

    spell_slots = _get_spell_slots(spellcasting)
    known_spell_count = _estimate_leveled_spell_count(
        character_obj, spellcasting, config
    )
    level_allocations = _allocate_spells_by_level(
        known_spell_count=known_spell_count,
        spell_slots=spell_slots,
        spell_pool=spell_pool,
        char_class=char_class,
        config=config,
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
        "capabilities": sorted(character_capabilities),
        "cantrips": [
            _spell_to_dict(spell)
            for spell in sorted(cantrips, key=lambda spell: spell.name)
        ],
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
