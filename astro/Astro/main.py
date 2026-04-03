import asyncio
import json
import uuid
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, F, types
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    LabeledPrice, PreCheckoutQuery
)
from aiogram.filters import CommandStart

# ====== КОНФИГ ======
BOT_TOKEN = "ВАШ_ТОКЕН"
TRIBUTE_LINK = "https://tribute.tg/ВАШ_НИКНЕЙМ"
SUPPORT_USERNAME = "@ВАШ_НИКНЕЙМ"
ADMIN_ID = 123456789
STARS_AMOUNT = 199      # 199 звёзд
PRICE_RUB = 199         # 199 рублей
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

def create_user(user_id, name):
    db = load_db()
    uid = str(user_id)
    if uid not in db:
        db[uid] = {
            "name": name,
            "balance": 0,
            "subscription": None,
            "total_paid": 0
        }
        save_db(db)

def set_subscription(user_id, days=30, source="stars"):
    db = load_db()
    uid = str(user_id)
    if uid not in db:
        return None, None

    existing = db[uid].get("subscription")
    if existing:
        old_exp = datetime.fromisoformat(existing["expires"])
        base = old_exp if old_exp > datetime.now() else datetime.now()
        user_uuid = existing["uuid"]
    else:
        base = datetime.now()
        user_uuid = str(uuid.uuid4())

    expires = base + timedelta(days=days)
    db[uid]["subscription"] = {
        "uuid": user_uuid,
        "expires": expires.isoformat(),
        "source": source,
        "created": datetime.now().isoformat()
    }
    db[uid]["total_paid"] = db[uid].get("total_paid", 0) + 1
    save_db(db)
    return user_uuid, expires

def get_active_subscription(user_id):
    db = load_db()
    uid = str(user_id)
    if uid not in db:
        return None
    sub = db[uid].get("subscription")
    if not sub:
        return None
    if datetime.fromisoformat(sub["expires"]) > datetime.now():
        return sub
    return None

def revoke_subscription(user_id):
    db = load_db()
    uid = str(user_id)
    if uid in db:
        db[uid]["subscription"] = None
        save_db(db)
        return True
    return False

def get_user(user_id):
    db = load_db()
    return db.get(str(user_id))

# ====== КЛАВИАТУРЫ ======
def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐️ Получить доступ", callback_data="buy")],
        [InlineKeyboardButton(text="🔑 Мой ключ", callback_data="mykey")],
        [InlineKeyboardButton(text="📖 Гайд по подключению", callback_data="guide")],
        [InlineKeyboardButton(text="🆘 Поддержка", callback_data="support")]
    ])

def back_to_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu")]
    ])

def guide_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🍏 iOS", callback_data="guide_ios")],
        [InlineKeyboardButton(text="🤖 Android", callback_data="guide_android")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu")]
    ])

def buy_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"⭐️ Telegram Stars ({STARS_AMOUNT} ⭐)",
            callback_data="pay_stars"
        )],
        [InlineKeyboardButton(
            text=f"💳 СБП / Карта ({PRICE_RUB} ₽)",
            callback_data="pay_tribute"
        )],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu")]
    ])

# ====== ЧЕК ======
async def send_receipt(chat_id, user_uuid, expires, stars_amount=None, source="stars"):
    if source == "stars":
        method = f"⭐️ Telegram Stars ({stars_amount} ⭐)"
    elif source == "manual":
        method = "👤 Выдан администратором"
    else:
        method = f"💳 СБП / Карта ({PRICE_RUB} ₽)"

    text = (
        "🧾 <b>ЧЕК ОБ ОПЛАТЕ</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"📦 Товар: VPN доступ на 30 дней\n"
        f"💳 Способ: {method}\n"
        f"📅 Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
        f"⏳ Истекает: {expires.strftime('%d.%m.%Y %H:%M')}\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"🔑 Ваш ключ:\n<code>{user_uuid}</code>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "💡 Нажмите на ключ чтобы скопировать\n"
        "📖 Как подключить — раздел <b>Гайд</b>"
    )
    await bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=back_to_menu())

# ====== ПРОФИЛЬ ======
async def show_profile(chat_id, user_id, message_id=None):
    db = load_db()
    uid = str(user_id)
    if uid not in db:
        return
    user = db[uid]
    active_sub = get_active_subscription(user_id)

    if active_sub:
        exp = datetime.fromisoformat(active_sub["expires"])
        sub_text = f"✅ Подписка активна до {exp.strftime('%d.%m.%Y %H:%M')}"
    else:
        sub_text = "❌ Подписка отсутствует"

    text = (
        f"👋 Привет, {user['name']}!\n\n"
        f"🆔 ID: <code>{uid}</code>\n"
        f"💰 Стоимость: {PRICE_RUB} ₽ / {STARS_AMOUNT} ⭐\n\n"
        f"{sub_text}"
    )
    if message_id:
        await bot.edit_message_text(
            text=text, chat_id=chat_id,
            message_id=message_id,
            reply_markup=main_menu(),
            parse_mode="HTML"
        )
    else:
        await bot.send_message(
            chat_id, text,
            reply_markup=main_menu(),
            parse_mode="HTML"
        )

