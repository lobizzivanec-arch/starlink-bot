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
    InputMediaPhoto,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)

# ─── НАСТРОЙКИ ────────────────────────────────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN")

ADMIN_ID = int(os.getenv("ADMIN_ID", "8197197463"))
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "sunrisseq")  # БЕЗ @

# Группа/канал поддержки (сюда идут ТЕКСТ / ФОТО / ФАЙЛЫ для обычного чата)
ADMIN_TEXT_CHANNEL_ID = int(os.getenv("ADMIN_TEXT_CHANNEL_ID", "-1003842776546"))

# Группа/канал заявок (сюда идут только скрины на модерацию после "Получить доступ")
ADMIN_PHOTO_CHANNEL_ID = int(os.getenv("ADMIN_PHOTO_CHANNEL_ID", "-1003907521717"))

REVIEWS_CHANNEL_USERNAME = os.getenv("REVIEWS_CHANNEL_USERNAME", "@your_reviews_channel")
REVIEWS_CHANNEL_LINK = os.getenv("REVIEWS_CHANNEL_LINK", "https://t.me/your_reviews_channel")

# FILE_ID картинок
STEP2_IMAGE_1 = os.getenv("STEP2_IMAGE_1", "")
STEP2_IMAGE_2 = os.getenv("STEP2_IMAGE_2", "")

STEP3_IMAGE_1 = os.getenv("STEP3_IMAGE_1", "")
STEP3_IMAGE_2 = os.getenv("STEP3_IMAGE_2", "")
STEP3_IMAGE_3 = os.getenv("STEP3_IMAGE_3", "")

ACCESS_IMAGE_1 = os.getenv("ACCESS_IMAGE_1", "")
ACCESS_IMAGE_2 = os.getenv("ACCESS_IMAGE_2", "")

STATE_FILE = os.getenv("STATE_FILE", "bot_state.json")

# Антиспам
USER_MESSAGE_COOLDOWN = int(os.getenv("USER_MESSAGE_COOLDOWN", "6"))

# ──────────────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger(__name__)

# ─── СОСТОЯНИЯ ────────────────────────────────────────────────────────────────
waiting_for_photo: set[int] = set()      # ждём скрин после "Получить доступ"
submitted_requests: set[int] = set()     # скрин уже отправлен на модерацию
active_support_chats: set[int] = set()   # пользователь в активном чате с поддержкой
blocked_users: set[int] = set()          # заблокированные пользователи

# user_id -> last unix time
user_last_message_time: dict[int, float] = {}

# ─── PERSISTENCE JSON ─────────────────────────────────────────────────────────

def save_state():
    try:
        data = {
            "waiting_for_photo": list(waiting_for_photo),
            "submitted_requests": list(submitted_requests),
            "active_support_chats": list(active_support_chats),
            "blocked_users": list(blocked_users),
        }
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info("Состояние сохранено.")
    except Exception as e:
        logger.error(f"Ошибка сохранения состояния: {e}")

def load_state():
    global waiting_for_photo, submitted_requests, active_support_chats, blocked_users

    try:
        if not Path(STATE_FILE).exists():
            logger.info("Файл состояния не найден, стартуем с пустого.")
            return

        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        waiting_for_photo = set(map(int, data.get("waiting_for_photo", [])))
        submitted_requests = set(map(int, data.get("submitted_requests", [])))
        active_support_chats = set(map(int, data.get("active_support_chats", [])))
        blocked_users = set(map(int, data.get("blocked_users", [])))

        logger.info("Состояние загружено.")
    except Exception as e:
        logger.error(f"Ошибка загрузки состояния: {e}")

# ─── ТЕКСТЫ ───────────────────────────────────────────────────────────────────

WELCOME_TEXT = """
👋 Привет! Рады, что ты нашёл нас через TikTok.

🌐 <b>Starlink</b> — это то самое приложение, которое ты видел в ролике. Спутниковый интернет нового поколения, который работает <b>где угодно</b>: в горах, в поле, в машине — даже там, где нет ни одной вышки.

📶 Никаких операторов. Никаких мёртвых зон. Просто быстрый интернет везде.

Выбери, что тебя интересует 👇
"""

