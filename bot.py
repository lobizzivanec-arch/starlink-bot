import os
import re
import json
import time
import logging
from pathlib import Path
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)

# ─────────────────────────────────────────────────────────────────────────────
# НАСТРОЙКИ (Railway Variables)
# ─────────────────────────────────────────────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN")

ADMIN_ID = int(os.getenv("ADMIN_ID", "8197197463"))
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "sunrisseq")  # БЕЗ @

# Группа / канал поддержки (сюда идут ТЕКСТ / ФОТО / ВИДЕО / ФАЙЛЫ)
ADMIN_TEXT_CHANNEL_ID = int(os.getenv("ADMIN_TEXT_CHANNEL_ID", "-1003842776546"))

# Группа / канал заявок (сюда идут только скрины на модерацию)
ADMIN_PHOTO_CHANNEL_ID = int(os.getenv("ADMIN_PHOTO_CHANNEL_ID", "-1003907521717"))

REVIEWS_CHANNEL_USERNAME = os.getenv("REVIEWS_CHANNEL_USERNAME", "@your_reviews_channel")
REVIEWS_CHANNEL_LINK = os.getenv("REVIEWS_CHANNEL_LINK", "https://t.me/your_reviews_channel")

MEDIA_CHECK_ON_START = os.getenv("MEDIA_CHECK_ON_START", "1") == "1"

REQ_IMAGE_1 = os.getenv("REQ_IMAGE_1", "")
REQ_IMAGE_2 = os.getenv("REQ_IMAGE_2", "")
REQ_IMAGE_3 = os.getenv("REQ_IMAGE_3", "")

STEP1_IMAGE_1 = os.getenv("STEP1_IMAGE_1", "")
STEP1_IMAGE_2 = os.getenv("STEP1_IMAGE_2", "")

ACCESS_IMAGE_1 = os.getenv("ACCESS_IMAGE_1", "")
ACCESS_IMAGE_2 = os.getenv("ACCESS_IMAGE_2", "")

STEP2_IMAGE_1 = os.getenv("STEP2_IMAGE_1", "")
STEP2_IMAGE_2 = os.getenv("STEP2_IMAGE_2", "")

STEP3_VIDEO = os.getenv("STEP3_VIDEO", "")
STEP4_VIDEO = os.getenv("STEP4_VIDEO", "")

STEP5_IMAGE_1 = os.getenv("STEP5_IMAGE_1", "")
STEP5_IMAGE_2 = os.getenv("STEP5_IMAGE_2", "")

STATE_FILE = os.getenv("STATE_FILE", "bot_state.json")
USER_MESSAGE_COOLDOWN = int(os.getenv("USER_MESSAGE_COOLDOWN", "6"))

# ─────────────────────────────────────────────────────────────────────────────
# ЛОГИ
# ─────────────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# СОСТОЯНИЯ
# ─────────────────────────────────────────────────────────────────────────────
waiting_for_photo: set[int] = set()
submitted_requests: set[int] = set()
active_support_chats: set[int] = set()
blocked_users: set[int] = set()

# антиспам
user_last_message_time: dict[int, float] = {}

# стабильный UI
user_ui_message_ids: dict[int, int] = {}
user_ui_locks: set[int] = set()

# ─────────────────────────────────────────────────────────────────────────────
# PERSISTENCE JSON
# ─────────────────────────────────────────────────────────────────────────────
def save_state():
    try:
        data = {
            "waiting_for_photo": list(waiting_for_photo),
            "submitted_requests": list(submitted_requests),
            "active_support_chats": list(active_support_chats),
            "blocked_users": list(blocked_users),
            "ui_message_ids": {str(k): v for k, v in user_ui_message_ids.items()},
        }
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ошибка сохранения состояния: {e}")

def load_state():
    global waiting_for_photo, submitted_requests, active_support_chats, blocked_users, user_ui_message_ids

    try:
        if not Path(STATE_FILE).exists():
            return

        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        waiting_for_photo = set(map(int, data.get("waiting_for_photo", [])))
        submitted_requests = set(map(int, data.get("submitted_requests", [])))
        active_support_chats = set(map(int, data.get("active_support_chats", [])))
        blocked_users = set(map(int, data.get("blocked_users", [])))
        user_ui_message_ids = {int(k): int(v) for k, v in data.get("ui_message_ids", {}).items()}
    except Exception as e:
        logger.error(f"Ошибка загрузки состояния: {e}")

# ─────────────────────────────────────────────────────────────────────────────
# ТЕКСТЫ
# ─────────────────────────────────────────────────────────────────────────────
WELCOME_TEXT = """
👋 <b>Привет!</b>

Ты попал в официальный бот с пошаговой инструкцией по настройке <b>Starlink</b>.

📶 Здесь ты получишь:
• понятную пошаговую установку
• видео-инструкции
• доступ к аккаунту без ограничений для РФ
• помощь поддержки, если что-то не получится

⚡ Весь процесс обычно занимает <b>5–15 минут</b>.

Выбери, что тебя интересует 👇
"""

FAQ_TEXT = """
❓ <b>Часто задаваемые вопросы</b>

<b>Это реально работает?</b>
Да. Всё, что показано в инструкции — рабочая схема, которую уже используют другие пользователи.

<b>Это сложно настроить?</b>
Нет. Всё разбито на простые шаги:
• требования
• доступ к аккаунту
• установка приложения
• подключение к Wi-Fi
• настройка в приложении
• проверка скорости

<b>Что делать, если что-то не получается?</b>
Нажми <b>«💬 Связаться с поддержкой»</b> — мы ответим вручную.

<b>Нужно ли включать VPN?</b>
Нет. Во время настройки <b>VPN должен быть выключен</b>.

💡 Хочешь получить инструкцию? Нажми <b>«📦 Установка»</b>.
"""

INSTALL_TEXT = """
📦 <b>Инструкция по установке Starlink</b>

Перед получением <b>полного тутора</b> — один обязательный шаг:

👇 Подпишись на наш <b>новый канал с отзывами пользователей Starlink</b>.

После подписки нажми кнопку <b>«✅ Я подписался»</b> — и мы сразу откроем пошаговую инструкцию.
"""

REQUIREMENTS_TEXT = """
🖼 <b>Требования перед началом настройки</b>

Перед тем как переходить к установке, обязательно проверь:

• <b>Версия iOS не ниже 18.0</b>  
(желательно обновить iPhone до последней версии)

• <b>Полностью выключи VPN</b> на время настройки

• <b>Отключи режим энергосбережения</b>

• <b>Включи геолокацию / Локатор</b>

• <b>Разреши приложению Starlink доступ к геопозиции</b>

• <b>Разреши доступ к локальной сети и Wi-Fi</b>

После этого переходи к <b>Шагу 1</b> 👇
"""

REQUIREMENTS_TEXT_2 = """
🖼 <b>Требования — пример 2</b>

Проверь:
• VPN выключен
• геолокация включена
• режим энергосбережения выключен
• все разрешения активны

⚠️ Если хотя бы один пункт не выполнен — настройка может пройти с ошибками.
"""

REQUIREMENTS_TEXT_3 = """
🖼 <b>Требования — пример 3</b>

Финальная проверка:
• iPhone обновлён
• интернет стабилен
• доступы выданы
• система готова к настройке

После проверки переходи дальше 👇
"""

