# main.py
import asyncio
import os
import logging

from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from ai_engine import generate_answer
from memory import init_db, clear_memory, get_user_settings, set_user_long_mode

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в .env")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

WELCOME_VIDEO = "welcome.mp4"


@dp.message(CommandStart())
async def cmd_start(message: Message):
    """Команда /start."""
    await send_welcome(message)


async def send_welcome(message: Message):
    """Отправка приветственного сообщения."""
    welcome_text = (
        "Привет, я Алиана.\n\n"
        "Рада нашей встрече. Мы можем поболтать о чём угодно — "
        "о магии, приключениях или просто о жизни.\n\n"
        "Расскажи, что привело тебя в мою библиотеку?"
    )
    
    try:
        if os.path.exists(WELCOME_VIDEO):
            await message.answer_video(
                video=open(WELCOME_VIDEO, "rb"),
                caption=welcome_text,
            )
        else:
            await message.answer(welcome_text)
    except Exception as e:
        logger.exception("Ошибка отправки видео")
        await message.answer(welcome_text)


@dp.message(Command("reset"))
async def cmd_reset(message: Message):
    """Команда /reset с подтверждением."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Давай", callback_data="reset_confirm"),
            InlineKeyboardButton(text="Отмена", callback_data="reset_cancel")
        ]
    ])
    
    await message.answer(
        "Ты хочешь начать нашу историю сначала? Я ведь все забуду.",
        reply_markup=keyboard
    )


@dp.callback_query(F.data.in_({"reset_confirm", "reset_cancel"}))
async def reset_callback(query: CallbackQuery):
    """Обработка подтверждения сброса."""
    if query.data == "reset_confirm":
        clear_memory(query.from_user.id)
        await query.message.delete()
        await bot.send_message(
            chat_id=query.message.chat.id,
            text=(
                "Привет, я Алиана.\n\n"
                "Рада нашей встрече. Мы можем поболтать о чём угодно — "
                "о магии, приключениях или просто о жизни.\n\n"
                "Расскажи, что привело тебя в мою библиотеку?"
            )
        )
    else:
        await query.answer("Сброс отменён")
        await query.message.delete()


@dp.message(Command("longer"))
async def cmd_longer(message: Message):
    """Команда /longer для переключения длины ответов."""
    settings = get_user_settings(message.from_user.id)
    current_long_mode = settings.get("long_mode", False)
    
    if current_long_mode:
        question = "Я уже отвечаю тебе подробнее. \nТы хочешь уменьшить длину ответов?"
        new_mode = False
    else:
        question = "Ты хочешь увеличить длину моих ответов, так, как будто мы разговариваем неспеша?"
        new_mode = True
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Давай", callback_data=f"longer_{str(new_mode).lower()}"),
            InlineKeyboardButton(text="Отмена", callback_data="longer_cancel")
        ]
    ])
    
    await message.answer(question, reply_markup=keyboard)


@dp.callback_query(F.data.startswith("longer_"))
async def longer_callback(query: CallbackQuery):
    """Обработка переключения длины ответов."""
    data = query.data.split("_")[1]
    
    if data == "cancel":
        await query.answer("Изменение отменено")
        await query.message.delete()
        return
    
    new_mode = data == "true"
    set_user_long_mode(query.from_user.id, new_mode)
    
    await query.message.delete()
    mode_text = "увеличена" if new_mode else "уменьшена"
    await bot.send_message(
        chat_id=query.message.chat.id,
        text=f"Длина моих ответов {mode_text}."
    )


@dp.message(F.text & ~F.text.startswith("/"))
async def handle_message(message: Message):
    """Обработка текстовых сообщений."""
    user_id = message.from_user.id
    user_text = message.text
    
    await bot.send_chat_action(
        chat_id=message.chat.id,
        action="typing"
    )
    
    try:
        answer = await generate_answer(user_id, user_text)
        
        for i in range(0, len(answer), 4000):
            await message.answer(answer[i:i + 4000])
            
    except Exception as e:
        logger.exception("Ошибка генерации")
        await message.answer(
            "Прости, сейчас мне не удалось собраться с мыслями. Попробуй ещё раз."
        )


async def main():
    """Запуск бота."""
    init_db()
    logger.info("Fantasy Novel Bot запущен!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