FAQ_TEXT = """
❓ <b>Часто задаваемые вопросы о Starlink</b>

<b>Что такое Starlink?</b>
Starlink — система спутникового интернета от компании SpaceX. Спутники на низкой орбите обеспечивают покрытие по всему миру.

<b>Для кого это?</b>
• 🏕 Туристы и путешественники
• 🚗 Автопутешественники
• 🌾 Жители сёл и дач
• ⚡ Те, кто устал от плохого интернета

<b>Как это работает?</b>
Небольшая тарелка ловит сигнал со спутников → ты получаешь стабильный интернет. Всё управление через приложение.

💡 Хочешь узнать как установить? Нажми кнопку ниже 👇
"""

INSTALL_TEXT = """
📦 <b>Инструкция по установке Starlink</b>

Перед получением <b>тутора</b> — один шаг:

👇 Подпишись на наш <b>новый канал с отзывами пользователей Starlink</b>.

После подписки нажми кнопку <b>«✅ Я подписался»</b> — и мы сразу отправим тебе полную инструкцию.
"""

STEP_1_TEXT = """
📦 <b>Шаг 1. Доступ в аккаунт с доступом к Starlink</b>

<b>Краткое описание:</b>

Мы выдаём тебе доступ к аккаунту, в котором отсутствуют ограничения на подключение к Wi-Fi на территории России

Что нужно сделать:
• Нажать кнопку <b>«Получить доступ»</b>
• Получить данные для входа
• Авторизоваться в аккаунте

После этого переходи к следующему шагу 👇
"""

ACCESS_REQUEST_TEXT = """
✅ <b>Получить доступ</b>

Нажми там, где отмечено <b>красным</b>, затем пролистай вниз и нажми кнопку <b>«Выход»</b>.

После этого я дам тебе <b>почту и пароль</b> для входа.

📸 <b>Теперь просто отправь фото / скрин</b>, как на втором примере ниже.

Администрация рассмотрит заявку и предоставит данные для входа.
"""

ALREADY_WAITING_TEXT = """
⏳ <b>Заявка уже активна</b>

Ты уже нажал <b>«Получить доступ»</b>.

📸 Просто отправь фото / скрин по инструкции — мы ждём именно его.
"""

ALREADY_SUBMITTED_TEXT = """
📩 <b>Заявка уже отправлена</b>

Мы уже получили твой фото / скрин и отправили его на проверку.

Пожалуйста, дождись ответа поддержки.
"""

STEP_2_TEXT = """
📲 <b>Шаг 2. Установка приложения Starlink</b>

<b>Краткое описание:</b>

Скачай официальное приложение <b>Starlink</b> через:
• <b>App Store</b> (iPhone)
• <b>Google Play</b> (Android)

После установки:
• Открой приложение
• Разреши необходимые доступы
• Установи все доступные обновления
"""

STEP_3_TEXT = """
📶 <b>Шаг 3. Настройка приложения и подключение к Wi-Fi</b>

<b>Краткое описание:</b>

После входа в приложение:
• Открой настройки
• Найди доступную сеть
• Подключись к Wi-Fi
• Дождись стабильного соединения
"""

NOT_SUBSCRIBED_TEXT = """
⚠️ Похоже, ты ещё не подписался на канал.

Подпишись по кнопке ниже и нажми <b>«✅ Я подписался»</b> снова.
"""

PHOTO_RECEIVED_TEXT = """
✅ Фото / скрин получен! Спасибо.

Ожидайте проверки от поддержки 🛰
"""

PHOTO_APPROVED_TEXT = """
✅ <b>Ваше фото одобрено!</b>

Напишите менеджеру <b>@sunrisseq</b> для получения данных / доступа 👇
"""

PHOTO_REJECTED_TEXT = """
❌ <b>Поддержка не одобрила ваше фото.</b>

Если это ошибка — отправьте более чёткое фото / скрин ещё раз.
"""

ACCESS_PANEL_TEXT = """
📸 <b>Инструкция открыта выше</b>

Отправь фото / скрин по примеру выше — мы ждём его на проверку.
"""

STEP2_PANEL_TEXT = """
📲 <b>Шаг 2 открыт выше</b>

Смотри 2 изображения выше и переходи дальше 👇
"""

