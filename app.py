"""
EmbedForge — Application entry point.

Launches the FastAPI backend server.
Run: uvicorn app:app --reload
Or:  python app.py
"""

import logging
import os

log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format="%(asctime)s %(levelname)-8s [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

from server.main import app  # noqa: F401, E402

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("server.main:app", host="0.0.0.0", port=8000, reload=True)
