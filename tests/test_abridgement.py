import json
import tempfile
import unittest
from pathlib import Path
from api.services.abridgement import AbridgementEngine, EditorialError, split_source, words, allocate_targets, audit_statements


class FakeEditor:
    def __init__(self, supported=True):
        self.calls = []
        self.supported = supported

    def __call__(self, system, prompt):
        payload = json.loads(prompt)
        self.calls.append(payload)
        task, data = payload["task"], payload["data"]
        if task.startswith("Extract"):
            return json.dumps(dict(argument="A claim with evidence", examples="A memorable example",
                                   caveats="Not always", voice="Curious"))
        if task.startswith("Create"):
            return json.dumps({"plan": "Preserve reasoning and avoid repeating the definition."})
        if task.startswith("Allocate"):
            return json.dumps({"weights": {card["source_id"]: 1 for card in data["cards"]}})
        if task.startswith("Audit"):
            return json.dumps({"checks": [{"id": i, "supported": self.supported,
                "quotes": [data["source"][:30]] if self.supported else [], "issue": "" if self.supported else "Invented fact"}
                for i, _ in enumerate(data["statements"])]})
        return json.dumps({"text": " ".join(["word"] * data["target_words"])})


class AbridgementTests(unittest.TestCase):
    def test_audit_preserves_initials_and_name_titles(self):
        text = 'Hughes was nominated. W. R. Hearst visited Mrs. Roberts.\n\nDr. Smith left.'
        self.assertEqual(audit_statements(text), [
            'Hughes was nominated.', 'W. R. Hearst visited Mrs. Roberts.', 'Dr. Smith left.'])

    def test_audit_preserves_exclamatory_work_title(self):
        self.assertEqual(audit_statements('She appeared in Stop! Look! Listen! at the Globe. He attended.'),
            ['She appeared in Stop! Look! Listen! at the Globe.', 'He attended.'])

    def test_repetition_releases_budget_for_novel_material(self):
        result = allocate_targets([1000, 1000, 1000], [1, .2, 1.5], .35)
        self.assertEqual(sum(result), 1050)
        self.assertLess(result[1], result[0])
        self.assertGreater(result[2], result[0])

    def test_tiny_sections_do_not_expand(self):
        result = allocate_targets([2, 1000], [2, .15], .65)
        self.assertLessEqual(result[0], 2)
        self.assertEqual(sum(result), round(1002 * .65))
    def setUp(self):
        self.chapters = [{"title": "Chapter", "href": "one.xhtml", "text": "Evidence matters. " * 600}]

    def test_levels_use_original_not_previous_edition(self):
        editor = FakeEditor()
        counts = []
        for level in ("light", "standard", "compact", "essence"):
            result = AbridgementEngine(editor).run(self.chapters, level)
            counts.append(result["word_count"])
            self.assertEqual(result["quality_status"], "automated_review_passed")
        self.assertEqual(counts, sorted(counts, reverse=True))
        for call in editor.calls:
            if call["task"].startswith("Write"):
                self.assertIn("Evidence matters.", call["data"]["source"]["text"])

    def test_cache_resume_and_language_separation(self):
        with tempfile.TemporaryDirectory() as folder:
            editor = FakeEditor()
            first = AbridgementEngine(editor, folder).run(self.chapters)
            calls = len(editor.calls)
            second = AbridgementEngine(editor, folder).run(self.chapters)
            self.assertEqual(len(editor.calls), calls)
            self.assertEqual(first["sections"], second["sections"])
            AbridgementEngine(editor, folder).run(self.chapters, language="de")
            self.assertGreater(len(editor.calls), calls)

    def test_model_change_invalidates_cache(self):
        with tempfile.TemporaryDirectory() as folder:
            editor = FakeEditor()
            AbridgementEngine(editor, folder, "model1").run(self.chapters)
            count = len(editor.calls)
            AbridgementEngine(editor, folder, "model2").run(self.chapters)
            self.assertEqual(len(editor.calls), count * 2)

    def test_retry_reuses_analysis_but_writes_fresh_drafts(self):
        with tempfile.TemporaryDirectory() as folder:
            editor = FakeEditor()
            AbridgementEngine(editor, folder, revision=0).run(self.chapters)
            count = len(editor.calls)
            AbridgementEngine(editor, folder, revision=1).run(self.chapters)
            retried = editor.calls[count:]
            self.assertTrue(retried)
            self.assertTrue(all(call["task"].startswith(("Write", "Audit")) for call in retried))

    def test_unsupported_prose_is_not_published(self):
        editor = FakeEditor(False)
        with self.assertRaises(EditorialError):
            AbridgementEngine(editor).run(self.chapters)
        self.assertEqual(sum(call["task"].startswith("Write") for call in editor.calls), 3)

    def test_empty_input_rejected(self):
        with self.assertRaises(ValueError):
            AbridgementEngine(FakeEditor()).run([])

    def test_multiple_chapters_preserve_order_and_source_links(self):
        chapters = self.chapters + [{"title": "Next", "href": "two.xhtml", "text": "Another example. " * 500}]
        result = AbridgementEngine(FakeEditor()).run(chapters)
        self.assertEqual([s["href"] for s in result["sections"]], ["one.xhtml", "two.xhtml"])
        self.assertEqual(set(result["editorial_weights"]), {"s1", "s2"})
        self.assertEqual(sum(s["target_words"] for s in result["sections"]), round(result["source_words"] * .35))

    def test_chunking_preserves_words_and_bounds(self):
        source = "First sentence.\n\n" + "Some evidence here. " * 6000
        chunks = split_source(source)
        self.assertEqual(" ".join(source.split()), " ".join(" ".join(chunks).split()))
        self.assertTrue(all(words(c) <= 1800 and len(c) <= 12000 for c in chunks))
        self.assertTrue(all(len(c) <= 12000 for c in split_source("a" * 40000)))

    def test_chunk_boundaries_do_not_cut_a_sentence_that_fits(self):
        source = "One two three four. Five six seven eight. Nine ten eleven twelve."
        self.assertEqual(split_source(source, max_words=6),
                         ["One two three four.", "Five six seven eight.", "Nine ten eleven twelve."])

    def test_invalid_json_retry_is_bounded(self):
        calls = []
        def invalid(*args):
            calls.append(args)
            return "not JSON"
        with self.assertRaises(EditorialError):
            AbridgementEngine(invalid).run(self.chapters)
        self.assertEqual(len(calls), 2)

    def test_invented_evidence_quote_is_rejected(self):
        value = {"checks": [{"id": 0, "supported": True, "quotes": ["Invented evidence"], "issue": ""}]}
        with self.assertRaises(ValueError):
            AbridgementEngine._review(value, ["A claim"], "Actual source")

    def test_display_quotes_resolve_to_exact_source_and_are_logged(self):
        value = {"checks": [{"id": 0, "supported": True, "quotes": ['"Water arrives daily."'], "issue": ""}]}
        AbridgementEngine._review(value, ['Water arrives daily.'], 'Water arrives daily. Ice arrives too.')
        self.assertEqual(value['checks'][0]['quotes'], ['Water arrives daily.'])
        self.assertEqual(value['checks'][0]['quote_format_repairs'][0]['reported'], '"Water arrives daily."')

    def test_quote_repair_cannot_remove_negation_or_internal_ellipsis(self):
        for quote in ['"It is safe."', '"It is ... safe."']:
            value = {"checks": [{"id": 0, "supported": True, "quotes": [quote], "issue": ""}]}
            with self.assertRaises(ValueError):
                AbridgementEngine._review(value, ['It is safe.'], 'It is not safe.')

    def test_excerpt_initial_capitalization_resolves_to_source(self):
        value = {'checks': [{'id': 0, 'supported': True, 'quotes': ['He had blue eyes'], 'issue': ''}]}
        AbridgementEngine._review(value, ['He had blue eyes.'], 'But he had blue eyes and dark hair.')
        self.assertEqual(value['checks'][0]['quotes'], ['he had blue eyes'])

    def test_missing_statement_check_is_rejected(self):
        with self.assertRaises(ValueError):
            AbridgementEngine._review({"checks": []}, ["A claim"], "Actual source")

    def test_small_unsupported_addition_is_removed_and_reaudited(self):
        base = FakeEditor()
        audits = []
        corrections = []
        def editor(system, prompt):
            payload = json.loads(prompt)
            if payload["task"].startswith("Write"):
                if "review" in payload["data"]:
                    corrections.extend(payload["data"]["review"]["corrections"])
                return json.dumps({"text": "Invented aside. " + "Supported prose remains here. " * 20})
            if payload["task"].startswith("Audit"):
                data = payload["data"]
                audits.append(data["statements"])
                return json.dumps({"checks": [{"id": i, "supported": s["text"] != "Invented aside.",
                    "quotes": [] if s["text"] == "Invented aside." else [data["source"][:30]],
                    "issue": "Invented" if s["text"] == "Invented aside." else ""}
                    for i, s in enumerate(data["statements"])]})
            return base(system, prompt)
        result = AbridgementEngine(editor).run(self.chapters)
        self.assertGreaterEqual(len(audits), 3)
        self.assertEqual(corrections[0]["statement"], "Invented aside.")
        self.assertEqual(corrections[0]["issue"], "Invented")
        checks = result["sections"][0]["evidence_checks"]
        self.assertEqual([check["id"] for check in checks], list(range(20)))
        self.assertNotIn("Invented aside.", result["sections"][0]["text"])
        self.assertEqual(result["sections"][0]["removed_unsubstantiated_sentences"], ["Invented aside."])


if __name__ == "__main__":
    unittest.main()
