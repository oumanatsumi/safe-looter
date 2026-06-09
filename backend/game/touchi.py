"""Core game logic — item loading, safe-layout generation, GIF rendering.

Adapted from the AstrBot plugin.  Removed async / AstrBot API dependencies.
"""
import os
import random
import math
import time
from PIL import Image, ImageDraw
from datetime import datetime
import glob

from config import ITEMS_DIR, EXPRESSIONS_DIR, OUTPUT_DIR

os.makedirs(OUTPUT_DIR, exist_ok=True)

ITEM_BORDER_COLOR = (100, 100, 110)
BORDER_WIDTH = 1

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
# GIF rendering
# ---------------------------------------------------------------------------

def _rotation_duration(level):
    return {"blue": 4, "purple": 6, "gold": 10, "red": 25}.get(level, 6)


def render_safe_layout_gif(placed_items, start_x, start_y, region_width, region_height,
                           grid_size=2, cell_size=100):
    img_size = grid_size * cell_size
    frames = []

    # Compute total frames
    if placed_items:
        total_search = sum(_rotation_duration(p["item"]["level"]) for p in placed_items)
        total_frames = total_search + 15
    else:
        total_frames = 5

    bg_colors = {
        "purple": (50, 43, 97, 90), "blue": (49, 91, 126, 90),
        "gold": (153, 116, 22, 90), "red": (139, 35, 35, 90),
    }

    # Preload item images
    item_images = {}
    for i, placed in enumerate(placed_items):
        try:
            img = Image.open(placed["item"]["path"]).convert("RGBA")
            if placed["rotated"]:
                img = img.rotate(90, expand=True)
            iw, ih = placed["width"] * cell_size, placed["height"] * cell_size
            img.thumbnail((iw, ih), Image.LANCZOS)
            item_images[i] = img.copy()
        except Exception:
            item_images[i] = None

    sousuo_path = os.path.join(EXPRESSIONS_DIR, "sousuo.png")
    sousuo_img = None
    if os.path.exists(sousuo_path):
        try:
            s_img = Image.open(sousuo_path).convert("RGBA")
            sousuo_img = s_img.resize((60, 60), Image.LANCZOS)
        except Exception:
            pass

    for frame_idx in range(total_frames):
        safe_img = Image.new("RGB", (img_size, img_size), (50, 50, 50))
        draw = ImageDraw.Draw(safe_img)

        # Grid lines
        for i in range(1, grid_size):
            draw.line([(i * cell_size, 0), (i * cell_size, img_size)], fill=(80, 80, 80), width=1)
            draw.line([(0, i * cell_size), (img_size, i * cell_size)], fill=(80, 80, 80), width=1)

        overlay = Image.new("RGBA", safe_img.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)

        # Determine how many items are revealed
        cum_time = 0
        current_count = 0
        for i, placed in enumerate(placed_items):
            rot_start = cum_time
            if frame_idx >= rot_start:
                current_count = i + 1
            else:
                break
            cum_time += _rotation_duration(placed["item"]["level"])

        # Draw unrevealed items as hatched covers
        for i in range(current_count, len(placed_items)):
            placed = placed_items[i]
            x0 = placed["x"] * cell_size
            y0 = placed["y"] * cell_size
            x1 = x0 + placed["width"] * cell_size
            y1 = y0 + placed["height"] * cell_size

            overlay_draw.rectangle([x0, y0, x1, y1], fill=(0, 0, 0, 80))
            for y in range(int(y0), int(y1), 6):
                overlay_draw.line([(int(x0), y), (int(x1), y)], fill=(0, 0, 0, 80), width=1)
            for x in range(int(x0), int(x1), 6):
                overlay_draw.line([(x, int(y0)), (x, int(y1))], fill=(0, 0, 0, 80), width=1)
            overlay_draw.rectangle([int(x0), int(y0), int(x1), int(y1)],
                                   outline=(80, 80, 80, 180), width=1)

            # Diagonal hatching
            for line_off in range(-int(x1 - x0) - int(y1 - y0),
                                  int(x1 - x0) + int(y1 - y0), 15):
                pts = []
                y_left = -int(x0) + (int(x0) + line_off + int(y0))
                if int(y0) <= y_left <= int(y1):
                    pts.append((int(x0), int(y_left)))
                y_right = -int(x1) + (int(x0) + line_off + int(y0))
                if int(y0) <= y_right <= int(y1):
                    pts.append((int(x1), int(y_right)))
                x_top = (int(x0) + line_off + int(y0)) - int(y0)
                if int(x0) <= x_top <= int(x1):
                    pts.append((int(x_top), int(y0)))
                x_bot = (int(x0) + line_off + int(y0)) - int(y1)
                if int(x0) <= x_bot <= int(x1):
                    pts.append((int(x_bot), int(y1)))
                if len(pts) >= 2:
                    overlay_draw.line([pts[0], pts[1]], fill=(128, 128, 128, 150), width=2)

        # Draw revealed items
        for i in range(current_count):
            placed = placed_items[i]
            item = placed["item"]
            x0 = placed["x"] * cell_size
            y0 = placed["y"] * cell_size
            x1 = x0 + placed["width"] * cell_size
            y1 = y0 + placed["height"] * cell_size
            bg = bg_colors.get(item["level"], (128, 128, 128, 200))

            # Build cumulative rotation time window for this item
            cum_prev = sum(_rotation_duration(placed_items[j]["item"]["level"])
                           for j in range(i))
            rot_start = cum_prev
            rot_end = rot_start + _rotation_duration(item["level"])
            is_rotating = rot_start <= frame_idx < rot_end

            if is_rotating:
                # Draw hatched cover + rotation indicator
                overlay_draw.rectangle([x0, y0, x1, y1], fill=(0, 0, 0, 80))
                for y in range(int(y0), int(y1), 6):
                    overlay_draw.line([(int(x0), y), (int(x1), y)], fill=(0, 0, 0, 80), width=1)
                for x in range(int(x0), int(x1), 6):
                    overlay_draw.line([(x, int(y0)), (x, int(y1))], fill=(0, 0, 0, 80), width=1)
                overlay_draw.rectangle([int(x0), int(y0), int(x1), int(y1)],
                                       outline=(80, 80, 80, 180), width=1)

                rot_frame = (frame_idx - rot_start) % _rotation_duration(item["level"])
                base_dur = 20
                speed_boost = 3.0
                mult = _rotation_duration(item["level"]) / base_dur
                angle = (rot_frame * 360 * mult * speed_boost // _rotation_duration(item["level"])) % 360

                cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
                radius = cell_size // 14

                if sousuo_img:
                    ang_rad = math.radians(angle)
                    orb_x = cx + radius * math.cos(ang_rad)
                    orb_y = cy + radius * math.sin(ang_rad)
                    px = int(orb_x - 30 + 10)
                    py = int(orb_y - 30 + 10)
                    overlay.paste(sousuo_img, (px, py), sousuo_img)
                else:
                    bbox = [cx - radius, cy - radius, cx + radius, cy + radius]
                    overlay_draw.arc(bbox, angle, angle + 150, fill=(255, 255, 255, 220), width=3)
            else:
                # Entrance animation
                entrance_dur = 2
                entrance_frame = frame_idx - rot_end
                is_entrance = 0 <= entrance_frame < entrance_dur

                if is_entrance:
                    progress = entrance_frame / entrance_dur
                    scale = 1.5 - 0.5 * progress

                    # Color block effect
                    r, g, b, a = bg
                    lr, lg, lb = (int(r + (255-r)*0.3), int(g + (255-g)*0.3), int(b + (255-b)*0.3))
                    dr, dg, db = (int(r*0.1), int(g*0.1), int(b*0.1))
                    cr = int(lr + (dr - lr) * progress)
                    cg = int(lg + (dg - lg) * progress)
                    cb = int(lb + (db - lb) * progress)
                    ca = int(a + (255 - a) * progress * 0.5)
                    blk_scale = 1.0 + 0.3 * progress
                    bw = int((placed["width"] * cell_size) * blk_scale)
                    bh = int((placed["height"] * cell_size) * blk_scale)
                    bx = x0 + (placed["width"] * cell_size - bw) // 2
                    by = y0 + (placed["height"] * cell_size - bh) // 2
                    overlay_draw.rectangle([bx, by, bx + bw, by + bh],
                                           fill=(cr, cg, cb, ca))
                else:
                    overlay_draw.rectangle([x0, y0, x1, y1], fill=bg)
                    scale = 1.0

                # Draw item image
                if i in item_images and item_images[i] is not None:
                    iimg = item_images[i]
                    if scale != 1.0:
                        sw = int(iimg.width * scale)
                        sh = int(iimg.height * scale)
                        si = iimg.resize((sw, sh), Image.LANCZOS)
                        px = x0 + (placed["width"] * cell_size - sw) // 2
                        py = y0 + (placed["height"] * cell_size - sh) // 2
                        overlay.paste(si, (int(px), int(py)), si)
                    else:
                        px = x0 + (placed["width"] * cell_size - iimg.width) // 2
                        py = y0 + (placed["height"] * cell_size - iimg.height) // 2
                        overlay.paste(iimg, (int(px), int(py)), iimg)

                # Border
                draw.rectangle([x0, y0, x1, y1], outline=ITEM_BORDER_COLOR, width=BORDER_WIDTH)

        frame = Image.alpha_composite(safe_img.convert("RGBA"), overlay).convert("RGB")
        frames.append(frame)

    return frames, len(frames)


def get_highest_level(placed_items):
    if not placed_items:
        return "purple"
    levels = {"purple": 2, "blue": 1, "gold": 3, "red": 4}
    return max((p["item"]["level"] for p in placed_items),
               key=lambda l: levels.get(l, 0))


# ---------------------------------------------------------------------------
# Full image generation (GIF + static)
# ---------------------------------------------------------------------------

def generate_safe_image(menggong_mode=False, grid_size=2, time_multiplier=1.0,
                        gif_scale=0.7, enable_static_image=False,
                        custom_normal_rates=None, custom_menggong_rates=None):
    items = load_items()
    expressions = load_expressions()
    if not items or not expressions:
        return None, []

    placed_items, start_x, start_y, region_w, region_h = create_safe_layout(
        items, menggong_mode, grid_size, auto_mode=False, time_multiplier=time_multiplier,
        custom_normal_rates=custom_normal_rates, custom_menggong_rates=custom_menggong_rates)

    safe_frames, total_frames = render_safe_layout_gif(
        placed_items, start_x, start_y, region_w, region_h, grid_size)

    highest = get_highest_level(placed_items)
    total_val = sum(p["item"]["value"] for p in placed_items)
    has_gold = any(p["item"]["level"] == "gold" for p in placed_items)

    if highest == "red":
        final_expr = "eat"
    elif highest == "gold":
        final_expr = "happy"
    elif total_val > 300000 and not has_gold:
        final_expr = "happy"
    else:
        final_expr = "cry"

    eating_path = expressions.get("eating")
    final_expr_path = expressions.get(final_expr)
    if not eating_path or not final_expr_path:
        return None, []

    expr_size = grid_size * 100

    # Load eating.gif frames
    eating_frames = []
    try:
        with Image.open(eating_path) as gif:
            for idx in range(gif.n_frames):
                gif.seek(idx)
                eating_frames.append(
                    gif.convert("RGBA").resize((expr_size, expr_size), Image.LANCZOS).copy())
    except Exception:
        return None, []

    with Image.open(final_expr_path).convert("RGBA") as final_img:
        final_img = final_img.resize((expr_size, expr_size), Image.LANCZOS)

        final_frames = []
        for idx, sf in enumerate(safe_frames):
            canvas = Image.new("RGB", (expr_size + sf.width, sf.height), (50, 50, 50))
            expr = final_img if idx == 0 else eating_frames[(idx - 1) % len(eating_frames)]
            if expr.mode == 'RGBA':
                canvas.paste(expr, (0, 0), expr)
            else:
                canvas.paste(expr, (0, 0))
            canvas.paste(sf, (expr_size, 0))
            if gif_scale != 1.0:
                nw, nh = int(canvas.width * gif_scale), int(canvas.height * gif_scale)
                canvas = canvas.resize((nw, nh), Image.LANCZOS)
            final_frames.append(canvas)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    if enable_static_image:
        # Static PNG — last frame only
        safe_frame = safe_frames[max(0, total_frames - 6)]
        out_path = os.path.join(OUTPUT_DIR, f"safe_{timestamp}.png")
        static = Image.new("RGB", (expr_size + safe_frame.width, safe_frame.height), (50, 50, 50))
        static.paste(final_img, (0, 0), final_img if final_img.mode == 'RGBA' else None)
        static.paste(safe_frame, (expr_size, 0))
        if gif_scale != 1.0:
            nw, nh = int(static.width * gif_scale), int(static.height * gif_scale)
            static = static.resize((nw, nh), Image.LANCZOS)
        static.save(out_path, 'PNG')
    else:
        out_path = os.path.join(OUTPUT_DIR, f"safe_{timestamp}.gif")
        if final_frames:
            final_frames[0].save(
                out_path, save_all=True, append_images=final_frames[1:],
                duration=150, loop=0)

    # Cleanup old files
    for kind in ('*.png', '*.gif'):
        files = sorted(glob.glob(os.path.join(OUTPUT_DIR, kind)),
                       key=os.path.getmtime, reverse=True)
        for old in files[2:]:
            try:
                os.remove(old)
            except Exception:
                pass

    return out_path, placed_items, total_frames
