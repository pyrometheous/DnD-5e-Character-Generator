import copy
import random
import unittest

from scripts import character
from scripts.feats import resolve_feat_selection


class FeatSelectionPipelineTests(unittest.TestCase):
    def setUp(self):
        self.original_feat_config = copy.deepcopy(character.FEAT_CONFIG)

    def tearDown(self):
        character.FEAT_CONFIG = self.original_feat_config

    def test_forced_feat_selection_replaces_asi(self):
        random.seed(1)
        character.FEAT_CONFIG = {
            'selection': {
                'asi_base_weight': 0.01,
                'max_feats_per_character': 4,
                'class_affinity_multiplier': 1.0,
                'species_affinity_multiplier': 1.0,
                'magic_feat_multiplier': 1.0,
                'martial_feat_multiplier': 1.0,
                'stealth_feat_multiplier': 1.0,
                'under_ten_alignment_multiplier': 1.0,
                'ability_alignment_multiplier': 1.0,
                'redundant_grant_multiplier': 1.0,
                'level_multipliers': {'4': 1.0},
            },
            'feats': [
                {
                    'name': 'Resilient',
                    'weight': 100.0,
                    'ability_bonus_options': ['dexterity'],
                    'grants': {'saving_throw_choice': True},
                }
            ],
        }

        char_obj = character.Character('Feat Test', 'Human', 'wizard', 'Male', 4)
        char_obj.strength = 12
        char_obj.dexterity = 8
        char_obj.constitution = 12
        char_obj.intelligence = 15
        char_obj.wisdom = 11
        char_obj.charisma = 10

        char_obj.apply_asi()

        self.assertEqual(len(char_obj.feats), 1)
        self.assertEqual(char_obj.feats[0]['name'], 'Resilient')
        self.assertEqual(char_obj.advancement_log[0]['type'], 'feat')
        self.assertEqual(char_obj.dexterity, 9)
        self.assertIn('DEX', char_obj.saving_throw_proficiencies)

    def test_feat_name_replaces_asi_in_feature_annotation(self):
        random.seed(2)
        character.FEAT_CONFIG = {
            'selection': {
                'asi_base_weight': 0.01,
                'max_feats_per_character': 4,
                'class_affinity_multiplier': 1.0,
                'species_affinity_multiplier': 1.0,
                'magic_feat_multiplier': 1.0,
                'martial_feat_multiplier': 1.0,
                'stealth_feat_multiplier': 1.0,
                'under_ten_alignment_multiplier': 1.0,
                'ability_alignment_multiplier': 1.0,
                'redundant_grant_multiplier': 1.0,
                'level_multipliers': {'4': 1.0},
            },
            'feats': [
                {
                    'name': 'Actor',
                    'weight': 100.0,
                    'ability_bonus_options': ['charisma'],
                }
            ],
        }

        char_obj = character.Character('Actor Test', 'Human', 'bard', 'Female', 4)
        char_obj.strength = 10
        char_obj.dexterity = 12
        char_obj.constitution = 12
        char_obj.intelligence = 10
        char_obj.wisdom = 10
        char_obj.charisma = 15

        char_obj.apply_asi()

        annotated = char_obj.get_features_annotated()
        self.assertIn('Actor (+1 CHA)', annotated)
        self.assertNotIn('Ability Score Improvement', annotated)

    def test_linguist_adds_languages_from_resolved_feat(self):
        random.seed(3)
        char_obj = character.Character('Linguist Test', 'Human', 'wizard', 'Male', 4)
        char_obj.intelligence = 15

        resolved = resolve_feat_selection(
            char_obj,
            {
                'name': 'Linguist',
                'ability_bonus_options': ['intelligence'],
                'grants': {'language_choices': 3},
            },
            asi_level=4,
        )
        char_obj._apply_selected_feat(resolved)

        self.assertEqual(char_obj.intelligence, 16)
        self.assertGreaterEqual(len(char_obj.extra_languages), 3)
        self.assertIn('Linguist', char_obj.selected_feat_names())


if __name__ == '__main__':
    unittest.main()