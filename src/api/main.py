import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

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

    # --- SPA Static File Serving ---
    frontend_dist = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist")
    
    if os.path.exists(frontend_dist):
        # Serve the /assets/ folder (JS, CSS, images) directly
        assets_path = os.path.join(frontend_dist, "assets")
        if os.path.exists(assets_path):
            app.mount("/assets", StaticFiles(directory=assets_path), name="assets")
        
        # Catch-all route for React Router fallback
        @app.get("/{full_path:path}", include_in_schema=False)
        async def serve_spa(full_path: str):
            file_path = os.path.join(frontend_dist, full_path)
            # If requesting a specific file (e.g. favicon.svg), serve it directly
            if full_path and os.path.isfile(file_path):
                return FileResponse(file_path)
            # Otherwise fallback to React's index.html
            return FileResponse(os.path.join(frontend_dist, "index.html"))
    else:
        logger = logging.getLogger(__name__)
        logger.warning("Frontend dist folder not found. API running without UI.")

    return app


app = create_app()
