from typing import Any, Dict

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.core.config import settings
from app.core.db.utils import check_database_connection, get_database_info
from app.core.utils.response import BaseResponse

router: APIRouter = APIRouter(prefix="/health", tags=["health"])


class DatabaseHealthResponse(BaseModel):
    connected: bool
    info: Dict[str, Any]


class HealthResponse(BaseModel):
    overall_status: str
    version: str
    database_health: DatabaseHealthResponse
    configuration: Dict[str, Any]


@router.get(
    "/",
    response_model=BaseResponse[HealthResponse],
    responses={500: {"model": BaseResponse}},
)
async def health_check() -> JSONResponse:
    try:
        db_connected = await check_database_connection()

        if db_connected:
            db_info_dict = await get_database_info()
        else:
            db_info_dict = {
                "status": "disconnected",
                "message": "Failed to connect to the database.",
            }

        db_health_details = DatabaseHealthResponse(
            connected=db_connected, info=db_info_dict
        )

        app_health_data = HealthResponse(
            overall_status="healthy" if db_connected else "unhealthy",
            version=settings.app_version,
            database_health=db_health_details,
            configuration={
                "app_name": settings.app_name,
                "debug": settings.debug,
                "postgres_host": settings.postgres_host,
                "postgres_port": settings.postgres_port,
                "postgres_db": settings.postgres_db,
                "pool_size": settings.db_pool_size,
                "max_overflow": settings.db_max_overflow,
            },
        )

        status_code = 200 if db_connected else 503
        return BaseResponse.success(
            message="Health check performed successfully.",
            data=app_health_data,
            status_code=status_code,
        )

    except Exception as e:
        return BaseResponse.error(
            message=f"Health check internal server error: {str(e)}",
            status_code=500,
        )
