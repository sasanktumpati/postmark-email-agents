import asyncio
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.apis.v1 import router as api_v1_router
from app.core.config import settings
from app.core.db import init_db
from app.core.logger import get_logger, set_log_level
from app.core.middleware.auth import AuthMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger = get_logger("main")

    if settings.debug:
        set_log_level("DEBUG")
    else:
        set_log_level("INFO")

    logger.info("Starting postmark-email-agents application with centralized logging")
    logger.info(
        "Log files: logs/app.log (main), logs/errors.log (errors), logs/security.log (security)"
    )

    await asyncio.sleep(2)
    try:
        await init_db()
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
        title="Actionable Mail",
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

    app.add_middleware(AuthMiddleware)

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
