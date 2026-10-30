import unittest

from app import ALLOWED_COLOURINGS, apply_colour_policy


class ColourPolicyTests(unittest.TestCase):
    def test_turmeric_rejects_rose_pink_top_score(self):
        raw = {
            'Pure': 0.08,
            'PillarRed': 0.12,
            'RosePink': 0.60,
            'LemonYellow': 0.11,
            'EggYellow': 0.09,
        }
        result = {
            'powder': 'Turmeric',
            'colouring': 'RosePink',
            'raw_colouring_probabilities': raw.copy(),
        }

        apply_colour_policy(result)

        self.assertEqual(result['colouring'], 'LemonYellow')
        self.assertEqual(result['model_colouring_prediction'], 'RosePink')
        self.assertEqual(result['allowed_colourings'], list(ALLOWED_COLOURINGS['Turmeric']))
        self.assertEqual(result['eligible_colouring_probabilities'], {
            'Pure': 0.08,
            'LemonYellow': 0.11,
            'EggYellow': 0.09,
        })
        self.assertEqual(result['raw_colouring_probabilities'], raw)

    def test_chilli_and_curry_reject_yellow_classes(self):
        for powder in ('Chilli', 'CurryPowder'):
            with self.subTest(powder=powder):
                result = {
                    'powder': powder,
                    'colouring': 'EggYellow',
                    'raw_colouring_probabilities': {
                        'Pure': 0.1,
                        'PillarRed': 0.7,
                        'RosePink': 0.2,
                        'LemonYellow': 0.9,
                        'EggYellow': 0.8,
                    },
                }

                apply_colour_policy(result)

                self.assertEqual(result['colouring'], 'PillarRed')
                self.assertIn(result['colouring'], ALLOWED_COLOURINGS[powder])

    def test_unknown_powder_fails_closed(self):
        result = {
            'powder': 'Unknown',
            'colouring': 'Pure',
            'raw_colouring_probabilities': {'Pure': 1.0},
        }

        with self.assertRaises(RuntimeError):
            apply_colour_policy(result)


if __name__ == '__main__':
    unittest.main()