# ====== СТАРТ ======
@dp.message(CommandStart())
async def start_command(message: types.Message):
    create_user(message.from_user.id, message.from_user.first_name or "Пользователь")
    await show_profile(message.chat.id, message.from_user.id)

# ====== МЕНЮ ======
@dp.callback_query(F.data == "menu")
async def menu_callback(call: types.CallbackQuery):
    await show_profile(
        call.message.chat.id,
        call.from_user.id,
        call.message.message_id
    )
    await call.answer()

# ====== МОЙ КЛЮЧ ======
@dp.callback_query(F.data == "mykey")
async def mykey_callback(call: types.CallbackQuery):
    active_sub = get_active_subscription(call.from_user.id)
    if active_sub:
        exp = datetime.fromisoformat(active_sub["expires"])
        text = (
            "🔑 <b>Ваш активный ключ:</b>\n\n"
            f"<code>{active_sub['uuid']}</code>\n\n"
            f"📅 Действует до: {exp.strftime('%d.%m.%Y %H:%M')}\n\n"
            "💡 Нажмите на ключ чтобы скопировать"
        )
    else:
        text = (
            "❌ У вас нет активного ключа.\n\n"
            "Нажмите <b>⭐️ Получить доступ</b> чтобы оформить подписку."
        )
    await bot.edit_message_text(
        text=text, chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=back_to_menu(),
        parse_mode="HTML"
    )
    await call.answer()

# ====== ГАЙД (ИСПРАВЛЕН) ======
@dp.callback_query(F.data == "guide")
async def guide_callback(call: types.CallbackQuery):
    await bot.edit_message_text(
        text="📖 <b>Выберите вашу платформу:</b>",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=guide_menu(),
        parse_mode="HTML"
    )
    await call.answer()

@dp.callback_query(F.data == "guide_ios")
async def guide_ios_callback(call: types.CallbackQuery):
    text = (
        "🍏 <b>Подключение на iOS:</b>\n\n"
        "1️⃣ Скачайте Amnezia VPN:\n"
        "https://apps.apple.com/us/app/amneziavpn/id1600529900\n\n"
        "2️⃣ Оформите подписку в боте\n\n"
        "3️⃣ Скопируйте ключ в разделе 🔑 Мой ключ\n\n"
        "4️⃣ Откройте Amnezia VPN\n\n"
        "5️⃣ Нажмите <b>+</b> внизу экрана\n\n"
        "6️⃣ Вставьте ключ и нажмите <b>Подключиться</b> ✅"
    )
    await bot.edit_message_text(
        text=text,
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=back_to_menu(),
        parse_mode="HTML"
    )
    await call.answer()

@dp.callback_query(F.data == "guide_android")
async def guide_android_callback(call: types.CallbackQuery):
    text = (
        "🤖 <b>Подключение на Android:</b>\n\n"
        "1️⃣ Скачайте Amnezia VPN:\n"
        "https://play.google.com/store/apps/details?id=org.amnezia.vpn\n\n"
        "2️⃣ Оформите подписку в боте\n\n"
        "3️⃣ Скопируйте ключ в разделе 🔑 Мой ключ\n\n"
        "4️⃣ Откройте Amnezia VPN\n\n"
        "5️⃣ Нажмите <b>+</b> внизу экрана\n\n"
        "6️⃣ Вставьте ключ и нажмите <b>Подключиться</b> ✅"
    )
    await bot.edit_message_text(
        text=text,
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=back_to_menu(),
        parse_mode="HTML"
    )
    await call.answer()

# ====== ПОДДЕРЖКА ======
@dp.callback_query(F.data == "support")
async def support_callback(call: types.CallbackQuery):
    text = (
        f"🆘 <b>Поддержка:</b>\n\n"
        f"По всем вопросам: {SUPPORT_USERNAME}\n\n"
        f"⏱ Отвечаем в течение 24 часов."
    )
    await bot.edit_message_text(
        text=text,
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=back_to_menu(),
        parse_mode="HTML"
    )
    await call.answer()

# ====== КУПИТЬ ======
@dp.callback_query(F.data == "buy")
async def buy_callback(call: types.CallbackQuery):
    active_sub = get_active_subscription(call.from_user.id)
    if active_sub:
        exp = datetime.fromisoformat(active_sub["expires"])
        text = (
            f"✅ Подписка активна до {exp.strftime('%d.%m.%Y %H:%M')}.\n\n"
            f"Хотите продлить? Выберите способ оплаты:"
        )
    else:
        text = (
            f"💰 <b>Доступ на 30 дней</b>\n\n"
            f"Выберите способ оплаты:"
        )
    await bot.edit_message_text(
        text=text,
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=buy_menu(),
        parse_mode="HTML"
    )
    await call.answer()