STEP3_PANEL_TEXT = """
📶 <b>Шаг 3 открыт выше</b>

Смотри изображения выше и заверши настройку 👇
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

# ─── КЛАВИАТУРЫ ───────────────────────────────────────────────────────────────

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

def back_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📦 Установка", callback_data="install")],
        [InlineKeyboardButton("💬 Связаться с поддержкой", callback_data="support")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="start")],
    ])

def step_1_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Получить доступ", callback_data="get_access")],
        [InlineKeyboardButton("➡️ Шаг 2", callback_data="step2")],
        [InlineKeyboardButton("💬 Связаться с поддержкой", callback_data="support")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="start")],
    ])

def access_panel_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 Связаться с поддержкой", callback_data="support")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="start")],
    ])

def step_2_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Шаг 1", callback_data="step1")],
        [InlineKeyboardButton("➡️ Шаг 3", callback_data="step3")],
        [InlineKeyboardButton("💬 Связаться с поддержкой", callback_data="support")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="start")],
    ])

def step_3_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Шаг 2", callback_data="step2")],
        [InlineKeyboardButton("💬 Связаться с поддержкой", callback_data="support")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="start")],
    ])

def support_keyboard():
    return InlineKeyboardMarkup([
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

def approved_contact_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 Написать менеджеру", url=f"https://t.me/{ADMIN_USERNAME}")],
        [InlineKeyboardButton("💬 Связаться с поддержкой", callback_data="support")],
    ])

def retry_request_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📩 Отправить заявку повторно", callback_data="retry_access")],
        [InlineKeyboardButton("💬 Связаться с поддержкой", callback_data="support")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="start")],
    ])

# ─── ВСПОМОГАТЕЛЬНОЕ ──────────────────────────────────────────────────────────

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
    """
    Ищет user_id в тексте вида:
    🆔 123456789
    🆔 <code>123456789</code>
    """
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
    """
    Достаёт ID из reply_to_message (текст или caption)
    """
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
    """
    /r 123 текст
    или reply на сообщение + /r текст
    """
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
    """
    Поддержка:
    /r 123 текст
    /r текст   (если media отправлен reply'ем)
    """
    if not caption:
        return None, ""

    if not caption.strip().startswith("/r"):
        return None, ""

    # убираем /r
    body = caption.strip()[2:].strip()
    if not body:
        return None, ""

    parts = body.split(maxsplit=1)

    if parts[0].isdigit():
        target_id = int(parts[0])
        reply_text = parts[1] if len(parts) > 1 else ""
        return target_id, reply_text

    # если ID нет, значит это текст, а ID берём из reply_to_message
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

async def send_album_with_single_caption(
    chat_id: int,
    context: ContextTypes.DEFAULT_TYPE,
    image_ids: list[str],
    caption: str | None = None,
):
    valid_images = [img for img in image_ids if img]

    if not valid_images:
        if caption:
            await context.bot.send_message(chat_id=chat_id, text=caption, parse_mode="HTML")
        return

    media = []
    for i, image_id in enumerate(valid_images):
        if i == 0 and caption:
            media.append(InputMediaPhoto(media=image_id, caption=caption, parse_mode="HTML"))
        else:
            media.append(InputMediaPhoto(media=image_id))

    try:
        await context.bot.send_media_group(chat_id=chat_id, media=media)
    except Exception as e:
        logger.error(f"Ошибка media_group: {e}")

        # fallback
        for i, image_id in enumerate(valid_images):
            try:
                if i == 0 and caption:
                    await context.bot.send_photo(chat_id=chat_id, photo=image_id, caption=caption, parse_mode="HTML")
                else:
                    await context.bot.send_photo(chat_id=chat_id, photo=image_id)
            except Exception as e2:
                logger.error(f"Fallback send_photo error: {e2}")

async def send_access_request_flow(query, context: ContextTypes.DEFAULT_TYPE):
    user_id = query.from_user.id
    chat_id = query.message.chat_id

    if user_id in blocked_users:
        await query.edit_message_text(
            SUPPORT_BLOCKED_TEXT,
            parse_mode="HTML",
            reply_markup=support_keyboard(),
        )
        return

    if user_id in waiting_for_photo:
        await query.edit_message_text(
            ALREADY_WAITING_TEXT,
            parse_mode="HTML",
            reply_markup=access_panel_keyboard(),
        )
        return

    if user_id in submitted_requests:
        await query.edit_message_text(
            ALREADY_SUBMITTED_TEXT,
            parse_mode="HTML",
            reply_markup=access_panel_keyboard(),
        )
        return

    waiting_for_photo.add(user_id)
    save_state()

    await send_album_with_single_caption(
        chat_id=chat_id,
        context=context,
        image_ids=[ACCESS_IMAGE_1, ACCESS_IMAGE_2],
        caption=ACCESS_REQUEST_TEXT,
    )

    await query.edit_message_text(
        ACCESS_PANEL_TEXT,
        parse_mode="HTML",
        reply_markup=access_panel_keyboard(),
    )

async def send_step_album_and_update_panel(
    query,
    context: ContextTypes.DEFAULT_TYPE,
    image_ids: list[str],
    caption_text: str,
    panel_text: str,
    panel_keyboard: InlineKeyboardMarkup,
):
    await send_album_with_single_caption(
        chat_id=query.message.chat_id,
        context=context,
        image_ids=image_ids,
        caption=caption_text,
    )

    await query.edit_message_text(
        panel_text,
        parse_mode="HTML",
        reply_markup=panel_keyboard,
    )

# ─── ОТПРАВКА В ГРУППУ ПОДДЕРЖКИ ─────────────────────────────────────────────

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
                f"Ответьте reply + <code>/r [текст]</code>\n"
                f"или <code>/close</code> / <code>/block</code>"
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
                f"Ответьте reply + текстом <code>/r [текст]</code>\n"
                f"или reply + фото с подписью <code>/r [текст]</code>\n"
                f"или reply + файлом с подписью <code>/r [текст]</code>\n"
                f"<code>/close</code> / <code>/block</code>"
            )[:1024],
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error(f"Не удалось отправить фото в support-группу: {e}")

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
                f"Ответьте reply + текстом <code>/r [текст]</code>\n"
                f"или reply + фото с подписью <code>/r [текст]</code>\n"
                f"или reply + файлом с подписью <code>/r [текст]</code>\n"
                f"<code>/close</code> / <code>/block</code>"
            )[:1024],
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error(f"Не удалось отправить файл в support-группу: {e}")

# ─── ХЕНДЛЕРЫ КНОПОК ──────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        WELCOME_TEXT,
        parse_mode="HTML",
        reply_markup=main_keyboard(),
    )

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    clicker_id = query.from_user.id

    # Модерация заявок
    if query.data.startswith(("approve:", "reject:", "blockcb:")):
        if clicker_id != ADMIN_ID:
            await query.answer("У вас нет доступа.", show_alert=True)
            return

        try:
            target_id = int(query.data.split(":")[1])
        except Exception:
            await query.answer("Ошибка данных.", show_alert=True)
            return

        if query.data.startswith("approve:"):
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
                    original_caption = query.message.caption or ""
                    new_caption = f"{original_caption}\n\n✅ <b>ОДОБРЕНО</b>"
                    if query.message.photo:
                        await query.edit_message_caption(
                            caption=new_caption[:1024],
                            parse_mode="HTML",
                            reply_markup=None,
                        )
                    else:
                        await query.edit_message_reply_markup(reply_markup=None)
                except Exception as e:
                    logger.warning(f"Не удалось обновить сообщение approve: {e}")

                await query.answer("Фото одобрено ✅")
            except Exception as e:
                logger.error(f"Ошибка approve: {e}")
                await query.answer("Не удалось одобрить.", show_alert=True)
            return

        if query.data.startswith("reject:"):
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
                    original_caption = query.message.caption or ""
                    new_caption = f"{original_caption}\n\n❌ <b>ОТКЛОНЕНО</b>"
                    if query.message.photo:
                        await query.edit_message_caption(
                            caption=new_caption[:1024],
                            parse_mode="HTML",
                            reply_markup=None,
                        )
                    else:
                        await query.edit_message_reply_markup(reply_markup=None)
                except Exception as e:
                    logger.warning(f"Не удалось обновить сообщение reject: {e}")

                await query.answer("Фото отклонено ❌")
            except Exception as e:
                logger.error(f"Ошибка reject: {e}")
                await query.answer("Не удалось отклонить.", show_alert=True)
            return

        if query.data.startswith("blockcb:"):
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

    # Обычные кнопки
    if query.data == "start":
        await query.edit_message_text(
            WELCOME_TEXT,
            parse_mode="HTML",
            reply_markup=main_keyboard()
        )

    elif query.data == "faq":
        await query.edit_message_text(
            FAQ_TEXT,
            parse_mode="HTML",
            reply_markup=back_keyboard()
        )

    elif query.data == "install":
        await query.edit_message_text(
            INSTALL_TEXT,
            parse_mode="HTML",
            reply_markup=install_keyboard()
        )

    elif query.data == "support":
        if clicker_id in blocked_users:
            await query.edit_message_text(
                SUPPORT_BLOCKED_TEXT,
                parse_mode="HTML",
                reply_markup=support_keyboard(),
            )
            return

        await query.edit_message_text(
            f"💬 <b>Связь с поддержкой</b>\n\n"
            f"Напишите сюда сообщение — и администратор @{ADMIN_USERNAME} ответит вам.\n\n"
            f"После первого ответа откроется режим чата.",
            parse_mode="HTML",
            reply_markup=support_keyboard(),
        )

    elif query.data == "check_sub":
        try:
            member = await context.bot.get_chat_member(REVIEWS_CHANNEL_USERNAME, query.from_user.id)
            if member.status in ("member", "administrator", "creator"):
                await query.edit_message_text(
                    STEP_1_TEXT,
                    parse_mode="HTML",
                    reply_markup=step_1_keyboard(),
                )
            else:
                await query.edit_message_text(
                    NOT_SUBSCRIBED_TEXT,
                    parse_mode="HTML",
                    reply_markup=install_keyboard(),
                )
        except Exception as e:
            logger.error(f"Ошибка проверки подписки: {e}")
            await query.edit_message_text(
                NOT_SUBSCRIBED_TEXT,
                parse_mode="HTML",
                reply_markup=install_keyboard(),
            )

    elif query.data == "step1":
        await query.edit_message_text(
            STEP_1_TEXT,
            parse_mode="HTML",
            reply_markup=step_1_keyboard(),
        )

    elif query.data == "get_access":
        await send_access_request_flow(query, context)

    elif query.data == "retry_access":
        await send_access_request_flow(query, context)

    elif query.data == "step2":
        await send_step_album_and_update_panel(
            query=query,
            context=context,
            image_ids=[STEP2_IMAGE_1, STEP2_IMAGE_2],
            caption_text=STEP_2_TEXT,
            panel_text=STEP2_PANEL_TEXT,
            panel_keyboard=step_2_keyboard(),
        )

    elif query.data == "step3":
        await send_step_album_and_update_panel(
            query=query,
            context=context,
            image_ids=[STEP3_IMAGE_1, STEP3_IMAGE_2, STEP3_IMAGE_3],
            caption_text=STEP_3_TEXT,
            panel_text=STEP3_PANEL_TEXT,
            panel_keyboard=step_3_keyboard(),
        )

# ─── АДМИН-КОМАНДЫ ───────────────────────────────────────────────────────────

async def cmd_r(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /r 123 текст
    или reply на сообщение + /r текст
    """
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

async def cmd_close(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    target_id = None

    if context.args and context.args[0].isdigit():
        target_id = int(context.args[0])
    else:
        target_id = resolve_target_id_from_reply(update)

    if not target_id:
        await update.message.reply_text(
            "📝 Формат:\n/close [ID]\n\nили reply на сообщение пользователя:\n/close"
        )
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
        await update.message.reply_text(
            "📝 Формат:\n/block [ID]\n\nили reply на сообщение пользователя:\n/block"
        )
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
        await update.message.reply_text("📝 Формат:\n/unblock [ID]")
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

async def cmd_reject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /reject [ID] [причина]
    """
    if update.effective_user.id != ADMIN_ID:
        return

    if not context.args or len(context.args) < 2:
        await update.message.reply_text("📝 Формат:\n/reject [ID] [причина]")
        return

    try:
        target_id = int(context.args[0])
        reason = " ".join(context.args[1:]).strip()

        submitted_requests.discard(target_id)
        waiting_for_photo.discard(target_id)
        save_state()

        await context.bot.send_message(
            chat_id=target_id,
            text=(
                "❌ <b>Поддержка не одобрила ваше фото.</b>\n\n"
                f"<b>Причина:</b> {reason}\n\n"
                "Отправьте более чёткое фото / скрин ещё раз."
            ),
            parse_mode="HTML",
            reply_markup=retry_request_keyboard(),
        )

        await update.message.reply_text(f"✅ Отклонение отправлено {target_id}")

    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

async def cmd_approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /approve [ID] [текст]
    """
    if update.effective_user.id != ADMIN_ID:
        return

    if not context.args or len(context.args) < 2:
        await update.message.reply_text("📝 Формат:\n/approve [ID] [текст]")
        return

    try:
        target_id = int(context.args[0])
        custom_text = " ".join(context.args[1:]).strip()

        if target_id in blocked_users:
            await update.message.reply_text("⛔ Пользователь заблокирован.")
            return

        submitted_requests.discard(target_id)
        waiting_for_photo.discard(target_id)
        save_state()

        await open_support_chat_for_user(context, target_id)

        await context.bot.send_message(
            chat_id=target_id,
            text=f"✅ <b>Поддержка:</b>\n\n{custom_text}",
            parse_mode="HTML",
            reply_markup=approved_contact_keyboard(),
        )

        await update.message.reply_text(f"✅ Одобрение отправлено {target_id}")

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

        if replied.document:
            file_id = replied.document.file_id
            await update.message.reply_text(f"📎 DOCUMENT FILE_ID:\n<code>{file_id}</code>", parse_mode="HTML")
            return

    await update.message.reply_text(
        "ℹ️ Ответь /getfileid на фото или файл, либо отправь с подписью /getfileid",
        parse_mode="HTML"
    )

# ─── АДМИН: ОТВЕТ МЕДИА ЧЕРЕЗ /r ─────────────────────────────────────────────

async def admin_r_photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Фото + подпись:
    /r 123 текст
    или reply на сообщение + фото с подписью /r текст
    """
    if update.effective_user.id != ADMIN_ID:
        return

    caption = update.message.caption or ""

    if caption.strip().startswith("/getfileid"):
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
                "📝 Формат:\n"
                "1) Фото + подпись: /r [ID] [текст]\n"
                "или\n"
                "2) Reply на сообщение пользователя + фото с подписью:\n"
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

async def admin_r_document_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Файл + подпись:
    /r 123 текст
    или reply на сообщение + файл с подписью /r текст
    """
    if update.effective_user.id != ADMIN_ID:
        return

    caption = update.message.caption or ""

    if caption.strip().startswith("/getfileid"):
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
                "📝 Формат:\n"
                "1) Файл + подпись: /r [ID] [текст]\n"
                "или\n"
                "2) Reply на сообщение пользователя + файл с подписью:\n"
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

# ─── ПОЛЬЗОВАТЕЛЬСКИЕ ТЕКСТЫ ──────────────────────────────────────────────────

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id, username, full_name = build_user_info(update)
    text = update.message.text if update.message.text else ""

    # Игнорим команды админа
    if user_id == ADMIN_ID and text.startswith("/"):
        return

    if user_id in blocked_users:
        await update.message.reply_text(SUPPORT_BLOCKED_TEXT, parse_mode="HTML")
        return

    # антиспам
    if is_user_rate_limited(user_id):
        await send_rate_limit_warning(update)
        return

    # если ждём именно фото/скрин
    if user_id in waiting_for_photo:
        await update.message.reply_text(
            "📸 Жду именно <b>фото / скрин</b>, не текст! Прикрепи изображение.",
            parse_mode="HTML",
        )
        return

    # любой текст = поддержка
    await forward_user_text_to_support(context, user_id, username, full_name, text)

    # если чат ещё не открыт — просто уведомляем пользователя
    if user_id not in active_support_chats:
        await update.message.reply_text(
            "💬 <b>Сообщение отправлено в поддержку.</b>\n\nОжидайте ответа администратора.",
            parse_mode="HTML",
            reply_markup=support_keyboard(),
        )

# ─── ПОЛЬЗОВАТЕЛЬСКИЕ ФОТО ────────────────────────────────────────────────────

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id, username, full_name = build_user_info(update)

    # если это админ шлёт фото с подписью /r
    if user_id == ADMIN_ID:
        await update.message.reply_text(
            "📸 Для ответа пользователю:\n"
            "Reply на сообщение пользователя + фото с подписью:\n"
            "<code>/r [текст]</code>\n\n"
            "или напрямую:\n"
            "<code>/r [ID] [текст]</code>\n\n"
            "или подпись <code>/getfileid</code>",
            parse_mode="HTML",
        )
        return

    if user_id in blocked_users:
        await update.message.reply_text(SUPPORT_BLOCKED_TEXT, parse_mode="HTML")
        return

    # антиспам
    if is_user_rate_limited(user_id):
        await send_rate_limit_warning(update)
        return

    # РЕЖИМ ЗАЯВКИ ПОСЛЕ "ПОЛУЧИТЬ ДОСТУП"
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
                reply_markup=main_keyboard()
            )

        except Exception as e:
            logger.error(f"Ошибка отправки фото на модерацию: {e}")
            submitted_requests.discard(user_id)
            save_state()
            await update.message.reply_text("❌ Ошибка при обработке фото. Попробуйте позже.")
        return

    # ИНАЧЕ ЭТО ОБЫЧНОЕ ФОТО В ПОДДЕРЖКУ
    try:
        await forward_user_photo_to_support(
            context,
            user_id,
            username,
            full_name,
            update.message.photo[-1].file_id
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

# ─── ПОЛЬЗОВАТЕЛЬСКИЕ ФАЙЛЫ / СКРИНЫ ─────────────────────────────────────────

async def document_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id, username, full_name = build_user_info(update)

    # если это админ шлёт файл с подписью /r
    if user_id == ADMIN_ID:
        await update.message.reply_text(
            "📎 Для ответа пользователю:\n"
            "Reply на сообщение пользователя + файл с подписью:\n"
            "<code>/r [текст]</code>\n\n"
            "или напрямую:\n"
            "<code>/r [ID] [текст]</code>\n\n"
            "или подпись <code>/getfileid</code>",
            parse_mode="HTML",
        )
        return

    if user_id in blocked_users:
        await update.message.reply_text(SUPPORT_BLOCKED_TEXT, parse_mode="HTML")
        return

    # антиспам
    if is_user_rate_limited(user_id):
        await send_rate_limit_warning(update)
        return

    file_name = update.message.document.file_name or "file"

    # Если ждём фото/скрин на модерацию — принимаем только image-документы как скрин
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
                reply_markup=main_keyboard()
            )

        except Exception as e:
            logger.error(f"Ошибка отправки image-doc на модерацию: {e}")
            submitted_requests.discard(user_id)
            save_state()
            await update.message.reply_text("❌ Ошибка при обработке файла. Попробуйте позже.")
        return

    # ИНАЧЕ ЭТО ОБЫЧНЫЙ ФАЙЛ В ПОДДЕРЖКУ
    try:
        await forward_user_document_to_support(
            context,
            user_id,
            username,
            full_name,
            update.message.document.file_id,
            file_name
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

# ─── ЗАПУСК ───────────────────────────────────────────────────────────────────

def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN не найден. Добавь переменную BOT_TOKEN в Railway Variables.")

    load_state()

    app = Application.builder().token(BOT_TOKEN).build()

    # Команды
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("r", cmd_r))
    app.add_handler(CommandHandler("close", cmd_close))
    app.add_handler(CommandHandler("block", cmd_block))
    app.add_handler(CommandHandler("unblock", cmd_unblock))
    app.add_handler(CommandHandler("reject", cmd_reject))
    app.add_handler(CommandHandler("approve", cmd_approve))
    app.add_handler(CommandHandler("state", cmd_state))
    app.add_handler(CommandHandler("getfileid", cmd_getfileid))

    # Кнопки
    app.add_handler(CallbackQueryHandler(callback_handler))

    # Админ: фото/файл с подписью /r
    app.add_handler(MessageHandler(
        filters.PHOTO & filters.CaptionRegex(r"^/r\b"),
        admin_r_photo_handler
    ))

    app.add_handler(MessageHandler(
        filters.PHOTO & filters.CaptionRegex(r"^/getfileid\b"),
        admin_r_photo_handler
    ))

    app.add_handler(MessageHandler(
        filters.Document.ALL & filters.CaptionRegex(r"^/r\b"),
        admin_r_document_handler
    ))

    app.add_handler(MessageHandler(
        filters.Document.ALL & filters.CaptionRegex(r"^/getfileid\b"),
        admin_r_document_handler
    ))

    # Пользовательские медиа
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    app.add_handler(MessageHandler(filters.Document.ALL, document_handler))

    # Текст
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    logger.info("Бот запускается...")
    app.run_polling()

if __name__ == "__main__":
    main()
