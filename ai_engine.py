
# ai_engine.py

import os
import re
import logging
from typing import List, Dict

from dotenv import load_dotenv
from openai import AsyncOpenAI

from memory import save_message, get_context, get_user_settings

load_dotenv()

logger = logging.getLogger(__name__)

client = AsyncOpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url=os.getenv("DEEPSEEK_BASE_URL"),
    max_retries=3
)

MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-flash")

# Лимиты генерации
SHORT_TOKENS = 220
LONG_TOKENS = 650

# Максимальное количество дополнительных запросов
MAX_CONTINUATIONS = 3


def load_character() -> str:
    """Загрузка описания персонажа."""
    with open("character.txt", "r", encoding="utf-8") as f:
        return f.read().strip()


CHARACTER = load_character()


def build_system_prompt(long_mode: bool) -> str:
    """Создание системного промпта."""

    if long_mode:
        format_instruction = """
ФОРМАТ ОТВЕТА (ДЛИННЫЙ РЕЖИМ):

Чередуй художественное повествование и диалоги.

1. Действия, эмоции, мысли и ощущения Алианы описывай от первого лица курсивом, отдельными абзацами.
2. Реплики оформляй отдельными строками через тире, без кавычек.
3. Используй несколько чередующихся абзацев, если этого требует сцена.
4. Допускаются подробные описания жестов, мимики и обстановки.
5. Сохраняй естественный художественный стиль, как в примере:
   
*Я улыбаюсь и осторожно беру тебя за руку.*

— Не волнуйся. Мы обязательно что-нибудь придумаем.

*Я отвожу взгляд к окну, ненадолго задумываясь.*

— А пока расскажи мне, что произошло.

Не превращай ответ в сплошной рассказ. Не злоупотребляй описаниями.
"""

    else:
        format_instruction = """
ФОРМАТ ОТВЕТА (КОРОТКИЙ РЕЖИМ):

1. Начинай с одного короткого описания действия или эмоции от первого лица курсивом.
2. Затем пиши одну законченную реплику через тире, без кавычек.
3. Используй естественную разговорную речь.
4. Не добавляй длинных описаний и лишних абзацев.

Пример:

*Я слегка улыбаюсь и смущённо отвожу взгляд.*

— Здравствуйте, господин... Я уж думала, вы забыли обо мне.
"""

    return f"""{CHARACTER}

{format_instruction}

ОБЩИЕ ПРАВИЛА:
- Всегда оставайся Алианой.
- Соблюдай факты и хронологию диалога.
- Не управляй персонажем пользователя.
- Не повторяй уже сказанное без необходимости.
- Не раскрывай внутренние рассуждения.
- Завершай ответ логически законченным предложением.
- Не обрывай реплики и описания посреди мысли.
"""


async def request_completion(
    messages: List[Dict],
    max_tokens: int
):
    """Отправка запроса к DeepSeek."""

    return await client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.7,
        max_tokens=max_tokens
    )


def trim_incomplete_answer(text: str) -> str:
    """Удаление незаконченного последнего предложения."""

    text = text.strip()

    if not text:
        return text

    # Если текст уже заканчивается знаком завершения,
    # дополнительная обрезка не нужна.
    if re.search(r'[.!?…][»"”’)]*$', text):
        return text

    # Находим последнее завершённое предложение.
    matches = list(re.finditer(r'[.!?…][»"”’)]*', text))

    if matches:
        return text[:matches[-1].end()].strip()

    return text


async def generate_answer(user_id: int, user_message: str) -> str:
    """Генерация ответа Алианы."""

    save_message(user_id, "user", user_message)

    settings = get_user_settings(user_id)
    long_mode = settings.get("long_mode", False)

    history = get_context(
        user_id,
        max_messages=16 if long_mode else 10
    )

    system_prompt = build_system_prompt(long_mode)

    messages = [
        {"role": "system", "content": system_prompt},
        *history
    ]

    max_tokens = LONG_TOKENS if long_mode else SHORT_TOKENS

    try:
        # Первая генерация
        response = await request_completion(
            messages,
            max_tokens
        )

        answer = response.choices[0].message.content or ""
        finish_reason = response.choices[0].finish_reason

        # Если ответ оборвался из-за ограничения токенов,
        # запрашиваем продолжение.
        continuation_count = 0

        while (
            finish_reason == "length"
            and continuation_count < MAX_CONTINUATIONS
        ):
            continuation_count += 1

            continuation_messages = messages + [
                {
                    "role": "assistant",
                    "content": answer
                },
                {
                    "role": "user",
                    "content": (
                        "Продолжи ответ строго с места остановки. "
                        "Не повторяй предыдущий текст. "
                        "Закончи текущую мысль и заверши ответ "
                        "логически законченным предложением. "
                        "Сохраняй установленный формат общения."
                    )
                }
            ]

            response = await request_completion(
                continuation_messages,
                350 if long_mode else 180
            )

            continuation = response.choices[0].message.content or ""
            finish_reason = response.choices[0].finish_reason

            answer += continuation

        # Убираем возможный незаконченный фрагмент,
        # если все попытки продолжения исчерпаны.
        if finish_reason == "length":
            answer = trim_incomplete_answer(answer)

        answer = answer.strip()

        if not answer:
            answer = " *Алиана ненадолго задумалась.*"

    except Exception:
        logger.exception("Ошибка генерации ответа")
        answer = " *Алиана задумалась, подбирая слова...*"

    save_message(user_id, "assistant", answer)

    return answer
