import random
import unittest
from unittest import mock

from tinys_srd import Levels

from scripts.character import Character, SPELLCASTING_ABILITY, SPELLCASTING_GUIDANCE, SPELLCASTING_NOTES, build_spell_slot_fields
from scripts.spellbook import _allocate_spells_by_level


class SpellAllocationTests(unittest.TestCase):
    def setUp(self):
        self.config = {
            "limited_caster_classes": ["paladin", "ranger", "warlock"],
            "default_base_spells_per_level": 2,
            "limited_caster_base_spells_per_level": 1,
        }

    def make_spell_pool(self):
        return {level: [f"spell_{level}_{index}" for index in range(20)] for level in range(10)}

    def test_warlock_keeps_lower_level_spells_visible(self):
        random.seed(0)
        allocation = _allocate_spells_by_level(
            known_spell_count=6,
            spell_slots={3: 2},
            spell_pool=self.make_spell_pool(),
            char_class="warlock",
            config=self.config,
        )

        self.assertGreaterEqual(allocation.get(1, 0), 1)
        self.assertGreaterEqual(allocation.get(2, 0), 1)
        self.assertGreaterEqual(allocation.get(3, 0), 1)

    def test_slot_totals_are_fully_populated_when_possible(self):
        random.seed(0)
        allocation = _allocate_spells_by_level(
            known_spell_count=9,
            spell_slots={1: 4, 2: 3, 3: 2},
            spell_pool=self.make_spell_pool(),
            char_class="cleric",
            config=self.config,
        )

        self.assertEqual(allocation[1], 4)
        self.assertEqual(allocation[2], 3)
        self.assertEqual(allocation[3], 2)


class SpellSheetSlotFieldTests(unittest.TestCase):
    def assert_slot_totals(self, fields, expected_totals):
        slot_field_order = {
            1: 'SlotsTotal 19',
            2: 'SlotsTotal 20',
            3: 'SlotsTotal 21',
            4: 'SlotsTotal 22',
            5: 'SlotsTotal 23',
            6: 'SlotsTotal 24',
            7: 'SlotsTotal 25',
            8: 'SlotsTotal 26',
            9: 'SlotsTotal 27',
        }
        for level, total_field in slot_field_order.items():
            expected = expected_totals.get(level, '')
            self.assertEqual(fields[total_field], expected)
            remaining_field = total_field.replace('SlotsTotal', 'SlotsRemaining')
            self.assertEqual(fields[remaining_field], '')

    def build_spellbook_levels(self, included_levels):
        return {
            'spells_by_level': {
                level: [{'name': f'test_{level}', 'level': level, 'school': 'Test'}]
                for level in included_levels
            }
        }

    def test_wizard_spell_sheet_slots_levels_10_15_20(self):
        expected_by_level = {
            10: {1: '4', 2: '3', 3: '3', 4: '3', 5: '2'},
            15: {1: '4', 2: '3', 3: '3', 4: '3', 5: '2', 6: '1', 7: '1', 8: '1'},
            20: {1: '4', 2: '3', 3: '3', 4: '3', 5: '3', 6: '2', 7: '2', 8: '1', 9: '1'},
        }

        for level, expected_totals in expected_by_level.items():
            with self.subTest(level=level):
                spellcasting = getattr(Levels, f'wizard_{level}').spellcasting
                fields = build_spell_slot_fields(
                    spellcasting,
                    spellbook=self.build_spellbook_levels(expected_totals.keys()),
                )
                self.assert_slot_totals(fields, expected_totals)

    def test_warlock_spell_sheet_slots_levels_10_15_20(self):
        expected_by_level = {
            10: {5: '2'},
            15: {5: '3'},
            20: {5: '4'},
        }

        for level, expected_totals in expected_by_level.items():
            with self.subTest(level=level):
                spellcasting = getattr(Levels, f'warlock_{level}').spellcasting
                fields = build_spell_slot_fields(
                    spellcasting,
                    spellbook=self.build_spellbook_levels(expected_totals.keys()),
                )
                self.assert_slot_totals(fields, expected_totals)

    def test_slot_total_uses_available_slots_even_without_spells_at_level(self):
        spellcasting = getattr(Levels, 'wizard_10').spellcasting
        # Only include spells for level 1 and 3; slot totals should still reflect
        # available slots for all castable levels.
        spellbook = self.build_spellbook_levels([1, 3])
        fields = build_spell_slot_fields(spellcasting, spellbook=spellbook)

        self.assertEqual(fields['SlotsTotal 19'], '4')
        self.assertEqual(fields['SlotsTotal 20'], '3')
        self.assertEqual(fields['SlotsTotal 21'], '3')
        self.assertEqual(fields['SlotsTotal 22'], '3')
        self.assertEqual(fields['SlotsTotal 23'], '2')


