#!/usr/bin/env python
"""
Entwicklungs-Starter

Startet API-Server und Huey Consumer parallel.
Beide Ausgaben gehen live in die Konsole.
"""
import os
import sys
import subprocess
import time

# UTF-8 für Windows
os.environ["PYTHONIOENCODING"] = "utf-8"

# Lade Settings
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from api.config.settings import settings
from api.config.huey_config import QUEUE_BACKEND


WORKERS = settings.worker_threads


def print_banner():
    """Startup-Konfiguration"""
    print()
    print("╔" + "═" * 58 + "╗")
    print("║" + " " * 15 + "📚 eBook to Audiobook API" + " " * 18 + "║")
    print("╠" + "═" * 58 + "╣")
    print(f"║  🌐 Server:   http://localhost:8000" + " " * 22 + "║")
    print(f"║  📖 Docs:     http://localhost:8000/docs" + " " * 17 + "║")
    print("╠" + "═" * 58 + "╣")
    print(f"║  📊 Queue:      {QUEUE_BACKEND:<40} ║")
    print(f"║  👷 Workers:    {WORKERS:<40} ║")
    print(f"║  🤖 LLM:        {settings.llm_model_provider:<40} ║")
    print(f"║  🗣️  TTS:        {settings.openai_tts_model:<40} ║")
    print("╚" + "═" * 58 + "╝")
    print()
    print("  ⏹️  Beenden mit Ctrl+C")
    print()
    print("─" * 60)
    sys.stdout.flush()


def main():
    print_banner()
    
    cwd = os.path.dirname(os.path.abspath(__file__))
    
    # Starte beide Prozesse - stdout geht direkt in Konsole
    api_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "api.main:app", 
         "--host", "0.0.0.0", "--port", "8000", "--reload"],
        cwd=cwd
    )
    
    time.sleep(2)
    
    consumer_process = subprocess.Popen(
        [sys.executable, "-m", "huey.bin.huey_consumer",
         "api.config.huey_config.huey", "-w", str(WORKERS), "-k", "thread"],
        cwd=cwd
    )
    
    try:
        while True:
            if api_process.poll() is not None:
                print("\n⚠️  API Server beendet!")
                break
            if consumer_process.poll() is not None:
                print("\n⚠️  Consumer beendet!")
                break
            time.sleep(1)
            
    except KeyboardInterrupt:
        pass
    finally:
        api_process.terminate()
        consumer_process.terminate()
        api_process.wait(timeout=5)
        consumer_process.wait(timeout=5)
        print("\n👋 Server beendet")


if __name__ == "__main__":
    main()
