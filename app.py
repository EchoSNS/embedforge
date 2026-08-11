"""
EmbedForge — Application entry point.

Launches the FastAPI backend server.
Run: uvicorn app:app --reload
Or:  python app.py
"""

from server.main import app  # noqa: F401

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("server.main:app", host="0.0.0.0", port=8000, reload=True)
