import asyncio
import logging
import os
import sqlite3
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
DB_PATH = "crimea_bot.db"


def init_db():
  conn = sqlite3.connect(DB_PATH)
  cursor = conn.cursor()
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            city TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
  conn.commit()
  conn.close()


def save_user_city(user_id: int, username: str, city: str):
  conn = sqlite3.connect(DB_PATH)
  cursor = conn.cursor()
  cursor.execute(
      """
        INSERT INTO users (user_id, username, city, updated_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(user_id) DO UPDATE SET 
            city = excluded.city,
            username = excluded.username,
            updated_at = CURRENT_TIMESTAMP
    """,
      (user_id, username, city),
  )
  conn.commit()
  conn.close()


def get_cities_keyboard():
  return InlineKeyboardMarkup(
      inline_keyboard=[
          [
              InlineKeyboardButton(text="🏙 Судак", callback_data="city_Судак"),
              InlineKeyboardButton(
                  text="🌊 Феодосия", callback_data="city_Феодосия"
              ),
          ],
          [
              InlineKeyboardButton(text="⚓ Керчь", callback_data="city_Керчь"),
              InlineKeyboardButton(
                  text="🏛 Симферополь", callback_data="city_Симферополь"
              ),
          ],
          [
              InlineKeyboardButton(
                  text="⚙️ Сменить город", callback_data="change_city"
              )
          ],
      ]
  )


async def cmd_start(message: types.Message):
  init_db()
  await message.answer(
      "⚡💧 **Крымский Монитор Систем**\n\n"
      "Выбери свой город, чтобы получать уведомления об отключениях:",
      reply_markup=get_cities_keyboard(),
      parse_mode="Markdown",
  )


async def process_city_callback(callback: types.CallbackQuery):
  data = callback.data
  user = callback.from_user

  if data == "change_city":
    await callback.message.edit_text(
        "Выбери город:", reply_markup=get_cities_keyboard()
    )
    await callback.answer()
    return

  if data.startswith("city_"):
    selected_city = data.split("_")[1]
    save_user_city(user.id, user.username or "нет_username", selected_city)
    await callback.message.edit_text(
        f"✅ **Город зафиксирован: {selected_city}**\n\n"
        f"Как только появится инфа по {selected_city}, бот пришлет молнию.",
        parse_mode="Markdown",
    )
    await callback.answer(f"Сохранено: {selected_city}")


async def main():
  logging.basicConfig(level=logging.INFO)
  init_db()
  bot = Bot(token=TOKEN)
  dp = Dispatcher()

  dp.message.register(cmd_start, Command("start"))
  dp.callback_query.register(
      process_city_callback,
      F.data.startswith("city_") | (F.data == "change_city"),
  )

  print("🚀 Бот запущен!")
  await dp.delete_webhook(drop_pending_updates=True)
  await dp.start_polling(bot)


if __name__ == "__main__":
  asyncio.run(main())