STEP_1_TEXT = """
🖼 <b>Шаг 1. Доступ в аккаунт с доступом к Starlink</b>

<b>Краткое описание:</b>

Мы выдаём тебе доступ к аккаунту, в котором отсутствуют ограничения на подключение к Wi-Fi на территории России

Что нужно сделать:
• Нажать кнопку <b>«Получить доступ»</b>
• Получить данные для входа
• Авторизоваться в аккаунте

После этого переходи к следующему шагу 👇
"""

STEP_1_IMAGE_2_TEXT = """
🖼 <b>Шаг 1. Дополнительный пример</b>

На этой картинке показано, как должен выглядеть первый этап перед получением доступа.

Далее:
• Нажми <b>«✅ Получить доступ»</b>
• Выполни действия по примеру
• Потом переходи к <b>Шагу 2</b>
"""

ACCESS_TEXT_1 = """
🖼 <b>Получение доступа — пример 1</b>

Что сделать:
• Нажми там, где отмечено <b>красным</b>
• Пролистай вниз
• Нажми <b>«Выход»</b>

После этого:
• отправь скрин
• администрация проверит
• тебе выдадут данные для входа
"""

ACCESS_TEXT_2 = """
🖼 <b>Получение доступа — пример 2</b>

Теперь отправь <b>фото / скрин</b>, как показано на примере.

Что дальше:
• администрация проверит скрин
• если всё верно — заявка будет одобрена
• после одобрения тебя переведут к менеджеру
"""

STEP_2_TEXT = """
🖼 <b>Шаг 2. Установка приложения Starlink</b>

Скачай приложение <b>только через App Store</b>.

После установки:
• открой приложение
• выдай разрешения
• установи обновления

Далее переходи к <b>Шагу 3</b> 👇
"""

STEP_2_IMAGE_2_TEXT = """
🖼 <b>Шаг 2. Пример после установки</b>

Проверь:
• приложение установлено
• обновления поставлены
• разрешения выданы

После этого переходи к <b>Шагу 3</b> 👇
"""

STEP_3_TEXT = """
🎬 <b>Шаг 3. Подключение к Wi-Fi</b>

Повтори действия из видео:
• выбери нужную сеть
• подключись к Wi-Fi
• проверь соединение

Далее переходи к <b>Шагу 4</b> 👇
"""

STEP_4_TEXT = """
🎬 <b>Шаг 4. Настройка в приложении</b>

Повтори действия из видео:
• открой Starlink
• подтверди разрешения
• дождись завершения настройки

После этого переходи к <b>Шагу 5</b> 👇
"""

STEP_5_TEXT = """
🖼 <b>Шаг 5. Проверка скорости интернета</b>

Проверь скорость через <b>Speedtest</b>:

• открой приложение Speedtest
• запусти тест
• дождись завершения

Если всё ок — настройка завершена ✅
"""

STEP_5_TEXT_2 = """
🖼 <b>Шаг 5. Второй пример Speedtest</b>

Проверь:
• тест завершился без ошибок
• показатели отображаются корректно
• соединение стабильное

Если результат похож на пример — всё настроено правильно.
"""

NOT_SUBSCRIBED_TEXT = """
⚠️ <b>Похоже, ты ещё не подписался на канал.</b>

Подпишись по кнопке ниже и нажми <b>«✅ Я подписался»</b> снова.
"""

WAITING_FOR_SCREEN_TEXT = """
📸 <b>Ждём фото / скрин</b>

Отправь сюда фото или скрин по примеру.

После отправки заявка уйдёт на проверку.
"""

ALREADY_WAITING_TEXT = """
⏳ <b>Заявка уже активна</b>

Ты уже нажал <b>«Получить доступ»</b>.

📸 Просто отправь фото / скрин.
"""

ALREADY_SUBMITTED_TEXT = """
📩 <b>Заявка уже отправлена</b>

Мы уже получили твой фото / скрин и отправили его на проверку.

Пожалуйста, дождись ответа поддержки.
"""

PHOTO_RECEIVED_TEXT = """
✅ <b>Фото / скрин получен!</b>

Ожидайте проверки от поддержки 🛰
"""

PHOTO_APPROVED_TEXT = f"""
✅ <b>Ваше фото одобрено!</b>

Напишите менеджеру <b>@{ADMIN_USERNAME}</b> для получения данных / доступа 👇
"""

PHOTO_REJECTED_TEXT = """
❌ <b>Поддержка не одобрила ваше фото.</b>

Если это ошибка — отправьте более чёткое фото / скрин ещё раз.
"""

SUPPORT_MENU_TEXT = f"""
💬 <b>Связь с поддержкой</b>

Напишите сюда сообщение — и администратор <b>@{ADMIN_USERNAME}</b> ответит вам.

После первого ответа откроется режим чата.
"""

SUPPORT_OPEN_TEXT = f"""
💬 <b>Вы в чате с админом: @{ADMIN_USERNAME}</b>

Теперь вы можете писать сообщения прямо сюда.
"""

SUPPORT_BLOCKED_TEXT = """
⛔ <b>Вы не можете связаться с поддержкой.</b>
"""

SUPPORT_CLOSED_TEXT = """
🔒 <b>Чат с поддержкой завершён.</b>
"""

SPAM_WAIT_TEXT = f"""
⏳ <b>Подожди {USER_MESSAGE_COOLDOWN} сек перед следующим сообщением.</b>
"""

# ─────────────────────────────────────────────────────────────────────────────
# КЛАВИАТУРЫ
# ─────────────────────────────────────────────────────────────────────────────
def main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❓ Частые вопросы", callback_data="faq")],
        [InlineKeyboardButton("📦 Установка", callback_data="install")],
        [InlineKeyboardButton("💬 Связаться с поддержкой", callback_data="support")],
    ])

def install_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Подписаться на канал", url=REVIEWS_CHANNEL_LINK)],
        [InlineKeyboardButton("✅ Я подписался", callback_data="check_sub")],
        [InlineKeyboardButton("💬 Связаться с поддержкой", callback_data="support")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="start")],
    ])

def faq_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📦 Установка", callback_data="install")],
        [InlineKeyboardButton("💬 Поддержка", callback_data="support")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="start")],
    ])

def support_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 Главное меню", callback_data="start")],
    ])

def requirements_keyboard(page: int):
    rows = []
    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"req:{page-1}"))
    if page < 3:
        nav.append(InlineKeyboardButton("➡️ Далее", callback_data=f"req:{page+1}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton("➡️ Перейти к Шагу 1", callback_data="step1:1")])
    rows.append([InlineKeyboardButton("💬 Поддержка", callback_data="support")])
    rows.append([InlineKeyboardButton("🏠 Главное меню", callback_data="start")])
    return InlineKeyboardMarkup(rows)

def step1_keyboard(page: int):
    rows = []
    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton("⬅️ Фото 1", callback_data="step1:1"))
    if page < 2:
        nav.append(InlineKeyboardButton("➡️ Фото 2", callback_data="step1:2"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton("✅ Получить доступ", callback_data="access:1")])
    rows.append([InlineKeyboardButton("➡️ Шаг 2", callback_data="step2:1")])
    rows.append([InlineKeyboardButton("💬 Поддержка", callback_data="support")])
    rows.append([InlineKeyboardButton("🏠 Главное меню", callback_data="start")])
    return InlineKeyboardMarkup(rows)

def access_keyboard(page: int):
    rows = []
    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton("⬅️ Фото 1", callback_data="access:1"))
    if page < 2:
        nav.append(InlineKeyboardButton("➡️ Фото 2", callback_data="access:2"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton("📸 Отправить скрин", callback_data="access_wait")])
    rows.append([InlineKeyboardButton("➡️ Шаг 2", callback_data="step2:1")])
    rows.append([InlineKeyboardButton("💬 Поддержка", callback_data="support")])
    rows.append([InlineKeyboardButton("🏠 Главное меню", callback_data="start")])
    return InlineKeyboardMarkup(rows)

