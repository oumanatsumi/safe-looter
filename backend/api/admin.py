from flask import Blueprint, request, jsonify

from config import DB_PATH, ADMIN_TOKEN
from database import get_game_config, save_game_config

admin_bp = Blueprint("admin", __name__)


def _get_token():
    """Extract token from JSON body, form, or query string."""
    data = request.get_json(silent=True) or {}
    token = data.get("token", "")
    if not token:
        token = request.args.get("token", "")
    if not token:
        token = (request.form or {}).get("token", "")
    return token


@admin_bp.route("/admin/auth", methods=["POST"])
def admin_auth():
    token = _get_token()
    if token == ADMIN_TOKEN:
        return jsonify({"ok": True})
    return jsonify({"ok": False, "message": "token无效"})


@admin_bp.route("/admin/config", methods=["GET"])
def admin_get_config():
    if _get_token() != ADMIN_TOKEN:
        return jsonify({"ok": False, "message": "token无效"})
    cfg = get_game_config(DB_PATH)
    return jsonify({"ok": True, "config": cfg})


@admin_bp.route("/admin/config", methods=["POST"])
def admin_save_config():
    data = request.get_json(silent=True) or {}
    token = data.get("token", "")
    updates = data.get("config", {})
    if not updates:
        return jsonify({"ok": False, "message": "没有配置数据"})

    ok, msg = save_game_config(DB_PATH, updates, token)
    return jsonify({"ok": ok, "message": msg})
