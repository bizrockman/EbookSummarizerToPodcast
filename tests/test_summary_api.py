import json
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from api.middleware.auth import get_current_user, get_db
from api.models.database_models import Base, Book, Job, User
from api.routers.summaries import router
from api.models.schemas import Chapter


class SummaryApiTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()
        self.user = User(user_id="owner", user_name="Owner", api_key="key", is_admin=False)
        self.db.add(self.user)
        self.db.add(Book(book_id="book", user_id="owner", original_filename="book.epub",
                         file_path="book.epub", file_hash="hash", file_size_bytes=123, title="Test"))
        self.db.add(Job(job_id="edition", user_id="owner", book_id="book", job_type="book_summary",
                        status="completed", file_path="book.epub", config=json.dumps({"chapters": ["one.xhtml"]}),
                        result_data=json.dumps({"quality_status": "automated_review_passed", "sections": []})))
        self.db.commit()
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_current_user] = lambda: self.user
        app.dependency_overrides[get_db] = lambda: self.db
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        self.db.close()
        self.engine.dispose()

    def test_completed_edition_is_readable(self):
        result = self.client.get("/summaries/edition")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()["book_id"], "book")

    def test_other_users_cannot_read_or_generate_audio(self):
        self.user.user_id = "other"
        self.assertEqual(self.client.get("/summaries/edition").status_code, 404)
        self.assertEqual(self.client.post("/summaries/edition/audio", json={}).status_code, 404)

    def test_audio_uses_exact_edition(self):
        queue = Mock()
        queue.create_job.return_value = "audio"
        with patch("api.routers.summaries.get_queue_service", return_value=queue):
            result = self.client.post("/summaries/edition/audio", json={"voice": "nova"})
        self.assertEqual(result.status_code, 200)
        self.assertEqual(queue.create_job.call_args.args[4]["edition_job_id"], "edition")

    def test_worker_speaks_saved_text_without_extracting_original(self):
        from api.tasks.audiobook_tasks import _generate_audiobook_from_chapters
        edition = self.db.get(Job, "edition")
        edition.result_data = json.dumps({"quality_status": "automated_review_passed", "sections": [
            {"href": "one.xhtml", "text": "The saved short reading edition."}]})
        self.db.add(Job(job_id="audio", user_id="owner", book_id="book", job_type="audiobook_chapters",
                        status="processing", file_path="book.epub",
                        config=json.dumps({"edition_job_id": "edition"})))
        self.db.commit()
        chapter = Chapter(title="One", href="one.xhtml")
        spoken = []
        tts = Mock(spec=["generate_speech"])
        def speak(text, voice, output_file, progress_callback):
            spoken.append(text)
            Path(output_file).write_bytes(b"fake-audio")
            return output_file, 1., {"total_cost_usd": 0., "characters": len(text), "provider": "test"}
        tts.generate_speech.side_effect = speak
        with tempfile.TemporaryDirectory() as folder:
            combined = Path(folder) / "combined.mp3"
            combined.write_bytes(b"fake-combined")
            with patch("api.tasks.audiobook_tasks.get_tts_dao", return_value=tts), \
                 patch("api.tasks.audiobook_tasks.settings.audiofiles_dir", folder), \
                 patch("api.tasks.audiobook_tasks.combine_audio_files", return_value=str(combined)), \
                 patch("api.tasks.audiobook_tasks.EPUBService.extract_chapter_content", side_effect=AssertionError("Original used")):
                _generate_audiobook_from_chapters(self.db, "audio", "owner", "book.epub", "Book",
                                                  [chapter], [chapter], "openai", "alloy")
            self.assertEqual(spoken, ["One\n\nThe saved short reading edition."])
            self.assertEqual(self.db.get(Job, "audio").status, "completed")
            result = json.loads(self.db.get(Job, "audio").result_data)
            self.assertTrue(result["chapters_audio"][0]["was_summarized"])
            self.assertIn("audio_", result["chapters_audio"][0]["audio_file"])

    def test_unresolved_review_blocks_audio(self):
        job = self.db.get(Job, "edition")
        job.result_data = json.dumps({"quality_status": "needs_review"})
        self.db.commit()
        self.assertEqual(self.client.post("/summaries/edition/audio", json={}).status_code, 409)

    def test_length_warning_does_not_block_requested_audio(self):
        job = self.db.get(Job, "edition")
        job.result_data = json.dumps({"quality_status": "length_warning", "sections": [{"href": "one.xhtml"}]})
        self.db.commit()
        queue = Mock()
        queue.create_job.return_value = "audio"
        with patch("api.routers.summaries.get_queue_service", return_value=queue):
            self.assertEqual(self.client.post("/summaries/edition/audio", json={}).status_code, 200)

    def test_invalid_chapter_and_level_rejected(self):
        payload = {"book_id": "book", "chapters": ["missing"], "level": "standard"}
        with patch("api.routers.summaries.EPUBService.extract_chapters", return_value=[Chapter(title="One", href="one.xhtml")]):
            self.assertEqual(self.client.post("/summaries", json=payload).status_code, 422)
        payload["level"] = "invented"
        self.assertEqual(self.client.post("/summaries", json=payload).status_code, 422)


if __name__ == "__main__":
    unittest.main()
