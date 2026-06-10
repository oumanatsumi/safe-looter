from flask import Blueprint, request, jsonify
import os
import time
import random

from config import DB_PATH
from database import write_with_retry, get_game_config
from game.touchi import load_items, get_item_value, create_safe_layout, build_touchi_result
from game.events import check_random_events
from game.economy import add_items_to_collection, get_economy

touchi_bp = Blueprint("touchi", __name__)


def _load_game_rates():
    """Read drop rates and cooldown from system_config."""
    cfg = get_game_config(DB_PATH)
    normal_rates = {
        "blue": float(cfg["rate_blue"]),
        "purple": float(cfg["rate_purple"]),
        "gold": float(cfg["rate_gold"]),
        "red": float(cfg["rate_red"]),
    }
    menggong_rates = {
        "purple": float(cfg["menggong_rate_purple"]),
        "gold": float(cfg["menggong_rate_gold"]),
        "red": float(cfg["menggong_rate_red"]),
    }
    cooldown = (int(cfg["cooldown_min"]), int(cfg["cooldown_max"]))
    return normal_rates, menggong_rates, cooldown


@touchi_bp.route("/touchi", methods=["POST"])
def do_touchi():
    """Perform one touchi (open safe box)."""
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id", "default")

    # Check / resolve menggong status
    eco = get_economy(user_id, DB_PATH)
    now = int(time.time())
    menggong = bool(eco["menggong_active"] and now < eco.get("menggong_end_time", 0))

    # Check auto-touchi conflict
    if eco.get("auto_touchi_active"):
        return jsonify({"ok": False, "message": "自动偷吃进行中，无法手动偷吃。请先关闭自动偷吃。"})

    # Check cooldown
    last_time = eco.get("last_touchi_time", 0)
    last_cd = eco.get("touchi_cooldown", 0)
    if last_time and last_cd:
        remaining = last_time + last_cd - now
        if remaining > 0:
            return jsonify({
                "ok": False,
                "message": f"冷却中，剩余 {remaining} 秒",
                "cooldown_remaining": remaining,
            })

    # Generate the safe box layout
    items = load_items()
    normal_rates, menggong_rates, (cd_min, cd_max) = _load_game_rates()
    time_multiplier = random.uniform(0.6, 1.4)

    placed_items, _, _, region_w, region_h = create_safe_layout(
        items, menggong_mode=menggong, grid_size=eco["grid_size"],
        time_multiplier=time_multiplier,
        custom_normal_rates=normal_rates,
        custom_menggong_rates=menggong_rates)

    if not placed_items:
        return jsonify({"ok": False, "message": "没有获得任何物品"})

    # Build frontend-ready result (grid layout, items, expression)
    result = build_touchi_result(placed_items, eco["grid_size"], region_w, region_h)

    total_value = result["total_value"]

    # Check random events
    triggered, evt_type, final_items, final_value, evt_msg, extra = \
        check_random_events(placed_items, total_value)

    # Handle event side effects
    event_extra = None
    cooldown_modifier = 1.0

    if triggered:
        if evt_type == "genius_kick":
            # Items shown but not saved
            pass
        elif evt_type == "genius_fine":
            add_items_to_collection(user_id, final_items, DB_PATH)
            event_extra = {"fine_amount": extra}
        elif evt_type == "passerby_mouse" and extra:
            gold_item_base = os.path.splitext(os.path.basename(extra))[0]
            def _add_gold(c):
                c.execute(
                    "INSERT OR IGNORE INTO user_touchi_collection (user_id, item_name, item_level) VALUES (?,?,?)",
                    (user_id, gold_item_base, "gold"))
                c.execute(
                    "UPDATE user_economy SET warehouse_value = warehouse_value + ? WHERE user_id=?",
                    (get_item_value(gold_item_base), user_id))
            write_with_retry(DB_PATH, _add_gold)
            # Prepend gifted gold item to frontend items list
            result["items"].insert(0, {
                "name": gold_item_base, "level": "gold", "size": "1x1",
                "value": get_item_value(gold_item_base),
                "image_url": f"/resources/items/{os.path.basename(extra)}",
                "x": 0, "y": 0, "width": 1, "height": 1,
                "rotated": False, "search_duration_ms": 1000,
                "from_event": True,
            })
            final_value += get_item_value(gold_item_base)
            add_items_to_collection(user_id, final_items, DB_PATH)
            event_extra = {"gifted_gold": gold_item_base}
            # Rebuild result with updated items
            result["total_value"] = final_value
            result["highest_level"] = "gold" if result["highest_level"] not in ("red", "gold") else result["highest_level"]
        elif evt_type == "system_compensation":
            add_items_to_collection(user_id, final_items, DB_PATH)
            cooldown_modifier = extra or 0.5
            event_extra = {"cooldown_modifier": cooldown_modifier}
        elif evt_type == "broken_liutao":
            add_items_to_collection(user_id, final_items, DB_PATH)
            dur = extra or 60
            def _activate(c):
                c.execute(
                    "UPDATE user_economy SET menggong_active=1, menggong_end_time=? WHERE user_id=?",
                    (int(time.time()) + dur, user_id))
            write_with_retry(DB_PATH, _activate)
            event_extra = {"menggong_duration": dur}
        elif evt_type == "noob_teammate":
            add_items_to_collection(user_id, final_items, DB_PATH)
            cooldown_modifier = extra or 2.0
            event_extra = {"cooldown_modifier": cooldown_modifier}
        else:
            add_items_to_collection(user_id, final_items, DB_PATH)
    else:
        add_items_to_collection(user_id, placed_items, DB_PATH)

    display_value = final_value if triggered and evt_type != "genius_kick" else total_value
    wait_time = int(random.uniform(cd_min, cd_max) * cooldown_modifier)

    # Persist cooldown to database
    def _save_cd(c):
        c.execute(
            "UPDATE user_economy SET last_touchi_time=?, touchi_cooldown=? WHERE user_id=?",
            (now, wait_time, user_id))
    write_with_retry(DB_PATH, _save_cd)

    # Total search animation duration (frontend uses this for overall timing)
    total_search_ms = sum(it.get("search_duration_ms", 600) for it in result["items"])

    return jsonify({
        "ok": True,
        "items": result["items"],
        "grid_size": result["grid_size"],
        "region_width": result["region_width"],
        "region_height": result["region_height"],
        "expression": result["expression"],
        "total_search_ms": total_search_ms,
        "total_value": display_value,
        "total_profit": 0 if (triggered and evt_type == "genius_kick") else total_value,
        "highest_level": result["highest_level"],
        "event": {
            "triggered": triggered,
            "type": evt_type,
            "message": evt_msg,
            "extra": event_extra,
        } if triggered else None,
        "menggong_active": menggong,
        "cooldown_modifier": cooldown_modifier,
        "wait_time": wait_time,
    })
