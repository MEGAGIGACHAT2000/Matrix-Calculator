from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException

from config import Config

_DEV_SECRET = "dev-secret-key-change-me"


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)
    app.json.ensure_ascii = False

    from web.routes import main_bp
    from web.api import api_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix="/api")

    if not app.debug and app.config.get("SECRET_KEY") == _DEV_SECRET:
        raise RuntimeError(
            "SECRET_KEY не установлен. Задайте переменную окружения "
            "SECRET_KEY перед запуском в production-режиме."
        )
    
    @app.errorhandler(HTTPException)
    def handle_http_exception(e: HTTPException):
        return jsonify({
            "ok": False,
            "error": e.description,
            "error_type": e.name,
        }), e.code

    @app.errorhandler(Exception)
    def handle_unexpected_exception(e: Exception):
        app.logger.exception("Unhandled server error")
        return jsonify({
            "ok": False,
            "error": "Внутренняя ошибка сервера",
            "error_type": "ServerError",
        }), 500

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=Config.DEBUG)