"""Entrypoint for the hactl-companion add-on."""

from aiohttp import web

from companion.server import create_app


def main() -> None:
    app = create_app()
    web.run_app(app, host="0.0.0.0", port=9100)


if __name__ == "__main__":
    main()
