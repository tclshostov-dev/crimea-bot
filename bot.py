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
  """Расширенная база данных: Город + Настройки подписок (Свет, Вода, МАКС)"""
  conn = sqlite3.connect(DB_PATH)
  cursor = conn.cursor()
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            city TEXT,
            notify_light INTEGER DEFAULT 1,
            notify_water INTEGER DEFAULT 1,
            notify_max INTEGER DEFAULT 1,
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


def get_user(user_id: int):
  conn = sqlite3.connect(DB_PATH)
  cursor = conn.cursor()
  cursor.execute(
      "SELECT city, notify_light, notify_water, notify_max FROM users WHERE"
      " user_id = ?",
      (user_id,),
  )
  row = cursor.fetchone()
  conn.close()
  return row


def toggle_setting(user_id: int, field: str):
  conn = sqlite3.connect(DB_PATH)
  cursor = conn.cursor()
  cursor.execute(
      f"UPDATE users SET {field} = CASE WHEN {field} = 1 THEN 0 ELSE 1 END"
      " WHERE user_id = ?",
      (user_id,),
  )
  conn.commit()
  conn.close()


# Клавиатура выбора городов
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
      ]
  )


# Меню управления подписками (Свет, Вода, МАКС)
def get_dashboard_keyboard(user_data):
  city, light, water, max_net = user_data
  l_btn = "✅ Свет" if light else "❌ Свет"
  w_btn = "✅ Вода" if water else "❌ Вода"
  m_btn = "✅ Сеть МАКС" if max_net else "❌ Сеть МАКС"

  return InlineKeyboardMarkup(
      inline_keyboard=[
          [
              InlineKeyboardButton(text=l_btn, callback_data="toggle_light"),
              InlineKeyboardButton(text=w_btn, callback_data="toggle_water"),
          ],
          [
              InlineKeyboardButton(text=m_btn, callback_data="toggle_max"),
          ],
          [
              InlineKeyboardButton(
                  text="⚙️ Изменить город", callback_data="change_city"
              )
          ],
      ]
  )


async def cmd_start(message: types.Message):
  init_db()
  user = get_user(message.from_user.id)

  if not user or not user[0]:
    await message.answer(
        "⚡💧🌐 **Крым Монитор: Свет | Вода | Сеть МАКС**\n\n"
        "Выбери свой город для точечных оповещений об авариях:",
        reply_markup=get_cities_keyboard(),
        parse_mode="Markdown",
    )
  else:
    await message.answer(
        f"📍 **Твой город: {user[0]}**\n\nУправляй категориями уведомлений:",
        reply_markup=get_dashboard_keyboard(user),
        parse_mode="Markdown",
    )


async def process_callbacks(callback: types.CallbackQuery):
  user_id = callback.from_user.id
  data = callback.data

  if data == "change_city":
    await callback.message.edit_text(
        "Выбери город:", reply_markup=get_cities_keyboard()
    )
    await callback.answer()
    return

  if data.startswith("city_"):
    city = data.split("_")[1]
    save_user_city(user_id, callback.from_user.username or "none", city)
    user = get_user(user_id)
    await callback.message.edit_text(
        f"✅ **Город сохранен: {city}**\n\nНастрой нужные каналы уведомлений:",
        reply_markup=get_dashboard_keyboard(user),
        parse_mode="Markdown",
    )
    await callback.answer()
    return

  # Переключение тумблеров (Свет, Вода, МАКС)
  if data.startswith("toggle_"):
    field_map = {
        "toggle_light": "notify_light",
        "toggle_water": "notify_water",
        "toggle_max": "notify_max",
    }
    field = field_map.get(data)
    if field:
      toggle_setting(user_id, field)
      user = get_user(user_id)
      await callback.message.edit_reply_markup(
          reply_markup=get_dashboard_keyboard(user)
      )
      await callback.answer("Настройка обновлена!")


async def main():
  logging.basicConfig(level=logging.INFO)
  init_db()
  bot = Bot(token=TOKEN)
  dp = Dispatcher()

  dp.message.register(cmd_start, Command("start"))
  dp.callback_query.register(process_callbacks)

  print("🚀 Единый Монитор (TG + Сеть МАКС) запущен!")
  await bot.delete_webhook(drop_pending_updates=True)
  await dp.start_polling(bot)


if __name__ == "__main__":
  asyncio.run(main())
