"""Core game logic — item loading, safe-layout generation, result building.

Adapted from the AstrBot plugin.  Removed async / AstrBot API dependencies.
Frontend handles all rendering; backend returns structured data only.
"""
import os
import random
import time

from config import ITEMS_DIR, EXPRESSIONS_DIR

# ---------------------------------------------------------------------------
# Item discovery & value mapping
# ---------------------------------------------------------------------------

def get_size(size_str):
    if 'x' in size_str:
        parts = size_str.split('x')
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            return int(parts[0]), int(parts[1])
    return 1, 1


# Rare items have reduced probability
RARE_ITEMS = {
    "gold_1x1_1", "gold_1x1_2", "red_1x1_1", "red_1x1_2", "red_1x1_3",
    "red_3x3_ecmo", "red_3x3_huxiji", "gold_3x2_bendishoushi",
    "purple_1x1_2", "purple_1x1_4", "purple_1x1_3", "purple_1x1_1",
    "red_4x3_cipanzhenlie", "red_4x3_dongdidianchi", "red_3x4_daopian",
    "red_3x3_wanjinleiguan", "red_3x3_tanke",
}

ULTRA_RARE_ITEMS = {"red_1x1_xin", "red_1x1_lei"}

_item_values_cache = None
_items_cache = None
_cache_time = 0
CACHE_DURATION = 300


def generate_item_values():
    """Scan items directory and build name->value mapping from filenames."""
    global _item_values_cache
    now = time.time()
    if _item_values_cache is not None and (now - _cache_time) < CACHE_DURATION:
        return _item_values_cache

    values = {}
    valid_exts = ('.png', '.jpg', '.jpeg', '.gif', '.bmp')

    for fname in os.listdir(ITEMS_DIR):
        if not fname.lower().endswith(valid_exts):
            continue
        name_no_ext = os.path.splitext(fname)[0]
        parts = name_no_ext.split('_')
        if len(parts) >= 4 and parts[-1].isdigit():
            base_name = '_'.join(parts[:-1])
            values[base_name] = int(parts[-1])
        else:
            # legacy format — use level-based defaults
            level = parts[0].lower() if parts else "blue"
            defaults = {"blue": 10000, "purple": 50000, "gold": 100000, "red": 500000}
            values[name_no_ext] = defaults.get(level, 10000)

    _item_values_cache = values
    return values


def reload_values():
    """Force reload of item values."""
    global _item_values_cache
    _item_values_cache = None
    return generate_item_values()


def get_item_value(item_name):
    vals = generate_item_values()
    if item_name in vals:
        return vals[item_name]
    # Try extracting price from the last underscore-delimited part
    parts = item_name.split('_')
    if len(parts) >= 2 and parts[-1].isdigit():
        return int(parts[-1])
    return 1000


def load_items():
    """Return list of all item dicts found under ITEMS_DIR."""
    global _items_cache, _cache_time
    now = time.time()
    if _items_cache is not None and (now - _cache_time) < CACHE_DURATION:
        return _items_cache

    items = []
    valid_exts = ('.png', '.jpg', '.jpeg', '.gif', '.bmp')
    value_map = generate_item_values()

    for fname in os.listdir(ITEMS_DIR):
        if not fname.lower().endswith(valid_exts):
            continue
        file_path = os.path.join(ITEMS_DIR, fname)
        if not os.path.isfile(file_path):
            continue

        parts = os.path.splitext(fname)[0].split('_')
        if len(parts) >= 4 and parts[-1].isdigit():
            level = parts[0].lower()
            size = parts[1]
            name_parts = parts[2:-1]
            base_name = '_'.join([level, size, '_'.join(name_parts)])
        else:
            level = parts[0].lower() if len(parts) >= 2 else "purple"
            size = parts[1] if len(parts) >= 2 else "1x1"
            base_name = os.path.splitext(fname)[0]

        w, h = get_size(size)
        items.append({
            "path": file_path, "level": level, "size": size,
            "grid_width": w, "grid_height": h,
            "base_name": base_name,
            "value": value_map.get(base_name, 1000),
        })

    _items_cache = items
    _cache_time = now
    return items


def load_expressions():
    """Return dict {name: path} for all expression images."""
    expressions = {}
    valid_exts = ('.png', '.jpg', '.jpeg', '.gif', '.bmp')
    for fname in os.listdir(EXPRESSIONS_DIR):
        path = os.path.join(EXPRESSIONS_DIR, fname)
        if os.path.isfile(path) and fname.lower().endswith(valid_exts):
            expressions[os.path.splitext(fname)[0]] = path
    return expressions


# ---------------------------------------------------------------------------
# Grid placement
# ---------------------------------------------------------------------------

def place_items(items, grid_width, grid_height, total_grid_size=2):
    grid = [0] * (grid_width * grid_height)
    placed = []
    shuffled = items.copy()
    random.shuffle(shuffled)

    for item in shuffled:
        orientations = [(item["grid_width"], item["grid_height"], False)]
        if item["grid_width"] != item["grid_height"]:
            orientations.append((item["grid_height"], item["grid_width"], True))

        placed_success = False
        for y in range(grid_height):
            if placed_success:
                break
            for x in range(grid_width):
                if placed_success:
                    break
                for width, height, rotated in orientations:
                    if x >= grid_width or y >= grid_height:
                        continue
                    if x + width > total_grid_size or y + height > total_grid_size:
                        continue

                    can_place = True
                    for dy in range(height):
                        if not can_place:
                            break
                        for dx in range(width):
                            cx, cy = x + dx, y + dy
                            if cx < grid_width and cy < grid_height:
                                if grid[cy * grid_width + cx] != 0:
                                    can_place = False
                                    break

                    if can_place:
                        for dy in range(height):
                            for dx in range(width):
                                cx, cy = x + dx, y + dy
                                if cx < grid_width and cy < grid_height:
                                    grid[cy * grid_width + cx] = 1
                        placed.append({
                            "item": item, "x": x, "y": y,
                            "width": width, "height": height, "rotated": rotated,
                        })
                        placed_success = True
                        break
    return placed


