from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Iterable

from scripts.character import create_random_character

CONFIG_PATH = (
    Path(__file__).resolve().parent.parent / "config" / "party_balance_rules.json"
)


def load_party_balance_config(config_path: str | Path | None = None) -> dict:
    target_path = Path(config_path) if config_path else CONFIG_PATH
    with target_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _dedupe_preserve_order(values: Iterable[str] | None) -> list[str]:
    if not values:
        return []
    return list(dict.fromkeys(values))


def _get_role_plan(party_size: int, config: dict) -> list[str]:
    templates = config.get("party_size_roles", {})
    if str(party_size) in templates:
        return list(templates[str(party_size)])

    if not templates:
        return ["frontline"] * max(1, party_size)

    largest_size = max(int(size) for size in templates)
    roles = list(templates[str(largest_size)])
    overflow_roles = config.get("overflow_role_cycle", ["support", "striker", "frontline"])
    while len(roles) < party_size:
        overflow_index = (len(roles) - largest_size) % len(overflow_roles)
        roles.append(overflow_roles[overflow_index])
    return roles[:party_size]


def _get_class_roles(config: dict) -> dict[str, set[str]]:
    class_roles: dict[str, set[str]] = {}
    for role_name, role_info in config.get("role_definitions", {}).items():
        for class_name in role_info.get("classes", []):
            class_roles.setdefault(class_name, set()).add(role_name)
    return class_roles


def _get_capability_map(config: dict) -> dict[str, set[str]]:
    capability_map: dict[str, set[str]] = {}
    for capability, classes in config.get("capability_requirements", {}).get("must_have", {}).items():
        for class_name in classes:
            capability_map.setdefault(class_name, set()).add(capability)
    return capability_map


def _get_missing_capabilities(
    selected_classes: list[str],
    capability_map: dict[str, set[str]],
    required_capabilities: set[str],
) -> set[str]:
    covered_capabilities: set[str] = set()
    for class_name in selected_classes:
        covered_capabilities.update(capability_map.get(class_name, set()))
    return required_capabilities - covered_capabilities


def _score_candidate(
    candidate: str,
    role: str,
    selected_classes: list[str],
    remaining_roles: list[str],
    preferred_classes: list[str],
    class_roles: dict[str, set[str]],
    capability_map: dict[str, set[str]],
    missing_capabilities: set[str],
    synergy_map: dict[str, list[str]],
) -> int:
    score = 0
    candidate_roles = class_roles.get(candidate, set())

    if candidate not in selected_classes:
        score += 5
    else:
        score -= 4

    if role in candidate_roles:
        score += 4

    if candidate in preferred_classes:
        score += 3

    score += len(candidate_roles.intersection(set(remaining_roles))) * 2
    score += len(capability_map.get(candidate, set()).intersection(missing_capabilities)) * 4

    for existing_class in selected_classes:
        if candidate in synergy_map.get(existing_class, []):
            score += 2
        if existing_class in synergy_map.get(candidate, []):
            score += 2

    if not selected_classes and "frontline" in candidate_roles:
        score += 1

    return score


def _choose_class_for_role(
    role: str,
    selected_classes: list[str],
    remaining_roles: list[str],
    preferred_classes: list[str],
    config: dict,
    class_roles: dict[str, set[str]],
    capability_map: dict[str, set[str]],
    missing_capabilities: set[str],
) -> str:
    role_candidates = list(
        config.get("role_definitions", {}).get(role, {}).get("classes", [])
    )
    unused_preferred = [
        class_name for class_name in preferred_classes if class_name not in selected_classes
    ]
    preferred_for_role = [
        class_name
        for class_name in unused_preferred
        if role in class_roles.get(class_name, set())
        or capability_map.get(class_name, set()).intersection(missing_capabilities)
    ]
    candidate_pool = list(dict.fromkeys(role_candidates + preferred_for_role))
    if not candidate_pool:
        candidate_pool = list(dict.fromkeys(role_candidates + unused_preferred))
    if not candidate_pool:
        candidate_pool = list(class_roles.keys())

    synergy_map = config.get("class_synergy", {})
    scored_candidates = []
    for candidate in candidate_pool:
        score = _score_candidate(
            candidate=candidate,
            role=role,
            selected_classes=selected_classes,
            remaining_roles=remaining_roles,
            preferred_classes=preferred_classes,
            class_roles=class_roles,
            capability_map=capability_map,
            missing_capabilities=missing_capabilities,
            synergy_map=synergy_map,
        )
        scored_candidates.append((score, random.random(), candidate))

    scored_candidates.sort(reverse=True)
    return scored_candidates[0][2]


