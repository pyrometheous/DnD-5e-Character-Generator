import unittest
from unittest import mock

from scripts.character import Character


class AbilityScoreWeightingTests(unittest.TestCase):
    def _seed_stats(self, character, values):
        for ability, value in values.items():
            setattr(character, ability, value)

    def test_rogue_aggressive_dex_floor_when_under_ten(self):
        rogue = Character(
            name='Test Rogue',
            species='Human',
            char_class='rogue',
            sex='Male',
            level=10,
        )
        self._seed_stats(
            rogue,
            {
                'strength': 12,
                'dexterity': 9,
                'constitution': 12,
                'intelligence': 12,
                'wisdom': 12,
                'charisma': 12,
            },
        )

        with mock.patch('scripts.character.choose_feat_for_character', return_value=None):
            rogue.apply_asi()

        self.assertGreaterEqual(rogue.dexterity, 14)
        self.assertTrue(all(entry.get('type') == 'asi' for entry in rogue.advancement_log))

    def test_rogue_dex_preferred_over_non_key_scores(self):
        rogue = Character(
            name='Dex Priority Rogue',
            species='Human',
            char_class='rogue',
            sex='Female',
            level=8,
        )
        self._seed_stats(
            rogue,
            {
                'strength': 15,
                'dexterity': 11,
                'constitution': 14,
                'intelligence': 14,
                'wisdom': 14,
                'charisma': 14,
            },
        )

        with mock.patch('scripts.character.choose_feat_for_character', return_value=None):
            rogue.apply_asi()

        self.assertGreaterEqual(rogue.dexterity, 15)
        self.assertEqual(rogue.strength, 15)

    def test_species_weights_are_applied_from_config(self):
        test_config = {
            'global': {
                'class_primary_weight': 0,
                'class_secondary_weight': 0,
                'spellcasting_weight': 0,
                'species_weight_scale': 100,
                'under_cap_weight': 0,
                'odd_score_weight': 0,
                'sub_ten_weight': 0,
                'important_below_floor_weight': 0,
                'important_floor_target': 14,
                'important_floor_trigger': 10,
                'force_asi_when_important_below_floor': False,
            },
            'class_priorities': {},
            'species_modifiers': {
                'tiefling': {
                    'charisma': 2,
                }
            },
        }

        fighter = Character(
            name='Species Weighted Fighter',
            species='Tiefling',
            char_class='fighter',
            sex='Male',
            level=4,
        )
        self._seed_stats(
            fighter,
            {
                'strength': 12,
                'dexterity': 12,
                'constitution': 12,
                'intelligence': 12,
                'wisdom': 12,
                'charisma': 12,
            },
        )

        with mock.patch('scripts.character.ASI_WEIGHT_CONFIG', test_config), \
                mock.patch('scripts.character.choose_feat_for_character', return_value=None):
            fighter.apply_asi()

        self.assertEqual(fighter.charisma, 14)


if __name__ == '__main__':
    unittest.main()
