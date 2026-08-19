"""
FastAPI application — REST + WebSocket API for EmbedForge.
"""

from __future__ import annotations

import importlib
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.settings import AppSettings
from plugins.base import PluginRegistry

logger = logging.getLogger(__name__)

_registry: PluginRegistry | None = None


def get_registry() -> PluginRegistry:
    if _registry is None:
        raise RuntimeError("Plugin registry not initialized")
    return _registry


def _load_plugins(settings: AppSettings) -> PluginRegistry:
    registry = PluginRegistry()
    plugin_dir = settings.plugins_dir
    logger.info("Scanning plugins directory: %s", plugin_dir)
    for candidate in plugin_dir.iterdir():
        if candidate.is_dir() and (candidate / "__init__.py").exists():
            try:
                module = importlib.import_module(f"plugins.{candidate.name}")
                if hasattr(module, "register"):
                    module.register(registry)
                    logger.info("Loaded plugin: %s", candidate.name)
            except Exception as e:
                logger.warning("Failed to load plugin %s: %s", candidate.name, e)

    if settings.plugin_name and registry._plugins:
        try:
            registry.activate(settings.plugin_name)
            logger.info("Activated plugin: %s", settings.plugin_name)
        except ValueError:
            first = next(iter(registry._plugins))
            registry.activate(first)
            logger.warning("Plugin '%s' not found, activated fallback: %s", settings.plugin_name, first)

    return registry


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _registry
    settings = AppSettings()

    from config.logging_config import configure_logging
    configure_logging(level=settings.log_level)

    _registry = _load_plugins(settings)
    logger.info(f"EmbedForge started — plugin: {_registry.active.name if _registry.active else 'none'}")
    yield
    _registry = None


app = FastAPI(
    title="EmbedForge",
    description="Agentic AI workflow for embedded C code generation",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from server.routes import plugins, workflow, sdk, flash, cost  # noqa: E402
from server import ws  # noqa: E402
from server.activity_log import activity_log  # noqa: E402

app.include_router(workflow.router, prefix="/api/workflow", tags=["workflow"])
app.include_router(plugins.router, prefix="/api/plugins", tags=["plugins"])
app.include_router(sdk.router, prefix="/api/sdk", tags=["sdk"])
app.include_router(flash.router, prefix="/api/flash", tags=["flash"])
app.include_router(cost.router, prefix="/api/cost", tags=["cost"])
app.include_router(ws.router)


@app.get("/health")
async def health():
    return {"status": "ok", "plugin": _registry.active.name if _registry and _registry.active else None}


@app.get("/api/logs/stream")
async def log_stream():
    from starlette.responses import StreamingResponse
    return StreamingResponse(activity_log.subscribe(), media_type="text/event-stream")


@app.get("/api/logs/recent")
async def recent_logs():
    return activity_log.get_recent(50)
