import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from api.services.reading_reduction import prepare, candidate_pairs, accepted_repetitions, allocate, validate_sections
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from experiment_usage import Meter


class ReadingReductionTests(unittest.TestCase):
    def test_structure_preserves_all_words_and_order(self):
        chapters = [{'title': 'A', 'text': 'W. R. Hearst attended Stop! Look! Listen! at the Globe.\n\n' + 'Another event happened. ' * 300},
                    {'title': 'B', 'text': 'A different argument. ' * 100}]
        units, blocks = prepare(chapters)
        expected = ' '.join(' '.join(c['text'].split()) for c in chapters)
        self.assertEqual(' '.join(' '.join(b['text'].split()) for b in blocks), expected)
        self.assertEqual([u for b in blocks for u in b['unit_ids']], list(range(len(units))))
        self.assertIn('W. R. Hearst attended Stop! Look! Listen!', units[0]['text'])

    def test_similar_events_are_not_deleted(self):
        units, blocks = prepare([{'title': 'A', 'text': 'John visited London in March.\n\nJohn visited London in July.'}], block_limit=6)
        pairs = candidate_pairs([[1, 0], [1, .01]])
        good, bad = accepted_repetitions([{'a': 0, 'b': 1, 'relation': 'different_event'}], pairs, units)
        self.assertEqual(good, [])
        self.assertEqual(sum(allocate(blocks, units, good, .4)), 4)
        self.assertTrue(all(v > 0 for v in allocate(blocks, units, good, .4)))

    def test_repeated_spans_reduce_later_budget_without_deleting_blocks(self):
        text = 'A repeated statement describes the same important mechanism. '
        units, blocks = prepare([{'title': 'A', 'text': (text * 10) + '\n\n' + (text * 10)}], block_limit=100)
        repeat = {'a': 0, 'b': 1, 'relation': 'same_claim', 'confidence': .95,
            'safe_to_shorten_later': True, 'earlier_span': units[0]['text'], 'later_span': units[1]['text']}
        accepted, _ = accepted_repetitions([repeat], [{'a':0,'b':1}], units)
        budgets = allocate(blocks, units, accepted, .4)
        self.assertLess(budgets[1], budgets[0])
        self.assertGreater(budgets[1], 0)
        self.assertEqual(budgets, allocate(blocks, units, accepted * 2, .4))
        self.assertEqual(sum(budgets), round(sum(len(b['text'].split()) for b in blocks)*.4))

    def test_invented_repeat_span_is_not_accepted(self):
        units, _ = prepare([{'title': 'A', 'text': 'These words really occur here.\n\nThese are some different words.'}])
        repeat = {'a':0,'b':1,'relation':'same_claim','confidence':1,'safe_to_shorten_later':True,
                  'earlier_span':'These words really occur here.', 'later_span':'An invented assertion not present.'}
        accepted, rejected = accepted_repetitions([repeat], [{'a':0,'b':1}], units)
        self.assertFalse(accepted)
        self.assertEqual(len(rejected),1)

    def test_missing_and_reordered_output_blocks_are_rejected(self):
        for sections in [[{'id':0,'text':'Some text.'}], [{'id':1,'text':'B'},{'id':0,'text':'A'}]]:
            with self.assertRaises(ValueError):
                validate_sections({'sections':sections},[0,1])

    def test_candidates_are_bounded_stable_and_not_self_pairs(self):
        v=np.eye(8)+.9
        pairs=candidate_pairs(v,threshold=.1,limit=5)
        self.assertEqual(pairs,candidate_pairs(v,threshold=.1,limit=5))
        self.assertEqual(len(pairs),5)
        self.assertTrue(all(p['a']<p['b'] for p in pairs))


class MeterTests(unittest.TestCase):
    def test_concurrent_cache_hits_are_not_billed_twice_and_subtotals_not_added(self):
        calls=[]
        usage=SimpleNamespace(model_dump=lambda:{'prompt_tokens':100,'completion_tokens':40,
            'prompt_tokens_details':{'cached_tokens':50},'completion_tokens_details':{'reasoning_tokens':10}})
        def create(**kwargs):
            calls.append(kwargs)
            return SimpleNamespace(model='test-snapshot',id='r1',usage=usage,
                choices=[SimpleNamespace(finish_reason='stop',message=SimpleNamespace(content='{"ok":true}'))])
        client=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
        with tempfile.TemporaryDirectory() as folder:
            meter=Meter(folder,'unused','gpt-5',client)
            with ThreadPoolExecutor(2) as pool:
                list(pool.map(lambda owner:meter.call(owner,'writing',{'same':'data'},'system'),['a','b']))
            rows=meter.report()
            self.assertEqual(len(calls),1)
            self.assertEqual(rows[0]['input'],100)
            self.assertEqual(rows[0]['output'],40)
            self.assertEqual(rows[0]['cached_input'],50)
            self.assertEqual(rows[0]['reasoning'],10)
            events=[json.loads(x) for x in (Path(folder)/'events.jsonl').read_text().splitlines()]
            self.assertEqual(sum(e['kind']=='local_cache_hit' for e in events),1)

    def test_timeouts_are_logged_as_unknown_not_zero_cost(self):
        def create(**kwargs):
            raise TimeoutError('test')
        client=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
        with tempfile.TemporaryDirectory() as folder:
            meter=Meter(folder,'unused','gpt-5',client)
            with self.assertRaises(TimeoutError):
                meter.call('a','writing',{},'system')
            self.assertEqual(meter.report()[0]['unknown_usage'],2)
            self.assertEqual(meter.report()[0]['calls'],2)


if __name__ == '__main__':
    unittest.main()
