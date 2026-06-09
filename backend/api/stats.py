from flask import Blueprint, jsonify
from config import DB_PATH
from database import get_connection

stats_bp = Blueprint("stats", __name__)


@stats_bp.route("/leaderboard", methods=["GET"])
def get_leaderboard():
    conn = get_connection(DB_PATH)
    try:
        # Top 10 by collection count
        coll_rows = conn.execute(
            "SELECT user_id, COUNT(DISTINCT item_name) as cnt "
            "FROM user_touchi_collection GROUP BY user_id "
            "ORDER BY cnt DESC LIMIT 10"
        ).fetchall()

        # Top 10 by warehouse value
        val_rows = conn.execute(
            "SELECT user_id, warehouse_value FROM user_economy "
            "WHERE warehouse_value > 0 ORDER BY warehouse_value DESC LIMIT 10"
        ).fetchall()

        return jsonify({
            "ok": True,
            "collection_top": [
                {"user_id": r["user_id"], "count": r["cnt"]} for r in coll_rows
            ],
            "warehouse_top": [
                {"user_id": r["user_id"], "value": r["warehouse_value"]} for r in val_rows
            ],
        })
    finally:
        conn.close()


@stats_bp.route("/items", methods=["GET"])
def list_items():
    """List all available items (for the collection checklist)."""
    from game.touchi import load_items
    all_items = load_items()
    gold_red = [i for i in all_items if i["level"] in ("gold", "red")]
    result = []
    seen = set()
    for item in gold_red:
        if item["base_name"] not in seen:
            seen.add(item["base_name"])
            result.append({
                "name": item["base_name"],
                "level": item["level"],
                "value": item["value"],
                "size": item["size"],
                "image_url": f"/resources/items/{item['base_name']}.png",
            })
    return jsonify({"ok": True, "items": result})
