import unittest
import numpy as np
from generation import generate_dishes, generate_dish, parse_query, METHODS, EXTRAS, STYLES


class FakeEngine:
    def __init__(self):
        self.vocab = dict.fromkeys([*METHODS, *EXTRAS])
        self.encoded = []
        self.steered = []

    def encode_ingredient_list(self, ingredients):
        self.encoded.append(list(ingredients))
        return np.array([1., 0.])

    def get_pole_vector(self, key):
        self.steered.append(key)
        return np.array([0., 1.])

    def slerp(self, vector, pole, theta_deg):
        return pole

    def get_ingredient_vector(self, ingredient):
        return np.array([0., 1.]) if ingredient in self.vocab else None


class GenerationTests(unittest.TestCase):
    def test_all_inputs_contribute_to_model_and_plan(self):
        engine = FakeEngine()
        dish = generate_dishes(engine, 'potatoes + spinach + garlic + north indian')[0]
        self.assertEqual(engine.encoded, [['potato', 'spinach', 'garlic']])
        self.assertEqual(engine.steered, ['cuisine:South_Asian'])
        self.assertEqual(dish['requested_ingredients'], ['potato', 'spinach', 'garlic'])
        self.assertIn('12–15 minutes', ' '.join(dish['directions']))
        self.assertIn('2–3 minutes', ' '.join(dish['directions']))
        self.assertTrue(any('tomato' in i for i in dish['ingredients']))
        self.assertIsNone(dish['flavour_match_score'])

    def test_multiple_cuisines_change_recipe_not_just_title(self):
        engine = FakeEngine()
        dishes = generate_dishes(engine, 'tofu + mushroom + chinese + thai')
        self.assertEqual(len(dishes), 2)
        self.assertEqual(engine.steered, ['cuisine:East_Asian', 'cuisine:Southeast_Asian'])
        self.assertNotEqual(dishes[0]['ingredients'], dishes[1]['ingredients'])
        self.assertNotEqual(dishes[0]['directions'], dishes[1]['directions'])
        self.assertNotEqual(dishes[0]['id'], dishes[1]['id'])
        self.assertTrue(any('soy sauce' in i for i in dishes[0]['ingredients']))
        self.assertTrue(any('coconut milk' in i for i in dishes[1]['ingredients']))

    def test_normalization_deduplication_and_legacy_cuisine(self):
        self.assertEqual(parse_query(' POTATOES + potato + North_Indian + north indian'),
                         (['potato'], ['north indian']))
        self.assertEqual(parse_query('rice', 'cuisine:South_Asian'), (['rice'], ['indian']))
        self.assertEqual(generate_dish(FakeEngine(), 'potato')['main_ingredient'], 'potato')

    def test_unknowns_and_malformed_queries_are_not_ignored(self):
        for query in ['', 'potato +', 'potato ++ rice', 'north indian', 'garlic',
                      'potato + moon dust + thai', 'potato + imaginary cuisine',
                      'potato + thai + chinese + italian + mexican',
                      'potato + rice + tofu + paneer + carrot + spinach + mushroom + garlic + onion']:
            with self.subTest(query=query), self.assertRaises(ValueError):
                generate_dishes(FakeEngine(), query)

    def test_every_main_and_style_has_complete_plan(self):
        for main in METHODS:
            for style in STYLES:
                with self.subTest(main=main, style=style):
                    dish = generate_dishes(FakeEngine(), main + ' + ' + style)[0]
                    self.assertEqual(dish['servings'], 2)
                    self.assertIn(main, dish['requested_ingredients'])
                    self.assertGreater(len(dish['directions']), 5)
                    self.assertGreater(dish['prep_time'], 0)
                    self.assertEqual(dish['model'], 'Kaikaku/epicure-core')

    def test_requested_pantry_ingredients_are_not_duplicated(self):
        dish = generate_dishes(FakeEngine(), 'paneer + onion + garlic + tomato + north indian')[0]
        for name in ['onion', 'garlic', 'tomato']:
            self.assertEqual(sum(name in line for line in dish['ingredients']), 1)

    def test_missing_model_data_fails_clearly(self):
        engine = FakeEngine()
        engine.get_pole_vector = lambda _: None
        with self.assertRaisesRegex(ValueError, 'cuisine vector'):
            generate_dishes(engine, 'potato + thai')
        engine = FakeEngine()
        engine.vocab = {'potato': 0}
        with self.assertRaisesRegex(ValueError, 'seasonings'):
            generate_dishes(engine, 'potato')

    def test_rice_and_protein_have_separate_cooking_steps(self):
        dish = generate_dishes(FakeEngine(), 'rice + chicken + garlic + chettinad')[0]
        steps = ' '.join(dish['directions'])
        self.assertIn('74°C', steps)
        self.assertIn('covered for 10 minutes', steps)
        self.assertEqual(dish['diet'], 'Non-vegetarian')
        self.assertIn('not dried', ' '.join(generate_dish(FakeEngine(), 'chickpeas')['directions']))
        self.assertEqual(generate_dishes(FakeEngine(), 'tofu + mughlai')[0]['diet'], 'Vegetarian')

    def test_embedding_ranking_changes_selected_seasonings(self):
        engine = FakeEngine()
        engine.get_ingredient_vector = lambda key: np.array([0., 1. if key == 'turmeric' else 0.])
        self.assertEqual(generate_dish(engine, 'potato')['selected_seasonings'][0], 'turmeric')
        engine.get_ingredient_vector = lambda key: np.array([0., 1. if key == 'garam_masala' else 0.])
        self.assertEqual(generate_dish(engine, 'potato')['selected_seasonings'][0], 'garam_masala')


if __name__ == '__main__':
    unittest.main()