def step2_keyboard(page: int):
    rows = []
    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton("⬅️ Фото 1", callback_data="step2:1"))
    if page < 2:
        nav.append(InlineKeyboardButton("➡️ Фото 2", callback_data="step2:2"))
    if nav:
        rows.append(nav)
    rows.append([
        InlineKeyboardButton("⬅️ Шаг 1", callback_data="step1:1"),
        InlineKeyboardButton("➡️ Шаг 3", callback_data="step3:1"),
    ])
    rows.append([InlineKeyboardButton("💬 Поддержка", callback_data="support")])
    rows.append([InlineKeyboardButton("🏠 Главное меню", callback_data="start")])
    return InlineKeyboardMarkup(rows)

def step3_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⬅️ Шаг 2", callback_data="step2:1"),
            InlineKeyboardButton("➡️ Шаг 4", callback_data="step4:1"),
        ],
        [InlineKeyboardButton("💬 Поддержка", callback_data="support")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="start")],
    ])

def step4_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⬅️ Шаг 3", callback_data="step3:1"),
            InlineKeyboardButton("➡️ Шаг 5", callback_data="step5:1"),
        ],
        [InlineKeyboardButton("💬 Поддержка", callback_data="support")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="start")],
    ])

def step5_keyboard(page: int):
    rows = []
    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton("⬅️ Скрин 1", callback_data="step5:1"))
    if page < 2:
        nav.append(InlineKeyboardButton("➡️ Скрин 2", callback_data="step5:2"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton("⬅️ Шаг 4", callback_data="step4:1")])
    rows.append([InlineKeyboardButton("💬 Поддержка", callback_data="support")])
    rows.append([InlineKeyboardButton("🏠 Главное меню", callback_data="start")])
    return InlineKeyboardMarkup(rows)

def approved_contact_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 Написать менеджеру", url=f"https://t.me/{ADMIN_USERNAME}")],
        [InlineKeyboardButton("💬 Связаться с поддержкой", callback_data="support")],
    ])

def retry_request_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📩 Отправить заявку повторно", callback_data="access:1")],
        [InlineKeyboardButton("💬 Связаться с поддержкой", callback_data="support")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="start")],
    ])

def photo_moderation_keyboard(user_id: int):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Одобрить", callback_data=f"approve:{user_id}"),
            InlineKeyboardButton("❌ Отклонить", callback_data=f"reject:{user_id}"),
        ],
        [
            InlineKeyboardButton("⛔ Заблокировать", callback_data=f"blockcb:{user_id}")
        ]
    ])

# ─────────────────────────────────────────────────────────────────────────────
# ВСПОМОГАТЕЛЬНЫЕ
# ─────────────────────────────────────────────────────────────────────────────
def safe_username(username: str | None) -> str:
    return f"@{username}" if username else "без username"

def build_user_info(update: Update) -> tuple[int, str, str]:
    user_id = update.effective_user.id
    username = update.effective_user.username or None
    full_name = update.effective_user.full_name
    return user_id, safe_username(username), full_name

def is_user_rate_limited(user_id: int) -> bool:
    if user_id == ADMIN_ID:
        return False
    now = time.time()
    last_ts = user_last_message_time.get(user_id)
    if last_ts is not None and (now - last_ts) < USER_MESSAGE_COOLDOWN:
        return True
    user_last_message_time[user_id] = now
    return False

async def send_rate_limit_warning(update: Update):
    try:
        await update.message.reply_text(SPAM_WAIT_TEXT, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Ошибка антиспам-уведомления: {e}")

def extract_user_id_from_text(text: str | None) -> int | None:
    if not text:
        return None

    patterns = [
        r"🆔\s*<code>(\d+)</code>",
        r"🆔\s*(\d+)",
    ]

    for pattern in patterns:
        m = re.search(pattern, text)
        if m:
            try:
                return int(m.group(1))
            except Exception:
                return None
    return None

def resolve_target_id_from_reply(update: Update) -> int | None:
    if not update.message or not update.message.reply_to_message:
        return None

    replied = update.message.reply_to_message

    if replied.caption:
        uid = extract_user_id_from_text(replied.caption)
        if uid:
            return uid

    if replied.text:
        uid = extract_user_id_from_text(replied.text)
        if uid:
            return uid

    return None

def parse_r_text_args(update: Update, context: ContextTypes.DEFAULT_TYPE) -> tuple[int | None, str]:
    if context.args:
        first = context.args[0]
        if first.isdigit():
            target_id = int(first)
            reply_text = " ".join(context.args[1:]).strip()
            return target_id, reply_text

    target_id = resolve_target_id_from_reply(update)
    reply_text = " ".join(context.args).strip() if context.args else ""
    return target_id, reply_text

def parse_r_media_caption(caption: str) -> tuple[int | None, str]:
    if not caption:
        return None, ""
    if not caption.strip().startswith("/r"):
        return None, ""
    body = caption.strip()[2:].strip()
    if not body:
        return None, ""
    parts = body.split(maxsplit=1)
    if parts and parts[0].isdigit():
        target_id = int(parts[0])
        reply_text = parts[1] if len(parts) > 1 else ""
        return target_id, reply_text
    return None, body

def get_target_id_for_r_media(update: Update) -> tuple[int | None, str]:
    caption = update.message.caption or ""
    explicit_id, reply_text = parse_r_media_caption(caption)
    if explicit_id:
        return explicit_id, reply_text
    reply_target = resolve_target_id_from_reply(update)
    if reply_target:
        return reply_target, reply_text
    return None, reply_text

async def open_support_chat_for_user(context: ContextTypes.DEFAULT_TYPE, user_id: int):
    if user_id in active_support_chats:
        return

    active_support_chats.add(user_id)
    save_state()

    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=SUPPORT_OPEN_TEXT,
            parse_mode="HTML",
            reply_markup=support_keyboard(),
        )
    except Exception as e:
        logger.error(f"Не удалось открыть чат поддержки для {user_id}: {e}")

# ─────────────────────────────────────────────────────────────────────────────
# STABLE UI (без edit_message_media)
# ─────────────────────────────────────────────────────────────────────────────
async def acquire_ui_lock(user_id: int) -> bool:
    if user_id in user_ui_locks:
        return False
    user_ui_locks.add(user_id)
    return True

def release_ui_lock(user_id: int):
    user_ui_locks.discard(user_id)

async def cleanup_old_ui_message(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    old_message_id = user_ui_message_ids.get(chat_id)
    if not old_message_id:
        return

    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=old_message_id)
    except Exception:
        pass

async def send_new_ui_message(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    text: str,
    reply_markup: InlineKeyboardMarkup,
    media_type: str | None = None,
    file_id: str | None = None,
):
    await cleanup_old_ui_message(context, chat_id)

    sent = None

    try:
        if media_type == "photo" and file_id:
            sent = await context.bot.send_photo(
                chat_id=chat_id,
                photo=file_id,
                caption=text[:1024],
                parse_mode="HTML",
                reply_markup=reply_markup,
            )
        elif media_type == "video" and file_id:
            sent = await context.bot.send_video(
                chat_id=chat_id,
                video=file_id,
                caption=text[:1024],
                parse_mode="HTML",
                reply_markup=reply_markup,
            )
        else:
            sent = await context.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode="HTML",
                reply_markup=reply_markup,
            )

    except Exception as e:
        logger.warning(f"send_new_ui_message media fallback: {e}")

        sent = await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode="HTML",
            reply_markup=reply_markup,
        )

    user_ui_message_ids[chat_id] = sent.message_id
    save_state()
    return sent

