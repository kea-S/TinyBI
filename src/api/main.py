from fastapi import FastAPI

from src.api.routes.vector import router as vector_router


def create_app() -> FastAPI:
    app = FastAPI(title="TinyBI API")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(vector_router)
    return app


app = create_app()
