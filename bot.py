import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import sqlite3
import logging

# ============ НАСТРОЙКИ ============
BOT_TOKEN = "7829147082:AAFu1zuFCv9Z2-nMlGiIC16-PlCoXWnogoI"
ADMIN_ID = 7765822255
PAYMENT_INFO = "💳 <b>Оплата по запросу</b>\n\n📤 Напишите админу @Karapski"
DATABASE = "cpm_bot.db"

# ============ Логирование ============
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# ============ Бот и диспетчер ============
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ============ Инициализация базы ============
def init_db():
    default_description = '''🎁 Фулл-аккаунт — 249₽

• Все машины + мигалки
• 50.000.000$
• 500.000 коинов

Готов к использованию!'''

    with sqlite3.connect(DATABASE) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS vinyls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                price INTEGER NOT NULL,
                photo_id TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                creds TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS full_accounts_info (
                id INTEGER PRIMARY KEY,
                description TEXT NOT NULL
            )
        """)
        conn.execute("INSERT OR IGNORE INTO full_accounts_info (id, description) VALUES (1, ?)", (default_description,))
        conn.commit()
    log.info("✅ База данных готова")

# ============ КНОПКИ ============
def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Накрутка", callback_data="boost_menu")],
        [InlineKeyboardButton(text="🖼 Винилы", callback_data="show_vinyls_list")],
        [InlineKeyboardButton(text="🎁 Фулл-аккаунт", callback_data="show_full_info")],
    ])

def back():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]
    ])

def admin_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить винил", callback_data="admin_add_vinyl")],
        [InlineKeyboardButton(text="🔐 Добавить аккаунты", callback_data="admin_add_acc")],
        [InlineKeyboardButton(text="📝 Изменить описание фулл-аккаунта", callback_data="admin_edit_full")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")]
    ])

# ============ START ============
@dp.message(Command("start"))
async def start(m: types.Message, state: FSMContext):
    await state.clear()
    await m.answer("🏎 Добро пожаловать в Perspectiva Shop", reply_markup=main_menu())

# ============ НАЗАД ============
@dp.callback_query(F.data == "back_main")
async def go_back(c: types.CallbackQuery):
    await c.message.edit_text("🏎 Главное меню", reply_markup=main_menu())
    await c.answer()

# ============ АДМИНКА ============
@dp.message(Command("admin"))
async def admin(m: types.Message):
    if m.from_user.id != ADMIN_ID:
        await m.answer("❌ Доступ запрещён")
        return
    await m.answer("🔐 Админ-панель", reply_markup=admin_menu())

# ============ ДОБАВИТЬ ВИНК ============
class AddVinyl(StatesGroup):
    photo = State()
    name = State()
    desc = State()
    price = State()

@dp.callback_query(F.data == "admin_add_vinyl")
async def admin_add_vinyl_photo(c: types.CallbackQuery, state: FSMContext):
    await c.message.edit_text("📸 Отправьте фото винила")
    await state.set_state(AddVinyl.photo)
    await c.answer()

@dp.message(F.photo, StateFilter(AddVinyl.photo))
async def admin_vinyl_name(m: types.Message, state: FSMContext):
    photo_id = m.photo[-1].file_id
    await state.update_data(photo_id=photo_id)
    await m.answer("🔤 Введите название:")
    await state.set_state(AddVinyl.name)

@dp.message(F.text, StateFilter(AddVinyl.name))
async def admin_vinyl_desc(m: types.Message, state: FSMContext):
    await state.update_data(name=m.text)
    await m.answer("📝 Введите описание:")
    await state.set_state(AddVinyl.desc)

@dp.message(F.text, StateFilter(AddVinyl.desc))
async def admin_vinyl_price(m: types.Message, state: FSMContext):
    await state.update_data(desc=m.text)
    await m.answer("💵 Введите цену:")
    await state.set_state(AddVinyl.price)

@dp.message(F.text, StateFilter(AddVinyl.price))
async def admin_save_vinyl(m: types.Message, state: FSMContext):
    try:
        price = int(m.text)
        if price <= 0: raise ValueError
    except:
        await m.answer("❌ Цена — положительное число")
        return
    data = await state.get_data()
    with sqlite3.connect(DATABASE) as conn:
        conn.execute("""
            INSERT INTO vinyls (name, description, price, photo_id)
            VALUES (?, ?, ?, ?)
        """, (data['name'], data['desc'], price, data['photo_id']))
        conn.commit()
    await m.answer("✅ Винил добавлен!", reply_markup=admin_menu())
    await state.clear()

# ============ ПОКАЗАТЬ СПИСОК ВИНЛОВ ============
@dp.callback_query(F.data == "show_vinyls_list")
async def show_vinyls_list(c: types.CallbackQuery):
    with sqlite3.connect(DATABASE) as conn:
        rows = conn.execute("SELECT id, name FROM vinyls").fetchall()
    if not rows:
        await c.message.edit_text("🖼 Нет винилов", reply_markup=back())
        await c.answer()
        return

    kb = [[InlineKeyboardButton(text=name, callback_data=f"view_vinyl_{vid}")] for vid, name in rows]
    kb.append([InlineKeyboardButton(text="❌ Отмена", callback_data="back_main")])

    await c.message.edit_text("<b>🖼 Выберите винил:</b>", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await c.answer()

# ============ ПРОСМОТР ВИНЛА ============
@dp.callback_query(F.data.startswith("view_vinyl_"))
async def view_vinyl(c: types.CallbackQuery):
    try:
        vinyl_id = int(c.data.split("_")[-1])
    except:
        await c.answer("❌ Ошибка: неверный ID")
        return

    with sqlite3.connect(DATABASE) as conn:
        row = conn.execute("SELECT name, description, price FROM vinyls WHERE id = ?", (vinyl_id,)).fetchone()
    if not row:
        await c.message.edit_text("❌ Винил не найден", reply_markup=main_menu())
        await c.answer()
        return

    name, desc, price = row
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Купить", callback_data="buy_vinyl_flow")],
        [InlineKeyboardButton(text="❌ Назад", callback_data="show_vinyls_list")]
    ])

    await c.message.edit_text(
        f"🖼 <b>{name}</b>\n\n{desc}\n\n💰 <b>{price}₽</b>",
        parse_mode="HTML",
        reply_markup=kb
    )
    await c.answer()

# ============ КУПИТЬ ВИНЛ ============
@dp.callback_query(F.data == "buy_vinyl_flow")
async def buy_vinyl_flow(c: types.CallbackQuery):
    await c.message.edit_text(
        f"📦 Вы выбрали винил!\n\n{PAYMENT_INFO}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📸 Отправил оплату", callback_data="vinyl_paid")],
            [InlineKeyboardButton(text="❌ Отказаться", callback_data="show_vinyls_list")]
        ])
    )
    await c.answer()

@dp.callback_query(F.data == "vinyl_paid")
async def vinyl_paid(c: types.CallbackQuery, state: FSMContext):
    await c.message.edit_text("📸 Отправьте **скриншот оплаты**")
    await state.set_state("waiting_vinyl_screenshot")
    await c.answer()

@dp.message(F.photo, StateFilter("waiting_vinyl_screenshot"))
async def got_vinyl_screenshot(m: types.Message, state: FSMContext):
    try:
        await m.forward(ADMIN_ID)
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"adm_appr_vinyl_{m.from_user.id}")],
            [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"adm_rej_vinyl_{m.from_user.id}")]
        ])
        await bot.send_message(ADMIN_ID, "📸 **Скриншот (Винил)**", reply_markup=kb)
        await m.answer("✅ Скриншот отправлен. Ожидайте подтверждения.")
    except Exception as e:
        await m.answer(f"❌ Ошибка: {str(e)}")
    finally:
        await state.clear()

@dp.callback_query(F.data.startswith("adm_appr_vinyl_"))
async def approve_vinyl(c: types.CallbackQuery):
    try:
        user_id = int(c.data.split("_")[-1])
        await bot.send_message(user_id, "✅ Оплата подтверждена! Товар будет отправлен.")
        await c.message.edit_text("✅ Пользователю отправлено")
    except Exception as e:
        await c.message.edit_text("❌ Ошибка отправки")
        log.error(f"approve_vinyl: {e}")
    finally:
        await c.answer()

@dp.callback_query(F.data.startswith("adm_rej_vinyl_"))
async def reject_vinyl(c: types.CallbackQuery):
    try:
        user_id = int(c.data.split("_")[-1])
        await bot.send_message(user_id, "❌ Оплата не подтверждена.")
        await c.message.edit_text("❌ Оплата отклонена")
    except Exception as e:
        log.error(f"reject_vinyl: {e}")
    finally:
        await c.answer()

# ============ ДОБАВИТЬ АККАУНТЫ ============
class AddAccounts(StatesGroup):
    accounts = State()

@dp.callback_query(F.data == "admin_add_acc")
async def admin_prompt_acc(c: types.CallbackQuery, state: FSMContext):
    await c.message.edit_text("🔐 Введите аккаунты по одному в строке:\n\nlogin1:pass1\nlogin2:pass2\n...\n\nМаксимум 1000 шт.")
    await state.set_state(AddAccounts.accounts)
    await c.answer()

@dp.message(F.text, StateFilter(AddAccounts.accounts))
async def admin_save_accs(m: types.Message, state: FSMContext):
    lines = m.text.strip().split("\n")
    valid = []
    for line in lines:
        if ":" in line.strip():
            valid.append((line.strip(),))
    if not valid:
        await m.answer("❌ Нет аккаунтов в формате логин:пароль")
        return
    if len(valid) > 1000:
        await m.answer("❌ Нельзя загрузить больше 1000 аккаунтов")
        return
    with sqlite3.connect(DATABASE) as conn:
        conn.executemany("INSERT INTO accounts (creds) VALUES (?)", valid)
        conn.commit()
    await m.answer(f"✅ Добавлено: {len(valid)} аккаунтов", reply_markup=admin_menu())
    await state.clear()

# ============ ПОКАЗАТЬ ФУЛЛ-АККАУНТ ============
@dp.callback_query(F.data == "show_full_info")
async def show_full_info(c: types.CallbackQuery):
    with sqlite3.connect(DATABASE) as conn:
        result = conn.execute("SELECT description FROM full_accounts_info WHERE id = 1").fetchone()
        count = conn.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]
    desc = result[0]
    text = f"{desc}\n\n📦 Доступно: {count} шт."
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Купить", callback_data="buy_full_acc")],
        [InlineKeyboardButton(text="❌ Назад", callback_data="back_main")]
    ])
    await c.message.edit_text(text, reply_markup=kb)
    await c.answer()

# ============ ИЗМЕНИТЬ ОПИСАНИЕ ============
class EditFullDesc(StatesGroup):
    waiting = State()

@dp.callback_query(F.data == "admin_edit_full")
async def admin_edit_full(c: types.CallbackQuery, state: FSMContext):
    await c.message.edit_text("📝 Введите новое описание для фулл-аккаунта:")
    await state.set_state(EditFullDesc.waiting)
    await c.answer()

@dp.message(F.text, StateFilter(EditFullDesc.waiting))
async def save_full_desc(m: types.Message, state: FSMContext):
    with sqlite3.connect(DATABASE) as conn:
        conn.execute("UPDATE full_accounts_info SET description = ? WHERE id = 1", (m.text,))
        conn.commit()
    await m.answer("✅ Описание обновлено!", reply_markup=admin_menu())
    await state.clear()

# ============ КУПИТЬ ФУЛЛ-АККАУНТ ============
@dp.callback_query(F.data == "buy_full_acc")
async def buy_full_acc(c: types.CallbackQuery, state: FSMContext):
    with sqlite3.connect(DATABASE) as conn:
        row = conn.execute("SELECT creds FROM accounts LIMIT 1").fetchone()
    if not row:
        await c.message.edit_text("❌ Нет аккаунтов в наличии", reply_markup=back())
        await c.answer()
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Оплатил", callback_data="full_paid")],
        [InlineKeyboardButton(text="❌ Отказаться", callback_data="show_full_info")]
    ])
    await c.message.edit_text(f"🎁 Подтвердите оплату\n\n{PAYMENT_INFO}", reply_markup=kb)
    await c.answer()

@dp.callback_query(F.data == "full_paid")
async def full_paid(c: types.CallbackQuery, state: FSMContext):
    await c.message.edit_text("📸 Отправьте **скриншот оплаты**")
    await state.set_state("waiting_full_screenshot")
    await c.answer()

@dp.message(F.photo, StateFilter("waiting_full_screenshot"))
async def got_full_screenshot(m: types.Message, state: FSMContext):
    try:
        forwarded = await m.forward(ADMIN_ID)
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Выдать", callback_data=f"adm_appr_full_{m.from_user.id}")],
            [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"adm_rej_full_{m.from_user.id}")]
        ])
        await bot.send_message(ADMIN_ID, "🎁 **Запрос фулл-аккаунта**", reply_markup=kb)
    except Exception as e:
        await m.answer(f"❌ Ошибка: {str(e)}")
        return
    finally:
        await m.answer("✅ Скриншот отправлен. Ожидайте подтверждения.")
        await state.clear()

@dp.callback_query(F.data.startswith("adm_appr_full_"))
async def approve_full(c: types.CallbackQuery):
    try:
        user_id = int(c.data.split("_")[-1])
        with sqlite3.connect(DATABASE) as conn:
            row = conn.execute("SELECT creds FROM accounts LIMIT 1").fetchone()
            if not row:
                await c.message.edit_text("❌ Нет аккаунтов")
                await c.answer()
                return
            cred = row[0]
            conn.execute("DELETE FROM accounts WHERE creds = ?", (cred,))
            conn.commit()
        await bot.send_message(user_id, f"🔐 Фулл-аккаунт:\n\n<code>{cred}</code>", parse_mode="HTML")
        await c.message.edit_text("✅ Аккаунт выдан")
    except Exception as e:
        await c.message.edit_text("❌ Ошибка отправки")
        log.error(f"approve_full: {e}")
    finally:
        await c.answer()

@dp.callback_query(F.data.startswith("adm_rej_full_"))
async def reject_full(c: types.CallbackQuery):
    try:
        user_id = int(c.data.split("_")[-1])
        await bot.send_message(user_id, "❌ Оплата не подтверждена.")
        await c.message.edit_text("❌ Отклонено")
    except Exception as e:
        log.error(f"reject_full: {e}")
    finally:
        await c.answer()

# ============ НАКРУТКА ============
@dp.callback_query(F.data == "boost_menu")
async def boost_menu(c: types.CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💵 50кк — 29₽", callback_data="boost_50k")],
        [InlineKeyboardButton(text="🪙 30к — 70₽", callback_data="boost_30k")],
        [InlineKeyboardButton(text="🪙 500к — 129₽", callback_data="boost_500k")],
        [InlineKeyboardButton(text="🚨 Мигалки — 99₽", callback_data="boost_lights")],
        [InlineKeyboardButton(text="⚡ Силы — 49₽", callback_data="boost_power")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]
    ])
    await c.message.edit_text("🔧 Выберите услугу:", reply_markup=kb)
    await c.answer()

BOOST_NAMES = {
    "boost_50k": "💵 50кк — 29₽",
    "boost_30k": "🪙 30к — 70₽",
    "boost_500k": "🪙 500к — 129₽",
    "boost_lights": "🚨 Мигалки — 99₽",
    "boost_power": "⚡ Силы — 49₽"
}

@dp.callback_query(F.data.startswith("boost_"))
async def confirm_boost(c: types.CallbackQuery, state: FSMContext):
    boost_type = c.data
    title = BOOST_NAMES.get(boost_type, "Услуга")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Оплатил", callback_data=f"paid_{boost_type}")],
        [InlineKeyboardButton(text="❌ Отказаться", callback_data="boost_menu")]
    ])
    await c.message.edit_text(
        f"{title}\n\nОплатите на:\n💳Оплата через админа.\n\nПожалуйста напишите админу @Karapski",
        reply_markup=kb
    )
    await state.update_data(boost_type=boost_type)
    await c.answer()

@dp.callback_query(F.data.startswith("paid_boost_"))
async def user_paid(c: types.CallbackQuery, state: FSMContext):
    await c.message.edit_text("📸 Отправьте **скриншот оплаты**")
    await state.set_state("waiting_boost_screenshot")
    await c.answer()

@dp.message(F.photo, StateFilter("waiting_boost_screenshot"))
async def got_boost_screenshot(m: types.Message, state: FSMContext):
    data = await state.get_data()
    boost_type = data.get("boost_type", "unknown")
    title = BOOST_NAMES.get(boost_type, "Накрутка")
    try:
        forwarded = await m.forward(ADMIN_ID)
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"adm_appr_boost_{m.from_user.id}_{boost_type}")],
            [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"adm_rej_boost_{m.from_user.id}")]
        ])
        user_link = m.from_user.username or m.from_user.full_name
        await bot.send_message(
            ADMIN_ID,
            f"🔧 **Новая накрутка**\n\n"
            f"👤: @{user_link}\n"
            f"🆔: {m.from_user.id}\n"
            f"🎁: {title}",
            reply_markup=kb,
            parse_mode="Markdown"
        )
    except Exception as e:
        await m.answer(f"❌ Ошибка: {str(e)}")
    finally:
        await m.answer("✅ Скриншот отправлен. Ожидайте подтверждения.")
        await state.clear()

# ============ ✅ ИСПРАВЛЕННЫЙ approve_boost ============
@dp.callback_query(F.data.startswith("adm_appr_boost_"))
async def approve_boost(c: types.CallbackQuery):
    try:
        parts = c.data.split("_", 4)  # adm_appr_boost_12345_boost_50k
        if len(parts) < 5:
            await c.answer("❌ Ошибка: неверные данные", show_alert=True)
            return
        user_id = int(parts[3])
        boost_type = parts[4]

        # ✅ Создаём FSMContext вручную
        from aiogram.fsm.context import FSMContext
        from aiogram.fsm.storage.base import StorageKey

        key = StorageKey(
            bot_id=bot.id,
            user_id=user_id,
            chat_id=user_id
        )
        state = FSMContext(storage=dp.storage, key=key)
        await state.set_state(f"waiting_creds_from_{user_id}")

        await bot.send_message(
            user_id,
            f"✅ Оплата подтверждена!\n\n"
            f"Пожалуйста, пришлите:\n"
            f"📧 Почту и пароль от аккаунта\n"
            f"🔐 и выйдите с него.\n\n"
            f"Формат: login@gmail.com:password"
        )
        await c.message.edit_text("✅ Пользователю отправлено: пришлите логин:пароль")
    except Exception as e:
        await c.message.edit_text("❌ Ошибка при подтверждении")
        log.error(f"approve_boost: {e}")
    finally:
        await c.answer()

# ============ ИСПРАВЛЕННЫЙ reject_boost ============
@dp.callback_query(F.data.startswith("adm_rej_boost_"))
async def reject_boost(c: types.CallbackQuery):
    try:
        user_id = int(c.data.split("_")[-1])
        await bot.send_message(user_id, "❌ Оплата не подтверждена. Попробуйте снова.")
        await c.message.edit_text("❌ Оплата отклонена")
    except Exception as e:
        log.error(f"reject_boost: {e}")
    finally:
        await c.answer()

# ============ ✅ ИСПРАВЛЕННЫЙ got_user_creds ============
@dp.message(F.text & ~F.text.startswith("/"))
async def got_user_creds(m: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if not current_state or not current_state.startswith("waiting_creds_from_"):
        return

    if ":" not in m.text:
        await m.answer("❌ Отправьте в формате:\n\nlogin@example.com:password")
        return

    user_id = m.from_user.id
    creds = m.text.strip()

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Готово", callback_data=f"done_creds_{user_id}")],
        [InlineKeyboardButton(text="❌ Отказ", callback_data=f"fail_creds_{user_id}")]
    ])
    user_link = m.from_user.username or m.from_user.full_name
    try:
        await bot.send_message(
            ADMIN_ID,
            f"🔐 **Получены данные аккаунта**\n\n"
            f"👤: @{user_link}\n"
            f"🆔: {user_id}\n\n"
            f"📩: <code>{creds}</code>",
            parse_mode="HTML",
            reply_markup=kb
        )
        await m.answer("✅ Данные отправлены. Ожидайте обработки.")
    except Exception as e:
        await m.answer("❌ Ошибка при отправке")
        log.error(f"got_user_creds: {e}")

    await state.clear()

# ============ done_creds / fail_creds ============
@dp.callback_query(F.data.startswith("done_creds_"))
async def done_creds(c: types.CallbackQuery, state: FSMContext):
    try:
        user_id = int(c.data.split("_")[-1])
        await bot.send_message(
            user_id,
            "✅ Готово! Заходите в аккаунт.\n\n"
            "🌟 Спасибо за заказ! Поделитесь вашим впечатлением — напишите отзыв!"
        )
        # Устанавливаем состояние для отзыва
        from aiogram.fsm.context import FSMContext
        from aiogram.fsm.storage.base import StorageKey
        key = StorageKey(bot_id=bot.id, user_id=user_id, chat_id=user_id)
        user_state = FSMContext(storage=dp.storage, key=key)
        await user_state.set_state("waiting_review_from_user")
        await c.message.edit_text("✅ Пользователь уведомлён. Ждём отзыв.")
    except Exception as e:
        log.error(f"done_creds: {e}")
    finally:
        await c.answer()

@dp.callback_query(F.data.startswith("fail_creds_"))
async def fail_creds(c: types.CallbackQuery):
    try:
        user_id = int(c.data.split("_")[-1])
        await bot.send_message(user_id, "❌ Ошибка при обработке. Админ свяжется с вами.")
        await c.message.edit_text("❌ Отклонено")
    except Exception as e:
        log.error(f"fail_creds: {e}")
    finally:
        await c.answer()

# ============ ОТЗЫВЫ ============
@dp.message(F.text | F.photo)
async def got_review(m: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if not current_state or not current_state.startswith("waiting_review_from_user"):
        return

    user_link = m.from_user.username or m.from_user.full_name
    try:
        if m.text:
            await bot.send_message(
                ADMIN_ID,
                f"📝 **Новый отзыв**\n\n"
                f"👤: @{user_link}\n"
                f"🆔: {m.from_user.id}\n\n"
                f"💬: {m.text}",
                parse_mode="HTML"
            )
        elif m.photo:
            await m.forward(ADMIN_ID)
            await bot.send_message(
                ADMIN_ID,
                f"📸 **Новый отзыв (фото)**\n\n"
                f"👤: @{user_link}\n"
                f"🆔: {m.from_user.id}",
                parse_mode="HTML"
            )
        await m.answer("✅ Спасибо за отзыв!")
    except Exception as e:
        await m.answer("❌ Спасибо, но не удалось отправить отзыв.")
    finally:
        await state.clear()

# ============ СТАТИСТИКА ============
@dp.callback_query(F.data == "admin_stats")
async def stats(c: types.CallbackQuery):
    with sqlite3.connect(DATABASE) as conn:
        v_count = conn.execute("SELECT COUNT(*) FROM vinyls").fetchone()[0]
        a_count = conn.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]
    await c.message.edit_text(
        f"📊 Статистика:\n\n"
        f"🖼 Винилов: {v_count}\n"
        f"🔐 Аккаунтов: {a_count}",
        reply_markup=back()
    )
    await c.answer()

# ============ ЗАПУСК ============
async def main():
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
