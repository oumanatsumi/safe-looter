"""Economy helpers and auto-touchi scheduler.

No AstrBot dependencies — pure Python.  The Flask app imports these.
"""
import time
import os
import threading
import sqlite3

from config import (
    MENGONG_COST, MENGONG_BASE_DURATION, AUTO_TOUCHI_INTERVAL,
    AUTO_TOUCHI_MAX_DURATION, MAX_TEQIN_LEVEL, DB_PATH,
)
from database import get_connection, write_with_retry

# Upgrade cost table — index = current level -> cost to reach next level
UPGRADE_COSTS = [640_000, 3_200_000, 25_600_000, 64_800_000, 102_400_000]


def grid_size_for_level(level):
    """Map teqin level to grid size."""
    return 2 + level if level > 0 else 2


def get_economy(user_id, db_path):
    """Get economy dict for a user, creating one if absent."""
    conn = get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT warehouse_value, teqin_level, grid_size, menggong_active, "
            "menggong_end_time, auto_touchi_active, auto_touchi_start_time, "
            "auto_touchi_red_count FROM user_economy WHERE user_id=?",
            (user_id,)
        ).fetchone()

        if row:
            return dict(row)

        # New user
        base = conn.execute(
            "SELECT config_value FROM system_config WHERE config_key='base_teqin_level'"
        ).fetchone()
        base_level = int(base["config_value"]) if base else 0
        gs = grid_size_for_level(base_level)
        conn.execute(
            "INSERT INTO user_economy (user_id, teqin_level, grid_size) VALUES (?,?,?)",
            (user_id, base_level, gs))
        conn.commit()
        return {
            "warehouse_value": 0, "teqin_level": base_level, "grid_size": gs,
            "menggong_active": 0, "menggong_end_time": 0,
            "auto_touchi_active": 0, "auto_touchi_start_time": 0,
            "auto_touchi_red_count": 0,
        }
    finally:
        conn.close()


def add_items_to_collection(user_id, placed_items, db_path):
    """Insert collected items and update warehouse value."""
    if not placed_items:
        return 0
    from game.touchi import get_item_value

    def _do(conn):
        total = 0
        items_for_last = []
        for p in placed_items:
            item = p["item"]
            item_name = os.path.splitext(os.path.basename(item["path"]))[0]
            item_level = item["level"]
            item_value = item.get("value", get_item_value(item_name))
            total += item_value

            parts = item_name.split('_')
            unique_id = parts[-1] if len(parts) >= 3 else item_name
            items_for_last.append({
                "item_name": item_name,
                "unique_id": unique_id,
                "item_level": item_level,
            })

            conn.execute(
                "INSERT OR IGNORE INTO user_touchi_collection (user_id, item_name, item_level) VALUES (?,?,?)",
                (user_id, item_name, item_level))

        conn.execute(
            "INSERT OR IGNORE INTO user_economy (user_id) VALUES (?)", (user_id,))
        conn.execute(
            "UPDATE user_economy SET warehouse_value = warehouse_value + ? WHERE user_id=?",
            (total, user_id))

        import json
        conn.execute(
            "INSERT OR REPLACE INTO user_last_touchi (user_id, items_json, total_value) VALUES (?,?,?)",
            (user_id, json.dumps(items_for_last), total))
        return total

    return write_with_retry(db_path, _do)


def activate_menggong(user_id, db_path):
    """Activate menggong mode.  Returns (ok, message)."""
    def _do(conn):
        row = conn.execute(
            "SELECT warehouse_value, menggong_active, menggong_end_time FROM user_economy WHERE user_id=?",
            (user_id,)).fetchone()
        if not row:
            return False, "用户不存在"
        val, active, end_time = row["warehouse_value"], row["menggong_active"], row["menggong_end_time"]
        now = int(time.time())
        if active and now < end_time:
            remaining = end_time - now
            mins, secs = divmod(remaining, 60)
            return False, f"刘涛状态进行中，剩余 {mins}分{secs}秒"
        if val < MENGONG_COST:
            return False, f"哈夫币不足！当前: {val:,}，需要: {MENGONG_COST:,}"

        # Read duration from config
        row_cfg = conn.execute(
            "SELECT config_value FROM system_config WHERE config_key='menggong_duration'"
        ).fetchone()
        duration = int(row_cfg["config_value"]) if row_cfg else MENGONG_BASE_DURATION

        conn.execute(
            "UPDATE user_economy SET warehouse_value=warehouse_value-?, menggong_active=1, menggong_end_time=? WHERE user_id=?",
            (MENGONG_COST, now + duration, user_id))
        mins, secs = divmod(duration, 60)
        dur_str = f"{mins}分{secs}秒" if secs else f"{mins}分钟"
        return True, f"🔥 六套猛攻激活！{dur_str}内提高红色和金色物品概率，不出现蓝色物品！\n消耗 3,000,000 哈夫币"

    return write_with_retry(db_path, _do)


