from flask import Blueprint, jsonify
from config import DB_PATH
from database import get_connection
from game.touchi import get_item_value

collection_bp = Blueprint("collection", __name__)


@collection_bp.route("/collection/<user_id>", methods=["GET"])
def get_collection(user_id):
    """Return user's collected gold/red items, sorted by value descending."""
    conn = get_connection(DB_PATH)
    try:
        rows = conn.execute(
            "SELECT DISTINCT item_name, item_level FROM user_touchi_collection "
            "WHERE user_id=? AND item_level IN ('gold','red')",
            (user_id,)
        ).fetchall()

        gold_total = 0
        red_total = 0

        items = []
        for r in rows:
            level = r["item_level"]
            value = get_item_value(r["item_name"])
            items.append({
                "name": r["item_name"],
                "level": level,
                "value": value,
                "image_url": f"/resources/items/{r['item_name']}.png",
            })
            if level == "gold":
                gold_total += 1
            elif level == "red":
                red_total += 1

        # Sort: red before gold, then by value descending within each tier
        level_order = {"red": 0, "gold": 1}
        items.sort(key=lambda x: (level_order.get(x["level"], 9), -x["value"]))

        return jsonify({
            "ok": True,
            "items": items,
            "gold_count": gold_total,
            "red_count": red_total,
            "total_count": gold_total + red_total,
        })
    finally:
        conn.close()