# ─────────────────────────────────────────────────────────────────────────────
# ПРОВЕРКА MEDIA НА СТАРТЕ
# ─────────────────────────────────────────────────────────────────────────────
async def check_media_on_start(context: ContextTypes.DEFAULT_TYPE):
    if not MEDIA_CHECK_ON_START:
        return

    media_map = {
        "REQ_IMAGE_1": REQ_IMAGE_1,
        "REQ_IMAGE_2": REQ_IMAGE_2,
        "REQ_IMAGE_3": REQ_IMAGE_3,
        "STEP1_IMAGE_1": STEP1_IMAGE_1,
        "STEP1_IMAGE_2": STEP1_IMAGE_2,
        "ACCESS_IMAGE_1": ACCESS_IMAGE_1,
        "ACCESS_IMAGE_2": ACCESS_IMAGE_2,
        "STEP2_IMAGE_1": STEP2_IMAGE_1,
        "STEP2_IMAGE_2": STEP2_IMAGE_2,
        "STEP3_VIDEO": STEP3_VIDEO,
        "STEP4_VIDEO": STEP4_VIDEO,
        "STEP5_IMAGE_1": STEP5_IMAGE_1,
        "STEP5_IMAGE_2": STEP5_IMAGE_2,
    }

    logger.info("──── Проверка media variables ────")
    for name, file_id in media_map.items():
        if not file_id:
            logger.info(f"{name}: EMPTY")
            continue

        try:
            await context.bot.get_file(file_id)
            logger.info(f"{name}: OK")
        except Exception as e:
            logger.error(f"{name}: BAD FILE_ID | {e}")
    logger.info("──── Конец проверки media ────")

