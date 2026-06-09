from flask import Blueprint, request, jsonify
import time

from config import DB_PATH
from game.economy import (
    get_economy, activate_menggong, upgrade_teqin,
    start_auto_touchi, stop_auto_touchi,
)

economy_bp = Blueprint("economy", __name__)


@economy_bp.route("/economy/<user_id>", methods=["GET"])
def get_user_economy(user_id):
    eco = get_economy(user_id, DB_PATH)
    now = int(time.time())
    menggong_remaining = 0
    if eco["menggong_active"] and now < eco["menggong_end_time"]:
        menggong_remaining = eco["menggong_end_time"] - now

    return jsonify({
        "ok": True,
        "warehouse_value": eco["warehouse_value"],
        "teqin_level": eco["teqin_level"],
        "grid_size": eco["grid_size"],
        "menggong_active": eco["menggong_active"] and menggong_remaining > 0,
        "menggong_remaining": menggong_remaining,
        "auto_touchi_active": bool(eco.get("auto_touchi_active")),
        "auto_touchi_start_time": eco.get("auto_touchi_start_time", 0),
        "auto_touchi_red_count": eco.get("auto_touchi_red_count", 0),
    })


@economy_bp.route("/menggong", methods=["POST"])
def do_menggong():
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id", "default")
    ok, msg = activate_menggong(user_id, DB_PATH)
    return jsonify({"ok": ok, "message": msg})


@economy_bp.route("/upgrade", methods=["POST"])
def do_upgrade():
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id", "default")
    ok, msg = upgrade_teqin(user_id, DB_PATH)
    return jsonify({"ok": ok, "message": msg})


@economy_bp.route("/auto-touchi/start", methods=["POST"])
def do_auto_start():
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id", "default")
    ok, msg = start_auto_touchi(user_id, DB_PATH)
    return jsonify({"ok": ok, "message": msg})


@economy_bp.route("/auto-touchi/stop", methods=["POST"])
def do_auto_stop():
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id", "default")
    ok, msg = stop_auto_touchi(user_id, DB_PATH)
    return jsonify({"ok": ok, "message": msg})
