import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

# --- ТВОИ ДАННЫЕ ---
API_TOKEN = '8671861165:AAFf3H08iwrLfuToHCqIqEEiCy1r04ERjyE'
ADMIN_ID = 8777986259
PRICE = 4.5

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Временная база (в реальности лучше использовать БД)
user_db = {} # {id: {'balance': 0, 'sold': 0, 'name': ''}}
all_users = set() # Для рассылки

def register_user(user: types.User):
    all_users.add(user.id)
    if user.id not in user_db:
        user_db[user.id] = {'balance': 0, 'sold': 0, 'name': user.first_name}

# --- КЛАВИАТУРЫ ---
def main_kb(user_id):
    kb = ReplyKeyboardBuilder()
    kb.button(text="💰 Продать токен")
    kb.button(text="👤 Профиль")
    if user_id == ADMIN_ID:
        kb.button(text="⚙️ Админка")
    kb.adjust(2)
    return kb.as_markup(resize_keyboard=True)

# --- ОБРАБОТЧИКИ ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    register_user(message.from_user)
    await message.answer(
        f"🌟 **Здравствуйте, {message.from_user.first_name}!** 🌟\n\n"
        f"🚀 Вы попали в бота по покупке токенов!\n"
        f"💎 Мы скупаем токены по **{PRICE}$** за файл! 💎\n\n"
        f"Жми кнопку ниже, чтобы начать! 👇",
        reply_markup=main_kb(message.from_user.id),
        parse_mode="Markdown"
    )

@dp.message(F.text == "👤 Профиль")
async def view_profile(message: types.Message):
    register_user(message.from_user)
    user = user_db[message.from_user.id]
    await message.answer(
        f"👤 **Твой профиль** ✨\n\n"
        f"🆔 ID: `{message.from_user.id}`\n"
        f"📦 Продано файлов: {user['sold']} шт. 📈\n"
        f"💵 Баланс: {user['balance']}$ 💰",
        parse_mode="Markdown"
    )

@dp.message(F.text == "💰 Продать токен")
async def sell_info(message: types.Message):
    await message.answer("📁 **Пришлите файл .txt с токенами** 📥\n"
                         "Наш админ проверит его в кратчайшие сроки! ⚡️")

# --- ЛОГИКА ДЛЯ АДМИНА ---

@dp.message(F.text == "⚙️ Админка", F.from_user.id == ADMIN_ID)
async def admin_panel(message: types.Message):
    kb = InlineKeyboardBuilder()
    kb.button(text="📢 Сделать рассылку", callback_data="admin_broadcast")
    kb.button(text="📊 Статистика", callback_data="admin_stats")
    await message.answer("🛠 **Панель администратора**\nВыберите действие:", reply_markup=kb.as_markup())

@dp.callback_query(F.data == "admin_stats")
async def admin_stats(call: types.CallbackQuery):
    await call.message.answer(f"📊 **Статистика бота:**\n\n👤 Всего юзеров: {len(all_users)}\n💰 Выплачено (виртуально): {sum(u['balance'] for u in user_db.values())}$")
    await call.answer()

@dp.callback_query(F.data == "admin_broadcast")
async def start_broadcast(call: types.CallbackQuery):
    await call.message.answer("📝 **Введите текст для рассылки всем пользователям:**")
    # Здесь можно было бы использовать FSM, но для простоты сделаем ожидание следующего сообщения

# Логика получения ФАЙЛА
@dp.message(F.document)
async def handle_docs(message: types.Message):
    if message.document.file_name.endswith('.txt'):
        register_user(message.from_user)
        
        # Кнопки для тебя
        check_kb = InlineKeyboardBuilder()
        check_kb.button(text="✅ Принять", callback_data=f"win_{message.from_user.id}")
        check_kb.button(text="❌ Отклонить", callback_data=f"fail_{message.from_user.id}")

        # Пересылаем файл тебе
        await bot.send_document(
            ADMIN_ID,
            message.document.file_id,
            caption=f"📩 **Новый файл на проверку!**\n👤 От: {message.from_user.full_name} (`{message.from_user.id}`)",
            reply_markup=check_kb.as_markup(),
            parse_mode="Markdown"
        )
        await message.answer("📩 **Файл получен и отправлен на проверку!** ⏳\nОжидайте уведомления ✅")
    else:
        await message.answer("❌ Пожалуйста, присылайте только файлы формата **.txt**")

# Обработка решения админа
@dp.callback_query(F.data.startswith(("win_", "fail_")))
async def process_check(callback: types.CallbackQuery):
    action, client_id = callback.data.split("_")
    client_id = int(client_id)

    if action == "win":
        user_db[client_id]['sold'] += 1
        user_db[client_id]['balance'] += PRICE
        await bot.send_message(client_id, "✅ **Ваш файл проверен!** 💰\nОплата зачислена на баланс в профиле.")
        res = "ПРИНЯТО ✅"
    else:
        await bot.send_message(client_id, "❌ **Ваш файл отклонен (невалид).** 😔")
        res = "ОТКЛОНЕНО ❌"

    await callback.message.edit_caption(caption=f"{callback.message.caption}\n\n📝 Итог: **{res}**")

# Очень простая реализация рассылки (хватает любое текстовое сообщение, если админ нажал кнопку)
@dp.message(F.from_user.id == ADMIN_ID)
async def broadcast_handler(message: types.Message):
    if message.text not in ["💰 Продать токен", "👤 Профиль", "⚙️ Админка"]:
        count = 0
        for user_id in all_users:
            try:
                await bot.send_message(user_id, f"📢 **Объявление:**\n\n{message.text}", parse_mode="Markdown")
                count += 1
            except: pass
        await message.answer(f"✅ Рассылка завершена! Получили {count} человек.")

async def main():
    print("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
                    
