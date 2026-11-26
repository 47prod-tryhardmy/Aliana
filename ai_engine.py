
import os

from dotenv import load_dotenv
from openai import AsyncOpenAI

from memory import get_context, save_message

load_dotenv()

client = AsyncOpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com"
)

MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-flash")

# Загружаем личность персонажа
with open("character.txt", "r", encoding="utf-8") as file:
    CHARACTER = file.read()


async def generate_answer(user_id, user_message):

    # Сохраняем новое сообщение
    save_message(user_id, "user", user_message)

    # Извлекаем воспоминания и последние сообщения
    memories, history = get_context(
        user_id,
        user_message
    )

    # Формируем блок воспоминаний
    memory_text = "\n".join(
        [
            f"{item['role']}: {item['content']}"
            for item in memories
        ]
    )

    # Дополнительные инструкции
    instructions = f"""
{CHARACTER}

ДОПОЛНИТЕЛЬНЫЕ ПРАВИЛА:

Ты продолжаешь существующий диалог.
Учитывай всю доступную информацию.

Ниже представлены найденные фрагменты
из предыдущих разговоров.

Они являются архивными воспоминаниями,
а не новыми сообщениями пользователя.

АРХИВ:
{memory_text if memory_text else "Подходящие старые воспоминания не найдены."}

ТВОЯ ЗАДАЧА:

1. Внимательно учитывай предыдущие события.
2. Не противоречь установленным фактам.
3. Отвечай от лица своего персонажа.
4. Органично развивай сюжет.
5. Вплетай новые идеи в предложения пользователя.
6. Сохраняй естественность диалога.
7. Не раскрывай внутренние рассуждения.
8. Не придумывай события, которых не было.
"""

    response = await client.responses.create(
        model=MODEL,
        instructions=instructions,
        input=history,
        store=False
    )

    answer = response.output_text

    if not answer:
        answer = "Алиана задумалась, подбирая слова..."

    # Сохраняем ответ персонажа
    save_message(user_id, "assistant", answer)
    
    usage = response.usage
    logging.info(
        "tokens in=%s out=%s",
        usage.prompt_tokens,
        usage.completion_tokens,
    )
    return answer
