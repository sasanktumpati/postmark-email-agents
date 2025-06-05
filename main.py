import asyncio
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.apis.v1 import router as api_v1_router
from app.core.db import init_db_async


@asynccontextmanager
async def lifespan(app: FastAPI):
    await asyncio.sleep(2)
    try:
        await init_db_async()
        print("Database initialized successfully")
    except Exception as e:
        print(f"Database initialization failed: {e}")
        raise

    yield

    from app.core.db.database import close_db

    try:
        await close_db()
        print("Database connections closed")
    except Exception as e:
        print(f"Error closing database: {e}")


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


def main():
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=35000,
        reload=True,
    )


if __name__ == "__main__":
    main()
