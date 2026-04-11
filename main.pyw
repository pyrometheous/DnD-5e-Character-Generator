#!/usr/bin/env python3
from __future__ import annotations

import os
import random
import subprocess
import sys
import traceback
from pathlib import Path


def show_popup(title: str, message: str) -> None:
    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(title, message)
        root.destroy()
    except Exception:
        print(f"{title}: {message}")


try:
    import pygame
except ImportError:
    show_popup(
        "Missing dependency",
        "PyGame is required for the GUI launcher.\n\n"
        "Please install the project requirements first:\n"
        "pip install -r requirements.txt",
    )
    raise

from tinys_srd import Classes
from tinys_srd import Races as Species

from scripts import character
from scripts.party_balance import build_balanced_party, format_party_summary
from scripts.spellbook import build_spellbook_for_character, format_spellbook

BASE_DIR = Path(__file__).resolve().parent
GUI_DIR = BASE_DIR / "GUI"
BACKGROUND_PATH = GUI_DIR / "parchment_bg.jpg"
FONT_PATH = GUI_DIR / "Cinzel-Regular.ttf"

WINDOW_TITLE = "The Fellowship Forge"
DEFAULT_SIZE = (1160, 780)
MIN_SIZE = (960, 680)
FPS = 60

PARCHMENT = (238, 227, 201)
PARCHMENT_DARK = (210, 194, 160)
INK = (56, 40, 20)
INK_SOFT = (91, 69, 42)
GOLD = (161, 126, 60)
GOLD_HOVER = (188, 149, 74)
FOREST = (73, 92, 67)
FOREST_SOFT = (103, 125, 96)
CRIMSON = (120, 64, 57)
WHITE = (250, 247, 241)
SHADOW = (28, 20, 11)


def clamp(value: int | float, lower: int | float, upper: int | float):
    return max(lower, min(upper, value))


def pretty_label(value: str) -> str:
    return value.replace("_", " ").title()


def open_output_folder(path: Path) -> None:
    target = str(path)
    if sys.platform.startswith("win"):
        os.startfile(target)  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", target])
    else:
        subprocess.Popen(["xdg-open", target])


def choose_requested_value(values: list[str], index: int):
    if not values:
        return None
    if index < len(values):
        return values[index]
    return random.choice(values)


def wrap_text(text: str, font: pygame.font.Font, max_width: int) -> list[str]:
    lines: list[str] = []
    for paragraph in text.splitlines():
        if not paragraph.strip():
            lines.append("")
            continue

        words = paragraph.split()
        current = words[0]
        for word in words[1:]:
            test = f"{current} {word}"
            if font.size(test)[0] <= max_width:
                current = test
            else:
                lines.append(current)
                current = word
        lines.append(current)
    return lines


def draw_text(
    surface: pygame.Surface,
    text: str,
    font: pygame.font.Font,
    color: tuple[int, int, int],
    pos: tuple[int, int],
    shadow: bool = False,
) -> None:
    if shadow:
        shadow_surface = font.render(text, True, SHADOW)
        surface.blit(shadow_surface, (pos[0] + 2, pos[1] + 2))
    rendered = font.render(text, True, color)
    surface.blit(rendered, pos)


