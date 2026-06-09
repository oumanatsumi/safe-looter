import os
import sys
from flask import Flask, send_from_directory
from config import DB_PATH, OUTPUT_DIR
from database import init_db

def create_app():
    app = Flask(
        __name__,
        static_folder="../frontend",
        static_url_path="",
    )

    # Init database tables
    init_db(DB_PATH)

    # Register API blueprints
    from api.touchi import touchi_bp
    from api.collection import collection_bp
    from api.economy import economy_bp
    from api.stats import stats_bp
    from api.admin import admin_bp

    app.register_blueprint(touchi_bp, url_prefix="/api")
    app.register_blueprint(collection_bp, url_prefix="/api")
    app.register_blueprint(economy_bp, url_prefix="/api")
    app.register_blueprint(stats_bp, url_prefix="/api")
    app.register_blueprint(admin_bp, url_prefix="/api")

    # Serve generated GIF/PNG output
    @app.route("/output/<path:filename>")
    def serve_output(filename):
        return send_from_directory(OUTPUT_DIR, filename)

    # Serve item images
    from config import ITEMS_DIR, EXPRESSIONS_DIR

    @app.route("/resources/items/<path:filename>")
    def serve_items(filename):
        return send_from_directory(ITEMS_DIR, filename)

    @app.route("/resources/expressions/<path:filename>")
    def serve_expressions(filename):
        return send_from_directory(EXPRESSIONS_DIR, filename)

    # SPA fallback — serve index.html for any non-API route
    @app.route("/")
    @app.route("/<path:path>")
    def serve_spa(path=""):
        if path.startswith("api/") or path.startswith("output/") or path.startswith("resources/"):
            return app.response_class(status=404)
        return send_from_directory(app.static_folder, "index.html")

    # Start auto-touchi scheduler in a background thread
    from game.economy import start_scheduler
    start_scheduler(DB_PATH)

    return app


if __name__ == "__main__":
    from config import HOST, PORT
    app = create_app()
    app.run(host=HOST, port=PORT, debug=True)
