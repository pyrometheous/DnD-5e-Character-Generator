import copy
import unittest

from scripts.character import Character
from scripts.progression import _get_spell_slots, ensure_progression, export_spellbook, load_progression_config, load_spellbook_config


class ProgressionFeatureSelectionTests(unittest.TestCase):
    def setUp(self):
        self.progression_config = copy.deepcopy(load_progression_config())
        self.spellbook_config = load_spellbook_config()

    def test_fighter_weighted_styles_are_deterministic(self):
        self.progression_config['feature_selection']['fighter-fighting-style']['weights'] = {
            'fighter-fighting-style-defense': 100.0,
            'fighter-fighting-style-archery': 0.0,
            'fighter-fighting-style-dueling': 0.0,
            'fighter-fighting-style-great-weapon-fighting': 0.0,
            'fighter-fighting-style-protection': 0.0,
            'fighter-fighting-style-two-weapon-fighting': 0.0,
        }
        self.progression_config['feature_selection']['additional-fighting-style']['weights'] = {
            'fighter-fighting-style-archery': 100.0,
            'fighter-fighting-style-defense': 0.0,
            'fighter-fighting-style-dueling': 0.0,
            'fighter-fighting-style-great-weapon-fighting': 0.0,
            'fighter-fighting-style-protection': 0.0,
            'fighter-fighting-style-two-weapon-fighting': 0.0,
        }

        fighter = Character('Weighted Fighter', 'Human', 'fighter', 'Male', 10, seed=7)
        fighter.strength = 16
        fighter.dexterity = 14
        fighter.constitution = 14
        fighter.intelligence = 10
        fighter.wisdom = 10
        fighter.charisma = 10

        ensure_progression(fighter, config=self.progression_config, spellbook_config=self.spellbook_config)

        annotated = fighter.get_features_annotated()
        self.assertIn('Fighting Style (Defense)', annotated)
        self.assertIn('Archery', annotated)
        self.assertEqual(fighter.armor_class_bonus, 1)
        self.assertEqual(fighter.ranged_attack_bonus, 2)
        self.assertEqual(fighter.subclass, 'Champion')

    def test_warlock_progression_tracks_pact_and_invocations(self):
        self.progression_config['feature_selection']['pact-boon']['weights'] = {
            'pact-of-the-blade': 100.0,
            'pact-of-the-chain': 0.0,
            'pact-of-the-tome': 0.0,
        }
        self.progression_config['feature_selection']['eldritch-invocations']['weights'].update({
            'eldritch-invocation-agonizing-blast': 100.0,
            'eldritch-invocation-thirsting-blade': 90.0,
            'eldritch-invocation-repelling-blast': 80.0,
        })

        warlock = Character('Weighted Warlock', 'Tiefling', 'warlock', 'Female', 5, seed=11)
        warlock.strength = 10
        warlock.dexterity = 14
        warlock.constitution = 14
        warlock.intelligence = 10
        warlock.wisdom = 12
        warlock.charisma = 17

        ensure_progression(warlock, config=self.progression_config, spellbook_config=self.spellbook_config)

        invocation_choices = [
            entry['choice_name']
            for entry in warlock.class_feature_choices
            if entry['feature_index'] == 'eldritch-invocations'
        ]
        self.assertEqual(len(invocation_choices), 3)
        self.assertTrue(any('Pact of the Blade' in feature for feature in warlock.get_features_annotated()))

    def test_paladin_subclass_spells_are_always_prepared(self):
        paladin = Character('Devoted Knight', 'Human', 'paladin', 'Male', 5, seed=3)
        paladin.strength = 16
        paladin.dexterity = 10
        paladin.constitution = 14
        paladin.intelligence = 8
        paladin.wisdom = 10
        paladin.charisma = 16

        ensure_progression(paladin, config=self.progression_config, spellbook_config=self.spellbook_config)
        spellbook = export_spellbook(paladin)

        self.assertIsNotNone(spellbook)
        always_prepared = {spell['name'] for spell in spellbook['always_prepared']}
        self.assertIn('Sanctuary', always_prepared)
        self.assertIn('Lesser Restoration', always_prepared)
        self.assertIn('Oath of Devotion', paladin._progression_notes()[0])

    def test_draconic_resilience_updates_mechanics(self):
        sorcerer = Character('Dragonblood', 'Human', 'sorcerer', 'Female', 6, seed=5)
        sorcerer.strength = 8
        sorcerer.dexterity = 14
        sorcerer.constitution = 14
        sorcerer.intelligence = 10
        sorcerer.wisdom = 10
        sorcerer.charisma = 17

        ensure_progression(sorcerer, config=self.progression_config, spellbook_config=self.spellbook_config)

        self.assertEqual(sorcerer.subclass, 'Draconic Bloodline')
        self.assertEqual(sorcerer.armor_class_bonus, 3)
        self.assertEqual(sorcerer.hp_bonus_per_level, 1)

    def test_phb_slot_fallback_applies_when_tinys_slots_missing(self):
        spellcasting = {
            'spell_slots_level_1': 4,
            'spell_slots_level_2': 0,
            'spell_slots_level_3': 0,
        }

        slots = _get_spell_slots(spellcasting, 'wizard', 5, self.progression_config)

        self.assertEqual(slots[1], 4)
        self.assertEqual(slots[2], 3)
        self.assertEqual(slots[3], 2)


if __name__ == '__main__':
    unittest.main()