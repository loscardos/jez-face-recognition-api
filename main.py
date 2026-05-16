import uvicorn

from jez_face_api.app import create_app
from jez_face_api.config import settings

app = create_app()


if __name__ == "__main__":
    uvicorn.run(app, host=settings.HOST, port=settings.PORT, log_level="info")
