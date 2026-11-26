# ai_engine.py
import os
import logging
from dotenv import load_dotenv
from openai import AsyncOpenAI

from memory import save_message, get_context, get_user_settings

load_dotenv()

logger = logging.getLogger(__name__)

client = AsyncOpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    max_retries=3
)

MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-flash")


def load_character() -> str:
    """Загрузка описания персонажа."""
    with open("character.txt", "r", encoding="utf-8") as f:
        return f.read()


CHARACTER = load_character()


async def generate_answer(user_id: int, user_message: str) -> str:
    """Генерация ответа Алианы с оптимизацией токенов."""

    save_message(user_id, "user", user_message)

    settings = get_user_settings(user_id)
    long_mode = settings.get("long_mode", False)

    history = get_context(user_id, max_messages=16 if long_mode else 10)

    system_prompt = build_system_prompt(long_mode)

    messages = [
        {"role": "system", "content": system_prompt},
        *history
    ]

    try:
        response = await client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0.7,
            max_tokens=500 if long_mode else 200
        )

        answer = response.choices[0].message.content.strip()

    except Exception as e:
        logger.exception("Ошибка генерации ответа")
        answer = "Элиана задумалась, подбирая слова..."

    save_message(user_id, "assistant", answer)
    return answer


def build_system_prompt(long_mode: bool) -> str:
    """Сборка системного промпта с оптимизацией токенов."""

    format_instruction = (
        "ФОРМАТ ОТВЕТА:\n"
        "- Одна строка описания действия\n"
        "- Одна фраза Алианы\n\n"
        "Пример:\n"
        "Алиана улыбнулась, глядя на тебя.\n"
        "\"Привет, как твои дела?\""
    ) if not long_mode else "Отвечай развёрнуто, как в неспешной беседе."

    return f"""{CHARACTER}

{format_instruction}

ПРАВИЛА:
1. Не противоречь фактам из истории
2. Сохраняй естественность диалога
3. Не раскрывай внутренние рассуждения"""