class SpellSheetPdfFieldPopulationTests(unittest.TestCase):
    SLOT_FIELD_ORDER = {
        1: 'SlotsTotal 19',
        2: 'SlotsTotal 20',
        3: 'SlotsTotal 21',
        4: 'SlotsTotal 22',
        5: 'SlotsTotal 23',
        6: 'SlotsTotal 24',
        7: 'SlotsTotal 25',
        8: 'SlotsTotal 26',
        9: 'SlotsTotal 27',
    }

    def _capture_pdf_fields(self, char_class, level):
        character = Character(
            name='Slot Field Test',
            species='Human',
            char_class=char_class,
            sex='Male',
            level=level,
        )

        captured_fields = {}

        def fake_write_fillable_pdf(_infile, _outfile, fields):
            captured_fields.update(fields)

        with mock.patch('scripts.character.urllib.request.urlretrieve', return_value=None), \
                mock.patch('scripts.character.fillpdfs.write_fillable_pdf', side_effect=fake_write_fillable_pdf), \
                mock.patch('scripts.character.apply_custom_font', return_value=None):
            character.create_pdf_file(font_name='cinzel', spellbook=None)

        return captured_fields

    def _expected_slot_totals_for(self, char_class, level):
        spellcasting = getattr(Levels, f'{char_class}_{level}').spellcasting
        expected = {}
        for spell_level, field_name in self.SLOT_FIELD_ORDER.items():
            slots = int(spellcasting.get(f'spell_slots_level_{spell_level}', 0) or 0)
            expected[field_name] = str(slots) if slots > 0 else ''
        return expected

    def test_level_20_warlock_pdf_fields_use_tinys_srd_slots(self):
        fields = self._capture_pdf_fields('warlock', 20)

        self.assertEqual(fields['SlotsTotal 19'], '')
        self.assertEqual(fields['SlotsTotal 20'], '')
        self.assertEqual(fields['SlotsTotal 21'], '')
        self.assertEqual(fields['SlotsTotal 22'], '')
        self.assertEqual(fields['SlotsTotal 23'], '4')

        for field_name in self.SLOT_FIELD_ORDER.values():
            remaining_field = field_name.replace('SlotsTotal', 'SlotsRemaining')
            self.assertEqual(fields[remaining_field], '')

    def test_spellcaster_slot_fields_levels_15_to_20(self):
        for char_class in sorted(SPELLCASTING_ABILITY):
            for level in range(15, 21):
                with self.subTest(char_class=char_class, level=level):
                    fields = self._capture_pdf_fields(char_class, level)
                    expected_slot_totals = self._expected_slot_totals_for(char_class, level)

                    for field_name, expected_value in expected_slot_totals.items():
                        self.assertEqual(fields[field_name], expected_value)

                        remaining_field = field_name.replace('SlotsTotal', 'SlotsRemaining')
                        self.assertEqual(fields[remaining_field], '')

    def test_warlock_additional_traits_include_pact_magic_note(self):
        fields = self._capture_pdf_fields('warlock', 20)
        note_text = fields.get('Feat+Traits', '')

        self.assertIn('Pact Magic: slots refresh on short rest.', note_text)
        self.assertIn('At high levels, warlock uses 5th-level pact slots.', note_text)
        self.assertIn('Mystic Arcanum handles 6th-9th level spells (1/long rest each).', note_text)

    def test_spellcaster_additional_traits_include_class_notes(self):
        for char_class, expected_lines in SPELLCASTING_NOTES.items():
            with self.subTest(char_class=char_class):
                fields = self._capture_pdf_fields(char_class, 20)
                note_text = fields.get('Feat+Traits', '')
                for expected_line in expected_lines:
                    self.assertIn(expected_line, note_text)

    def test_spellcaster_usage_basics_and_prepared_instructions(self):
        for char_class in sorted(SPELLCASTING_ABILITY):
            with self.subTest(char_class=char_class):
                fields = self._capture_pdf_fields(char_class, 20)
                note_text = fields.get('Feat+Traits', '')

                self.assertIn('Spell Use Basics:', note_text)
                self.assertIn('Spellcasting ability:', note_text)
                self.assertIn('Spell Save DC:', note_text)
                self.assertIn('Spell Attack Bonus:', note_text)

        wizard_notes = self._capture_pdf_fields('wizard', 20).get('Feat+Traits', '')
        self.assertIn('Prepared wizard spells each day:', wizard_notes)

        cleric_notes = self._capture_pdf_fields('cleric', 20).get('Feat+Traits', '')
        self.assertIn('Prepared spells each day:', cleric_notes)

        warlock_notes = self._capture_pdf_fields('warlock', 20).get('Feat+Traits', '')
        self.assertIn('Pact slots refresh on a short or long rest.', warlock_notes)

    def test_spellcasting_guidance_config_sections_loaded(self):
        self.assertIn('global_rules', SPELLCASTING_GUIDANCE)
        self.assertIn('class_rules', SPELLCASTING_GUIDANCE)
        self.assertIn('class_notes', SPELLCASTING_GUIDANCE)
        self.assertIn('feat_note_rules', SPELLCASTING_GUIDANCE)
        self.assertIn('feat_notes', SPELLCASTING_GUIDANCE)
        self.assertIn('species_notes', SPELLCASTING_GUIDANCE)
        self.assertIn('templates', SPELLCASTING_GUIDANCE)
        self.assertIn('warlock', SPELLCASTING_GUIDANCE['class_rules'])
        self.assertIn('warlock', SPELLCASTING_GUIDANCE['class_notes'])
        self.assertIn('match_mode', SPELLCASTING_GUIDANCE['feat_note_rules'])
        self.assertIn('aliases', SPELLCASTING_GUIDANCE['feat_note_rules'])
        self.assertIn('spellcasting_ability_line', SPELLCASTING_GUIDANCE['templates'])

    def test_feat_notes_support_alias_matching_from_config_rules(self):
        custom_guidance = {
            'global_rules': {'include_spell_use_basics': False},
            'class_rules': {'wizard': {'resource_refresh': 'long_rest'}},
            'class_notes': {},
            'feat_note_rules': {
                'match_mode': 'exact_normalized',
                'use_contains_fallback': False,
                'aliases': {'War Caster': ['War-Caster']},
            },
            'feat_notes': {'War Caster': ['Alias feat note works.']},
            'species_notes': {},
            'templates': {},
        }

        with mock.patch('scripts.character.SPELLCASTING_GUIDANCE', custom_guidance), \
                mock.patch.object(Character, 'selected_feat_names', return_value=['War-Caster']):
            fields = self._capture_pdf_fields('wizard', 20)

        self.assertIn('Alias feat note works.', fields.get('Feat+Traits', ''))


