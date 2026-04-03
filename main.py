import asyncio
import json
import uuid
from datetime import datetime, timedelta

from aiohttp import web
from aiogram import Bot, Dispatcher, F, types
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    LabeledPrice, PreCheckoutQuery
)
from aiogram.filters import CommandStart

# ====== КОНФИГ ======
BOT_TOKEN = "8335279244:AAFMK4Ku9rmTmoL56FL2N8Zhe8EJYgw1pnc"
TRIBUTE_LINK = "https://web.tribute.tg/d/I5p"
TRIBUTE_API_KEY = "3287c474-3f61-4a29-b31a-e1ef71cc"
SUPPORT_USERNAME = "@ВАШ_НИКНЕЙМ"
ADMIN_ID = 8339239363
STARS_AMOUNT = 1
PRICE_RUB = 199
WEBHOOK_HOST = "https://astrobot-production-6d6d.up.railway.app"
DB_FILE = "users.json"
KEYS_FILE = "keys.json"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ====== БАЗА ПОЛЬЗОВАТЕЛЕЙ ======
def load_db():
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# ====== БАЗА КЛЮЧЕЙ ======
def load_keys():
    try:
        with open(KEYS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_keys(data):
    with open(KEYS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def add_key(key_value):
    keys = load_keys()
    for k, v in keys.items():
        if v["key"] == key_value:
            return False
    key_id = str(uuid.uuid4())
    keys[key_id] = {
        "key": key_value,
        "status": "free",
        "user_id": None,
        "assigned_at": None
    }
    save_keys(keys)
    return True

def get_free_key():
    keys = load_keys()
    for key_id, data in keys.items():
        if data["status"] == "free":
            return key_id, data["key"]
    return None, None

def assign_key(key_id, user_id):
    keys = load_keys()
    if key_id in keys:
        keys[key_id]["status"] = "used"
        keys[key_id]["user_id"] = str(user_id)
        keys[key_id]["assigned_at"] = datetime.now().isoformat()
        save_keys(keys)

def get_user_key(user_id):
    keys = load_keys()
    uid = str(user_id)
    for key_id, data in keys.items():
        if data["user_id"] == uid and data["status"] == "used":
            return data["key"]
    return None

def delete_key_by_user(user_id):
    keys = load_keys()
    uid = str(user_id)
    to_delete = None
    for key_id, data in keys.items():
        if data["user_id"] == uid:
            to_delete = key_id
            break
    if to_delete:
        del keys[to_delete]
        save_keys(keys)
        return True
    return False

def count_free_keys():
    keys = load_keys()
    return sum(1 for v in keys.values() if v["status"] == "free")

# ====== ПОЛЬЗОВАТЕЛИ ======
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

    existing_key = get_user_key(user_id)

    if existing_key:
        existing_sub = db[uid].get("subscription")
        if existing_sub:
            old_exp = datetime.fromisoformat(existing_sub["expires"])
            base = old_exp if old_exp > datetime.now() else datetime.now()
        else:
            base = datetime.now()
        expires = base + timedelta(days=days)
        db[uid]["subscription"] = {
            "key": existing_key,
            "expires": expires.isoformat(),
            "source": source
        }
        db[uid]["total_paid"] = db[uid].get("total_paid", 0) + 1
        save_db(db)
        return existing_key, expires

    key_id, key_value = get_free_key()
    if not key_value:
        return None, None

    expires = datetime.now() + timedelta(days=days)
    assign_key(key_id, user_id)
    db[uid]["subscription"] = {
        "key": key_value,
        "expires": expires.isoformat(),
        "source": source
    }
    db[uid]["total_paid"] = db[uid].get("total_paid", 0) + 1
    save_db(db)
    return key_value, expires

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
async def send_receipt(chat_id, key_value, expires, stars_amount=None, source="stars"):
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
        f"🔑 Ваш ключ:\n<code>{key_value}</code>\n"
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
    free_keys = count_free_keys()

    if active_sub:
        exp = datetime.fromisoformat(active_sub["expires"])
        sub_text = f"✅ Подписка активна до {exp.strftime('%d.%m.%Y %H:%M')}"
    else:
        sub_text = "❌ Подписка отсутствует"

    text = (
        f"👋 Привет, {user['name']}!\n\n"
        f"🆔 ID: <code>{uid}</code>\n"
        f"💰 Стоимость: {PRICE_RUB} ₽ / {STARS_AMOUNT} ⭐\n"
        f"🔓 Свободных мест: {free_keys}\n\n"
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

# ====== TRIBUTE WEBHOOK ======
async def tribute_webhook(request):
    try:
        data = await request.json()

        if data.get("status") != "paid":
            return web.Response(status=200)

        comment = str(data.get("comment", "")).strip()
        if not comment.isdigit():
            await bot.send_message(
                ADMIN_ID,
                f"⚠️ <b>Tribute оплата без ID!</b>\n\n"
                f"Комментарий: {comment}\n"
                f"Сумма: {data.get('amount', '?')} ₽\n\n"
                f"Выдайте ключ вручную: /give USER_ID",
                parse_mode="HTML"
            )
            return web.Response(status=200)

        user_id = int(comment)
        db = load_db()
        uid = str(user_id)

        if uid not in db:
            await bot.send_message(
                ADMIN_ID,
                f"⚠️ <b>Tribute оплата — пользователь не найден!</b>\n\n"
                f"ID: <code>{user_id}</code>\n"
                f"Сумма: {data.get('amount', '?')} ₽",
                parse_mode="HTML"
            )
            return web.Response(status=200)

        key_value, expires = set_subscription(user_id, days=30, source="tribute")

        if not key_value:
            await bot.send_message(
                user_id,
                f"⚠️ Оплата прошла но свободных ключей нет!\n"
                f"Напишите {SUPPORT_USERNAME} — разберёмся срочно."
            )
            return web.Response(status=200)

        await send_receipt(user_id, key_value, expires, source="tribute")

        user = get_user(user_id)
        await bot.send_message(
            ADMIN_ID,
            f"💰 <b>Новая оплата Tribute!</b>\n\n"
            f"👤 {user['name']} (ID: <code>{user_id}</code>)\n"
            f"💳 Сумма: {data.get('amount', '?')} ₽\n"
            f"📅 До: {expires.strftime('%d.%m.%Y %H:%M')}\n"
            f"🔓 Осталось свободных: {count_free_keys()}",
            parse_mode="HTML"
        )

    except Exception as e:
        print(f"Webhook error: {e}")

    return web.Response(status=200)

# ====== СТАРТ ======
@dp.message(CommandStart())
async def start_command(message: types.Message):
    create_user(message.from_user.id, message.from_user.first_name or "Пользователь")
    await show_profile(message.chat.id, message.from_user.id)

# ====== МЕНЮ ======
@dp.callback_query(F.data == "menu")
async def menu_callback(call: types.CallbackQuery):
    await show_profile(call.message.chat.id, call.from_user.id, call.message.message_id)
    await call.answer()

# ====== МОЙ КЛЮЧ ======
@dp.callback_query(F.data == "mykey")
async def mykey_callback(call: types.CallbackQuery):
    active_sub = get_active_subscription(call.from_user.id)
    if active_sub:
        exp = datetime.fromisoformat(active_sub["expires"])
        text = (
            "🔑 <b>Ваш активный ключ:</b>\n\n"
            f"<code>{active_sub['key']}</code>\n\n"
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

# ====== ГАЙД ======
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
        text=text, chat_id=call.message.chat.id,
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
        text=text, chat_id=call.message.chat.id,
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
        text=text, chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=back_to_menu(),
        parse_mode="HTML"
    )
    await call.answer()

# ====== КУПИТЬ ======
@dp.callback_query(F.data == "buy")
async def buy_callback(call: types.CallbackQuery):
    free_keys = count_free_keys()
    if free_keys == 0:
        await bot.edit_message_text(
            text=(
                "😔 <b>Свободных мест нет.</b>\n\n"
                f"Напишите {SUPPORT_USERNAME} — добавим вас в очередь."
            ),
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=back_to_menu(),
            parse_mode="HTML"
        )
        await call.answer()
        return

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
            f"🔓 Свободных мест: {free_keys}\n\n"
            f"Выберите способ оплаты:"
        )
    await bot.edit_message_text(
        text=text, chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=buy_menu(),
        parse_mode="HTML"
    )
    await call.answer()

# ====== ОПЛАТА STARS ======
@dp.callback_query(F.data == "pay_stars")
async def pay_stars_callback(call: types.CallbackQuery):
    if count_free_keys() == 0:
        await call.answer("😔 Свободных мест нет! Напишите в поддержку.", show_alert=True)
        return
    await bot.send_invoice(
        chat_id=call.message.chat.id,
        title="🔐 VPN доступ на 30 дней",
        description=f"Подписка на 30 дней — {STARS_AMOUNT} ⭐",
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

# ====== УСПЕШНАЯ ОПЛАТА STARS ======
@dp.message(F.successful_payment)
async def successful_payment_handler(message: types.Message):
    user_id = message.from_user.id
    stars = message.successful_payment.total_amount
    key_value, expires = set_subscription(user_id, days=30, source="stars")

    if not key_value:
        await message.answer(
            f"⚠️ Оплата прошла но свободных ключей нет!\n"
            f"Напишите {SUPPORT_USERNAME} — разберёмся срочно.")
        return

    await send_receipt(message.chat.id, key_value, expires, stars_amount=stars, source="stars")

    user = get_user(user_id)
    await bot.send_message(
        ADMIN_ID,
        f"💰 <b>Новая оплата Stars!</b>\n\n"
        f"👤 {user['name']} (ID: <code>{user_id}</code>)\n"
        f"⭐ Stars: {stars}\n"
        f"📅 До: {expires.strftime('%d.%m.%Y %H:%M')}\n"
        f"🔓 Осталось свободных: {count_free_keys()}",
        parse_mode="HTML"
    )

# ====== ОПЛАТА TRIBUTE ======
@dp.callback_query(F.data == "pay_tribute")
async def pay_tribute_callback(call: types.CallbackQuery):
    user_id = call.from_user.id
    create_user(user_id, call.from_user.first_name or "Пользователь")
    text = (
        "💳 <b>Оплата через СБП / Карту:</b>\n\n"
        f"1️⃣ Перейдите по ссылке и оплатите {PRICE_RUB} ₽:\n"
        f"{TRIBUTE_LINK}?comment={user_id}\n\n"
        "2️⃣ Ключ придёт автоматически после оплаты ✅"
    )
    await bot.edit_message_text(
        text=text, chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=back_to_menu(),
        parse_mode="HTML"
    )
    await call.answer()

# ====== АДМИН: добавить ключ ======
@dp.message(F.text.startswith("/addkey "))
async def admin_addkey(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    key_value = message.text[8:].strip()
    if not key_value:
        await message.answer("Использование: /addkey <ключ>")
        return
    success = add_key(key_value)
    if success:
        await message.answer(
            f"✅ Ключ добавлен в базу!\n"
            f"🔓 Всего свободных: {count_free_keys()}"
        )
    else:
        await message.answer("❌ Такой ключ уже есть в базе.")

# ====== АДМИН: выдать ключ вручную ======
@dp.message(F.text.startswith("/give "))
async def admin_give(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        target_id = int(message.text.split()[1])
        key_value, expires = set_subscription(target_id, days=30, source="manual")
        if not key_value:
            await message.answer("❌ Нет свободных ключей или пользователь не найден.")
            return
        await send_receipt(target_id, key_value, expires, source="manual")
        await message.answer(
            f"✅ Ключ выдан пользователю <code>{target_id}</code>\n"
            f"📅 До: {expires.strftime('%d.%m.%Y %H:%M')}\n"
            f"🔓 Осталось свободных: {count_free_keys()}",
            parse_mode="HTML"
        )
    except (IndexError, ValueError):
        await message.answer("Использование: /give <user_id>")

# ====== АДМИН: удалить ключ ======
@dp.message(F.text.startswith("/revoke "))
async def admin_revoke(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        target_id = int(message.text.split()[1])
        db = load_db()
        uid = str(target_id)
        if uid in db:
            db[uid]["subscription"] = None
            save_db(db)
        delete_key_by_user(target_id)
        await message.answer(
            f"✅ Ключ пользователя <code>{target_id}</code> удалён.",
            parse_mode="HTML"
        )
        await bot.send_message(
            target_id,
            "⚠️ <b>Ваша подписка закончилась.</b>\n\n"
            "Для продления нажмите кнопку ниже 👇",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⭐️ Продлить подписку", callback_data="buy")]
            ])
        )
    except (IndexError, ValueError):
        await message.answer("Использование: /revoke <user_id>")

# ====== АДМИН: список ключей ======
@dp.message(F.text == "/keys")
async def admin_keys(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    keys = load_keys()
    if not keys:
        await message.answer("📭 База ключей пуста.")
        return
    free = [v for v in keys.values() if v["status"] == "free"]
    used = [v for v in keys.values() if v["status"] == "used"]
    text = (
        f"🗝 <b>База ключей:</b>\n\n"
        f"🟢 Свободных: {len(free)}\n"
        f"🔴 Занятых: {len(used)}\n"
        f"📊 Всего: {len(keys)}"
    )
    await message.answer(text, parse_mode="HTML")

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
            exp = datetime.fromisoformat(sub["expires"])
            status = f"✅ до {exp.strftime('%d.%m')}"
            active_count += 1
        else:
            status = "❌"
        text += f"{status} — {user['name']} <code>{uid}</code>\n"
    text += f"\n📊 Активных: {active_count} / {len(db)}"
    await message.answer(text, parse_mode="HTML")

# ====== ЛЮБОЕ СООБЩЕНИЕ ======
@dp.message()
async def any_message(message: types.Message):
    create_user(message.from_user.id, message.from_user.first_name or "Пользователь")
    await show_profile(message.chat.id, message.from_user.id)

# ====== ЗАПУСК ======
async def main():
    app = web.Application()
    app.router.add_post("/tribute/webhook", tribute_webhook)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
    print("🤖 Бот запущен!")
    print("🌐 Webhook сервер запущен на порту 8080")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