# ====== ОПЛАТА STARS ======
@dp.callback_query(F.data == "pay_stars")
async def pay_stars_callback(call: types.CallbackQuery):
    await bot.send_invoice(
        chat_id=call.message.chat.id,
        title="🔐 VPN доступ на 30 дней",
        description=f"Подписка на 30 дней — {STARS_AMOUNT} ⭐. После оплаты вы получите ключ для Amnezia VPN.",
        payload=f"sub30_{call.from_user.id}_{uuid.uuid4()}",
        currency="XTR",
        prices=[LabeledPrice(label="Подписка 30 дней", amount=STARS_AMOUNT)],
        provider_token="",
    )
    await call.answer()

# ====== PRE-CHECKOUT ======
@dp.pre_checkout_query()
async def pre_checkout_handler(query: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(query.id, ok=True)

# ====== УСПЕШНАЯ ОПЛАТА ======
@dp.message(F.successful_payment)
async def successful_payment_handler(message: types.Message):
    user_id = message.from_user.id
    stars = message.successful_payment.total_amount
    user_uuid, expires = set_subscription(user_id, days=30, source="stars")

    await send_receipt(message.chat.id, user_uuid, expires, stars_amount=stars, source="stars")

    user = get_user(user_id)
    await bot.send_message(
        ADMIN_ID,
        f"💰 <b>Новая оплата Stars!</b>\n\n"
        f"👤 {user['name']} (ID: <code>{user_id}</code>)\n"
        f"⭐ Stars: {stars}\n"
        f"🔑 Ключ: <code>{user_uuid}</code>\n"
        f"📅 До: {expires.strftime('%d.%m.%Y %H:%M')}",
        parse_mode="HTML"
    )

# ====== ОПЛАТА TRIBUTE ======
@dp.callback_query(F.data == "pay_tribute")
async def pay_tribute_callback(call: types.CallbackQuery):
    text = (
        "💳 <b>Оплата через СБП / Карту:</b>\n\n"
        f"1️⃣ Перейдите по ссылке и оплатите {PRICE_RUB} ₽:\n"
        f"{TRIBUTE_LINK}\n\n"
        f"2️⃣ После оплаты напишите {SUPPORT_USERNAME}\n\n"
        "3️⃣ Активируем ключ в течение часа ✅"
    )
    await bot.edit_message_text(
        text=text,
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
         reply_markup=back_to_menu(),
        parse_mode="HTML"
    )
    await call.answer()

# ====== АДМИН: выдать ключ ======
@dp.message(F.text.startswith("/give "))
async def admin_give(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        target_id = int(message.text.split()[1])
        user_uuid, expires = set_subscription(target_id, days=30, source="manual")
        if not user_uuid:
            await message.answer("❌ Пользователь не найден.")
            return
        await send_receipt(target_id, user_uuid, expires, source="manual")
        await message.answer(
            f"✅ Ключ выдан пользователю <code>{target_id}</code>\n"
            f"🔑 <code>{user_uuid}</code>\n"
            f"📅 До: {expires.strftime('%d.%m.%Y %H:%M')}",
            parse_mode="HTML"
        )
    except (IndexError, ValueError):
        await message.answer("Использование: /give <user_id>")

# ====== АДМИН: обнулить ключ ======
@dp.message(F.text.startswith("/revoke "))
async def admin_revoke(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        target_id = int(message.text.split()[1])
        success = revoke_subscription(target_id)
        if success:
            await message.answer(
                f"✅ Ключ пользователя <code>{target_id}</code> обнулён.",
                parse_mode="HTML"
            )
            await bot.send_message(
                target_id,
                f"⚠️ Ваш ключ был деактивирован администратором.\n\n"
                f"По вопросам: {SUPPORT_USERNAME}"
            )
        else:
            await message.answer("❌ Пользователь не найден.")
    except (IndexError, ValueError):
        await message.answer("Использование: /revoke <user_id>")

# ====== АДМИН: список пользователей ======
@dp.message(F.text == "/users")
async def admin_users(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    db = load_db()
    now = datetime.now()
    active_count = 0
    text = "👥 <b>Пользователи:</b>\n\n"
    for uid, user in db.items():
        sub = user.get("subscription")
        if sub and datetime.fromisoformat(sub["expires"]) > now:
            status = "✅"
            active_count += 1
        else:
            status = "❌"
        text += f"{status} {user['name']} — <code>{uid}</code>\n"
    text += f"\n📊 Активных: {active_count} / {len(db)}"
    await message.answer(text, parse_mode="HTML")

# ====== ЛЮБОЕ СООБЩЕНИЕ ======
@dp.message()
async def any_message(message: types.Message):
    create_user(message.from_user.id, message.from_user.first_name or "Пользователь")
    await show_profile(message.chat.id, message.from_user.id)

# ====== ЗАПУСК ======
async def main():
    print("🤖 Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())