"""Offline invariants for the comparative extraction experiment."""
import sys
import unittest
import json
import tempfile
from unittest.mock import patch
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from compare_approaches import technical_selection, units_for, verify_final_current


class ComparisonSelectionTests(unittest.TestCase):
    def test_final_rewrite_is_reaudited_before_returning(self):
        initial = 'invented ' + 'detail ' * 598 + 'ends.'
        corrected = 'supported ' + 'detail ' * 598 + 'ends.'
        observed = []
        class FakeCalls:
            def complete(self, system, prompt):
                data = json.loads(prompt)['data']
                observed.append(data['draft_context'])
                supported = data['draft_context'] == corrected
                return json.dumps({'checks': [{'id': s['id'], 'supported': supported,
                    'quotes': ['Source fact.'] if supported else [],
                    'issue': '' if supported else 'Invented claim'} for s in data['statements']]})
            def ask(self, task, data):
                return {'text': corrected}
        with tempfile.TemporaryDirectory() as folder, patch('compare_approaches.OUT', Path(folder)), \
                patch('compare_approaches.polish', return_value=initial) as length_pass:
            result = verify_final_current(FakeCalls(), initial + ' extra' * 100, [{'text': 'Source fact.'}])
            length_pass.assert_called_once()
            audit = json.loads((Path(folder) / 'current-final-audit.json').read_text())
        self.assertEqual(result, corrected)
        self.assertEqual(observed, [initial, corrected])
        self.assertTrue(audit['passed'])
        self.assertEqual(audit['attempts'][-1]['text'], result)

    def test_units_preserve_source_words_and_chapter_order(self):
        chapters = [{'text': 'First thought.\n\nSecond thought.'}, {'text': 'Another paragraph. ' * 100}]
        units = units_for(chapters)
        self.assertEqual(' '.join(' '.join(c['text'].split()) for c in chapters),
                         ' '.join(' '.join(u['text'].split()) for u in units))
        self.assertEqual([u['chapter'] for u in units], sorted(u['chapter'] for u in units))
        self.assertTrue(all(len(u['text'].split()) <= 120 for u in units))

    def test_selection_is_reproducible_bounded_and_source_ordered(self):
        units = [{'id': i, 'chapter': i // 3, 'text': f'Evidence {i}. ' * 8} for i in range(9)]
        similarity = np.eye(9) + .3 * (np.ones((9, 9)) - np.eye(9))
        selected = technical_selection(units, similarity, 80)
        self.assertEqual(selected, technical_selection(units, similarity, 80))
        self.assertLessEqual(sum(len(u['text'].split()) for u in selected), 80)
        self.assertEqual([u['id'] for u in selected], sorted(u['id'] for u in selected))
        self.assertEqual(len({u['id'] for u in selected}), len(selected))

    def test_disconnected_sources_are_supported(self):
        units = [{'id': i, 'chapter': i, 'text': 'A complete thought.'} for i in range(3)]
        selected = technical_selection(units, np.eye(3), 9)
        self.assertEqual([u['id'] for u in selected], [0, 1, 2])


if __name__ == '__main__':
    unittest.main()