class Dropdown:
    def __init__(self, options: list[str], value: str):
        self.options = [str(option) for option in options]
        self.value = str(value)
        self.rect = pygame.Rect(0, 0, 0, 0)
        self.drop_rect = pygame.Rect(0, 0, 0, 0)
        self.option_rects: list[tuple[str, pygame.Rect]] = []
        self.open = False
        self.scroll_index = 0
        self.max_visible = 9

    def draw(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        font: pygame.font.Font,
        mouse_pos: tuple[int, int],
    ) -> None:
        self.rect = rect
        is_hovered = rect.collidepoint(mouse_pos)
        border = GOLD_HOVER if is_hovered or self.open else GOLD
        pygame.draw.rect(surface, (248, 243, 232), rect, border_radius=10)
        pygame.draw.rect(surface, border, rect, width=2, border_radius=10)
        label = self.value
        text = font.render(label, True, INK)
        surface.blit(text, (rect.x + 12, rect.y + (rect.height - text.get_height()) // 2))

        caret = "▴" if self.open else "▾"
        caret_surface = font.render(caret, True, INK_SOFT)
        surface.blit(
            caret_surface,
            (
                rect.right - caret_surface.get_width() - 12,
                rect.y + (rect.height - caret_surface.get_height()) // 2,
            ),
        )

    def draw_menu(
        self,
        surface: pygame.Surface,
        font: pygame.font.Font,
        mouse_pos: tuple[int, int],
    ) -> None:
        self.option_rects = []
        self.drop_rect = pygame.Rect(0, 0, 0, 0)
        if not self.open:
            return

        rect = self.rect
        option_height = rect.height
        visible_count = min(len(self.options), self.max_visible)
        max_scroll = max(0, len(self.options) - visible_count)
        self.scroll_index = int(clamp(self.scroll_index, 0, max_scroll))
        visible_options = self.options[self.scroll_index:self.scroll_index + visible_count]

        drop_height = visible_count * option_height
        self.drop_rect = pygame.Rect(rect.x, rect.bottom + 4, rect.width, drop_height)
        pygame.draw.rect(surface, (247, 240, 226), self.drop_rect, border_radius=10)
        pygame.draw.rect(surface, GOLD, self.drop_rect, width=2, border_radius=10)

        for index, option in enumerate(visible_options):
            option_rect = pygame.Rect(
                rect.x + 4,
                rect.bottom + 6 + index * option_height,
                rect.width - 8,
                option_height - 2,
            )
            hovered = option_rect.collidepoint(mouse_pos)
            if hovered or option == self.value:
                pygame.draw.rect(surface, PARCHMENT_DARK, option_rect, border_radius=8)
            option_text = font.render(option, True, INK)
            surface.blit(
                option_text,
                (
                    option_rect.x + 10,
                    option_rect.y + (option_rect.height - option_text.get_height()) // 2,
                ),
            )
            self.option_rects.append((option, option_rect))

        if len(self.options) > visible_count:
            track_rect = pygame.Rect(
                self.drop_rect.right - 8,
                self.drop_rect.y + 6,
                4,
                self.drop_rect.height - 12,
            )
            pygame.draw.rect(surface, PARCHMENT_DARK, track_rect, border_radius=4)
            thumb_height = max(18, int(track_rect.height * (visible_count / len(self.options))))
            thumb_y = track_rect.y + int(
                (track_rect.height - thumb_height)
                * (self.scroll_index / max_scroll if max_scroll else 0)
            )
            pygame.draw.rect(
                surface,
                FOREST_SOFT,
                pygame.Rect(track_rect.x, thumb_y, track_rect.width, thumb_height),
                border_radius=4,
            )

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEWHEEL and self.open:
            mouse_pos = pygame.mouse.get_pos()
            if self.drop_rect.collidepoint(mouse_pos) or self.rect.collidepoint(mouse_pos):
                visible_count = min(len(self.options), self.max_visible)
                max_scroll = max(0, len(self.options) - visible_count)
                self.scroll_index = int(clamp(self.scroll_index - event.y, 0, max_scroll))
                return True
            return False

        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return False

        if self.rect.collidepoint(event.pos):
            self.open = not self.open
            if self.open and self.value in self.options:
                visible_count = min(len(self.options), self.max_visible)
                max_scroll = max(0, len(self.options) - visible_count)
                selected_index = self.options.index(self.value)
                self.scroll_index = int(clamp(selected_index - 2, 0, max_scroll))
            return True

        if self.open:
            for option, rect in self.option_rects:
                if rect.collidepoint(event.pos):
                    self.value = option
                    self.open = False
                    return True
            self.open = False
        return False


class TextInput:
    def __init__(
        self,
        text: str = "",
        placeholder: str = "",
        max_length: int = 3,
        numeric_only: bool = False,
    ):
        self.text = text
        self.placeholder = placeholder
        self.max_length = max_length
        self.numeric_only = numeric_only
        self.active = False
        self.rect = pygame.Rect(0, 0, 0, 0)

    def draw(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        font: pygame.font.Font,
        mouse_pos: tuple[int, int],
    ) -> None:
        self.rect = rect
        hovered = rect.collidepoint(mouse_pos)
        border = GOLD_HOVER if hovered or self.active else GOLD
        pygame.draw.rect(surface, (248, 243, 232), rect, border_radius=10)
        pygame.draw.rect(surface, border, rect, width=2, border_radius=10)

        display_text = self.text if self.text else self.placeholder
        display_color = INK if self.text else FOREST_SOFT
        text_surface = font.render(display_text, True, display_color)
        text_x = rect.x + 12
        text_y = rect.y + (rect.height - text_surface.get_height()) // 2
        surface.blit(text_surface, (text_x, text_y))

        if self.active:
            cursor_x = text_x + (font.size(self.text)[0] if self.text else 0) + 2
            cursor_top = rect.y + 8
            cursor_bottom = rect.bottom - 8
            pygame.draw.line(surface, INK, (cursor_x, cursor_top), (cursor_x, cursor_bottom), 2)

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.active = self.rect.collidepoint(event.pos)
            return self.active

        if event.type == pygame.KEYDOWN and self.active:
            if event.key in (pygame.K_RETURN, pygame.K_TAB, pygame.K_ESCAPE):
                self.active = False
                return True
            if event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
                return True

            if event.unicode and event.unicode.isprintable():
                if self.numeric_only and not event.unicode.isdigit():
                    return True
                if len(self.text) < self.max_length:
                    self.text += event.unicode
                return True

        return False


class CheckBox:
    def __init__(self, label: str, checked: bool = False):
        self.label = label
        self.checked = checked
        self.rect = pygame.Rect(0, 0, 0, 0)

    def draw(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        font: pygame.font.Font,
        mouse_pos: tuple[int, int],
    ) -> None:
        self.rect = rect
        box_size = min(rect.height - 6, 24)
        box_rect = pygame.Rect(rect.x, rect.y + (rect.height - box_size) // 2, box_size, box_size)
        hovered = rect.collidepoint(mouse_pos)

        pygame.draw.rect(surface, (249, 244, 234), box_rect, border_radius=5)
        pygame.draw.rect(surface, GOLD_HOVER if hovered else GOLD, box_rect, width=2, border_radius=5)

        if self.checked:
            pygame.draw.line(surface, FOREST, (box_rect.x + 5, box_rect.centery), (box_rect.x + 9, box_rect.bottom - 6), 3)
            pygame.draw.line(surface, FOREST, (box_rect.x + 9, box_rect.bottom - 6), (box_rect.right - 5, box_rect.y + 5), 3)

        label_surface = font.render(self.label, True, INK)
        surface.blit(label_surface, (box_rect.right + 10, rect.y + (rect.height - label_surface.get_height()) // 2))

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos):
            self.checked = not self.checked
            return True
        return False


class ToggleChip:
    def __init__(self, label: str, value: str):
        self.label = label
        self.value = value
        self.selected = False
        self.rect = pygame.Rect(0, 0, 0, 0)

    def draw(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        font: pygame.font.Font,
        mouse_pos: tuple[int, int],
    ) -> None:
        self.rect = rect
        hovered = rect.collidepoint(mouse_pos)
        fill = FOREST if self.selected else (246, 239, 225)
        border = GOLD_HOVER if hovered else GOLD
        text_color = WHITE if self.selected else INK

        pygame.draw.rect(surface, fill, rect, border_radius=12)
        pygame.draw.rect(surface, border, rect, width=2, border_radius=12)
        text = font.render(self.label, True, text_color)
        surface.blit(text, (rect.x + (rect.width - text.get_width()) // 2, rect.y + (rect.height - text.get_height()) // 2))

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos):
            self.selected = not self.selected
            return True
        return False


class ActionButton:
    def __init__(self, label: str, accent: bool = False):
        self.label = label
        self.accent = accent
        self.rect = pygame.Rect(0, 0, 0, 0)

    def draw(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        font: pygame.font.Font,
        mouse_pos: tuple[int, int],
    ) -> None:
        self.rect = rect
        hovered = rect.collidepoint(mouse_pos)
        fill = GOLD_HOVER if self.accent and hovered else GOLD if self.accent else (244, 236, 220)
        if not self.accent and hovered:
            fill = PARCHMENT_DARK
        text_color = INK if self.accent else INK_SOFT
        pygame.draw.rect(surface, fill, rect, border_radius=12)
        pygame.draw.rect(surface, INK if self.accent else GOLD, rect, width=2, border_radius=12)
        text = font.render(self.label, True, text_color)
        surface.blit(text, (rect.x + (rect.width - text.get_width()) // 2, rect.y + (rect.height - text.get_height()) // 2))

    def handle_event(self, event: pygame.event.Event) -> bool:
        return event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos)


class GeneratorApp:
    def __init__(self, smoke_test: bool = False):
        os.chdir(BASE_DIR)
        self.smoke_test = smoke_test

        pygame.init()
        pygame.display.set_caption(WINDOW_TITLE)
        self.screen = pygame.display.set_mode(DEFAULT_SIZE, pygame.RESIZABLE)
        self.clock = pygame.time.Clock()
        self.running = True

        self.bg_original = None
        if BACKGROUND_PATH.exists():
            try:
                self.bg_original = pygame.image.load(str(BACKGROUND_PATH)).convert()
            except pygame.error:
                self.bg_original = None
        self.bg_cache: pygame.Surface | None = None
        self.bg_cache_size: tuple[int, int] | None = None

        self.class_dropdown = Dropdown(
            ["Random", *[pretty_label(name) for name in Classes.entries]],
            "Random",
        )
        self.species_dropdown = Dropdown(
            ["Random", *[pretty_label(name.capitalize()) for name in Species.entries]],
            "Random",
        )
        self.level_input = TextInput(
            text="",
            placeholder="blank = random",
            max_length=2,
            numeric_only=True,
        )
        self.count_input = TextInput(
            text="1",
            placeholder="1",
            max_length=2,
            numeric_only=True,
        )
        self.font_dropdown = Dropdown(["Random", *list(character.AVAILABLE_FONTS.keys())], "Random")
        self.balance_box = CheckBox("Build a balanced party", False)
        self.spellbook_box = CheckBox("Generate spellbook pages", False)

        self.generate_button = ActionButton("Generate PDFs", accent=True)
        self.clear_button = ActionButton("Clear Filters")
        self.open_button = ActionButton("Open Output Folder")

        self.output_rect = pygame.Rect(0, 0, 0, 0)
        self.scroll_offset = 0
        self.status_message = "Select your options, then forge a new adventurer."
        self.output_text = (
            "Welcome to The Fellowship Forge.\n\n"
            "Choose a level, party size, optional class/species anchors, and whether "
            "you want party balancing or spellbooks. Generated PDFs are saved next to "
            "main.py in this project folder."
        )

    def get_font(self, size: int | float) -> pygame.font.Font:
        size = int(clamp(size, 12, 40))
        try:
            if FONT_PATH.exists():
                return pygame.font.Font(str(FONT_PATH), size)
        except Exception:
            pass
        return pygame.font.SysFont("serif", size)

    def close_dropdowns(self, except_for: Dropdown | None = None) -> None:
        for dropdown in (self.class_dropdown, self.species_dropdown, self.font_dropdown):
            if dropdown is not except_for:
                dropdown.open = False

    def active_classes(self) -> list[str]:
        selected = self.class_dropdown.value.strip().lower().replace(" ", "_")
        if selected == "random":
            return []
        for class_name in Classes.entries:
            if class_name.lower() == selected:
                return [class_name]
        return []

    def active_species(self) -> list[str]:
        selected = self.species_dropdown.value.strip().lower().replace(" ", "_")
        if selected == "random":
            return []
        for species_name in Species.entries:
            if species_name.lower() == selected:
                return [species_name.capitalize()]
        return []

    def clear_filters(self) -> None:
        self.class_dropdown.value = "Random"
        self.species_dropdown.value = "Random"
        self.level_input.text = ""
        self.count_input.text = "1"
        self.font_dropdown.value = "Random"
        self.balance_box.checked = False
        self.spellbook_box.checked = False
        self.status_message = "Filters cleared."

    def get_background(self, size: tuple[int, int]) -> pygame.Surface:
        if self.bg_original is None:
            background = pygame.Surface(size)
            background.fill(PARCHMENT)
            return background

        if self.bg_cache is None or self.bg_cache_size != size:
            self.bg_cache = pygame.transform.smoothscale(self.bg_original, size)
            self.bg_cache_size = size
        return self.bg_cache

    def draw_panel(self, rect: pygame.Rect, alpha: int = 210) -> None:
        panel = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        panel.fill((252, 247, 238, alpha))
        self.screen.blit(panel, rect.topleft)
        pygame.draw.rect(self.screen, GOLD, rect, width=2, border_radius=16)

    def describe_character(self, char_obj) -> str:
        lines = [
            f"Name: {char_obj.name}",
            f"Sex: {char_obj.sex}",
            f"Species: {char_obj.species}",
            f"Class: {char_obj.char_class.capitalize()}",
            f"Level: {char_obj.level}",
            f"HP: {char_obj.hp}",
            f"AC: {10 + character.modifier(char_obj.dexterity)}",
            f"Speed: {char_obj.get_speed()} ft",
            (
                "Abilities: "
                f"STR {char_obj.strength} ({character.modifier(char_obj.strength):+d}), "
                f"DEX {char_obj.dexterity} ({character.modifier(char_obj.dexterity):+d}), "
                f"CON {char_obj.constitution} ({character.modifier(char_obj.constitution):+d}), "
                f"INT {char_obj.intelligence} ({character.modifier(char_obj.intelligence):+d}), "
                f"WIS {char_obj.wisdom} ({character.modifier(char_obj.wisdom):+d}), "
                f"CHA {char_obj.charisma} ({character.modifier(char_obj.charisma):+d})"
            ),
            f"Skill Proficiencies: {', '.join(char_obj.skill_proficiencies) or 'None'}",
            f"Languages: {', '.join(char_obj.get_languages())}",
            f"Features: {', '.join(char_obj.get_features())}",
        ]
        return "\n".join(lines)

    def append_output(self, text: str) -> None:
        self.output_text = text.strip() if text.strip() else self.output_text
        self.scroll_offset = 0

    def generate(self) -> None:
        self.status_message = "Generating character sheets..."
        self.draw()
        pygame.display.flip()
        pygame.event.pump()

        selected_classes = self.active_classes()
        selected_species = self.active_species()
        level_text = self.level_input.text.strip()
        count_text = self.count_input.text.strip()

        requested_level = None if not level_text else int(level_text)
        requested_count = int(count_text or "1")
        requested_font = None if self.font_dropdown.value == "Random" else self.font_dropdown.value

        if requested_level is not None and not 1 <= requested_level <= 20:
            raise ValueError("Level must be between 1 and 20.")
        if requested_count < 1:
            raise ValueError("Number of characters must be at least 1.")

        output_chunks: list[str] = []
        try:
            if self.balance_box.checked:
                party_members = build_balanced_party(
                    party_size=requested_count,
                    level=requested_level,
                    preferred_classes=selected_classes or None,
                    preferred_species=selected_species or None,
                )
                output_chunks.append(format_party_summary(party_members))

                for index, party_member in enumerate(party_members, start=1):
                    char_obj = party_member["character"]
                    output_chunks.append(f"\n--- Character {index} of {requested_count} ---")
                    output_chunks.append(self.describe_character(char_obj))

                    spellbook = None
                    if self.spellbook_box.checked:
                        spellbook = build_spellbook_for_character(char_obj)
                        if spellbook is None:
                            output_chunks.append(
                                f"{char_obj.name} the {char_obj.char_class.capitalize()} does not have a class spellbook to generate."
                            )
                        else:
                            output_chunks.append(format_spellbook(spellbook))

                    char_obj.create_pdf_file(font_name=requested_font, spellbook=spellbook)
                    output_chunks.append(
                        f"Saved PDF: {char_obj.name.replace(' ', '_')}_Character_Sheet.pdf"
                    )
            else:
                for index in range(requested_count):
                    char_obj = character.create_random_character(
                        level=requested_level,
                        char_class=choose_requested_value(selected_classes, index),
                        species=choose_requested_value(selected_species, index),
                    )
                    output_chunks.append(f"\n--- Character {index + 1} of {requested_count} ---")
                    output_chunks.append(self.describe_character(char_obj))

                    spellbook = None
                    if self.spellbook_box.checked:
                        spellbook = build_spellbook_for_character(char_obj)
                        if spellbook is None:
                            output_chunks.append(
                                f"{char_obj.name} the {char_obj.char_class.capitalize()} does not have a class spellbook to generate."
                            )
                        else:
                            output_chunks.append(format_spellbook(spellbook))

                    char_obj.create_pdf_file(font_name=requested_font, spellbook=spellbook)
                    output_chunks.append(
                        f"Saved PDF: {char_obj.name.replace(' ', '_')}_Character_Sheet.pdf"
                    )

            self.append_output("\n".join(output_chunks))
            self.status_message = f"Done. Generated {requested_count} PDF file(s) in {BASE_DIR.name}."
        except Exception as exc:
            detail = traceback.format_exc()
            self.append_output(f"Generation failed:\n{detail}")
            self.status_message = f"Error: {exc}"

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self.running = False
            return

        if event.type == pygame.VIDEORESIZE:
            new_size = (
                max(MIN_SIZE[0], event.w),
                max(MIN_SIZE[1], event.h),
            )
            self.screen = pygame.display.set_mode(new_size, pygame.RESIZABLE)
            return

        for dropdown in (self.class_dropdown, self.species_dropdown, self.font_dropdown):
            if dropdown.handle_event(event):
                self.close_dropdowns(dropdown if dropdown.open else None)
                return

        if self.level_input.handle_event(event):
            if event.type == pygame.MOUSEBUTTONDOWN:
                self.close_dropdowns()
            return
        if self.count_input.handle_event(event):
            if event.type == pygame.MOUSEBUTTONDOWN:
                self.close_dropdowns()
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.close_dropdowns()

        if self.balance_box.handle_event(event):
            return
        if self.spellbook_box.handle_event(event):
            return

        if self.generate_button.handle_event(event):
            self.generate()
            return
        if self.clear_button.handle_event(event):
            self.clear_filters()
            return
        if self.open_button.handle_event(event):
            try:
                open_output_folder(BASE_DIR)
                self.status_message = "Opened the output folder."
            except Exception as exc:
                self.status_message = f"Could not open folder: {exc}"
            return

        if event.type == pygame.MOUSEWHEEL:
            if self.output_rect.collidepoint(pygame.mouse.get_pos()):
                self.scroll_offset = max(0, self.scroll_offset - event.y * 34)
        elif event.type == pygame.MOUSEBUTTONDOWN and self.output_rect.collidepoint(event.pos):
            if event.button == 4:
                self.scroll_offset = max(0, self.scroll_offset - 34)
            elif event.button == 5:
                self.scroll_offset += 34

    def draw_chip_group(
        self,
        chips: list[ToggleChip],
        rect: pygame.Rect,
        font: pygame.font.Font,
        mouse_pos: tuple[int, int],
    ) -> int:
        x = rect.x
        y = rect.y
        gap = 8
        chip_height = max(28, font.get_height() + 10)

        for chip in chips:
            chip_width = font.size(chip.label)[0] + 22
            if x + chip_width > rect.right:
                x = rect.x
                y += chip_height + gap
            chip_rect = pygame.Rect(x, y, chip_width, chip_height)
            chip.draw(self.screen, chip_rect, font, mouse_pos)
            x += chip_width + gap

        return y + chip_height

    def draw_output_panel(
        self,
        rect: pygame.Rect,
        title_font: pygame.font.Font,
        body_font: pygame.font.Font,
    ) -> None:
        self.output_rect = rect
        self.draw_panel(rect)

        draw_text(self.screen, "Chronicle", title_font, INK, (rect.x + 16, rect.y + 12), shadow=False)
        content_rect = pygame.Rect(rect.x + 16, rect.y + 48, rect.width - 32, rect.height - 62)

        lines = wrap_text(self.output_text, body_font, content_rect.width - 14)
        line_height = body_font.get_linesize()
        total_height = max(line_height, len(lines) * line_height)
        max_scroll = max(0, total_height - content_rect.height)
        self.scroll_offset = int(clamp(self.scroll_offset, 0, max_scroll))

        previous_clip = self.screen.get_clip()
        self.screen.set_clip(content_rect)
        y = content_rect.y - self.scroll_offset
        for line in lines:
            rendered = body_font.render(line, True, INK_SOFT)
            self.screen.blit(rendered, (content_rect.x, y))
            y += line_height
        self.screen.set_clip(previous_clip)

        if max_scroll > 0:
            track_rect = pygame.Rect(content_rect.right - 6, content_rect.y, 6, content_rect.height)
            pygame.draw.rect(self.screen, PARCHMENT_DARK, track_rect, border_radius=6)
            thumb_height = max(28, int(content_rect.height * (content_rect.height / total_height)))
            scroll_ratio = 0 if max_scroll == 0 else self.scroll_offset / max_scroll
            thumb_y = content_rect.y + int((content_rect.height - thumb_height) * scroll_ratio)
            thumb_rect = pygame.Rect(track_rect.x, thumb_y, track_rect.width, thumb_height)
            pygame.draw.rect(self.screen, GOLD, thumb_rect, border_radius=6)

    def draw(self) -> None:
        width, height = self.screen.get_size()
        mouse_pos = pygame.mouse.get_pos()
        self.screen.blit(self.get_background((width, height)), (0, 0))

        overlay = pygame.Surface((width, height), pygame.SRCALPHA)
        overlay.fill((255, 250, 240, 36))
        self.screen.blit(overlay, (0, 0))

        margin = max(18, width // 60)
        top_banner_height = max(88, int(height * 0.13))
        left_width = int(width * 0.44)
        gutter = 16

        title_font = self.get_font(clamp(min(width // 26, height // 11), 24, 40))
        subtitle_font = self.get_font(clamp(min(width // 60, height // 24), 14, 20))
        section_font = self.get_font(clamp(min(width // 55, height // 24), 15, 22))
        body_font = self.get_font(clamp(min(width // 68, height // 30), 13, 18))
        small_font = self.get_font(clamp(min(width // 82, height // 34), 12, 16))

        banner_rect = pygame.Rect(margin, margin, width - margin * 2, top_banner_height)
        self.draw_panel(banner_rect, alpha=185)
        draw_text(self.screen, WINDOW_TITLE, title_font, INK, (banner_rect.x + 18, banner_rect.y + 14), shadow=True)
        draw_text(
            self.screen,
            "A fantasy-themed D&D 5e character sheet forge",
            subtitle_font,
            FOREST,
            (banner_rect.x + 20, banner_rect.y + 52),
            shadow=False,
        )
        draw_text(
            self.screen,
            self.status_message,
            small_font,
            CRIMSON if self.status_message.startswith("Error") else INK_SOFT,
            (banner_rect.x + 20, banner_rect.bottom - 28),
            shadow=False,
        )

        content_y = banner_rect.bottom + 14
        content_height = height - content_y - margin
        left_rect = pygame.Rect(margin, content_y, left_width - gutter // 2, content_height)
        right_rect = pygame.Rect(left_rect.right + gutter, content_y, width - left_rect.width - margin * 2 - gutter, content_height)

        self.draw_panel(left_rect)

        x = left_rect.x + 16
        y = left_rect.y + 14
        control_width = left_rect.width - 32
        control_height = max(38, int(height * 0.055))
        field_gap = 12
        half_width = (control_width - field_gap) // 2

        draw_text(self.screen, "Forge Settings", section_font, INK, (x, y), shadow=False)
        y += 30

        label = small_font.render("Class", True, INK_SOFT)
        self.screen.blit(label, (x, y))
        label = small_font.render("Species", True, INK_SOFT)
        self.screen.blit(label, (x + half_width + field_gap, y))
        y += 20
        self.class_dropdown.draw(
            self.screen,
            pygame.Rect(x, y, half_width, control_height),
            body_font,
            mouse_pos,
        )
        self.species_dropdown.draw(
            self.screen,
            pygame.Rect(x + half_width + field_gap, y, half_width, control_height),
            body_font,
            mouse_pos,
        )
        y += control_height + 18

        label = small_font.render("Level (blank = random)", True, INK_SOFT)
        self.screen.blit(label, (x, y))
        label = small_font.render("Number of characters", True, INK_SOFT)
        self.screen.blit(label, (x + half_width + field_gap, y))
        y += 20
        self.level_input.draw(
            self.screen,
            pygame.Rect(x, y, half_width, control_height),
            body_font,
            mouse_pos,
        )
        self.count_input.draw(
            self.screen,
            pygame.Rect(x + half_width + field_gap, y, half_width, control_height),
            body_font,
            mouse_pos,
        )
        y += control_height + 18

        label = small_font.render("PDF Font", True, INK_SOFT)
        self.screen.blit(label, (x, y))
        y += 20
        self.font_dropdown.draw(
            self.screen,
            pygame.Rect(x, y, control_width, control_height),
            body_font,
            mouse_pos,
        )
        y += control_height + 14

        self.balance_box.draw(self.screen, pygame.Rect(x, y, control_width, 28), body_font, mouse_pos)
        y += 30
        self.spellbook_box.draw(self.screen, pygame.Rect(x, y, control_width, 28), body_font, mouse_pos)
        y += 38

        note_rect = pygame.Rect(x, y, control_width, max(110, int(left_rect.height * 0.18)))
        self.draw_panel(note_rect, alpha=120)
        draw_text(self.screen, "How this works", section_font, INK, (note_rect.x + 12, note_rect.y + 10), shadow=False)
        note_lines = wrap_text(
            "Use the class and species dropdowns for specific choices, type a level or party size, and leave fields on Random or blank when you want surprise adventurers.",
            small_font,
            note_rect.width - 24,
        )
        note_y = note_rect.y + 40
        for line in note_lines[:5]:
            draw_text(self.screen, line, small_font, INK_SOFT, (note_rect.x + 12, note_y), shadow=False)
            note_y += small_font.get_linesize()
        y = note_rect.bottom + 14

        button_gap = 10
        button_height = max(42, int(height * 0.058))
        self.generate_button.draw(
            self.screen,
            pygame.Rect(x, y, control_width, button_height),
            body_font,
            mouse_pos,
        )
        y += button_height + button_gap
        secondary_width = (control_width - button_gap) // 2
        self.clear_button.draw(
            self.screen,
            pygame.Rect(x, y, secondary_width, button_height),
            body_font,
            mouse_pos,
        )
        self.open_button.draw(
            self.screen,
            pygame.Rect(x + secondary_width + button_gap, y, secondary_width, button_height),
            body_font,
            mouse_pos,
        )

        self.draw_output_panel(right_rect, section_font, body_font)
        for dropdown in (self.class_dropdown, self.species_dropdown, self.font_dropdown):
            dropdown.draw_menu(self.screen, body_font, mouse_pos)

    def run(self) -> None:
        if self.smoke_test:
            self.draw()
            pygame.display.flip()
            pygame.time.wait(120)
            pygame.quit()
            return

        while self.running:
            for event in pygame.event.get():
                self.handle_event(event)

            self.draw()
            pygame.display.flip()
            self.clock.tick(FPS)

        pygame.quit()


def main() -> None:
    smoke_test = "--smoke-test" in sys.argv
    app = GeneratorApp(smoke_test=smoke_test)
    app.run()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        details = traceback.format_exc()
        show_popup("Launcher error", details[-3000:])
        raise
