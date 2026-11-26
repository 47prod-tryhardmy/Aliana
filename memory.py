# memory.py
import sqlite3
import os
from typing import List, Dict, Optional

DATA_DIR = os.environ.get("DATA_DIR", "/var/data")


def init_db():
    """Инициализация базы данных."""
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(f"{DATA_DIR}/memory.db")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_user_id ON messages(user_id)")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_settings (
            user_id INTEGER PRIMARY KEY,
            long_mode BOOLEAN DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()


def save_message(user_id: int, role: str, content: str) -> None:
    """Сохранение сообщения в БД."""
    conn = sqlite3.connect(f"{DATA_DIR}/memory.db")
    conn.execute(
        "INSERT INTO messages (user_id, role, content) VALUES (?, ?, ?)",
        (user_id, role, content)
    )
    conn.commit()
    conn.close()


def get_context(user_id: int, max_messages: int = 20) -> List[Dict[str, str]]:
    """Получение истории диалога пользователя."""
    conn = sqlite3.connect(f"{DATA_DIR}/memory.db")
    cursor = conn.execute(
        "SELECT role, content FROM messages WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
        (user_id, max_messages)
    )
    messages = cursor.fetchall()
    conn.close()
    
    return [{"role": m[0], "content": m[1]} for m in reversed(messages)]


def clear_memory(user_id: int) -> None:
    """Очистка истории пользователя."""
    conn = sqlite3.connect(f"{DATA_DIR}/memory.db")
    conn.execute("DELETE FROM messages WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


def get_user_settings(user_id: int) -> Dict:
    """Получение настроек пользователя."""
    conn = sqlite3.connect(f"{DATA_DIR}/memory.db")
    cursor = conn.execute(
        "SELECT long_mode FROM user_settings WHERE user_id = ?",
        (user_id,)
    )
    result = cursor.fetchone()
    conn.close()
    
    return {"long_mode": bool(result[0]) if result else False}


def set_user_long_mode(user_id: int, long_mode: bool) -> None:
    """Установка режима длины ответов."""
    conn = sqlite3.connect(f"{DATA_DIR}/memory.db")
    conn.execute(
        "INSERT OR REPLACE INTO user_settings (user_id, long_mode) VALUES (?, ?)",
        (user_id, long_mode)
    )
    conn.commit()
    conn.close()
