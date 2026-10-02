"""Queue worker for source-grounded book abridgements."""
import hashlib
import json
import time
from datetime import datetime
from pathlib import Path
from api.config.huey_config import huey
from api.config.settings import settings
from api.database.connection import SessionLocal
from api.models.database_models import Job
from api.services.abridgement import AbridgementEngine
from api.services.epub_service import EPUBService
from api.daos.job_tracking_dao import get_job_tracking_dao


class Cancelled(Exception):
    pass


@huey.task()
def process_book_summary(job_id):
    from openai import OpenAI
    db = SessionLocal()
    dao = get_job_tracking_dao(db)
    job = dao.get_job(job_id)
    try:
        if not job:
            return
        claimed = db.query(Job).filter(Job.job_id == job_id, Job.status.in_(["queued", "pending"])).update(
            {"status": "processing", "started_at": datetime.utcnow()}, synchronize_session=False)
        db.commit()
        if not claimed:
            return
        db.refresh(job)
        config = json.loads(job.config)
        dao.update_job(job_id, status="processing", started_at=datetime.utcnow(), progress=1,
                       current_step="Lese Originalkapitel")
        service = EPUBService()
        all_chapters = service.extract_chapters(job.file_path)
        selected = set(config["chapters"])
        chapters = [{"title": c.title, "href": c.href,
                     "text": service.extract_chapter_content(job.file_path, c.href, all_chapters)}
                    for c in all_chapters if c.href in selected]
        empty_chapters = [c["title"] for c in chapters if not c["text"].strip()]
        chapters = [c for c in chapters if c["text"].strip()]
        client = OpenAI(api_key=settings.openai_api_key, timeout=120, max_retries=2)

        def check_cancelled():
            db.refresh(job)
            if job.status == "cancelled":
                raise Cancelled()

        def progress(percent, message):
            check_cancelled()
            dao.update_job(job_id, progress=percent, current_step=message)

        def complete(system, prompt):
            check_cancelled()
            started = time.monotonic()
            response = client.chat.completions.create(
                model=config["model"], messages=[{"role": "system", "content": system},
                                                 {"role": "user", "content": prompt}],
                response_format={"type": "json_object"}, max_completion_tokens=12000,
                **({"reasoning_effort": "low"} if config["model"].startswith(("gpt-5", "o3", "o4")) else {}))
            usage = response.usage
            dao.add_cost(job_id, input_tokens=usage.prompt_tokens if usage else 0,
                         output_tokens=usage.completion_tokens if usage else 0)
            dao.create_event(job_id, job.user_id, "editorial_call_completed", status=job.status,
                progress=job.progress, step=job.current_step,
                details={"model": config["model"], "seconds": round(time.monotonic() - started, 2),
                         "input_tokens": usage.prompt_tokens if usage else 0,
                         "output_tokens": usage.completion_tokens if usage else 0})
            # Track usage, but do not apply stale/incorrect price tables to arbitrary models.
            check_cancelled()
            choice = response.choices[0]
            if choice.finish_reason != "stop" or not choice.message.content:
                raise ValueError("Modellantwort unvollständig: " + str(choice.finish_reason))
            return choice.message.content

        namespace = hashlib.sha256((job.user_id + ":" + (job.book_id or job.file_path)).encode()).hexdigest()
        engine = AbridgementEngine(complete, Path(settings.upload_dir) / ".editions" / namespace,
                                    config["model"], progress, revision=config.get("revision", 0))
        result = engine.run(chapters, config["level"], config["language"])
        result["empty_chapters"] = empty_chapters
        result["selected_chapters"] = config["chapters"]
        result["billing_note"] = "Tokenverbrauch erfasst; Modellkosten werden nicht geschätzt."
        check_cancelled()
        dao.update_job(job_id, status="completed", progress=100, current_step="Lesefassung fertig",
                       completed_at=datetime.utcnow(), result_data=json.dumps(result, ensure_ascii=False))
    except Cancelled:
        pass
    except Exception as exc:
        if job:
            db.rollback()
            db.refresh(job)
            if job.status != "cancelled":
                dao.update_job(job_id, status="failed", completed_at=datetime.utcnow(),
                               current_step="Lesefassung fehlgeschlagen", error_message=str(exc))
    finally:
        db.close()
