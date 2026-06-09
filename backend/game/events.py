"""Random events that trigger during touchi — 7 event types.

Adapted from the AstrBot plugin. Stripped out AstrBot / async / group-chat
dependencies.  The caller is responsible for saving / applying results.
"""
import random
import os
import glob
import time

from config import ITEMS_DIR

# ---------------------------------------------------------------------------
# Event probability table
# ---------------------------------------------------------------------------

EVENT_PROBABILITIES = {
    "broken_liutao": 0.04,
    "genius_kick": 0.04,
    "genius_fine": 0.04,
    "noob_teammate": 0.04,
    "hunted_escape": 0.04,
    "passerby_mouse": 0.04,
    "system_compensation": 0.04,
    "chixiao_battle": 0.20,       # kept for compatibility but never fires
}


def _extract_size(item_name):
    parts = item_name.split('_')
    if len(parts) >= 2:
        potential = parts[1]
        if 'x' in potential:
            return potential
    return None


# ---------------------------------------------------------------------------
# Event handler helpers — each returns (items, value, message)
# ---------------------------------------------------------------------------

def handle_broken_liutao(placed_items, total_value):
    """Gain 'broken liutao' — activates temporary menggong buff."""
    duration = 60  # 1 minute
    msg = (
        "🎉 特殊事件触发！\n"
        "💎 你额外获得了残缺的刘涛！\n"
        f"⚡ 六套加成时间已激活 {duration // 60}分{duration % 60}秒！\n"
        "🔥 期间红色和金色物品概率大幅提升！"
    )
    return "broken_liutao", placed_items, total_value, msg, duration


def handle_genius_kick(placed_items, total_value):
    """Kicked by a genius player — lose all items this round."""
    msg = (
        "💀 特殊事件触发！\n"
        "👦 你遇到了天才少年，被一脚踢死了！\n"
        "📦 本次偷吃展示如下，但物品不会计入仓库！\n"
        "💸 本次偷吃的物品全部丢失..."
    )
    return "genius_kick", placed_items, 0, msg


def handle_genius_fine(placed_items, total_value):
    """Fined 60% of value by a genius player."""
    fine = int(total_value * 0.6)
    msg = (
        "⚖️ 特殊事件触发！\n"
        "👦 你排到了天才少年！\n"
        "🍽️ 虽然成功偷吃了，但被追缴了哈夫币！\n"
        f"📦 本次偷吃价值: {total_value:,}\n"
        f"⚖️ 追缴金额: {fine:,} (60%)"
    )
    return "genius_fine", placed_items, total_value, msg, fine


def handle_noob_teammate(placed_items, total_value):
    """Bad teammate doubles the cooldown."""
    msg = (
        "🤦 特殊事件触发！\n"
        "👥 你遇到了唐氏队友，撤离时间翻倍！\n"
        "⏰ 下次偷吃冷却时间增加一倍！"
    )
    return "noob_teammate", placed_items, total_value, msg, 2.0  # 2x cooldown


def handle_hunted_escape(placed_items, total_value):
    """Forced to ditch large items — keep only small ones."""
    allowed = {'1x1', '1x2', '2x1', '1x3', '3x1'}
    filtered = []
    for p in placed_items:
        sz = _extract_size(p["item"]["base_name"])
        if sz and sz in allowed:
            filtered.append(p)
    new_val = sum(p["item"]["value"] for p in filtered)
    msg = (
        "🏃 特殊事件触发！\n"
        "🔫 你被追杀到了丢包撤离点！\n"
        "📦 只能保留小尺寸物品！"
    )
    return "hunted_escape", filtered, new_val, msg


def handle_passerby_mouse(placed_items, total_value):
    """A passerby mouse gifts a random gold item."""
    gold_items = glob.glob(os.path.join(ITEMS_DIR, "gold_*.png"))
    if not gold_items:
        return None, placed_items, total_value, None
    chosen = random.choice(gold_items)
    item_name = os.path.splitext(os.path.basename(chosen))[0]
    msg = (
        "🐭 特殊事件触发！\n"
        "👋 你遇到了路人鼠鼠，你们打了暗号！\n"
        "🎁 ta送给了你金色物品"
    )
    return "passerby_mouse", placed_items, total_value, msg, chosen


def handle_system_compensation(placed_items, total_value):
    """System compensation — boosted rates + halved cooldown."""
    msg = (
        "🎯 特殊事件触发！\n"
        "🔧 系统补偿局已启动！\n"
        "⚡ 本次爆率巨幅提升\n"
        "🕑 下次偷吃冷却时间减半！"
    )
    return "system_compensation", placed_items, total_value, msg, 0.5  # halved cooldown


# ---------------------------------------------------------------------------
# Main checker — rolls all events, returns the first one that triggers
# ---------------------------------------------------------------------------

HANDLERS = {
    "broken_liutao": handle_broken_liutao,
    "genius_kick": handle_genius_kick,
    "genius_fine": handle_genius_fine,
    "noob_teammate": handle_noob_teammate,
    "hunted_escape": handle_hunted_escape,
    "passerby_mouse": handle_passerby_mouse,
    "system_compensation": handle_system_compensation,
}

# Handlers that return extra data beyond the standard 4-tuple
EXTRA_RETURN_HANDLERS = {"genius_fine", "passerby_mouse", "system_compensation",
                         "broken_liutao", "noob_teammate"}


def check_random_events(placed_items, total_value):
    """Roll random events.  Returns the first one that triggers.

    Returns:
        (triggered: bool, event_type: str | None,
         final_items: list, final_value: int,
         event_message: str | None, extra: any)
    """
    rand = random.random()
    cumulative = 0.0

    for evt_type, prob in EVENT_PROBABILITIES.items():
        if evt_type == "chixiao_battle":
            continue  # offline mode — skip PVP
        cumulative += prob
        if rand < cumulative:
            handler = HANDLERS.get(evt_type)
            if handler is None:
                continue
            result = handler(placed_items, total_value)
            if result is None:
                return False, None, placed_items, total_value, None, None
            if evt_type in EXTRA_RETURN_HANDLERS:
                evt, items, val, msg, extra = result
                return True, evt, items, val, msg, extra
            else:
                evt, items, val, msg = result
                return True, evt, items, val, msg, None

    return False, None, placed_items, total_value, None, None
