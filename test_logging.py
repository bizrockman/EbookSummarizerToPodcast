"""
Einfaches Test-Script um das Logging der API zu demonstrieren
"""
import requests
import time

API_URL = "http://localhost:8000"
API_KEY = "dummy-api-key-12345"
headers = {"X-API-Key": API_KEY}


def test_logging_examples():
    """Verschiedene Requests um Logging zu demonstrieren"""
    
    print("=" * 60)
    print("  Test: API Logging Demo")
    print("=" * 60)
    print("\n👀 Schauen Sie in der API-Console, um die Logs zu sehen!\n")
    
    # Test 1: Erfolgreicher Request
    print("1️⃣  Teste erfolgreichen Request (Health Check)...")
    response = requests.get(f"{API_URL}/health")
    print(f"   → Status: {response.status_code}")
    print(f"   → Request-ID: {response.headers.get('X-Request-ID', 'N/A')}")
    time.sleep(1)
    
    # Test 2: Request mit API Key
    print("\n2️⃣  Teste Request mit API Key (EPUB Validation)...")
    response = requests.post(
        f"{API_URL}/epub/validate",
        json={"file_path": "uploads/Blitzscaling.epub"},
        headers=headers
    )
    print(f"   → Status: {response.status_code}")
    print(f"   → Request-ID: {response.headers.get('X-Request-ID', 'N/A')}")
    time.sleep(1)
    
    # Test 3: 404 Error
    print("\n3️⃣  Teste 404 Error (nicht existierender Endpoint)...")
    response = requests.get(
        f"{API_URL}/does-not-exist",
        headers=headers
    )
    print(f"   → Status: {response.status_code}")
    print(f"   → Request-ID: {response.headers.get('X-Request-ID', 'N/A')}")
    time.sleep(1)
    
    # Test 4: 401 Error (ungültiger API Key)
    print("\n4️⃣  Teste 401 Error (ungültiger API Key)...")
    response = requests.post(
        f"{API_URL}/epub/validate",
        json={"file_path": "test.epub"},
        headers={"X-API-Key": "invalid-key-123"}
    )
    print(f"   → Status: {response.status_code}")
    print(f"   → Request-ID: {response.headers.get('X-Request-ID', 'N/A')}")
    time.sleep(1)
    
    # Test 5: 400 Error (fehlende Datei)
    print("\n5️⃣  Teste 400 Error (nicht existierende Datei)...")
    response = requests.post(
        f"{API_URL}/epub/validate",
        json={"file_path": "/non/existent/file.epub"},
        headers=headers
    )
    print(f"   → Status: {response.status_code}")
    print(f"   → Request-ID: {response.headers.get('X-Request-ID', 'N/A')}")
    time.sleep(1)
    
    # Test 6: Mehrere schnelle Requests
    print("\n6️⃣  Teste mehrere schnelle Requests (5x Health Check)...")
    for i in range(5):
        response = requests.get(f"{API_URL}/health")
        print(f"   → Request {i+1}: {response.status_code} | Request-ID: {response.headers.get('X-Request-ID', 'N/A')[:8]}...")
        time.sleep(0.2)
    
    print("\n" + "=" * 60)
    print("  ✅ Test abgeschlossen!")
    print("=" * 60)
    print("\n💡 Tipp: Die API-Console sollte jetzt detaillierte Logs zeigen:")
    print("   - Eingehende Requests mit ➡️")
    print("   - Erfolgreiche Responses mit ✅")
    print("   - Errors mit ⚠️ oder ❌")
    print("   - Request-IDs für Tracking")
    print("   - Antwortzeiten in ms")
    print()


if __name__ == "__main__":
    try:
        test_logging_examples()
    except requests.exceptions.ConnectionError:
        print("\n❌ API ist nicht erreichbar!")
        print("Bitte starten Sie die API mit: python start_api.py")

