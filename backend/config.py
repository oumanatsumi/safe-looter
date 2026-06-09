import os
import yaml

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _load_yaml():
    path = os.path.join(BASE_DIR, "config.yaml")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


_yaml = _load_yaml()


def _get(key, default, env=None):
    """Resolve config: env var > yaml > default."""
    if env and os.environ.get(env):
        return os.environ[env]
    return _yaml.get(key, default)


def _resolve_path(raw):
    """Resolve a path: absolute stays absolute, relative joins to BASE_DIR."""
    if os.path.isabs(raw):
        return raw
    return os.path.join(BASE_DIR, raw)


# ── Paths ──
DB_PATH = _resolve_path(_get("db_path", "data/collection.db", "TOUCHI_DB_PATH"))
ITEMS_DIR = _resolve_path(_get("items_dir", "resources/items", "TOUCHI_ITEMS_DIR"))
EXPRESSIONS_DIR = _resolve_path(_get("expressions_dir", "resources/expressions", "TOUCHI_EXPRESSIONS_DIR"))
OUTPUT_DIR = _resolve_path(_get("output_dir", "output"))

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── Server ──
HOST = _get("host", "0.0.0.0", "TOUCHI_HOST")
PORT = int(_get("port", 5000, "TOUCHI_PORT"))

# ── Admin ──
ADMIN_TOKEN = _get("admin_token", "admin123", "ADMIN_TOKEN")

# ── Game ──
DEFAULT_GRID_SIZE = int(_get("default_grid_size", 2))
MAX_TEQIN_LEVEL = int(_get("max_teqin_level", 5))
MENGONG_COST = int(_get("mengong_cost", 3_000_000))
MENGONG_BASE_DURATION = int(_get("mengong_base_duration", 120))

# ── Auto touchi ──
AUTO_TOUCHI_INTERVAL = int(_get("auto_touchi_interval", 600))
AUTO_TOUCHI_MAX_DURATION = int(_get("auto_touchi_max_duration", 4 * 3600))

# ── DB sync ──
DB_BUSY_TIMEOUT = int(_get("db_busy_timeout", 5000))
DB_WRITE_RETRIES = int(_get("db_write_retries", 3))
