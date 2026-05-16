from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from jez_face_api.config import settings
from jez_face_api.routes.faces import router as faces_router
from jez_face_api.routes.health import router as health_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="JEZ Face Recognition API",
        description="Private face identity service for JEZ attendance",
        version="0.1.0",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_router)
    app.include_router(faces_router)
    return app


app = create_app()