def upgrade_teqin(user_id, db_path):
    """Upgrade teqin level.  Returns (ok, message)."""
    def _do(conn):
        row = conn.execute(
            "SELECT warehouse_value, teqin_level, grid_size FROM user_economy WHERE user_id=?",
            (user_id,)).fetchone()
        if not row:
            return False, "用户不存在"
        val, level, gs = row["warehouse_value"], row["teqin_level"], row["grid_size"]
        if level >= MAX_TEQIN_LEVEL:
            return False, "特勤处已达到最高等级！"
        cost = UPGRADE_COSTS[level] if level < len(UPGRADE_COSTS) else None
        if cost is None:
            return False, "升级费用配置错误"
        if val < cost:
            return False, f"哈夫币不足！当前: {val:,}，需要: {cost:,}"
        new_level = level + 1
        new_gs = grid_size_for_level(new_level)
        conn.execute(
            "UPDATE user_economy SET warehouse_value=warehouse_value-?, teqin_level=?, grid_size=? WHERE user_id=?",
            (cost, new_level, new_gs, user_id))
        return True, (
            f"🎉 特勤处升级成功！\n等级: {level} → {new_level}\n"
            f"格子大小: {gs}x{gs} → {new_gs}x{new_gs}\n"
            f"消耗: {cost:,}\n剩余: {val - cost:,}")

    return write_with_retry(db_path, _do)


def start_auto_touchi(user_id, db_path):
    """Enable auto touchi.  Returns (ok, message)."""
    def _do(conn):
        row = conn.execute(
            "SELECT auto_touchi_active, auto_touchi_start_time FROM user_economy WHERE user_id=?",
            (user_id,)).fetchone()
        if not row:
            conn.execute("INSERT OR IGNORE INTO user_economy (user_id) VALUES (?)", (user_id,))
            active, start = 0, 0
        else:
            active, start = row["auto_touchi_active"], row["auto_touchi_start_time"]
        if active:
            elapsed = int(time.time()) - start
            mins, secs = divmod(elapsed, 60)
            return False, f"自动偷吃已经在进行中，已运行 {mins}分{secs}秒"
        now = int(time.time())
        conn.execute(
            "UPDATE user_economy SET auto_touchi_active=1, auto_touchi_start_time=?, auto_touchi_red_count=0 WHERE user_id=?",
            (now, user_id))
        return True, (
            "🤖 自动偷吃已开启！\n"
            "⏰ 每 10 分钟自动偷吃\n"
            "🎯 金红概率降低\n"
            "⏱️ 4 小时后自动停止")

    return write_with_retry(db_path, _do)


def stop_auto_touchi(user_id, db_path):
    """Disable auto touchi.  Returns (ok, message)."""
    def _do(conn):
        row = conn.execute(
            "SELECT auto_touchi_active, auto_touchi_start_time, auto_touchi_red_count FROM user_economy WHERE user_id=?",
            (user_id,)).fetchone()
        if not row or not row["auto_touchi_active"]:
            return True, "自动偷吃未开启"
        start = row["auto_touchi_start_time"]
        red = row["auto_touchi_red_count"]
        elapsed = int(time.time()) - start
        mins, secs = divmod(elapsed, 60)
        conn.execute(
            "UPDATE user_economy SET auto_touchi_active=0, auto_touchi_start_time=0 WHERE user_id=?",
            (user_id,))
        return True, (
            f"🛑 自动偷吃已关闭\n"
            f"⏱️ 运行时长: {mins}分{secs}秒\n"
            f"🔴 获得红色物品数量: {red}个")

    return write_with_retry(db_path, _do)


# ---------------------------------------------------------------------------
# Auto-touchi scheduler — runs in a background thread
# ---------------------------------------------------------------------------

_auto_thread = None


def _auto_loop(db_path):
    """Background thread that processes auto-touchi for all active users."""
    from game.touchi import load_items, create_safe_layout, get_item_value

    while True:
        time.sleep(AUTO_TOUCHI_INTERVAL)
        try:
            conn = get_connection(db_path)
            rows = conn.execute(
                "SELECT user_id, grid_size, menggong_active, menggong_end_time, "
                "auto_touchi_start_time FROM user_economy WHERE auto_touchi_active=1"
            ).fetchall()
            conn.close()

            now = int(time.time())
            items = load_items()
            if not items:
                continue

            for row in rows:
                uid = row["user_id"]
                # Check 4-hour cap
                start_time = row["auto_touchi_start_time"]
                if now - start_time >= AUTO_TOUCHI_MAX_DURATION:
                    stop_auto_touchi(uid, db_path)
                    continue

                menggong = bool(row["menggong_active"] and now < row["menggong_end_time"])
                gs = row["grid_size"]

                placed, _, _, _, _ = create_safe_layout(items, menggong, gs, auto_mode=True)
                if placed:
                    add_items_to_collection(uid, placed, db_path)
                    red_count = sum(1 for p in placed if p["item"]["level"] == "red")
                    if red_count:
                        conn2 = get_connection(db_path)
                        conn2.execute(
                            "UPDATE user_economy SET auto_touchi_red_count = auto_touchi_red_count + ? WHERE user_id=?",
                            (red_count, uid))
                        conn2.commit()
                        conn2.close()
        except Exception:
            pass  # don't crash the scheduler on transient failures


def start_scheduler(db_path):
    global _auto_thread
    if _auto_thread is not None:
        return
    _auto_thread = threading.Thread(target=_auto_loop, args=(db_path,), daemon=True)
    _auto_thread.start()
