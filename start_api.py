"""
Hilfsskript zum Starten der FastAPI-Anwendung
"""
import uvicorn

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 Starte eBook to Audiobook API")
    print("=" * 60)
    print("\n📖 Dokumentation verfügbar unter:")
    print("   - Swagger UI: http://localhost:8000/docs")
    print("   - ReDoc:      http://localhost:8000/redoc")
    print("\n" + "=" * 60 + "\n")
    
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

