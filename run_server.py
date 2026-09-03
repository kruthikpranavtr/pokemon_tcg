"""
Launcher for the Pokemon TCG AI Engine Web Dashboard & REST API
"""
import sys
import uvicorn

if __name__ == "__main__":
    print("=" * 70)
    print("  POKEMON TCG AI ENGINE: WEB DASHBOARD & REST API")
    print("=" * 70)
    print("\nStarting local server...")
    print("--> Open in browser: http://127.0.0.1:8000")
    print("--> Interactive API Docs: http://127.0.0.1:8000/docs")
    print("\nPress Ctrl+C to stop the server.\n")
    uvicorn.run("src.api:app", host="127.0.0.1", port=8000, reload=True)
