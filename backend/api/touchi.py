from flask import Blueprint, request, jsonify
import os
import time
import random
import json

from config import DB_PATH
from database import get_connection, write_with_retry, get_game_config
from game.touchi import generate_safe_image, load_items, get_item_value
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

    # Generate the safe box
    normal_rates, menggong_rates, (cd_min, cd_max) = _load_game_rates()
    time_multiplier = random.uniform(0.6, 1.4)
    image_path, placed_items, total_frames = generate_safe_image(
        menggong_mode=menggong, grid_size=eco["grid_size"],
        time_multiplier=time_multiplier,
        custom_normal_rates=normal_rates,
        custom_menggong_rates=menggong_rates)
    # GIF duration: total_frames * 150ms
    gif_duration_ms = total_frames * 150

    if not image_path or not os.path.exists(image_path):
        return jsonify({"ok": False, "message": "生成图片失败，请重试"})

    if not placed_items:
        return jsonify({"ok": False, "message": "没有获得任何物品"})

    total_value = sum(
        p["item"].get("value", get_item_value(
            os.path.splitext(os.path.basename(p["item"]["path"]))[0]))
        for p in placed_items)

    # Check random events
    triggered, evt_type, final_items, final_value, evt_msg, extra = \
        check_random_events(placed_items, total_value)

    # Build result items list for frontend
    def make_item_info(p):
        item = p["item"]
        name = os.path.splitext(os.path.basename(item["path"]))[0]
        return {
            "name": name,
            "level": item["level"],
            "size": item["size"],
            "value": item.get("value", get_item_value(name)),
            "image_url": f"/resources/items/{os.path.basename(item['path'])}",
        }

    items_info = [make_item_info(p) for p in (final_items if final_items else placed_items)]
    # Sort: red before gold before purple before blue, then by value descending
    level_order = {"red": 0, "gold": 1, "purple": 2, "blue": 3}
    items_info.sort(key=lambda x: (level_order.get(x["level"], 9), -x["value"]))

    # Handle event side effects
    event_extra = None
    cooldown_modifier = 1.0

    if triggered:
        if evt_type == "genius_kick":
            # Items shown but not saved
            pass
        elif evt_type == "genius_fine":
            # Items saved; value already adjusted in events.py
            add_items_to_collection(user_id, final_items, DB_PATH)
            event_extra = {"fine_amount": extra}
        elif evt_type == "passerby_mouse" and extra:
            # Add the gifted gold item to the front of the list
            gold_name = os.path.splitext(os.path.basename(extra))[0]
            # Add the extra gold item to final_items
            gold_item_base = os.path.splitext(os.path.basename(extra))[0]
            # Record the gold item
            def _add_gold(c):
                c.execute(
                    "INSERT OR IGNORE INTO user_touchi_collection (user_id, item_name, item_level) VALUES (?,?,?)",
                    (user_id, gold_item_base, "gold"))
                c.execute(
                    "UPDATE user_economy SET warehouse_value = warehouse_value + ? WHERE user_id=?",
                    (get_item_value(gold_item_base), user_id))
            write_with_retry(DB_PATH, _add_gold)
            items_info.insert(0, {
                "name": gold_item_base, "level": "gold", "size": "1x1",
                "value": get_item_value(gold_item_base),
                "image_url": f"/resources/items/{os.path.basename(extra)}",
                "from_event": True,
            })
            final_value += get_item_value(gold_item_base)
            add_items_to_collection(user_id, final_items, DB_PATH)
            event_extra = {"gifted_gold": gold_name}
        elif evt_type == "system_compensation":
            add_items_to_collection(user_id, final_items, DB_PATH)
            cooldown_modifier = extra or 0.5
            event_extra = {"cooldown_modifier": cooldown_modifier}
        elif evt_type == "broken_liutao":
            add_items_to_collection(user_id, final_items, DB_PATH)
            # Activate menggong for the returned duration
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
            # Normal events — save items
            add_items_to_collection(user_id, final_items, DB_PATH)
    else:
        # No event — save normally
        add_items_to_collection(user_id, placed_items, DB_PATH)

    # Relative image URL
    rel_path = "output/" + os.path.basename(image_path)

    display_value = final_value if triggered and evt_type != "genius_kick" else total_value

    return jsonify({
        "ok": True,
        "image_url": f"/{rel_path}",
        "items": items_info,
        "total_value": display_value,
        "total_profit": 0 if (triggered and evt_type == "genius_kick") else total_value,
        "highest_level": max((it["level"] for it in items_info),
                             key=lambda l: {"blue": 1, "purple": 2, "gold": 3, "red": 4}.get(l, 0)),
        "gif_duration_ms": gif_duration_ms,
        "event": {
            "triggered": triggered,
            "type": evt_type,
            "message": evt_msg,
            "extra": event_extra,
        } if triggered else None,
        "menggong_active": menggong,
        "cooldown_modifier": cooldown_modifier,
        "wait_time": int(random.uniform(cd_min, cd_max) * cooldown_modifier),
    })
