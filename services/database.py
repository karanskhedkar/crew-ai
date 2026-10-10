import sqlite3
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "research_history.db"


def get_connection():
    connection = sqlite3.connect(DB_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT NOT NULL,
                year TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        connection.commit()


def save_article(topic: str, year: str, title: str, content: str) -> int:
    created_at = datetime.now().isoformat(timespec="seconds")
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO articles (topic, year, title, content, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (topic, year, title, content, created_at),
        )
        connection.commit()
        return int(cursor.lastrowid)


def list_articles(limit: int = 50):
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, topic, year, title, created_at
            FROM articles
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_article(article_id: int):
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM articles WHERE id = ?",
            (article_id,),
        ).fetchone()
    return dict(row) if row else None


def get_article_count() -> int:
    with get_connection() as connection:
        row = connection.execute("SELECT COUNT(*) AS total FROM articles").fetchone()
    return int(row["total"])
