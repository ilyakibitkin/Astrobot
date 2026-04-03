
import asyncio
import json
import uuid
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, F, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice, PreCheckoutQuery
from aiogram.filters import CommandStart

# ====== КОНФИГ ======
BOT_TOKEN = "8335279244:AAEl_ICWZzgmvY2kfL6HtJdmpBJHFzoftgw"  # ← Замените на свой токен
DB_FILE = "users.json"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ====== БАЗА ДАННЫХ ======
def load_db():
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def get_user_key(user_id):
    db = load_db()
    user_id = str(user_id)
    if user_id not in db:
        return None
    expires = datetime.fromisoformat(db[user_id]["expires"])
    if expires < datetime.now():
        return None
    return db[user_id]["uuid"]

def add_subscription(user_id, days=30):
    db = load_db()
    user_id = str(user_id)
    if user_id in db:
        # Если есть активная подписка, продлеваем
        expires = datetime.fromisoformat(db[user_id]["expires"])
        if expires > datetime.now():
            new_expires = expires + timedelta(days=days)
        else:
            new_expires = datetime.now() + timedelta(days=days)
    else:
        new_expires = datetime.now() + timedelta(days=days)
    
    user_uuid = str(uuid.uuid4())
    db[user_id] = {
        "uuid": user_uuid,
        "expires": new_expires.isoformat(),
        "created": datetime.now().isoformat()
    }
    save_db(db)
    return user_uuid

# ====== КЛАВИАТУРЫ ======
def main_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⭐️ Получить доступ", callback_data="buy")],
            [InlineKeyboardButton(text="🔑 Мой ключ", callback_data="mykey")],
            [InlineKeyboardButton(text="📺 Гайд", callback_data="guide")],
            [InlineKeyboardButton(text="🛠 Поддержка", callback_data="support")]
        ]
    )

def guide_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🤖 Android", callback_data="guide_android")],
            [InlineKeyboardButton(text="🍏 iOS", callback_data="guide_ios")]
        ]
    )

# ====== /START ======
@dp.message(CommandStart())
async def start_command(message: types.Message):
    text = (
        "👋 Добро пожаловать!\n\n"
        "📦 Доступ к сервису стоит всего 1 звезду\n"
        "💰 Оплата через Telegram Stars\n\n"
        "⚡️ После оплаты вы получите уникальный ключ доступа"
    )
    await message.answer(text, reply_markup=main_menu())

# ====== КНОПКА "МОЙ КЛЮЧ" ======
@dp.callback_query(F.data == "mykey")
async def mykey_command(call: types.CallbackQuery):
    user_id = call.from_user.id
    user_key = get_user_key(user_id)
    if user_key:
        db = load_db()
        expires = datetime.fromisoformat(db[str(user_id)]["expires"])
        days_left = (expires - datetime.now()).days
        text = (
            f"✅ Ваш ключ активен!\n\n"
            f"🔑 Ключ доступа:\n<code>{user_key}</code>\n\n"
            f"📅 Действует до: {expires.strftime('%d.%m.%Y')}\n"
            f"⏱️ Осталось дней: {days_left}"
        )
    else:
        text = "❌ У вас нет активного ключа.\nНажмите «⭐️ Получить доступ» для покупки."
    await call.message.answer(text, parse_mode="HTML")
    await call.answer()

# ====== КНОПКА "ПОЛУЧИТЬ ДОСТУП" ======
@dp.callback_query(F.data == "buy")
async def buy_command(call: types.CallbackQuery):
    prices = [LabeledPrice(label="Доступ к сервису", amount=1)]
    await call.message.answer_invoice(
        title="🔐 Доступ к сервису",
        description="Полный доступ ко всем функциям\nСрок: 30 дней",
        payload="subscription_30_days",
        currency="XTR",
        prices=prices,
        start_parameter="subscription",
        provider_token=None  # Telegram Stars
    )
    await call.answer()


# ====== ПРЕДВАРИТЕЛЬНЫЙ ЗАПРОС ======
@dp.pre_checkout_query()
async def pre_checkout(pre_checkout_query: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

# ====== УСПЕШНАЯ ОПЛАТА ======
@dp.message(F.successful_payment)
async def successful_payment(message: types.Message):
    user_id = message.from_user.id
    user_key = add_subscription(user_id, days=30)
    db = load_db()
    expires = datetime.fromisoformat(db[str(user_id)]["expires"])
    text = (
        "🎉 Оплата успешно принята!\n\n"
        f"🔑 Ваш ключ доступа:\n<code>{user_key}</code>\n\n"
        f"✅ Подписка активна до: {expires.strftime('%d.%m.%Y')}\n"
        f"⏱️ Срок: 30 дней"
    )
    await message.answer(text, parse_mode="HTML")

# ====== КНОПКА "ГАЙД" ======
@dp.callback_query(F.data == "guide")
async def guide_command(call: types.CallbackQuery):
    await call.message.answer("📺 Выберите платформу:", reply_markup=guide_menu())
    await call.answer()

@dp.callback_query(F.data == "guide_ios")
async def guide_ios_command(call: types.CallbackQuery):
    text = (
        "🍏 Чтобы активировать VPN на iPhone:\n\n"
        "1️⃣ Скачайте приложение [V2RayTun](https://apps.apple.com/ru/app/v2raytun/id6476628951)\n"
        "2️⃣ Вставьте порт, который вы получили после оплаты\n"
        "3️⃣ Активируйте VPN\n\n"
        "📹 Видео-инструкция:\n"
        "https://apps.apple.com/ru/app/v2raytun/id6476628951"
    )
    await call.message.answer(text, parse_mode="Markdown", disable_web_page_preview=False)
    await call.answer()

@dp.callback_query(F.data == "guide_android")
async def guide_android_command(call: types.CallbackQuery):
    await call.message.answer("🤖 Инструкция для Android будет добавлена позже.")
    await call.answer()

# ====== КНОПКА "ПОДДЕРЖКА" ======
@dp.callback_query(F.data == "support")
async def support_command(call: types.CallbackQuery):
    await call.message.answer("🛠 Поддержка пока недоступна. Скоро будет информация.")
    await call.answer()

# ====== ОБРАБОТКА ВСЕХ ТЕКСТОВЫХ СООБЩЕНИЙ ======
@dp.message()
async def text_messages(message: types.Message):
    # Показываем главное меню на любое текстовое сообщение
    await message.answer("Используйте кнопки ниже:", reply_markup=main_menu())

# ====== ЗАПУСК БОТА ======
async def main():
    print("🤖 Бот запущен!")
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            db = json.load(f)
            print(f"👥 Пользователей в базе: {len(db)}")
    except:
        print("📁 Файл базы данных будет создан при первой оплате")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())