# ─────────────────────────────────────────────────────────────────────────────
# ЭКРАНЫ
# ─────────────────────────────────────────────────────────────────────────────
async def render_start(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    await send_new_ui_message(
        context=context,
        chat_id=chat_id,
        text=WELCOME_TEXT,
        reply_markup=main_keyboard(),
    )

async def render_faq(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    await send_new_ui_message(
        context=context,
        chat_id=chat_id,
        text=FAQ_TEXT,
        reply_markup=faq_keyboard(),
    )

async def render_install(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    await send_new_ui_message(
        context=context,
        chat_id=chat_id,
        text=INSTALL_TEXT,
        reply_markup=install_keyboard(),
    )

async def render_support(context: ContextTypes.DEFAULT_TYPE, chat_id: int, user_id: int):
    if user_id in blocked_users:
        await send_new_ui_message(
            context=context,
            chat_id=chat_id,
            text=SUPPORT_BLOCKED_TEXT,
            reply_markup=support_keyboard(),
        )
        return

    await send_new_ui_message(
        context=context,
        chat_id=chat_id,
        text=SUPPORT_MENU_TEXT,
        reply_markup=support_keyboard(),
    )

async def render_requirements(context: ContextTypes.DEFAULT_TYPE, chat_id: int, page: int):
    if page == 2:
        text = REQUIREMENTS_TEXT_2
        image = REQ_IMAGE_2
    elif page == 3:
        text = REQUIREMENTS_TEXT_3
        image = REQ_IMAGE_3
    else:
        text = REQUIREMENTS_TEXT
        image = REQ_IMAGE_1

    await send_new_ui_message(
        context=context,
        chat_id=chat_id,
        text=text,
        reply_markup=requirements_keyboard(page),
        media_type="photo" if image else None,
        file_id=image if image else None,
    )

async def render_step1(context: ContextTypes.DEFAULT_TYPE, chat_id: int, page: int):
    if page == 2:
        text = STEP_1_IMAGE_2_TEXT
        image = STEP1_IMAGE_2
    else:
        text = STEP_1_TEXT
        image = STEP1_IMAGE_1

    await send_new_ui_message(
        context=context,
        chat_id=chat_id,
        text=text,
        reply_markup=step1_keyboard(page),
        media_type="photo" if image else None,
        file_id=image if image else None,
    )

async def render_access(context: ContextTypes.DEFAULT_TYPE, chat_id: int, user_id: int, page: int):
    if user_id in blocked_users:
        await send_new_ui_message(
            context=context,
            chat_id=chat_id,
            text=SUPPORT_BLOCKED_TEXT,
            reply_markup=support_keyboard(),
        )
        return

    if page == 2:
        text = ACCESS_TEXT_2
        image = ACCESS_IMAGE_2
    else:
        text = ACCESS_TEXT_1
        image = ACCESS_IMAGE_1

    await send_new_ui_message(
        context=context,
        chat_id=chat_id,
        text=text,
        reply_markup=access_keyboard(page),
        media_type="photo" if image else None,
        file_id=image if image else None,
    )

async def render_access_wait(context: ContextTypes.DEFAULT_TYPE, chat_id: int, user_id: int):
    if user_id in blocked_users:
        await send_new_ui_message(
            context=context,
            chat_id=chat_id,
            text=SUPPORT_BLOCKED_TEXT,
            reply_markup=support_keyboard(),
        )
        return

    if user_id in waiting_for_photo:
        await send_new_ui_message(
            context=context,
            chat_id=chat_id,
            text=ALREADY_WAITING_TEXT,
            reply_markup=access_keyboard(2),
        )
        return

    if user_id in submitted_requests:
        await send_new_ui_message(
            context=context,
            chat_id=chat_id,
            text=ALREADY_SUBMITTED_TEXT,
            reply_markup=retry_request_keyboard(),
        )
        return

    waiting_for_photo.add(user_id)
    save_state()

    await send_new_ui_message(
        context=context,
        chat_id=chat_id,
        text=WAITING_FOR_SCREEN_TEXT,
        reply_markup=retry_request_keyboard(),
    )

async def render_step2(context: ContextTypes.DEFAULT_TYPE, chat_id: int, page: int):
    if page == 2:
        text = STEP_2_IMAGE_2_TEXT
        image = STEP2_IMAGE_2
    else:
        text = STEP_2_TEXT
        image = STEP2_IMAGE_1

    await send_new_ui_message(
        context=context,
        chat_id=chat_id,
        text=text,
        reply_markup=step2_keyboard(page),
        media_type="photo" if image else None,
        file_id=image if image else None,
    )

async def render_step3(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    await send_new_ui_message(
        context=context,
        chat_id=chat_id,
        text=STEP_3_TEXT,
        reply_markup=step3_keyboard(),
        media_type="video" if STEP3_VIDEO else None,
        file_id=STEP3_VIDEO if STEP3_VIDEO else None,
    )

async def render_step4(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    await send_new_ui_message(
        context=context,
        chat_id=chat_id,
        text=STEP_4_TEXT,
        reply_markup=step4_keyboard(),
        media_type="video" if STEP4_VIDEO else None,
        file_id=STEP4_VIDEO if STEP4_VIDEO else None,
    )

async def render_step5(context: ContextTypes.DEFAULT_TYPE, chat_id: int, page: int):
    if page == 2:
        text = STEP_5_TEXT_2
        image = STEP5_IMAGE_2
    else:
        text = STEP_5_TEXT
        image = STEP5_IMAGE_1

    await send_new_ui_message(
        context=context,
        chat_id=chat_id,
        text=text,
        reply_markup=step5_keyboard(page),
        media_type="photo" if image else None,
        file_id=image if image else None,
    )

# ─────────────────────────────────────────────────────────────────────────────
# ОТПРАВКА В ГРУППУ ПОДДЕРЖКИ
# ─────────────────────────────────────────────────────────────────────────────
async def forward_user_text_to_support(
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int,
    username: str,
    full_name: str,
    text: str,
):
    try:
        await context.bot.send_message(
            chat_id=ADMIN_TEXT_CHANNEL_ID,
            text=(
                f"💬 <b>Сообщение от пользователя</b>\n"
                f"👤 {full_name} ({username})\n"
                f"🆔 <code>{user_id}</code>\n\n"
                f"<i>{text}</i>\n\n"
                f"Reply + <code>/r [текст]</code>\n"
                f"или <code>/c</code> / <code>/b</code>"
            ),
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error(f"Не удалось отправить текст в support-группу: {e}")

async def forward_user_photo_to_support(
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int,
    username: str,
    full_name: str,
    photo_file_id: str,
):
    try:
        await context.bot.send_photo(
            chat_id=ADMIN_TEXT_CHANNEL_ID,
            photo=photo_file_id,
            caption=(
                f"📸 <b>Фото от пользователя</b>\n"
                f"👤 {full_name} ({username})\n"
                f"🆔 <code>{user_id}</code>\n\n"
                f"Reply + <code>/r [текст]</code>\n"
                f"или reply + фото с подписью <code>/r [текст]</code>\n"
                f"или reply + файлом с подписью <code>/r [текст]</code>\n"
                f"<code>/c</code> / <code>/b</code>"
            )[:1024],
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error(f"Не удалось отправить фото в support-группу: {e}")

async def forward_user_video_to_support(
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int,
    username: str,
    full_name: str,
    video_file_id: str,
):
    try:
        await context.bot.send_video(
            chat_id=ADMIN_TEXT_CHANNEL_ID,
            video=video_file_id,
            caption=(
                f"🎥 <b>Видео от пользователя</b>\n"
                f"👤 {full_name} ({username})\n"
                f"🆔 <code>{user_id}</code>\n\n"
                f"Reply + <code>/r [текст]</code>\n"
                f"или reply + фото с подписью <code>/r [текст]</code>\n"
                f"или reply + файлом с подписью <code>/r [текст]</code>\n"
                f"<code>/c</code> / <code>/b</code>"
            )[:1024],
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error(f"Не удалось отправить видео в support-группу: {e}")

async def forward_user_document_to_support(
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int,
    username: str,
    full_name: str,
    document_file_id: str,
    file_name: str,
):
    try:
        await context.bot.send_document(
            chat_id=ADMIN_TEXT_CHANNEL_ID,
            document=document_file_id,
            caption=(
                f"📎 <b>Файл от пользователя</b>\n"
                f"👤 {full_name} ({username})\n"
                f"🆔 <code>{user_id}</code>\n"
                f"📄 <code>{file_name}</code>\n\n"
                f"Reply + <code>/r [текст]</code>\n"
                f"или reply + фото с подписью <code>/r [текст]</code>\n"
                f"или reply + файлом с подписью <code>/r [текст]</code>\n"
                f"<code>/c</code> / <code>/b</code>"
            )[:1024],
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error(f"Не удалось отправить файл в support-группу: {e}")

# ─────────────────────────────────────────────────────────────────────────────
# CALLBACK / КНОПКИ
# ─────────────────────────────────────────────────────────────────────────────
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await render_start(context, update.effective_chat.id)

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id

    if not await acquire_ui_lock(user_id):
        await query.answer("⏳ Подожди...", show_alert=False)
        return

    try:
        await query.answer()
        clicker_id = query.from_user.id
        data = query.data
        chat_id = query.message.chat_id

        # ── модерация фото ────────────────────────────────────────────────────
        if data.startswith(("approve:", "reject:", "blockcb:")):
            if clicker_id != ADMIN_ID:
                await query.answer("У вас нет доступа.", show_alert=True)
                return

            try:
                target_id = int(data.split(":")[1])
            except Exception:
                await query.answer("Ошибка данных.", show_alert=True)
                return

            if data.startswith("approve:"):
                try:
                    submitted_requests.discard(target_id)
                    waiting_for_photo.discard(target_id)
                    save_state()

                    await context.bot.send_message(
                        chat_id=target_id,
                        text=PHOTO_APPROVED_TEXT,
                        parse_mode="HTML",
                        reply_markup=approved_contact_keyboard(),
                    )

                    try:
                        await query.edit_message_reply_markup(reply_markup=None)
                    except Exception:
                        pass

                    await query.answer("Фото одобрено ✅")
                except Exception as e:
                    logger.error(f"Ошибка approve: {e}")
                    await query.answer("Не удалось одобрить.", show_alert=True)
                return

            if data.startswith("reject:"):
                try:
                    submitted_requests.discard(target_id)
                    waiting_for_photo.discard(target_id)
                    save_state()

                    await context.bot.send_message(
                        chat_id=target_id,
                        text=PHOTO_REJECTED_TEXT,
                        parse_mode="HTML",
                        reply_markup=retry_request_keyboard(),
                    )

                    try:
                        await query.edit_message_reply_markup(reply_markup=None)
                    except Exception:
                        pass

                    await query.answer("Фото отклонено ❌")
                except Exception as e:
                    logger.error(f"Ошибка reject: {e}")
                    await query.answer("Не удалось отклонить.", show_alert=True)
                return

            if data.startswith("blockcb:"):
                try:
                    blocked_users.add(target_id)
                    active_support_chats.discard(target_id)
                    waiting_for_photo.discard(target_id)
                    submitted_requests.discard(target_id)
                    save_state()

                    await context.bot.send_message(
                        chat_id=target_id,
                        text=SUPPORT_BLOCKED_TEXT,
                        parse_mode="HTML",
                    )

                    await query.answer("Пользователь заблокирован ⛔")
                except Exception as e:
                    logger.error(f"Ошибка blockcb: {e}")
                    await query.answer("Не удалось заблокировать.", show_alert=True)
                return

        # ── основная навигация ────────────────────────────────────────────────
        if data == "start":
            await render_start(context, chat_id)
            return

        if data == "faq":
            await render_faq(context, chat_id)
            return

        if data == "install":
            await render_install(context, chat_id)
            return

        if data == "support":
            await render_support(context, chat_id, user_id)
            return

        if data == "check_sub":
            try:
                member = await context.bot.get_chat_member(REVIEWS_CHANNEL_USERNAME, user_id)
                if member.status in ("member", "administrator", "creator"):
                    await render_requirements(context, chat_id, 1)
                else:
                    await send_new_ui_message(
                        context=context,
                        chat_id=chat_id,
                        text=NOT_SUBSCRIBED_TEXT,
                        reply_markup=install_keyboard(),
                    )
            except Exception as e:
                logger.error(f"Ошибка проверки подписки: {e}")
                await send_new_ui_message(
                    context=context,
                    chat_id=chat_id,
                    text=NOT_SUBSCRIBED_TEXT,
                    reply_markup=install_keyboard(),
                )
            return

        if data.startswith("req:"):
            page = int(data.split(":")[1])
            await render_requirements(context, chat_id, page)
            return

        if data.startswith("step1:"):
            page = int(data.split(":")[1])
            await render_step1(context, chat_id, page)
            return

        if data.startswith("access:"):
            page = int(data.split(":")[1])
            await render_access(context, chat_id, user_id, page)
            return

        if data == "access_wait":
            await render_access_wait(context, chat_id, user_id)
            return

        if data.startswith("step2:"):
            page = int(data.split(":")[1])
            await render_step2(context, chat_id, page)
            return

        if data.startswith("step3:"):
            await render_step3(context, chat_id)
            return

        if data.startswith("step4:"):
            await render_step4(context, chat_id)
            return

        if data.startswith("step5:"):
            page = int(data.split(":")[1])
            await render_step5(context, chat_id, page)
            return

    finally:
        release_ui_lock(user_id)

# ─────────────────────────────────────────────────────────────────────────────
# АДМИН-КОМАНДЫ
# ─────────────────────────────────────────────────────────────────────────────
async def cmd_r(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    target_id, reply_text = parse_r_text_args(update, context)

    if not target_id:
        await update.message.reply_text(
            "📝 Формат:\n"
            "/r [ID] [текст]\n\n"
            "или reply на сообщение пользователя:\n"
            "/r [текст]"
        )
        return

    if not reply_text:
        await update.message.reply_text("❌ Напиши текст ответа.")
        return

    try:
        if target_id in blocked_users:
            await update.message.reply_text("⛔ Пользователь заблокирован.")
            return

        await open_support_chat_for_user(context, target_id)

        await context.bot.send_message(
            chat_id=target_id,
            text=f"💬 <b>Ответ от поддержки:</b>\n\n{reply_text}",
            parse_mode="HTML",
        )

        await update.message.reply_text(f"✅ Ответ отправлен пользователю {target_id}")

    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

async def cmd_approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    target_id = None
    if context.args and context.args[0].isdigit():
        target_id = int(context.args[0])
    else:
        target_id = resolve_target_id_from_reply(update)

    if not target_id:
        await update.message.reply_text("📝 /a [ID] или reply + /a")
        return

    try:
        submitted_requests.discard(target_id)
        waiting_for_photo.discard(target_id)
        save_state()

        await context.bot.send_message(
            chat_id=target_id,
            text=PHOTO_APPROVED_TEXT,
            parse_mode="HTML",
            reply_markup=approved_contact_keyboard(),
        )

        await update.message.reply_text(f"✅ Пользователь {target_id} одобрен.")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

async def cmd_decline(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    target_id = None
    decline_reason = ""

    if context.args:
        if context.args[0].isdigit():
            target_id = int(context.args[0])
            decline_reason = " ".join(context.args[1:]).strip()
        else:
            target_id = resolve_target_id_from_reply(update)
            decline_reason = " ".join(context.args).strip()
    else:
        target_id = resolve_target_id_from_reply(update)

    if not target_id:
        await update.message.reply_text("📝 /d [ID] [причина] или reply + /d [причина]")
        return

    try:
        submitted_requests.discard(target_id)
        waiting_for_photo.discard(target_id)
        save_state()

        reject_text = PHOTO_REJECTED_TEXT
        if decline_reason:
            reject_text += f"\n\n💬 <b>Комментарий поддержки:</b>\n{decline_reason}"

        await context.bot.send_message(
            chat_id=target_id,
            text=reject_text,
            parse_mode="HTML",
            reply_markup=retry_request_keyboard(),
        )

        await update.message.reply_text(f"❌ Пользователь {target_id} отклонён.")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

async def cmd_close(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    target_id = None
    if context.args and context.args[0].isdigit():
        target_id = int(context.args[0])
    else:
        target_id = resolve_target_id_from_reply(update)

    if not target_id:
        await update.message.reply_text("📝 /c [ID] или reply + /c")
        return

    try:
        active_support_chats.discard(target_id)
        save_state()

        await context.bot.send_message(
            chat_id=target_id,
            text=SUPPORT_CLOSED_TEXT,
            parse_mode="HTML",
            reply_markup=main_keyboard(),
        )

        await update.message.reply_text(f"🔒 Чат с пользователем {target_id} завершён.")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

async def cmd_block(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    target_id = None
    if context.args and context.args[0].isdigit():
        target_id = int(context.args[0])
    else:
        target_id = resolve_target_id_from_reply(update)

    if not target_id:
        await update.message.reply_text("📝 /b [ID] или reply + /b")
        return

    try:
        blocked_users.add(target_id)
        active_support_chats.discard(target_id)
        waiting_for_photo.discard(target_id)
        submitted_requests.discard(target_id)
        save_state()

        await context.bot.send_message(
            chat_id=target_id,
            text=SUPPORT_BLOCKED_TEXT,
            parse_mode="HTML",
        )

        await update.message.reply_text(f"⛔ Пользователь {target_id} заблокирован.")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

async def cmd_unblock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("📝 /u [ID]")
        return

    target_id = int(context.args[0])

    try:
        blocked_users.discard(target_id)
        save_state()

        await context.bot.send_message(
            chat_id=target_id,
            text="✅ <b>Доступ к поддержке восстановлен.</b>",
            parse_mode="HTML",
            reply_markup=main_keyboard(),
        )

        await update.message.reply_text(f"✅ Пользователь {target_id} разблокирован.")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

async def cmd_state(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    await update.message.reply_text(
        "📊 <b>Состояние бота</b>\n\n"
        f"waiting_for_photo: <code>{len(waiting_for_photo)}</code>\n"
        f"submitted_requests: <code>{len(submitted_requests)}</code>\n"
        f"active_support_chats: <code>{len(active_support_chats)}</code>\n"
        f"blocked_users: <code>{len(blocked_users)}</code>\n"
        f"ui_messages: <code>{len(user_ui_message_ids)}</code>\n"
        f"cooldown: <code>{USER_MESSAGE_COOLDOWN}</code>\n"
        f"text_group: <code>{ADMIN_TEXT_CHANNEL_ID}</code>\n"
        f"photo_group: <code>{ADMIN_PHOTO_CHANNEL_ID}</code>\n"
        f"state_file: <code>{STATE_FILE}</code>",
        parse_mode="HTML",
    )

async def cmd_getfileid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    if update.message.reply_to_message:
        replied = update.message.reply_to_message

        if replied.photo:
            file_id = replied.photo[-1].file_id
            await update.message.reply_text(f"🖼 PHOTO FILE_ID:\n<code>{file_id}</code>", parse_mode="HTML")
            return

        if replied.video:
            file_id = replied.video.file_id
            await update.message.reply_text(f"🎥 VIDEO FILE_ID:\n<code>{file_id}</code>", parse_mode="HTML")
            return

        if replied.document:
            file_id = replied.document.file_id
            await update.message.reply_text(f"📎 DOCUMENT FILE_ID:\n<code>{file_id}</code>", parse_mode="HTML")
            return

    await update.message.reply_text(
        "ℹ️ Ответь /g на фото, видео или файл,\n"
        "либо отправь медиа с подписью /g",
        parse_mode="HTML"
    )

# ─────────────────────────────────────────────────────────────────────────────
# АДМИН: ФОТО / ВИДЕО / ФАЙЛЫ ЧЕРЕЗ /r И /g
# ─────────────────────────────────────────────────────────────────────────────
async def admin_r_photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    caption = update.message.caption or ""

    if caption.strip().startswith("/g"):
        if update.message.photo:
            file_id = update.message.photo[-1].file_id
            await update.message.reply_text(f"🖼 PHOTO FILE_ID:\n<code>{file_id}</code>", parse_mode="HTML")
        return

    if not update.message.photo:
        return

    try:
        target_id, reply_text = get_target_id_for_r_media(update)

        if not target_id:
            await update.message.reply_text(
                "📝 Фото + подпись:\n"
                "/r [ID] [текст]\n\n"
                "или reply на сообщение пользователя + фото с подписью:\n"
                "/r [текст]"
            )
            return

        if not reply_text:
            reply_text = "📸 Сообщение от поддержки"

        if target_id in blocked_users:
            await update.message.reply_text("⛔ Пользователь заблокирован.")
            return

        await open_support_chat_for_user(context, target_id)

        photo = update.message.photo[-1].file_id

        await context.bot.send_photo(
            chat_id=target_id,
            photo=photo,
            caption=f"💬 <b>Ответ от поддержки:</b>\n\n{reply_text}",
            parse_mode="HTML",
        )

        await update.message.reply_text(f"✅ Фото отправлено пользователю {target_id}")

    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

async def admin_r_video_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    caption = update.message.caption or ""

    if caption.strip().startswith("/g"):
        if update.message.video:
            file_id = update.message.video.file_id
            await update.message.reply_text(f"🎥 VIDEO FILE_ID:\n<code>{file_id}</code>", parse_mode="HTML")
        return

    if not caption.strip().startswith("/r"):
        return

    try:
        target_id, reply_text = get_target_id_for_r_media(update)

        if not target_id:
            await update.message.reply_text(
                "📝 Видео + подпись:\n"
                "/r [ID] [текст]\n\n"
                "или reply на сообщение пользователя + видео с подписью:\n"
                "/r [текст]"
            )
            return

        if not reply_text:
            reply_text = "🎥 Сообщение от поддержки"

        if target_id in blocked_users:
            await update.message.reply_text("⛔ Пользователь заблокирован.")
            return

        await open_support_chat_for_user(context, target_id)

        await context.bot.send_video(
            chat_id=target_id,
            video=update.message.video.file_id,
            caption=f"💬 <b>Ответ от поддержки:</b>\n\n{reply_text}",
            parse_mode="HTML",
        )

        await update.message.reply_text(f"✅ Видео отправлено пользователю {target_id}")

    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

async def admin_r_document_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    caption = update.message.caption or ""

    if caption.strip().startswith("/g"):
        if update.message.document:
            file_id = update.message.document.file_id
            await update.message.reply_text(f"📎 DOCUMENT FILE_ID:\n<code>{file_id}</code>", parse_mode="HTML")
        return

    if not update.message.document:
        return

    try:
        target_id, reply_text = get_target_id_for_r_media(update)

        if not target_id:
            await update.message.reply_text(
                "📝 Файл + подпись:\n"
                "/r [ID] [текст]\n\n"
                "или reply на сообщение пользователя + файл с подписью:\n"
                "/r [текст]"
            )
            return

        if not reply_text:
            reply_text = "📎 Сообщение от поддержки"

        if target_id in blocked_users:
            await update.message.reply_text("⛔ Пользователь заблокирован.")
            return

        await open_support_chat_for_user(context, target_id)

        document = update.message.document.file_id

        await context.bot.send_document(
            chat_id=target_id,
            document=document,
            caption=f"💬 <b>Ответ от поддержки:</b>\n\n{reply_text}",
            parse_mode="HTML",
        )

        await update.message.reply_text(f"✅ Файл отправлен пользователю {target_id}")

    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

# ─────────────────────────────────────────────────────────────────────────────
# ПОЛЬЗОВАТЕЛЬСКИЕ СООБЩЕНИЯ
# ─────────────────────────────────────────────────────────────────────────────
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id, username, full_name = build_user_info(update)
    text = update.message.text if update.message.text else ""

    if user_id == ADMIN_ID and text.startswith("/"):
        return

    if user_id in blocked_users:
        await update.message.reply_text(SUPPORT_BLOCKED_TEXT, parse_mode="HTML")
        return

    if is_user_rate_limited(user_id):
        await send_rate_limit_warning(update)
        return

    if user_id in waiting_for_photo:
        await update.message.reply_text(
            "📸 Жду именно <b>фото / скрин</b>, не текст! Прикрепи изображение.",
            parse_mode="HTML",
        )
        return

    await forward_user_text_to_support(context, user_id, username, full_name, text)

    if user_id not in active_support_chats:
        await update.message.reply_text(
            "💬 <b>Сообщение отправлено в поддержку.</b>\n\nОжидайте ответа администратора.",
            parse_mode="HTML",
            reply_markup=support_keyboard(),
        )

# ─────────────────────────────────────────────────────────────────────────────
# ПОЛЬЗОВАТЕЛЬСКИЕ ФОТО
# ─────────────────────────────────────────────────────────────────────────────
async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id, username, full_name = build_user_info(update)

    if user_id == ADMIN_ID:
        caption = update.message.caption or ""
        if caption.strip().startswith("/r") or caption.strip().startswith("/g"):
            return

        await update.message.reply_text(
            "📸 Reply на сообщение пользователя + фото с подписью:\n"
            "<code>/r [текст]</code>\n\n"
            "или:\n<code>/r [ID] [текст]</code>",
            parse_mode="HTML",
        )
        return

    if user_id in blocked_users:
        await update.message.reply_text(SUPPORT_BLOCKED_TEXT, parse_mode="HTML")
        return

    if is_user_rate_limited(user_id):
        await send_rate_limit_warning(update)
        return

    if user_id in waiting_for_photo:
        if user_id in submitted_requests:
            await update.message.reply_text(ALREADY_SUBMITTED_TEXT, parse_mode="HTML")
            return

        waiting_for_photo.discard(user_id)
        submitted_requests.add(user_id)
        save_state()

        try:
            photo = update.message.photo[-1].file_id

            caption = (
                f"📸 <b>Фото на модерацию</b>\n"
                f"👤 {full_name} ({username})\n"
                f"🆔 <code>{user_id}</code>\n\n"
                f"Ниже кнопки: одобрить / отклонить / блок"
            )

            await context.bot.send_photo(
                chat_id=ADMIN_PHOTO_CHANNEL_ID,
                photo=photo,
                caption=caption[:1024],
                parse_mode="HTML",
                reply_markup=photo_moderation_keyboard(user_id),
            )

            await update.message.reply_text(
                PHOTO_RECEIVED_TEXT,
                parse_mode="HTML",
                reply_markup=main_keyboard(),
            )

        except Exception as e:
            logger.error(f"Ошибка отправки фото на модерацию: {e}")
            submitted_requests.discard(user_id)
            save_state()
            await update.message.reply_text("❌ Ошибка при обработке фото. Попробуйте позже.")
        return

    try:
        await forward_user_photo_to_support(
            context,
            user_id,
            username,
            full_name,
            update.message.photo[-1].file_id,
        )

        if user_id not in active_support_chats:
            await update.message.reply_text(
                "📨 <b>Фото отправлено в поддержку.</b>",
                parse_mode="HTML",
                reply_markup=support_keyboard(),
            )
    except Exception as e:
        logger.error(f"Ошибка отправки фото в поддержку: {e}")
        await update.message.reply_text("❌ Не удалось отправить фото в поддержку.")

# ─────────────────────────────────────────────────────────────────────────────
# ПОЛЬЗОВАТЕЛЬСКИЕ ВИДЕО
# ─────────────────────────────────────────────────────────────────────────────
async def video_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id, username, full_name = build_user_info(update)

    if user_id == ADMIN_ID:
        caption = update.message.caption or ""
        if caption.strip().startswith("/g") or caption.strip().startswith("/r"):
            return

        await update.message.reply_text(
            "🎥 Reply на сообщение пользователя + видео с подписью:\n"
            "<code>/r [текст]</code>\n\n"
            "или:\n<code>/r [ID] [текст]</code>\n\n"
            "Для file_id:\n<code>/g</code>",
            parse_mode="HTML",
        )
        return

    if user_id in blocked_users:
        await update.message.reply_text(SUPPORT_BLOCKED_TEXT, parse_mode="HTML")
        return

    if is_user_rate_limited(user_id):
        await send_rate_limit_warning(update)
        return

    if user_id in waiting_for_photo:
        await update.message.reply_text(
            "📸 Для заявки нужен именно <b>фото / скрин</b>, а не видео.",
            parse_mode="HTML",
        )
        return

    try:
        await forward_user_video_to_support(
            context,
            user_id,
            username,
            full_name,
            update.message.video.file_id,
        )

        if user_id not in active_support_chats:
            await update.message.reply_text(
                "📨 <b>Видео отправлено в поддержку.</b>",
                parse_mode="HTML",
                reply_markup=support_keyboard(),
            )
    except Exception as e:
        logger.error(f"Ошибка отправки видео в поддержку: {e}")
        await update.message.reply_text("❌ Не удалось отправить видео в поддержку.")

# ─────────────────────────────────────────────────────────────────────────────
# ПОЛЬЗОВАТЕЛЬСКИЕ ФАЙЛЫ
# ─────────────────────────────────────────────────────────────────────────────
async def document_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id, username, full_name = build_user_info(update)

    if user_id == ADMIN_ID:
        caption = update.message.caption or ""
        if caption.strip().startswith("/r") or caption.strip().startswith("/g"):
            return

        await update.message.reply_text(
            "📎 Reply на сообщение пользователя + файл с подписью:\n"
            "<code>/r [текст]</code>\n\n"
            "или:\n<code>/r [ID] [текст]</code>",
            parse_mode="HTML",
        )
        return

    if user_id in blocked_users:
        await update.message.reply_text(SUPPORT_BLOCKED_TEXT, parse_mode="HTML")
        return

    if is_user_rate_limited(user_id):
        await send_rate_limit_warning(update)
        return

    file_name = update.message.document.file_name or "file"

    if user_id in waiting_for_photo:
        if user_id in submitted_requests:
            await update.message.reply_text(ALREADY_SUBMITTED_TEXT, parse_mode="HTML")
            return

        if not update.message.document.mime_type or not update.message.document.mime_type.startswith("image/"):
            await update.message.reply_text(
                "📸 Для заявки нужен именно <b>скрин / фото</b> (изображение), а не обычный файл.",
                parse_mode="HTML",
            )
            return

        waiting_for_photo.discard(user_id)
        submitted_requests.add(user_id)
        save_state()

        try:
            document = update.message.document.file_id

            await context.bot.send_document(
                chat_id=ADMIN_PHOTO_CHANNEL_ID,
                document=document,
                caption=(
                    f"🖼 <b>Скрин на модерацию</b>\n"
                    f"👤 {full_name} ({username})\n"
                    f"🆔 <code>{user_id}</code>\n"
                    f"📄 <code>{file_name}</code>"
                )[:1024],
                parse_mode="HTML",
            )

            await context.bot.send_message(
                chat_id=ADMIN_PHOTO_CHANNEL_ID,
                text=f"🛠 Модерация для пользователя <code>{user_id}</code>",
                parse_mode="HTML",
                reply_markup=photo_moderation_keyboard(user_id),
            )

            await update.message.reply_text(
                PHOTO_RECEIVED_TEXT,
                parse_mode="HTML",
                reply_markup=main_keyboard(),
            )

        except Exception as e:
            logger.error(f"Ошибка отправки image-doc на модерацию: {e}")
            submitted_requests.discard(user_id)
            save_state()
            await update.message.reply_text("❌ Ошибка при обработке файла. Попробуйте позже.")
        return

    try:
        await forward_user_document_to_support(
            context,
            user_id,
            username,
            full_name,
            update.message.document.file_id,
            file_name,
        )

        if user_id not in active_support_chats:
            await update.message.reply_text(
                "📨 <b>Файл отправлен в поддержку.</b>",
                parse_mode="HTML",
                reply_markup=support_keyboard(),
            )
    except Exception as e:
        logger.error(f"Ошибка отправки файла в поддержку: {e}")
        await update.message.reply_text("❌ Не удалось отправить файл в поддержку.")

# ─────────────────────────────────────────────────────────────────────────────
# ЗАПУСК
# ─────────────────────────────────────────────────────────────────────────────
async def on_startup(app: Application):
    logger.info("Бот успешно запущен.")
    try:
        await check_media_on_start(app)
    except Exception as e:
        logger.error(f"Ошибка media-check на старте: {e}")

def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN не найден. Добавь переменную BOT_TOKEN в Railway Variables.")

    load_state()

    app = Application.builder().token(BOT_TOKEN).post_init(on_startup).build()

    # команды
    app.add_handler(CommandHandler("start", cmd_start))

    # reply
    app.add_handler(CommandHandler("r", cmd_r))

    # approve / decline
    app.add_handler(CommandHandler("a", cmd_approve))
    app.add_handler(CommandHandler("approve", cmd_approve))

    app.add_handler(CommandHandler("d", cmd_decline))
    app.add_handler(CommandHandler("reject", cmd_decline))

    # close
    app.add_handler(CommandHandler("c", cmd_close))
    app.add_handler(CommandHandler("close", cmd_close))

    # block
    app.add_handler(CommandHandler("b", cmd_block))
    app.add_handler(CommandHandler("block", cmd_block))

    # unblock
    app.add_handler(CommandHandler("u", cmd_unblock))
    app.add_handler(CommandHandler("unblock", cmd_unblock))

    # state
    app.add_handler(CommandHandler("s", cmd_state))
    app.add_handler(CommandHandler("state", cmd_state))

    # get file id
    app.add_handler(CommandHandler("g", cmd_getfileid))
    app.add_handler(CommandHandler("getfileid", cmd_getfileid))

    # кнопки
    app.add_handler(CallbackQueryHandler(callback_handler))

    # админ: фото / видео / файлы через /r и /g
    app.add_handler(MessageHandler(
        filters.PHOTO & (filters.CaptionRegex(r"^/r\b") | filters.CaptionRegex(r"^/g\b")),
        admin_r_photo_handler
    ))
    app.add_handler(MessageHandler(
        filters.VIDEO & (filters.CaptionRegex(r"^/r\b") | filters.CaptionRegex(r"^/g\b")),
        admin_r_video_handler
    ))
    app.add_handler(MessageHandler(
        filters.Document.ALL & (filters.CaptionRegex(r"^/r\b") | filters.CaptionRegex(r"^/g\b")),
        admin_r_document_handler
    ))

    # пользовательские медиа
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    app.add_handler(MessageHandler(filters.VIDEO, video_handler))
    app.add_handler(MessageHandler(filters.Document.ALL, document_handler))

    # текст
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    logger.info("Бот запускается...")
    app.run_polling()

if __name__ == "__main__":
    main()
