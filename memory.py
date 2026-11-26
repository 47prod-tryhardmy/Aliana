import sqlite3
import re
import os

DATA_DIR = os.getenv("DATA_DIR", ".")
DB_NAME = os.path.join(DATA_DIR, "novel_memory.db")



def init_db():
    with sqlite3.connect(DB_NAME) as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)


def save_message(user_id, role, content):
    with sqlite3.connect(DB_NAME) as db:
        db.execute(
            """
            INSERT INTO messages (user_id, role, content)
            VALUES (?, ?, ?)
            """,
            (user_id, role, content)
        )


def get_context(user_id, current_message, limit=8):
    with sqlite3.connect(DB_NAME) as db:

        # Получаем последние сообщения
        recent = db.execute(
            """
            SELECT id, role, content
            FROM messages
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (user_id, limit)
        ).fetchall()

        recent.reverse()

        if not recent:
            return [], []

        first_recent_id = recent[0][0]

        # Ищем подходящие старые воспоминания
        words = set(
            re.findall(
                r"[а-яёa-z0-9]{4,}",
                current_message.lower()
            )
        )

        stop_words = {
            "когда", "почему", "который", "которая",
            "помнишь", "можешь", "расскажи", "сделать",
            "тогда", "теперь", "этого", "этот", "этим",
            "твоего", "твоей", "меня", "тебя", "сейчас"
        }

        words -= stop_words

        old_messages = db.execute(
            """
            SELECT role, content
            FROM messages
            WHERE user_id = ? AND id < ?
            ORDER BY id DESC
            LIMIT 5000
            """,
            (user_id, first_recent_id)
        ).fetchall()

        scored = []

        for role, content in old_messages:
            text = content.lower()

            score = sum(
                1 for word in words
                if word in text
            )

            if score > 0:
                scored.append((score, role, content))

        # Выбираем наиболее подходящие воспоминания
        scored.sort(key=lambda item: item[0], reverse=True)

        memories = [
            {"role": role, "content": content}
            for score, role, content in scored[:3]
        ]

        history = [
            {"role": role, "content": content}
            for _, role, content in recent
        ]

        return memories, history


def clear_memory(user_id):
    with sqlite3.connect(DB_NAME) as db:
        db.execute(
            "DELETE FROM messages WHERE user_id = ?",
            (user_id,)
        )
