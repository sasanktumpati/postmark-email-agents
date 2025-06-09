import asyncio
import logging
import sys
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.apis.v1 import router as api_v1_router
from app.core.config import settings
from app.core.db import init_db_async


def setup_logging():
    """Configure logging for the application."""

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)

    logging.getLogger("app.modules.actionables").setLevel(logging.DEBUG)
    logging.getLogger("app.modules.actionables.agents").setLevel(logging.DEBUG)
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("fastapi").setLevel(logging.INFO)

    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    print("Logging configuration completed - Agent logs will now be visible")


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Starting application with enhanced logging")

    await asyncio.sleep(2)
    try:
        await init_db_async()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise

    yield

    from app.core.db.database import close_db

    try:
        await close_db()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Error closing database: {e}")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Postmark Email Agents",
        description="API for handling Postmark email webhooks with AsyncPG support",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_v1_router)

    app.mount("/attachments", StaticFiles(directory="attachments"), name="attachments")

    return app


app = create_app()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    args = parser.parse_args()

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=35000,
        reload=settings.debug or args.reload,
        log_level="debug" if settings.debug else "info",
    )
