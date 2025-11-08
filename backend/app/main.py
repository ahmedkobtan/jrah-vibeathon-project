from fastapi import FastAPI

from .routers import estimate, insurance, query


def create_app() -> FastAPI:
    app = FastAPI(title="TransparentCare API Gateway", version="0.1.0")
    app.include_router(query.router)
    app.include_router(insurance.router)
    app.include_router(estimate.router)
    return app


app = create_app()
