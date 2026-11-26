# ai_engine.py
import os
import logging
from typing import List, Dict
from dotenv import load_dotenv
from openai import AsyncOpenAI

from memory import save_message, get_context, get_user_settings

load_dotenv()

logger = logging.getLogger(__name__)

client = AsyncOpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"), base_url=os.getenv("DEEPSEEK_BASE_URL"),
    max_retries=3
)

MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-flash")


def load_character() -> str:
    """Загрузка описания персонажа."""
    with open("character.txt", "r", encoding="utf-8") as f:
        return f.read().strip()


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
    
    # Измененный формат инструкций
    format_instruction = """
ПРАВИЛА ФОРМАТИРОВАНИЯ ОТВЕТА:

1.  **Повествование:** Описывай действия, ощущения и мысли Алианы. Используй курсив для выделения внутренних переживаний или особых моментов.
    Пример: *Я вздрагиваю от твоих слов...*

2.  **Реплики:** Диалоги оформляй тире и кавычками.
    Пример: — Спасибо... я... я не забуду вашей доброты.

3.  **Контекст:** Если нужно, можешь использовать короткие описания перед репликой, как в примере выше.

Если режим длинных ответов включен, отвечай развёрнуто, следуя этим правилам.
Если режим коротких ответов, старайся быть лаконичнее, но сохраняй структуру.
""" if long_mode else """
ПРАВИЛА ФОРМАТИРОВАНИЯ ОТВЕТА (КРАТКИЙ РЕЖИМ):

1.  **Повествование:** Кратко описывай действия.
2.  **Реплики:** Оформляй тире и кавычками.

Пример:
Алиана улыбнулась.
— Привет! Как дела?
"""
    
    return f"""{CHARACTER}

{format_instruction}

ДОПОЛНИТЕЛЬНЫЕ ПРАВИЛА:
1. Не противоречь фактам из истории
2. Сохраняй естественность диалога
3. Не раскрывай внутренние рассуждения"""
