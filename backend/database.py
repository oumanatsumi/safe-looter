import sqlite3
import time
from config import DB_BUSY_TIMEOUT, DB_WRITE_RETRIES


def get_connection(db_path, read_only=False):
    """Get a SQLite connection with WAL mode and busy timeout configured."""
    conn = sqlite3.connect(
        db_path,
        timeout=DB_BUSY_TIMEOUT / 1000.0,
        check_same_thread=False,
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=%d" % DB_BUSY_TIMEOUT)
    return conn


def write_with_retry(db_path, operation):
    """Execute a write operation with retry on database lock.

    Args:
        db_path: Path to the SQLite database.
        operation: Callable(conn) -> result.  Called inside a transaction.
                    If it raises, the transaction is rolled back.

    Returns:
        The result of `operation`.

    Raises:
        sqlite3.OperationalError after all retries are exhausted.
    """
    last_error = None
    for attempt in range(DB_WRITE_RETRIES):
        conn = get_connection(db_path)
        try:
            conn.execute("BEGIN IMMEDIATE")
            result = operation(conn)
            conn.commit()
            return result
        except sqlite3.OperationalError as e:
            conn.rollback()
            last_error = e
            if "locked" in str(e).lower() or "busy" in str(e).lower():
                time.sleep(0.5 * (attempt + 1))  # backoff
                continue
            raise
        finally:
            conn.close()
    raise last_error


def init_db(db_path):
    """Create tables if they don't exist, then migrate missing columns for
    compatibility with production DB schemas."""
    conn = get_connection(db_path)
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS user_touchi_collection (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                item_name TEXT NOT NULL,
                item_level TEXT NOT NULL,
                collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, item_name)
            );

            CREATE TABLE IF NOT EXISTS user_economy (
                user_id TEXT PRIMARY KEY,
                warehouse_value INTEGER DEFAULT 0,
                teqin_level INTEGER DEFAULT 0,
                grid_size INTEGER DEFAULT 2,
                menggong_active INTEGER DEFAULT 0,
                menggong_end_time INTEGER DEFAULT 0,
                auto_touchi_active INTEGER DEFAULT 0,
                auto_touchi_start_time INTEGER DEFAULT 0,
                auto_touchi_red_count INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS user_last_touchi (
                user_id TEXT PRIMARY KEY,
                items_json TEXT,
                total_value INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS system_config (
                config_key TEXT PRIMARY KEY,
                config_value TEXT NOT NULL
            );

            INSERT OR IGNORE INTO system_config (config_key, config_value)
            VALUES ('touchi_cooldown_multiplier', '1.0');

            INSERT OR IGNORE INTO system_config (config_key, config_value)
            VALUES ('base_teqin_level', '0');
        """)

        # Migration: add columns missing from production DB schemas
        try:
            conn.execute(
                "ALTER TABLE user_economy ADD COLUMN auto_touchi_red_count INTEGER DEFAULT 0")
        except:
            pass
        try:
            conn.execute(
                "ALTER TABLE user_last_touchi ADD COLUMN total_value INTEGER DEFAULT 0")
        except:
            pass
        try:
            conn.execute(
                "ALTER TABLE user_economy ADD COLUMN last_touchi_time INTEGER DEFAULT 0")
        except:
            pass
        try:
            conn.execute(
                "ALTER TABLE user_economy ADD COLUMN touchi_cooldown INTEGER DEFAULT 0")
        except:
            pass

        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Game configuration — stored in system_config table
# ---------------------------------------------------------------------------

GAME_CONFIG_DEFAULTS = {
    "cooldown_min": "60",
    "cooldown_max": "140",
    "rate_blue": "0.25",
    "rate_purple": "0.42",
    "rate_gold": "0.28",
    "rate_red": "0.05",
    "menggong_duration": "120",
    "menggong_rate_purple": "0.45",
    "menggong_rate_gold": "0.45",
    "menggong_rate_red": "0.10",
}


def get_game_config(db_path):
    """Read all game config from system_config, filling defaults for missing keys."""
    conn = get_connection(db_path)
    try:
        rows = conn.execute("SELECT config_key, config_value FROM system_config").fetchall()
        db_config = {r["config_key"]: r["config_value"] for r in rows}
    finally:
        conn.close()
    cfg = {}
    for key, default in GAME_CONFIG_DEFAULTS.items():
        cfg[key] = db_config.get(key, default)
    return cfg


def save_game_config(db_path, updates, admin_token):
    """Validate token and persist config updates. Returns (ok, message)."""
    from config import ADMIN_TOKEN
    if admin_token != ADMIN_TOKEN:
        return False, "token无效"

    conn = get_connection(db_path)
    try:
        for key in updates:
            if key not in GAME_CONFIG_DEFAULTS:
                return False, f"未知的配置项: {key}"
        for key, value in updates.items():
            conn.execute(
                "INSERT OR REPLACE INTO system_config (config_key, config_value) VALUES (?,?)",
                (key, str(value)))
        conn.commit()
        return True, "配置已保存"
    finally:
        conn.close()
