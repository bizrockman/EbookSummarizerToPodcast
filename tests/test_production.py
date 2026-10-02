"""Paid-call boundaries, persistence, recovery and source-preserving strategies."""
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from ebooklib import epub
from api.models.database_models import Base, Book, Job, User, CostLog, JobAsset
from api.middleware.auth import get_current_user, get_db
from api.routers.productions import router
from api.routers.books import router as books_router
from api.services.production.contracts import ProviderReply
from api.services.production.providers import ProviderRegistry, OpenAITextProvider, ProviderValidationError
from api.services.production.pipeline import CachedGenerator, split_audio, FFmpegAssembler
from api.services.production.library import load_chapters
from api.services.production.usage import UsageRecorder, usage_report, price_reply
from api.services.production.strategies import BlockReadingStrategy, TopicCoreStrategy, text_result
from api.tasks.production_tasks import run_book


def make_epub(path):
    book = epub.EpubBook()
    book.set_identifier("fixture")
    book.set_title("Workflow fixture")
    book.set_language("en")
    book.add_author("Test Author")
    chapters = []
    for i, title in enumerate(["Copyright", "Introduction", "First argument", "Bibliography"]):
        chapter = epub.EpubHtml(title=title, file_name=f"c{i}.xhtml", lang="en")
        text = "All rights reserved." if i == 0 else "A concrete example explains the idea. " * 100
        chapter.content = f"<h1>{title}</h1><p>{text}</p>"
        book.add_item(chapter)
        chapters.append(chapter)
    book.toc = chapters
    book.spine = ["nav", *chapters]
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    epub.write_epub(str(path), book)


class FakeText:
    name, model = "openai", "gpt-5"
    def __init__(self):
        self.calls = []
        self.fail = False
        self.after = None
    def validate_model(self):
        pass
    def generate(self, system, payload):
        self.calls.append(payload)
        if self.fail:
            raise TimeoutError("transport failure")
        if self.after:
            self.after()
        if "language" in payload:
            value = {"text": "Eine idiomatische Übersetzung mit einem verständlichen Beispiel.", "title": "Einleitung"}
        else:
            value = {"text": " ".join(payload["source"].split()[:payload["target_words"]])}
        return ProviderReply(content=json.dumps(value), model=self.model, input_tokens=100,
            output_tokens=40, cached_input=50, reasoning=10, raw_usage={"prompt_tokens": 100})


class FakeAudio:
    name, model, max_characters = "openai", "tts-1-hd", 200
    def __init__(self):
        self.calls = []
        self.fail_at = None
    def generate(self, text, voice, destination):
        self.calls.append(text)
        if self.fail_at == len(self.calls):
            raise TimeoutError("audio failure")
        destination.write_bytes(text.encode("utf-8"))
        return ProviderReply(model=self.model, characters=len(text))


class FakeAssembler:
    def available(self): return True
    def combine(self, files, destination):
        destination.write_bytes(b"".join(path.read_bytes() for path in files))
        return 12.5


class ProductionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name)
        self.epub = self.folder / "source.epub"
        make_epub(self.epub)
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.sessions = sessionmaker(bind=self.engine)
        self.db = self.sessions()
        self.user = User(user_id="owner", user_name="Owner", api_key="key", is_admin=False)
        self.db.add(self.user)
        self.db.add(Book(book_id="book", user_id="owner", original_filename="source.epub",
            file_path=str(self.epub), file_hash="hash", title="Workflow fixture"))
        self.db.commit()
        self.text, self.audio = FakeText(), FakeAudio()
        self.providers = ProviderRegistry({"openai": lambda model: self.text}, {"openai": lambda model: self.audio})
        self.registry = patch("api.routers.productions.get_providers", lambda: self.providers)
        self.registry.start()
        app = FastAPI()
        app.include_router(router)
        app.include_router(books_router)
        app.dependency_overrides[get_current_user] = lambda: self.user
        app.dependency_overrides[get_db] = lambda: self.db
        self.client = TestClient(app)
        self.paths = patch("api.tasks.production_tasks.settings.audiofiles_dir", str(self.folder / "audio"))
        self.paths.start()
    def tearDown(self):
        self.registry.stop()
        self.paths.stop()
        self.client.close(); self.db.close(); self.engine.dispose(); self.temp.cleanup()
    def job(self, key="job", **options):
        config = {"chapters": ["c1.xhtml", "c2.xhtml"], "strategy": "reading", "ratio": .4,
            "core_words": 300, "language": "original", "audio": False, "voice": "alloy",
            "text_provider": "openai", "text_model": "gpt-5", "audio_provider": "openai",
            "audio_model": "tts-1-hd", "workspace_id": "workspace", **options}
        job = Job(job_id=key, user_id="owner", book_id="book", job_type="book_processing",
            status="queued", file_path=str(self.epub), config=json.dumps(config))
        self.db.add(job); self.db.commit()
        return job
    def run_job(self, key="job"):
        run_book(key, self.sessions, lambda: self.providers, assembler=FakeAssembler())
        self.db.expire_all()
        return self.db.get(Job, key)

    def test_chapter_preview_is_free_and_preserves_introduction(self):
        response = self.client.get("/productions/books/book/chapters")
        self.assertEqual(response.status_code, 200)
        values = response.json()["chapters"]
        self.assertEqual([c["selected"] for c in values], [False, True, True, False])
        self.assertTrue(values[1]["excerpt"])
        self.assertEqual(self.db.query(CostLog).count(), 0)

    def test_worker_claims_once_and_preserves_every_selected_chapter(self):
        self.job()
        job = self.run_job()
        self.assertEqual(job.status, "completed")
        result = json.loads(job.result_data)
        self.assertEqual([s["href"] for s in result["sections"]], ["c1.xhtml", "c2.xhtml"])
        self.assertTrue(all(s["source_text"] and s["text"] for s in result["sections"]))
        report = usage_report(self.db, "job")
        self.assertEqual((report["totals"]["input"], report["totals"]["output"]), (200, 80))
        self.assertAlmostEqual(report["estimated_cost_usd"], 2 * ((50 * 1.25 + 50 * .125 + 40 * 10) / 1e6))
        self.run_job()
        self.assertEqual(len(self.text.calls), 2)

    def test_original_needs_no_text_provider_or_paid_call(self):
        self.job(strategy="original")
        job = self.run_job()
        self.assertEqual(job.status, "completed")
        self.assertFalse(self.text.calls)
        result = json.loads(job.result_data)
        self.assertEqual(result["actual_ratio"], 1)
        self.assertEqual(usage_report(self.db, "job")["totals"]["calls"], 0)

    def test_translation_then_audio_uses_exact_saved_translation(self):
        self.job(language="de", audio=True)
        job = self.run_job()
        self.assertEqual(job.status, "completed")
        result = json.loads(job.result_data)
        asset = self.db.query(JobAsset).first()
        self.assertEqual(Path(asset.file_path).read_text(encoding="utf-8"),
                         "".join(s["text"] for s in result["sections"]))
        self.assertTrue(all("pre_translation_text" in s for s in result["sections"]))
        self.assertEqual(self.db.query(JobAsset).count(), 1)
        self.assertEqual(usage_report(self.db, "job")["totals"]["unknown_calls"], 0)

    def test_timeout_is_not_zero_and_retry_reuses_completed_steps(self):
        self.job(audio=True)
        self.audio.fail_at = 2
        job = self.run_job()
        self.assertEqual(job.status, "failed")
        self.assertTrue(json.loads(job.result_data)["sections"])
        report = usage_report(self.db, "job")
        self.assertIsNone(report["estimated_cost_usd"])
        self.assertIsNone(report["calls"][-1]["cost_usd"])
        old_text_calls = len(self.text.calls)
        self.audio.fail_at = None
        self.job("retry", audio=True)
        self.assertEqual(self.run_job("retry").status, "completed")
        self.assertEqual(len(self.text.calls), old_text_calls)
        self.assertGreater(usage_report(self.db, "retry")["totals"]["cache_hits"], 0)

    def test_cancel_in_flight_records_usage_without_overwriting_cancelled_status(self):
        self.job()
        def cancel():
            with self.sessions() as session:
                session.query(Job).filter(Job.job_id == "job").update({"status": "cancelled"})
                session.commit()
        self.text.after = cancel
        job = self.run_job()
        self.assertEqual(job.status, "cancelled")
        self.assertEqual(len(self.text.calls), 1)
        self.assertEqual(job.input_tokens, 100)
        self.assertEqual(usage_report(self.db, "job")["totals"]["calls"], 1)

    def test_invalid_json_is_charged_but_not_cached(self):
        job = self.job()
        class Invalid(FakeText):
            def generate(self, system, payload):
                return ProviderReply(content="bad json", model="gpt-5", input_tokens=10, output_tokens=3)
        generator = CachedGenerator(Invalid(), UsageRecorder(self.db, job), self.folder / "cache", lambda: None)
        with self.assertRaises(json.JSONDecodeError):
            generator("reading", "system", {}, text_result)
        self.assertFalse(list((self.folder / "cache").glob("*.json")))
        self.assertEqual(usage_report(self.db, "job")["totals"]["input"], 10)

    def test_permissions_and_unimplemented_options_rejected_before_enqueue(self):
        self.job()
        self.user.user_id = "other"
        self.assertEqual(self.client.get("/productions/job").status_code, 404)
        self.assertEqual(self.client.get("/productions/books/book/chapters").status_code, 404)
        self.user.user_id = "owner"
        with patch("api.routers.productions.get_queue_service") as queue:
            for field, value in [("chapters", ["missing"]), ("strategy", "unknown"), ("text_provider", "local")]:
                response = self.client.post("/productions", json={"book_id": "book", "chapters": ["c1.xhtml"], field: value})
                self.assertEqual(response.status_code, 422)
            queue.return_value.create_job.assert_not_called()

    def test_same_options_reuse_job_and_different_length_creates_another(self):
        job = self.job()
        config = json.loads(job.config)
        from api.services.production.pipeline import VERSION
        config.update(book_id="book", file_hash="hash", version=VERSION, core_words=1200)
        job.config = json.dumps(config)
        self.db.commit()
        with patch("api.routers.productions.get_queue_service") as queue:
            queue.return_value.create_job.return_value = "new"
            payload = {"book_id": "book", "chapters": ["c2.xhtml", "c1.xhtml"]}
            self.assertTrue(self.client.post("/productions", json=payload).json()["reused"])
            payload["ratio"] = .6
            self.assertEqual(self.client.post("/productions", json=payload).json()["job_id"], "new")

    def test_topic_reduction_never_sends_full_book_to_reducer(self):
        chapters = [{"title": "A", "href": "a", "text": " ".join(["An event has a date and a consequence."] * 3000)}]
        phases = []
        def generate(phase, system, payload, validate=None):
            phases.append(phase)
            if phase == "topic_map":
                result = {"ideas": [{"topic": "Event", "claim": "It happened", "context": "One date and example"}]}
            else:
                self.assertLessEqual(len(payload["cards"]), 6)
                self.assertNotIn("source", payload)
                result = {"text": "An event and its consequence. " * 60}
            if validate: validate(result)
            return result
        sections, _ = TopicCoreStrategy().reduce(chapters, {"core_words": 300}, generate, lambda *args: None)
        self.assertIn("topic_reduce", phases)
        self.assertTrue(sections[0]["text"])

    def test_audio_chunks_preserve_long_sentences_and_punctuation(self):
        source = "A" * 5000 + "\n\nStop! Look! Listen! " * 500
        chunks = list(split_audio(source, 4000))
        self.assertEqual("".join(chunks), source)
        self.assertTrue(all(0 < len(c) <= 4000 for c in chunks))

    def test_unknown_model_is_not_priced_as_gpt5(self):
        self.assertIsNone(price_reply("openai", ProviderReply(model="unknown", input_tokens=100, output_tokens=50)))

    def test_model_validation_rejects_before_enqueue_and_retry_can_correct_model(self):
        job = self.job(text_model="gpt-6.1")
        job.status = "failed"
        self.db.commit()
        def reject():
            raise ProviderValidationError("Modell nicht verfügbar")
        with patch.object(self.text, "validate_model", reject), patch("api.routers.productions.get_queue_service") as queue:
            for path, body in [("/productions", {"book_id": "book", "chapters": ["c1.xhtml"]}),
                               ("/productions/job/retry", {})]:
                self.assertEqual(self.client.post(path, json=body).status_code, 422)
            queue.return_value.create_job.assert_not_called()
        with patch("api.routers.productions.get_queue_service") as queue:
            queue.return_value.create_job.return_value = "new"
            response = self.client.post("/productions/job/retry", json={"text_model": "gpt-6.1-sol"})
            self.assertEqual(response.status_code, 200)
            config = queue.return_value.create_job.call_args.args[4]
            self.assertEqual(config["text_model"], "gpt-6.1-sol")
            self.assertEqual(config["workspace_id"], "workspace")
            self.assertEqual(json.loads(job.config)["text_model"], "gpt-6.1")
        self.assertEqual(self.db.query(CostLog).count(), 0)

    def test_sol_prices_cache_reads_writes_and_reasoning_without_double_counting(self):
        reply = ProviderReply(model="gpt-6.1-sol", input_tokens=10000, cached_input=2000,
                              cache_write=3000, output_tokens=1000, reasoning=400)
        self.assertAlmostEqual(price_reply("openai", reply), (5000 * 2 + 2000 * .1 + 3000 * 2.5 + 1000 * 10) / 1e6)
        reply.input_tokens = 300000
        self.assertAlmostEqual(price_reply("openai", reply), ((295000 * 2 + 2000 * .1 + 3000 * 2.5) * 2 + 1000 * 10 * 1.5) / 1e6)

    def test_sdk_sol_uses_low_reasoning_and_preserves_cache_write_usage(self):
        raw = {"prompt_tokens": 100, "completion_tokens": 40,
               "prompt_tokens_details": {"cached_tokens": 20, "cache_write_tokens": 30}}
        usage = SimpleNamespace(prompt_tokens=100, completion_tokens=40, model_dump=lambda: raw)
        seen = []
        def create(**kwargs):
            seen.append(kwargs)
            return SimpleNamespace(model="gpt-6.1-sol", id="response", usage=usage,
                choices=[SimpleNamespace(finish_reason="stop", message=SimpleNamespace(content='{"text":"ok"}'))])
        client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
        reply = OpenAITextProvider("gpt-6.1-sol", client).generate("JSON", {})
        self.assertEqual((reply.cached_input, reply.cache_write), (20, 30))
        self.assertEqual(seen[0]["reasoning_effort"], "low")
        self.assertEqual(seen[0]["model"], "gpt-6.1-sol")
        self.assertNotIn("temperature", seen[0])

    def test_sdk_model_preflight_handles_network_and_invalid_name_without_generation(self):
        import httpx
        from openai import APIConnectionError, NotFoundError
        request = httpx.Request("GET", "https://api.openai.com/v1/models/missing")
        for error, expected in [(APIConnectionError(request=request), 503),
                               (NotFoundError("missing", response=httpx.Response(404, request=request), body={}), 422)]:
            def retrieve(model):
                self.assertEqual(model, "missing")
                raise error
            client = SimpleNamespace(models=SimpleNamespace(retrieve=retrieve))
            client.with_options = lambda **kwargs: client
            with self.assertRaises(ProviderValidationError) as caught:
                OpenAITextProvider("missing", client).validate_model()
            self.assertEqual(caught.exception.status_code, expected)

    def test_sdk_adapter_reports_incomplete_response_usage_before_validation(self):
        raw = {"prompt_tokens": 100, "completion_tokens": 40,
               "prompt_tokens_details": {"cached_tokens": 50},
               "completion_tokens_details": {"reasoning_tokens": 10}}
        usage = SimpleNamespace(prompt_tokens=100, completion_tokens=40, model_dump=lambda: raw)
        seen = []
        def create(**kwargs):
            seen.append(kwargs)
            return SimpleNamespace(model="gpt-5-2025-08-07", id="response", usage=usage,
                choices=[SimpleNamespace(finish_reason="length", message=SimpleNamespace(content='{"text":"cut'))])
        client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
        provider = OpenAITextProvider("gpt-5", client)
        job = self.job()
        generator = CachedGenerator(provider, UsageRecorder(self.db, job), self.folder / "cache", lambda: None)
        with self.assertRaises(json.JSONDecodeError):
            generator("reading", "system", {}, text_result)
        report = usage_report(self.db, "job")
        self.assertEqual((report["totals"]["input"], report["totals"]["output"],
                          report["totals"]["cached_input"], report["totals"]["reasoning"]), (100, 40, 50, 10))
        self.assertEqual(report["calls"][0]["model"], "gpt-5-2025-08-07")
        self.assertEqual(seen[0]["reasoning_effort"], "low")

    def test_epub_upload_and_duplicate_reuse_without_paid_analysis(self):
        from api.config.settings import settings
        with patch.object(settings, "upload_dir", str(self.folder / "uploads")):
            for expected in (False, True):
                with self.epub.open("rb") as stream:
                    response = self.client.post("/books/upload", files={"file": ("fixture.epub", stream, "application/epub+zip")})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["is_duplicate"], expected)
            response = self.client.post("/books/upload", files={"file": ("wrong.epub", b"not an epub", "application/epub+zip")})
            self.assertEqual(response.status_code, 400)
        self.assertEqual(self.db.query(CostLog).count(), 0)


if __name__ == "__main__":
    unittest.main()
