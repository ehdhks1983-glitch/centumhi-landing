"""SQLite 초기화 + CRUD + settings 헬퍼 (개발명령서 v1.1 §2)"""
import os
import sqlite3
from datetime import date

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rank_tracker.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS products (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    product_name  TEXT NOT NULL,
    mall_name     TEXT,
    nvmid         TEXT,
    product_link  TEXT,
    track_limit   INTEGER NOT NULL DEFAULT 100,
    is_active     INTEGER NOT NULL DEFAULT 1,
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS keywords (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id  INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    keyword     TEXT NOT NULL,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(product_id, keyword)
);

CREATE TABLE IF NOT EXISTS rank_history (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword_id    INTEGER NOT NULL REFERENCES keywords(id) ON DELETE CASCADE,
    checked_date  TEXT NOT NULL,
    rank          INTEGER,
    match_method  TEXT NOT NULL,
    UNIQUE(keyword_id, checked_date)
);
CREATE INDEX IF NOT EXISTS idx_rank_lookup ON rank_history(keyword_id, checked_date);

CREATE TABLE IF NOT EXISTS settings (
    key    TEXT PRIMARY KEY,
    value  TEXT
);
"""


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA)


# ---------- settings ----------

def get_setting(key, default=None):
    with get_conn() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else default


def set_setting(key, value):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO settings(key, value) VALUES(?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, str(value)),
        )


# 일일 API 사용량 — 'usage:YYYY-MM-DD' 키. 날짜가 바뀌면 새 키 = 리셋 로직 불필요.

def _usage_key():
    return f"usage:{date.today().isoformat()}"


def get_today_usage():
    return int(get_setting(_usage_key(), "0"))


def increment_today_usage():
    key = _usage_key()
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO settings(key, value) VALUES(?, '1') "
            "ON CONFLICT(key) DO UPDATE SET value = CAST(CAST(value AS INTEGER) + 1 AS TEXT)",
            (key,),
        )


# ---------- products / keywords ----------

def add_product(product_name, mall_name=None, product_link=None, track_limit=100, keywords=()):
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO products(product_name, mall_name, product_link, track_limit) "
            "VALUES(?, ?, ?, ?)",
            (product_name, mall_name or None, product_link or None, track_limit),
        )
        product_id = cur.lastrowid
        for kw in keywords:
            kw = kw.strip()
            if kw:
                conn.execute(
                    "INSERT OR IGNORE INTO keywords(product_id, keyword) VALUES(?, ?)",
                    (product_id, kw),
                )
    return product_id


def delete_product(product_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM products WHERE id = ?", (product_id,))


def set_product_active(product_id, is_active):
    with get_conn() as conn:
        conn.execute("UPDATE products SET is_active = ? WHERE id = ?", (1 if is_active else 0, product_id))


def get_active_products():
    with get_conn() as conn:
        return conn.execute("SELECT * FROM products WHERE is_active = 1 ORDER BY id").fetchall()


def get_all_products():
    with get_conn() as conn:
        return conn.execute("SELECT * FROM products ORDER BY id").fetchall()


def get_keywords(product_id):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM keywords WHERE product_id = ? ORDER BY id", (product_id,)
        ).fetchall()


def promote_nvmid(product_id, nvmid, mall_name=None):
    """첫 이름 매칭 성공 시 productId 자동 승격 저장 (§3).
    몰명 미입력 상품이면 첫 매칭 결과의 몰명도 같이 저장해 다음부터 자동 강화."""
    with get_conn() as conn:
        conn.execute("UPDATE products SET nvmid = ? WHERE id = ?", (nvmid, product_id))
        if mall_name:
            conn.execute(
                "UPDATE products SET mall_name = ? WHERE id = ? AND (mall_name IS NULL OR mall_name = '')",
                (mall_name, product_id),
            )


# ---------- rank_history ----------

def save_result(keyword_id, rank, match_method, checked_date=None):
    """같은 날 재조회 시 1행 유지, 최신값으로 갱신 (완료판정 1)."""
    checked_date = checked_date or date.today().isoformat()
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO rank_history(keyword_id, checked_date, rank, match_method) "
            "VALUES(?, ?, ?, ?) "
            "ON CONFLICT(keyword_id, checked_date) DO UPDATE SET "
            "rank = excluded.rank, match_method = excluded.match_method",
            (keyword_id, checked_date, rank, match_method),
        )


def get_history(keyword_id, limit=30):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM rank_history WHERE keyword_id = ? ORDER BY checked_date DESC LIMIT ?",
            (keyword_id, limit),
        ).fetchall()


def get_latest_rank(keyword_id):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM rank_history WHERE keyword_id = ? ORDER BY checked_date DESC LIMIT 1",
            (keyword_id,),
        ).fetchone()
