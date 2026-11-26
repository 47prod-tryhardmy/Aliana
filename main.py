
import asyncio
import os
import logging

from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message


from ai_engine import generate_answer
from memory import init_db, clear_memory

load_dotenv()

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("Не найден BOT_TOKEN в файле .env")
bot = Bot(token=BOT_TOKEN)

dp = Dispatcher()


@dp.message(CommandStart())
async def start(message: Message):

    await message.answer(
        "Привет! Я Алиана.\n\n"
        "Рада нашей встрече. "
        "О чём поговорим?"
    )


@dp.message(Command("reset"))
async def reset(message: Message):

    clear_memory(message.from_user.id)

    await message.answer(
        "Мои воспоминания о нашем разговоре "
        "начались заново."
    )


@dp.message(F.text)
async def handle_message(message: Message):

    user_id = message.from_user.id
    user_text = message.text

    await bot.send_chat_action(
        chat_id=message.chat.id,
        action="typing"
    )

    try:

        answer = await generate_answer(
            user_id,
            user_text
        )

        # Telegram ограничивает длину одного сообщения
        for i in range(0, len(answer), 4000):
            await message.answer(answer[i:i + 4000])

    except Exception as error:

        logging.exception("Ошибка генерации")
        await message.answer(f"DEBUG: {type(error).__name__}: {error}")
        await message.answer(
            "Прости, сейчас мне не удалось "
            "собраться с мыслями. Попробуй ещё раз."
        )


async def main():
    os.makedirs("/var/data", exist_ok=True)
    os.environ.setdefault("DATA_DIR", "/var/data")
    init_db()

    print("Fantasy Novel Bot запущен!")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