# ---------------------------------------------------------------------------
# Layout generation
# ---------------------------------------------------------------------------

def create_safe_layout(items, menggong_mode=False, grid_size=2, auto_mode=False,
                       time_multiplier=1.0, custom_normal_rates=None, custom_menggong_rates=None):
    selected_items = []

    # Drop-rate tables
    if auto_mode:
        level_chances = (
            {"purple": 0.55, "blue": 0.0, "gold": 0.15, "red": 0.033} if menggong_mode
            else {"purple": 0.52, "blue": 0.35, "gold": 0.093, "red": 0.017}
        )
    elif menggong_mode:
        if custom_menggong_rates:
            level_chances = custom_menggong_rates.copy()
            level_chances["blue"] = 0.0
        else:
            level_chances = {"purple": 0.45, "blue": 0.0, "gold": 0.45, "red": 0.10}
    else:
        if custom_normal_rates:
            level_chances = custom_normal_rates.copy()
        else:
            level_chances = {"purple": 0.42, "blue": 0.25, "gold": 0.28, "red": 0.05}

    # Time-multiplier adjustment (non-auto, non-menggong)
    if not auto_mode:
        rate_adj = (time_multiplier - 1.0) * 0.05
        orig_red = level_chances["red"]
        orig_gold = level_chances["gold"]
        level_chances["red"] = max(0.01, orig_red + orig_red * rate_adj)
        level_chances["gold"] = max(0.05, orig_gold + orig_gold * rate_adj)
        level_chances["purple"] = max(0.1, level_chances["purple"] -
                                      (level_chances["red"] - orig_red) -
                                      (level_chances["gold"] - orig_gold))

    # Select items by weighted probability
    for item in items:
        base = level_chances.get(item["level"], 0)
        name = item["base_name"]
        if name in ULTRA_RARE_ITEMS:
            final = level_chances.get("red", 0.05) / 100
        elif name in RARE_ITEMS:
            final = base / 3
        else:
            final = base
        if random.random() <= final:
            selected_items.append(item)

    num = random.randint(2, 6)
    if len(selected_items) > num:
        selected_items = random.sample(selected_items, num)
    elif len(selected_items) < num:
        purples = [i for i in items if i["level"] == "purple" and i["base_name"] not in RARE_ITEMS]
        if purples:
            needed = min(num - len(selected_items), len(purples))
            selected_items.extend(random.sample(purples, needed))
    random.shuffle(selected_items)

    # Region sizing (scales with grid_size)
    base_options = [(2, 1), (3, 1), (4, 1), (4, 2), (4, 3), (4, 4)]
    region_options = []
    for offset in range(grid_size - 1):
        region_options.extend([(w + offset, h + offset) for w, h in base_options])
    region_options = [(w, h) for w, h in region_options if w <= grid_size and h <= grid_size]
    if not region_options:
        region_options = [(2, 1)]
    region_w, region_h = random.choice(region_options)

    placed = place_items(selected_items, region_w, region_h, grid_size)
    return placed, 0, 0, region_w, region_h


# ---------------------------------------------------------------------------
# Result helpers
# ---------------------------------------------------------------------------

def get_highest_level(placed_items):
    if not placed_items:
        return "purple"
    levels = {"purple": 2, "blue": 1, "gold": 3, "red": 4}
    return max((p["item"]["level"] for p in placed_items),
               key=lambda l: levels.get(l, 0))


def _search_duration_ms(level):
    """Milliseconds the frontend should show searching animation per item."""
    return {"blue": 400, "purple": 600, "gold": 1000, "red": 2500}.get(level, 600)


def _determine_expression(placed_items):
    """Return expression key based on result quality."""
    highest = get_highest_level(placed_items)
    total_val = sum(p["item"]["value"] for p in placed_items)
    has_gold = any(p["item"]["level"] == "gold" for p in placed_items)

    if highest == "red":
        return "eat"
    elif highest == "gold":
        return "happy"
    elif total_val > 300000 and not has_gold:
        return "happy"
    else:
        return "cry"


def build_touchi_result(placed_items, grid_size, region_w, region_h):
    """Build frontend-ready result data from placed items.

    Returns a dict with grid layout, item list (with position/size/animation
    timing), and expression info.  The frontend handles all rendering.
    """
    items_data = []
    for p in placed_items:
        item = p["item"]
        fname = os.path.basename(item["path"])
        items_data.append({
            "name": os.path.splitext(fname)[0],
            "level": item["level"],
            "size": item["size"],
            "value": item["value"],
            "image_url": f"/resources/items/{fname}",
            "x": p["x"],
            "y": p["y"],
            "width": p["width"],
            "height": p["height"],
            "rotated": p["rotated"],
            "search_duration_ms": _search_duration_ms(item["level"]),
        })

    # Sort by reveal order: left→right, top→bottom (by grid position)
    items_data.sort(key=lambda x: (x["y"], x["x"]))

    expression = _determine_expression(placed_items)
    total_value = sum(p["item"]["value"] for p in placed_items)

    return {
        "items": items_data,
        "grid_size": grid_size,
        "region_width": region_w,
        "region_height": region_h,
        "total_value": total_value,
        "highest_level": get_highest_level(placed_items),
        "expression": expression,
    }
