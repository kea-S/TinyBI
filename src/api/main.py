import logging

from fastapi import FastAPI

from src.api.routes.vector import router as vector_router
from src.api.routes.query import router as query_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)


def create_app() -> FastAPI:
    app = FastAPI(title="TinyBI API")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(vector_router)
    app.include_router(query_router)
    return app


app = create_app()
