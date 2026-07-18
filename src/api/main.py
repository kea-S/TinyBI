import logging

from contextlib import asynccontextmanager
from fastapi import FastAPI

from src.api.routes.vector import router as vector_router
from src.api.routes.query import router as query_router
from src.api.routes.monitoring import router as monitoring_router
from src.api.routes.config import router as config_router, load_config_to_env
from src.config import SQLITE_DATA_PATH, TABLE_DATA_PATH
from src.utils.database import global_database

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger = logging.getLogger(__name__)
    logger.info("Setting up database at %s", TABLE_DATA_PATH)
    global_database.setup_database(str(TABLE_DATA_PATH), str(SQLITE_DATA_PATH))
    logger.info("Database ready")
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="TinyBI API", lifespan=lifespan)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    load_config_to_env()
    
    app.include_router(config_router)
    app.include_router(vector_router)
    app.include_router(query_router)
    app.include_router(monitoring_router)
    return app


app = create_app()
