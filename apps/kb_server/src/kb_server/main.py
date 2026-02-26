import uvicorn

from kb_server.config import Settings
from kb_server.http import create_app


def main() -> None:
    settings = Settings()
    app = create_app(settings)
    uvicorn.run(app, host=settings.app_host, port=settings.app_port)


if __name__ == "__main__":
    main()