def _reserve_preferred_classes(
    role_plan: list[str],
    preferred_classes: list[str],
    class_roles: dict[str, set[str]],
) -> dict[str, str]:
    reserved_roles: dict[str, str] = {}
    remaining_roles = list(role_plan)

    for class_name in preferred_classes:
        for role in list(remaining_roles):
            if role in class_roles.get(class_name, set()):
                reserved_roles[role] = class_name
                remaining_roles.remove(role)
                break

    return reserved_roles


def _pick_species_for_role(
    role: str,
    preferred_species: list[str],
    config: dict,
    index: int,
) -> str | None:
    if preferred_species:
        if index < len(preferred_species):
            return preferred_species[index]
        return random.choice(preferred_species)

    role_species = config.get("species_preferences", {}).get(role, [])
    if role_species:
        return random.choice(role_species)

    default_species = config.get("default_species_pool", [])
    return random.choice(default_species) if default_species else None


def plan_balanced_party(
    party_size: int,
    preferred_classes: Iterable[str] | None = None,
    preferred_species: Iterable[str] | None = None,
    config_path: str | Path | None = None,
) -> tuple[list[dict], dict]:
    config = load_party_balance_config(config_path)
    party_size = max(1, int(party_size))
    preferred_classes = _dedupe_preserve_order(preferred_classes)
    preferred_species = _dedupe_preserve_order(preferred_species)
    class_roles = _get_class_roles(config)
    capability_map = _get_capability_map(config)
    required_capabilities = set(
        config.get("capability_requirements", {}).get("must_have", {}).keys()
    )

    role_plan = _get_role_plan(party_size, config)
    reserved_classes = _reserve_preferred_classes(
        role_plan=role_plan,
        preferred_classes=preferred_classes,
        class_roles=class_roles,
    )
    selected_classes: list[str] = []
    planned_party: list[dict] = []

    for index, role in enumerate(role_plan):
        remaining_roles = role_plan[index:]
        missing_capabilities = _get_missing_capabilities(
            selected_classes, capability_map, required_capabilities
        )
        chosen_class = reserved_classes.get(role)
        if chosen_class is None or chosen_class in selected_classes:
            chosen_class = _choose_class_for_role(
                role=role,
                selected_classes=selected_classes,
                remaining_roles=remaining_roles,
                preferred_classes=preferred_classes,
                config=config,
                class_roles=class_roles,
                capability_map=capability_map,
                missing_capabilities=missing_capabilities,
            )
        selected_classes.append(chosen_class)
        planned_party.append(
            {
                "class": chosen_class,
                "role": role,
                "species": _pick_species_for_role(role, preferred_species, config, index),
            }
        )

    return planned_party, config


def build_balanced_party(
    party_size: int,
    level: int | None = None,
    preferred_classes: Iterable[str] | None = None,
    preferred_species: Iterable[str] | None = None,
    config_path: str | Path | None = None,
) -> list[dict]:
    planned_party, _ = plan_balanced_party(
        party_size=party_size,
        preferred_classes=preferred_classes,
        preferred_species=preferred_species,
        config_path=config_path,
    )

    generated_party = []
    for member_plan in planned_party:
        new_character = create_random_character(
            level=level,
            char_class=member_plan["class"],
            species=member_plan["species"],
        )
        generated_party.append(
            {
                "character": new_character,
                "role": member_plan["role"],
            }
        )

    return generated_party


def format_party_summary(
    party_members: list[dict], config_path: str | Path | None = None
) -> str:
    if not party_members:
        return "No party members were generated."

    config = load_party_balance_config(config_path)
    capability_map = _get_capability_map(config)
    role_definitions = config.get("role_definitions", {})
    covered_capabilities: set[str] = set()
    summary_lines = ["Balanced party plan:"]

    for item in party_members:
        generated_character = item["character"]
        role_name = item["role"]
        role_label = role_definitions.get(role_name, {}).get(
            "label", role_name.replace("_", " ").title()
        )
        covered_capabilities.update(capability_map.get(generated_character.char_class, set()))
        summary_lines.append(
            f"  - {generated_character.char_class.capitalize()} "
            f"({generated_character.species}) — {role_label}"
        )

    if covered_capabilities:
        summary_lines.append(
            "Coverage: " + ", ".join(sorted(capability.replace("_", " ") for capability in covered_capabilities))
        )

    return "\n".join(summary_lines)
