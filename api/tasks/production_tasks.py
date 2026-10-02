"""Queue adapter for the provider-independent book pipeline."""
import json
from datetime import datetime
from pathlib import Path
from api.config.huey_config import huey
from api.config.settings import settings
from api.database.connection import SessionLocal
from api.models.database_models import Job
from api.daos.job_tracking_dao import get_job_tracking_dao
from api.services.production.providers import get_providers, get_strategies
from api.services.production.pipeline import BookPipeline, CachedGenerator, FFmpegAssembler
from api.services.production.usage import UsageRecorder


class Cancelled(Exception):
    pass


def run_book(job_id, session_factory=SessionLocal, providers_factory=get_providers,
             strategies_factory=get_strategies, assembler=None):
    db = session_factory()
    tracking = get_job_tracking_dao(db)
    job = None
    try:
        claimed = db.query(Job).filter(Job.job_id == job_id, Job.status.in_(["queued", "pending"])).update(
            {"status": "processing", "started_at": datetime.utcnow()}, synchronize_session=False)
        db.commit()
        if not claimed:
            return
        job = db.get(Job, job_id)
        options = json.loads(job.config)

        def check():
            db.refresh(job)
            if job.status != "processing":
                raise Cancelled()

        def progress(percent, step):
            check()
            db.query(Job).filter(Job.job_id == job_id, Job.status == "processing").update(
                {"progress": percent, "current_step": step}, synchronize_session=False)
            db.commit()
            check()

        def save_text(result):
            check()
            db.query(Job).filter(Job.job_id == job_id, Job.status == "processing").update(
                {"result_data": json.dumps(result, ensure_ascii=False)}, synchronize_session=False)
            db.commit()
            check()

        from api.services.production.library import load_chapters
        progress(1, "Lese ausgewählte Kapitel")
        all_chapters = load_chapters(job.file_path)
        selected = set(options["chapters"])
        chapters = [c for c in all_chapters if c["href"] in selected and c["text"].strip()]
        if len({c["href"] for c in all_chapters if c["href"] in selected}) != len(selected):
            raise ValueError("Die Kapitelauswahl passt nicht mehr zur EPUB-Datei")
        db.query(Job).filter(Job.job_id == job_id).update({"total_chapters": len(chapters)}, synchronize_session=False)
        db.commit()
        folder = Path(settings.audiofiles_dir) / "productions" / options["workspace_id"]
        recorder = UsageRecorder(db, job)
        providers = providers_factory()
        text = providers.text(options["text_provider"], options["text_model"]) if (
            options["strategy"] != "original" or options["language"] != "original") else None
        generate = CachedGenerator(text, recorder, folder / "text", check) if text else None
        audio = providers.audio(options["audio_provider"], options["audio_model"]) if options["audio"] else None
        pipeline = BookPipeline(strategies_factory(), generate, audio, recorder,
            assembler or FFmpegAssembler(), folder, progress, check, save_text)
        result = pipeline.run(chapters, options)
        result["selected_chapters"] = [c["href"] for c in chapters]
        result["empty_chapters"] = [c["title"] for c in all_chapters if c["href"] in selected and not c["text"].strip()]
        check()
        for asset in result["audio"]:
            path = Path(asset.pop("path"))
            asset["asset_id"] = tracking.add_asset(job_id, "audio_combined", str(path), "hoerbuch.mp3",
                path.stat().st_size, asset["duration_seconds"])
        check()
        db.query(Job).filter(Job.job_id == job_id, Job.status == "processing").update({
            "status": "completed", "progress": 100, "processed_chapters": len(chapters),
            "current_step": "Auftrag fertig", "completed_at": datetime.utcnow(),
            "audio_duration_seconds": sum(a["duration_seconds"] for a in result["audio"]),
            "result_data": json.dumps(result, ensure_ascii=False)}, synchronize_session=False)
        db.commit()
        tracking.create_event(job_id, job.user_id, "production_completed", status="completed", progress=100)
    except Cancelled:
        pass
    except Exception as exc:
        db.rollback()
        if job:
            db.query(Job).filter(Job.job_id == job_id, Job.status == "processing").update({
                "status": "failed", "completed_at": datetime.utcnow(), "current_step": "Auftrag fehlgeschlagen",
                "error_message": f"{type(exc).__name__}: {exc}"}, synchronize_session=False)
            db.commit()
    finally:
        db.close()


@huey.task()
def process_book(job_id):
    return run_book(job_id)
