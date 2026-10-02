"""
Test-Script für die eBook to Audiobook API

Funktionale Tests der Endpunkte:
- Book Upload & Management
- Kapitel-Extraktion
- KI-Analyse (sync & async)
- Audiobook-Generierung

Verwendung:
    python test_api.py           # Interaktiver Modus
    python test_api.py --auto    # Automatisch ohne Analyse (schnell)
    python test_api.py --full    # Vollständig mit KI-Analyse
"""
import requests
import json
import time
import os
import sys
from pathlib import Path
from datetime import datetime

# Kommandozeilen-Argumente
AUTO_MODE = "--auto" in sys.argv
FULL_MODE = "--full" in sys.argv

# =============================================================================
# KONFIGURATION
# =============================================================================

API_URL = "http://localhost:8000"
API_KEY = "dummy-api-key-12345"
ADMIN_API_KEY = "admin-api-key-67890"

# Headers
headers = {"X-API-Key": API_KEY}
admin_headers = {"X-API-Key": ADMIN_API_KEY}

# Test-EPUB (Pfad anpassen!)
TEST_EPUB = "Blitzscaling.epub"


# =============================================================================
# HILFSFUNKTIONEN
# =============================================================================

def print_header(title: str):
    """Schöne Überschrift"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60 + "\n")


def print_step(step: str):
    """Schritt-Anzeige"""
    print(f"\n📌 {step}")
    print("-" * 50)


def print_success(msg: str):
    print(f"✅ {msg}")


def print_error(msg: str):
    print(f"❌ {msg}")


def print_info(msg: str):
    print(f"ℹ️  {msg}")


def print_json(data, indent=2):
    """Formatierte JSON-Ausgabe"""
    print(json.dumps(data, indent=indent, ensure_ascii=False, default=str))


def format_cost(cost: float) -> str:
    """Kosten formatieren"""
    return f"${cost:.4f}"


def format_time(seconds: float) -> str:
    """Zeit formatieren"""
    if seconds < 60:
        return f"{seconds:.1f}s"
    return f"{int(seconds // 60)}m {int(seconds % 60)}s"


# =============================================================================
# API HELPER
# =============================================================================

def api_get(endpoint: str, use_admin: bool = False) -> dict:
    """GET Request"""
    h = admin_headers if use_admin else headers
    response = requests.get(f"{API_URL}{endpoint}", headers=h)
    return {"status": response.status_code, "data": response.json()}


def api_post(endpoint: str, data: dict = None, use_admin: bool = False) -> dict:
    """POST Request (JSON)"""
    h = admin_headers if use_admin else headers
    response = requests.post(f"{API_URL}{endpoint}", json=data, headers=h)
    return {"status": response.status_code, "data": response.json()}


def api_delete(endpoint: str, use_admin: bool = False) -> dict:
    """DELETE Request"""
    h = admin_headers if use_admin else headers
    response = requests.delete(f"{API_URL}{endpoint}", headers=h)
    return {"status": response.status_code, "data": response.json()}


def api_upload(endpoint: str, file_path: str) -> dict:
    """File Upload"""
    with open(file_path, "rb") as f:
        files = {"file": (os.path.basename(file_path), f, "application/epub+zip")}
        response = requests.post(
            f"{API_URL}{endpoint}",
            files=files,
            headers=headers
        )
    return {"status": response.status_code, "data": response.json()}


# =============================================================================
# POLLING HELPER
# =============================================================================

def poll_job_status(
    job_id: str,
    max_wait: int = 300,
    poll_interval: int = 2,
    verbose: bool = True
) -> dict:
    """
    Prüfe Job-Status mit schöner Fortschrittsanzeige.
    
    Zeigt z.B.: "5/17 Kapitel analysiert, 3 mit Inhalt (29%)"
    """
    start_time = time.time()
    last_progress = -1
    
    while True:
        elapsed = time.time() - start_time
        
        if elapsed > max_wait:
            print_error(f"Timeout nach {format_time(max_wait)}")
            return None
        
        result = api_get(f"/jobs/{job_id}")
        if result["status"] != 200:
            print_error(f"Fehler: {result['data']}")
            return None
        
        status_data = result["data"]
        status = status_data["status"]
        progress = status_data["progress"]
        
        # Zeige Progress wenn geändert
        if progress != last_progress and verbose:
            # Baue Fortschrittsanzeige
            total_ch = status_data.get("total_chapters", 0)
            proc_ch = status_data.get("processed_chapters", 0)
            current = status_data.get("current_step", "")
            
            # Fortschrittsbalken
            bar_width = 20
            filled = int(bar_width * progress / 100)
            bar = "█" * filled + "░" * (bar_width - filled)
            
            # Zeitanzeige
            time_str = format_time(elapsed)
            
            # Kapitel-Info
            if total_ch > 0:
                ch_info = f"{proc_ch}/{total_ch} Kapitel"
            else:
                ch_info = ""
            
            # Ausgabe
            print(f"  [{time_str:>6}] {bar} {progress:3d}% | {ch_info} | {current[:40]}")
            
            last_progress = progress
        
        # Status prüfen
        if status == "completed":
            print()
            print_success(f"Abgeschlossen in {format_time(elapsed)}")
            return status_data
        elif status == "failed":
            print()
            print_error(f"Fehlgeschlagen: {status_data.get('error_message', 'Unbekannt')}")
            return status_data
        elif status == "cancelled":
            print()
            print_info("Abgebrochen")
            return status_data
        
        time.sleep(poll_interval)


# =============================================================================
# TESTS
# =============================================================================

def test_health():
    """Test 1: Health Check"""
    print_step("Health Check")
    
    result = api_get("/health")
    
    if result["status"] == 200:
        data = result["data"]
        print_success("API ist erreichbar")
        print(f"   Queue Backend: {data['queue_backend']}")
        print(f"   Pending Jobs:  {data['queue_pending']}")
        print(f"   Processing:    {data['jobs_processing']}")
        return True
    else:
        print_error("API nicht erreichbar")
        return False


def test_book_upload(epub_path: str) -> str:
    """Test 2: Buch hochladen"""
    print_step("Buch hochladen")
    
    if not os.path.exists(epub_path):
        print_error(f"Datei nicht gefunden: {epub_path}")
        return None
    
    result = api_upload("/books/upload", epub_path)
    
    if result["status"] == 200:
        data = result["data"]
        print_success(f"Buch hochgeladen: {data['title']}")
        print(f"   Book ID:  {data['book_id']}")
        print(f"   Autor:    {data['author']}")
        print(f"   Kapitel:  {data['chapter_count']}")
        print(f"   Duplikat: {'Ja' if data['is_duplicate'] else 'Nein'}")
        return data["book_id"]
    else:
        print_error(f"Upload fehlgeschlagen: {result['data']}")
        return None


def test_book_upload_duplicate(epub_path: str, expected_book_id: str) -> bool:
    """Test 3: Duplikat-Erkennung beim Upload"""
    print_step("Duplikat-Erkennung testen")
    
    result = api_upload("/books/upload", epub_path)
    
    if result["status"] == 200:
        data = result["data"]
        
        if data["is_duplicate"] and data["book_id"] == expected_book_id:
            print_success("Duplikat korrekt erkannt!")
            print(f"   Existierende Book ID: {data['book_id']}")
            return True
        else:
            print_error("Duplikat nicht erkannt")
            return False
    else:
        print_error(f"Request fehlgeschlagen: {result['data']}")
        return False


def test_list_books() -> list:
    """Test 4: Bücher auflisten"""
    print_step("Bücher des Users auflisten")
    
    result = api_get("/books")
    
    if result["status"] == 200:
        data = result["data"]
        print_success(f"{data['total_count']} Bücher gefunden")
        
        for book in data["books"]:
            analyzed = "✓" if book["is_analyzed"] else "○"
            print(f"   [{analyzed}] {book['title']} - {book['author']}")
            print(f"       ID: {book['book_id']}")
            print(f"       Kapitel: {book['chapter_count']}, Kosten: {format_cost(book['total_cost_usd'])}")
        
        return data["books"]
    else:
        print_error(f"Fehler: {result['data']}")
        return []


def test_book_details(book_id: str) -> dict:
    """Test 5: Buch-Details abrufen"""
    print_step("Buch-Details abrufen")
    
    result = api_get(f"/books/{book_id}")
    
    if result["status"] == 200:
        data = result["data"]
        print_success(f"Details für: {data['title']}")
        print(f"   Autor:        {data['author']}")
        print(f"   Kapitel:      {data['chapter_count']}")
        print(f"   Analysiert:   {'Ja' if data['is_analyzed'] else 'Nein'}")
        print(f"   Dateigröße:   {data['file_size_bytes'] / 1024:.1f} KB")
        
        if data["chapters_raw"]:
            print(f"\n   📚 Kapitel (erste 5):")
            for ch in data["chapters_raw"][:5]:
                print(f"      - {ch['title']}")
            if len(data["chapters_raw"]) > 5:
                print(f"      ... und {len(data['chapters_raw']) - 5} weitere")
        
        return data
    else:
        print_error(f"Fehler: {result['data']}")
        return None


def test_get_chapters(book_id: str) -> list:
    """Test 6: Kapitel abrufen (über /epub/chapters)"""
    print_step("Kapitel über EPUB-Endpoint abrufen")
    
    result = api_post("/epub/chapters", {"book_id": book_id})
    
    if result["status"] == 200:
        data = result["data"]
        print_success(f"{data['total_chapters']} Kapitel gefunden")
        
        print("\n   📖 Kapitel:")
        for i, ch in enumerate(data["chapters"][:8]):
            print(f"      {i+1:2d}. {ch['title'][:50]}")
        if len(data["chapters"]) > 8:
            print(f"      ... und {len(data['chapters']) - 8} weitere")
        
        return data["chapters"]
    else:
        print_error(f"Fehler: {result['data']}")
        return []


def test_analyze_chapters_sync(book_id: str) -> dict:
    """Test 7: Kapitel analysieren (synchron)"""
    print_step("KI-Kapitelanalyse (synchron)")
    
    print("   ⏳ Analysiere... (kann einige Sekunden dauern)")
    
    start = time.time()
    result = api_post("/epub/analyze-chapters", {"book_id": book_id})
    elapsed = time.time() - start
    
    if result["status"] == 200:
        data = result["data"]
        
        from_cache = data.get("from_cache", False)
        cache_str = " [aus Cache]" if from_cache else ""
        
        print_success(f"Analyse abgeschlossen in {format_time(elapsed)}{cache_str}")
        print(f"\n   📊 Ergebnis:")
        print(f"      Gesamt:        {data['total_chapters']} Kapitel")
        print(f"      Inhalt:        {data['content_count']} Kapitel ✓")
        print(f"      Zusatzmaterial: {data['supplement_count']} Kapitel ✗")
        
        if not from_cache:
            print(f"\n   💰 Kosten:")
            print(f"      Tokens: {data['total_tokens']:,}")
            print(f"      Kosten: {format_cost(data['analysis_cost_usd'])}")
        
        print(f"\n   ✓ Inhalts-Kapitel:")
        for ch in data["content_chapters"][:5]:
            print(f"      - {ch['title'][:50]}")
        if len(data["content_chapters"]) > 5:
            print(f"      ... und {len(data['content_chapters']) - 5} weitere")
        
        return data
    else:
        print_error(f"Fehler: {result['data']}")
        return None


def test_analyze_chapters_async(book_id: str) -> dict:
    """Test 8: Kapitel analysieren (asynchron mit Polling)"""
    print_step("KI-Kapitelanalyse (asynchron)")
    
    # Job starten
    result = api_post("/epub/analyze-chapters/async", {"book_id": book_id})
    
    if result["status"] != 200:
        print_error(f"Job konnte nicht gestartet werden: {result['data']}")
        return None
    
    job_data = result["data"]
    job_id = job_data["job_id"]
    
    print_success(f"Job gestartet: {job_id}")
    print(f"   Geschätzte Zeit: {job_data.get('estimated_time_seconds', '?')}s")
    print(f"   Queue-Position:  {job_data.get('queue_position', '?')}")
    print("\n   ⏳ Warte auf Abschluss...\n")
    
    # Polling
    status = poll_job_status(job_id, max_wait=300, poll_interval=2)
    
    if status and status["status"] == "completed":
        # Ergebnis holen
        result = api_get(f"/jobs/{job_id}/result")
        if result["status"] == 200:
            data = result["data"]
            
            print(f"\n   📊 Ergebnis:")
            if data.get("content_chapters"):
                print(f"      Inhalt: {len(data['content_chapters'])} Kapitel")
            if data.get("supplement_chapters"):
                print(f"      Zusatz: {len(data['supplement_chapters'])} Kapitel")
            
            print(f"\n   💰 Kosten:")
            costs = data.get("costs", {})
            print(f"      LLM:   {format_cost(costs.get('llm_cost_usd', 0))}")
            print(f"      Total: {format_cost(costs.get('total_cost_usd', 0))}")
            
            return data
    
    return None


def test_book_after_analysis(book_id: str):
    """Test 9: Buch-Details nach Analyse prüfen"""
    print_step("Buch-Details nach Analyse")
    
    result = api_get(f"/books/{book_id}")
    
    if result["status"] == 200:
        data = result["data"]
        
        print_success(f"Buch: {data['title']}")
        print(f"   Analysiert:    {'Ja ✓' if data['is_analyzed'] else 'Nein'}")
        
        if data["is_analyzed"]:
            print(f"   Analysiert am: {data['analyzed_at']}")
            print(f"   Analyse-Kosten: {format_cost(data['analysis_cost_usd'])}")
            
            if data.get("chapters_analyzed"):
                analyzed = data["chapters_analyzed"]
                print(f"\n   📊 Gespeicherte Analyse:")
                print(f"      Inhalt:  {analyzed.get('content_count', '?')} Kapitel")
                print(f"      Zusatz:  {analyzed.get('supplement_count', '?')} Kapitel")
        
        print(f"\n   💰 Gesamtkosten am Buch:")
        print(f"      LLM:   {format_cost(data['total_llm_cost_usd'])}")
        print(f"      TTS:   {format_cost(data['total_tts_cost_usd'])}")
        print(f"      Total: {format_cost(data['total_cost_usd'])}")
        
        return data
    else:
        print_error(f"Fehler: {result['data']}")
        return None


def test_second_analysis(book_id: str):
    """Test 10: Zweite Analyse sollte aus Cache kommen"""
    print_step("Zweite Analyse (sollte aus Cache kommen)")
    
    start = time.time()
    result = api_post("/epub/analyze-chapters", {"book_id": book_id})
    elapsed = time.time() - start
    
    if result["status"] == 200:
        data = result["data"]
        from_cache = data.get("from_cache", False)
        
        if from_cache:
            print_success(f"Ergebnis aus Cache in {elapsed:.2f}s")
            print(f"   Kosten: {format_cost(data['analysis_cost_usd'])} (sollte 0 sein)")
        else:
            print_error("Ergebnis NICHT aus Cache!")
        
        return from_cache
    else:
        print_error(f"Fehler: {result['data']}")
        return False


def test_admin_view():
    """Test 11: Admin sieht alle Bücher"""
    print_step("Admin: Alle Bücher anzeigen")
    
    result = api_get("/books", use_admin=True)
    
    if result["status"] == 200:
        data = result["data"]
        print_success(f"Admin sieht {data['total_count']} Bücher")
        
        for book in data["books"]:
            print(f"   - {book['title']} (User: {book.get('user_id', 'N/A')})")
        
        return True
    else:
        print_error(f"Fehler: {result['data']}")
        return False


def test_delete_book(book_id: str):
    """Test 12: Buch löschen"""
    print_step("Buch löschen")
    
    result = api_delete(f"/books/{book_id}?delete_file=false")
    
    if result["status"] == 200:
        print_success(f"Buch gelöscht: {result['data'].get('message', 'OK')}")
        return True
    else:
        print_error(f"Fehler: {result['data']}")
        return False


# =============================================================================
# MAIN
# =============================================================================

def main():
    """Hauptfunktion - führt alle Tests aus"""
    print_header("🧪 eBook to Audiobook API - Test Suite")
    
    print(f"API URL: {API_URL}")
    print(f"Test-EPUB: {TEST_EPUB}")
    print()
    
    # 1. Health Check
    if not test_health():
        print_error("\nAPI nicht erreichbar! Bitte starten mit: python start_dev.py")
        return
    
    # 2. Prüfe ob Test-EPUB existiert
    test_epub = TEST_EPUB
    if not os.path.exists(test_epub):
        # Suche in uploads/
        alt_path = f"uploads/{TEST_EPUB}"
        if os.path.exists(alt_path):
            test_epub = alt_path
        else:
            print_error(f"\nTest-EPUB nicht gefunden: {test_epub}")
            print_info("Bitte Pfad in test_api.py anpassen oder Datei bereitstellen.")
            return
    
    # 3. Buch hochladen
    book_id = test_book_upload(test_epub)
    if not book_id:
        return
    
    # 4. Duplikat-Test
    test_book_upload_duplicate(test_epub, book_id)
    
    # 5. Bücher auflisten
    test_list_books()
    
    # 6. Buch-Details
    test_book_details(book_id)
    
    # 7. Kapitel abrufen
    chapters = test_get_chapters(book_id)
    
    # 8. Kapitelanalyse
    print("\n" + "=" * 60)
    print("  🤖 KI-Kapitelanalyse")
    print("=" * 60)
    
    run_analysis = False
    run_async = False
    
    if FULL_MODE:
        print("\n--full Modus: Führe synchrone Analyse durch...")
        run_analysis = True
    elif AUTO_MODE:
        print("\n--auto Modus: Überspringe KI-Analyse (kostet Geld)")
    else:
        print("\nDie Analyse kostet ~$0.01-0.10 je nach Kapitelanzahl.")
        choice = input("\nAnalyse durchführen? (j/n/async): ").strip().lower()
        
        if choice in ["j", "y", "ja", "yes"]:
            run_analysis = True
        elif choice == "async":
            run_async = True
    
    if run_analysis:
        # Synchrone Analyse
        analysis = test_analyze_chapters_sync(book_id)
        
        if analysis:
            # 9. Buch nach Analyse prüfen
            test_book_after_analysis(book_id)
            
            # 10. Zweite Analyse (Cache-Test)
            test_second_analysis(book_id)
    
    elif run_async:
        # Asynchrone Analyse
        test_analyze_chapters_async(book_id)
        
        # Buch nach Analyse
        test_book_after_analysis(book_id)
    
    # 11. Admin-View
    if FULL_MODE or AUTO_MODE:
        test_admin_view()
    else:
        print("\n" + "=" * 60)
        choice = input("Admin-View testen? (j/n): ").strip().lower()
        if choice in ["j", "y"]:
            test_admin_view()
    
    # 12. Aufräumen
    if AUTO_MODE or FULL_MODE:
        # Im Auto-Modus nicht löschen
        print_info("Buch bleibt erhalten (--auto/--full Modus)")
    else:
        print("\n" + "=" * 60)
        choice = input("Test-Buch löschen? (j/n): ").strip().lower()
        if choice in ["j", "y"]:
            test_delete_book(book_id)
    
    # Zusammenfassung
    print_header("✅ Tests abgeschlossen!")
    print("📖 API Dokumentation: http://localhost:8000/docs")
    print()


if __name__ == "__main__":
    main()
