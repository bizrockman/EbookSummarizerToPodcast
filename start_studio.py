"""Start API, thread workers and Next.js together. Optional isolated runtime."""
import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-port", type=int, default=8000)
    parser.add_argument("--web-port", type=int, default=3000)
    parser.add_argument("--workers", type=int, default=3, help="Worker threads; 0 opens the app without processing jobs")
    parser.add_argument("--runtime", type=Path, help="Isolate database, uploads, audio and queue in this directory")
    args = parser.parse_args()
    if args.workers < 0:
        parser.error("--workers must not be negative")
    root = Path(__file__).resolve().parent
    environment = os.environ.copy()
    environment.update(PYTHONIOENCODING="utf-8", WORKER_THREADS=str(args.workers), RECOVER_JOBS_ON_START="false",
        NEXT_PUBLIC_API_BASE_URL=f"http://127.0.0.1:{args.api_port}", NEXT_TELEMETRY_DISABLED="1")
    if args.runtime:
        runtime = args.runtime.resolve()
        runtime.mkdir(parents=True, exist_ok=True)
        environment.update(DATABASE_URL="sqlite:///" + str(runtime / "studio.db").replace("\\", "/"),
            HUEY_DB_PATH=str(runtime / "queue.db"), UPLOAD_DIR=str(runtime / "uploads"),
            AUDIOFILES_DIR=str(runtime / "audio"))
    npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
    if not npm:
        parser.error("Node.js and npm are required")
    commands = [([sys.executable, "-m", "uvicorn", "api.main:app", "--host", "127.0.0.1", "--port", str(args.api_port)], root),
        ([npm, "run", "dev", "--", "--port", str(args.web_port), "--hostname", "127.0.0.1"], root / "frontend")]
    if args.workers:
        commands.append(([sys.executable, "-m", "huey.bin.huey_consumer", "api.config.huey_config.huey",
                          "-w", str(args.workers), "-k", "thread"], root))
    processes = []
    try:
        for command, directory in commands:
            processes.append(subprocess.Popen(command, cwd=directory, env=environment))
        print(f"Studio: http://127.0.0.1:{args.web_port} | API: http://127.0.0.1:{args.api_port}/docs | Workers: {args.workers}", flush=True)
        while all(process.poll() is None for process in processes):
            time.sleep(.5)
    except KeyboardInterrupt:
        pass
    finally:
        for process in processes:
            if process.poll() is None:
                process.terminate()
        for process in processes:
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()


if __name__ == "__main__":
    main()