class SpellSlotPhbParityTests(unittest.TestCase):
    def test_tinys_srd_matches_phb_slots_levels_15_to_20(self):
        phb_expected = {
            'bard': {
                15: [4, 3, 3, 3, 2, 1, 1, 1, 0],
                16: [4, 3, 3, 3, 2, 1, 1, 1, 0],
                17: [4, 3, 3, 3, 2, 1, 1, 1, 1],
                18: [4, 3, 3, 3, 3, 1, 1, 1, 1],
                19: [4, 3, 3, 3, 3, 2, 1, 1, 1],
                20: [4, 3, 3, 3, 3, 2, 2, 1, 1],
            },
            'cleric': {
                15: [4, 3, 3, 3, 2, 1, 1, 1, 0],
                16: [4, 3, 3, 3, 2, 1, 1, 1, 0],
                17: [4, 3, 3, 3, 2, 1, 1, 1, 1],
                18: [4, 3, 3, 3, 3, 1, 1, 1, 1],
                19: [4, 3, 3, 3, 3, 2, 1, 1, 1],
                20: [4, 3, 3, 3, 3, 2, 2, 1, 1],
            },
            'druid': {
                15: [4, 3, 3, 3, 2, 1, 1, 1, 0],
                16: [4, 3, 3, 3, 2, 1, 1, 1, 0],
                17: [4, 3, 3, 3, 2, 1, 1, 1, 1],
                18: [4, 3, 3, 3, 3, 1, 1, 1, 1],
                19: [4, 3, 3, 3, 3, 2, 1, 1, 1],
                20: [4, 3, 3, 3, 3, 2, 2, 1, 1],
            },
            'sorcerer': {
                15: [4, 3, 3, 3, 2, 1, 1, 1, 0],
                16: [4, 3, 3, 3, 2, 1, 1, 1, 0],
                17: [4, 3, 3, 3, 2, 1, 1, 1, 1],
                18: [4, 3, 3, 3, 3, 1, 1, 1, 1],
                19: [4, 3, 3, 3, 3, 2, 1, 1, 1],
                20: [4, 3, 3, 3, 3, 2, 2, 1, 1],
            },
            'wizard': {
                15: [4, 3, 3, 3, 2, 1, 1, 1, 0],
                16: [4, 3, 3, 3, 2, 1, 1, 1, 0],
                17: [4, 3, 3, 3, 2, 1, 1, 1, 1],
                18: [4, 3, 3, 3, 3, 1, 1, 1, 1],
                19: [4, 3, 3, 3, 3, 2, 1, 1, 1],
                20: [4, 3, 3, 3, 3, 2, 2, 1, 1],
            },
            'paladin': {
                15: [4, 3, 3, 2, 0, 0, 0, 0, 0],
                16: [4, 3, 3, 2, 0, 0, 0, 0, 0],
                17: [4, 3, 3, 3, 1, 0, 0, 0, 0],
                18: [4, 3, 3, 3, 1, 0, 0, 0, 0],
                19: [4, 3, 3, 3, 2, 0, 0, 0, 0],
                20: [4, 3, 3, 3, 2, 0, 0, 0, 0],
            },
            'ranger': {
                15: [4, 3, 3, 2, 0, 0, 0, 0, 0],
                16: [4, 3, 3, 2, 0, 0, 0, 0, 0],
                17: [4, 3, 3, 3, 1, 0, 0, 0, 0],
                18: [4, 3, 3, 3, 1, 0, 0, 0, 0],
                19: [4, 3, 3, 3, 2, 0, 0, 0, 0],
                20: [4, 3, 3, 3, 2, 0, 0, 0, 0],
            },
            'warlock': {
                15: [0, 0, 0, 0, 3, 0, 0, 0, 0],
                16: [0, 0, 0, 0, 3, 0, 0, 0, 0],
                17: [0, 0, 0, 0, 4, 0, 0, 0, 0],
                18: [0, 0, 0, 0, 4, 0, 0, 0, 0],
                19: [0, 0, 0, 0, 4, 0, 0, 0, 0],
                20: [0, 0, 0, 0, 4, 0, 0, 0, 0],
            },
        }

        for char_class, level_rows in phb_expected.items():
            for level, expected_slots in level_rows.items():
                with self.subTest(char_class=char_class, level=level):
                    spellcasting = getattr(Levels, f'{char_class}_{level}').spellcasting
                    actual_slots = [
                        int(spellcasting.get(f'spell_slots_level_{spell_level}', 0) or 0)
                        for spell_level in range(1, 10)
                    ]
                    self.assertEqual(actual_slots, expected_slots)


if __name__ == "__main__":
    unittest.main()
