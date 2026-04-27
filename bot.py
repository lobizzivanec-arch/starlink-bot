import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)

# ─── НАСТРОЙКИ (Railway Variables / ENV) ─────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "8197197463"))

# ВАЖНО: в Railway ставь ADMIN_USERNAME=sunrisseq (БЕЗ @)
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "sunrisseq")

ADMIN_CHANNEL_ID = int(os.getenv("ADMIN_CHANNEL_ID", "-1001234567890"))
REVIEWS_CHANNEL_USERNAME = os.getenv("REVIEWS_CHANNEL_USERNAME", "@your_reviews_channel")
REVIEWS_CHANNEL_LINK = os.getenv("REVIEWS_CHANNEL_LINK", "https://t.me/your_reviews_channel")

# ─── FILE_ID картинок для шагов ──────────────────────────────────────────────
STEP2_IMAGE_1 = os.getenv("STEP2_IMAGE_1", "")
STEP2_IMAGE_2 = os.getenv("STEP2_IMAGE_2", "")

STEP3_IMAGE_1 = os.getenv("STEP3_IMAGE_1", "")
STEP3_IMAGE_2 = os.getenv("STEP3_IMAGE_2", "")
STEP3_IMAGE_3 = os.getenv("STEP3_IMAGE_3", "")

ACCESS_IMAGE_1 = os.getenv("ACCESS_IMAGE_1", "")
ACCESS_IMAGE_2 = os.getenv("ACCESS_IMAGE_2", "")
# ──────────────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger(__name__)

# Пользователи, от которых ждём фото/скрин
waiting_for_photo: set[int] = set()

# Пользователи, которые уже отправили заявку (чтобы не спамили)
submitted_requests: set[int] = set()

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
Starlink — система спутникового интернета от компании SpaceX (Илон Маск). Сотни спутников на низкой орбите обеспечивают покрытие по всему миру. Скорость — до 200 Мбит/с, пинг — от 20 мс.

<b>Для кого это?</b>
• 🏕 Туристы и путешественники
• 🚗 Дальнобойщики и автопутешественники
• 🌾 Жители сёл и дач
• ⚡ Те, кто устал от плохого интернета

<b>Как это работает?</b>
Ты устанавливаешь небольшую тарелку → она ловит сигнал со спутников → ты получаешь стабильный интернет. Всё управление через приложение на телефоне.

<b>Нужен ли договор с оператором?</b>
Нет. Starlink работает напрямую через SpaceX, без посредников.

<b>Где работает?</b>
В большинстве стран мира. В движении, на природе, дома — везде где есть небо над головой.

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

Ниже смотри 2 примера / скрина 👇
"""

STEP_3_TEXT = """
📶 <b>Шаг 3. Настройка приложения и подключение к Wi-Fi</b>

<b>Краткое описание:</b>

После входа в приложение:
• Открой настройки
• Найди доступную сеть Starlink
• Подключись к Wi-Fi
• Дождись стабильного соединения

Ниже смотри примеры настройки 👇
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

WRONG_INPUT_TEXT = """
🤔 Не понял тебя.

Используй кнопки меню или просто отправь фото / скрин по инструкции.
"""

# ─── КЛАВИАТУРЫ ───────────────────────────────────────────────────────────────

def main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❓ Частые вопросы", callback_data="faq")],
        [InlineKeyboardButton("📦 Установка", callback_data="install")],
    ])

def install_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Подписаться на канал", url=REVIEWS_CHANNEL_LINK)],
        [InlineKeyboardButton("✅ Я подписался", callback_data="check_sub")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="start")],
    ])

def back_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📦 Установка", callback_data="install")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="start")],
    ])

def step_1_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Получить доступ", callback_data="get_access")],
        [InlineKeyboardButton("➡️ Шаг 2", callback_data="step2")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="start")],
    ])

def step_2_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Шаг 1", callback_data="step1")],
        [InlineKeyboardButton("➡️ Шаг 3", callback_data="step3")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="start")],
    ])

def step_3_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Шаг 2", callback_data="step2")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="start")],
    ])

def photo_moderation_keyboard(user_id: int):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Одобрить", callback_data=f"approve:{user_id}"),
            InlineKeyboardButton("❌ Отклонить", callback_data=f"reject:{user_id}"),
        ]
    ])

def approved_contact_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 Написать менеджеру", url=f"https://t.me/{ADMIN_USERNAME}")]
    ])

def retry_request_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📩 Отправить заявку повторно", callback_data="retry_access")],
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

async def notify_admin_text(context: ContextTypes.DEFAULT_TYPE, user_id: int, username: str, full_name: str, text: str):
    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=(
                f"💬 <b>Новое сообщение</b>\n"
                f"👤 {full_name} ({username})\n"
                f"🆔 <code>{user_id}</code>\n\n"
                f"<i>{text}</i>\n\n"
                f"✏️ Ответить: <code>/reply {user_id} [текст]</code>"
            ),
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error(f"Не удалось уведомить админа: {e}")

async def send_step_images(chat_id: int, context: ContextTypes.DEFAULT_TYPE, image_ids: list[str]):
    for image_id in image_ids:
        if image_id:
            try:
                await context.bot.send_photo(chat_id=chat_id, photo=image_id)
            except Exception as e:
                logger.error(f"Не удалось отправить картинку {image_id}: {e}")

async def send_access_request_flow(chat_id: int, user_id: int, context: ContextTypes.DEFAULT_TYPE):
    # Если уже ждём фото
    if user_id in waiting_for_photo:
        await context.bot.send_message(
            chat_id=chat_id,
            text=ALREADY_WAITING_TEXT,
            parse_mode="HTML",
        )
        return

    # Если уже отправил заявку и она на проверке
    if user_id in submitted_requests:
        await context.bot.send_message(
            chat_id=chat_id,
            text=ALREADY_SUBMITTED_TEXT,
            parse_mode="HTML",
        )
        return

    waiting_for_photo.add(user_id)

    await context.bot.send_message(
        chat_id=chat_id,
        text=ACCESS_REQUEST_TEXT,
        parse_mode="HTML",
    )

    await send_step_images(
        chat_id=chat_id,
        context=context,
        image_ids=[ACCESS_IMAGE_1, ACCESS_IMAGE_2],
    )

# ─── ХЕНДЛЕРЫ ─────────────────────────────────────────────────────────────────

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

    # ─── МОДЕРАЦИЯ ФОТО ───────────────────────────────────────────────────────
    if query.data.startswith(("approve:", "reject:")):
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
                # Заявка больше не "на рассмотрении"
                submitted_requests.discard(target_id)
                waiting_for_photo.discard(target_id)

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
                    logger.warning(f"Не удалось обновить сообщение после approve: {e}")

                await query.answer("Фото одобрено ✅")

            except Exception as e:
                logger.error(f"Ошибка одобрения фото: {e}")
                await query.answer("Не удалось одобрить.", show_alert=True)
            return

        if query.data.startswith("reject:"):
            try:
                # Снимаем с рассмотрения, чтобы пользователь мог отправить заново
                submitted_requests.discard(target_id)
                waiting_for_photo.discard(target_id)

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
                    logger.warning(f"Не удалось обновить сообщение после reject: {e}")

                await query.answer("Фото отклонено ❌")

            except Exception as e:
                logger.error(f"Ошибка отклонения фото: {e}")
                await query.answer("Не удалось отклонить.", show_alert=True)
            return

    # ─── ОБЫЧНЫЕ КНОПКИ ───────────────────────────────────────────────────────
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
        await send_access_request_flow(
            chat_id=query.message.chat_id,
            user_id=query.from_user.id,
            context=context,
        )

    elif query.data == "retry_access":
        await send_access_request_flow(
            chat_id=query.message.chat_id,
            user_id=query.from_user.id,
            context=context,
        )

    elif query.data == "step2":
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=STEP_2_TEXT,
            parse_mode="HTML",
            reply_markup=step_2_keyboard(),
        )

        await send_step_images(
            chat_id=query.message.chat_id,
            context=context,
            image_ids=[STEP2_IMAGE_1, STEP2_IMAGE_2],
        )

    elif query.data == "step3":
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=STEP_3_TEXT,
            parse_mode="HTML",
            reply_markup=step_3_keyboard(),
        )

        await send_step_images(
            chat_id=query.message.chat_id,
            context=context,
            image_ids=[STEP3_IMAGE_1, STEP3_IMAGE_2, STEP3_IMAGE_3],
        )

# ─── АДМИН-КОМАНДЫ ───────────────────────────────────────────────────────────

async def cmd_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /reply [ID] [текст]
    """
    if update.effective_user.id != ADMIN_ID:
        return

    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "📝 Формат:\n"
            "/reply [ID пользователя] [текст]\n\n"
            "Пример:\n"
            "/reply 987654321 Привет! Ваш вопрос решён."
        )
        return

    try:
        target_id = int(context.args[0])
        reply_text = " ".join(context.args[1:]).strip()

        await context.bot.send_message(
            chat_id=target_id,
            text=f"💬 <b>Ответ от поддержки:</b>\n\n{reply_text}",
            parse_mode="HTML",
        )

        await update.message.reply_text(f"✅ Текст отправлен пользователю {target_id}")

    except ValueError:
        await update.message.reply_text("❌ Неверный ID. Используй числовой ID.")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

async def cmd_reject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /reject [ID] [причина]
    """
    if update.effective_user.id != ADMIN_ID:
        return

    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "📝 Формат:\n"
            "/reject [ID пользователя] [причина]\n\n"
            "Пример:\n"
            "/reject 987654321 Фото размыто, пришлите чёткий скрин"
        )
        return

    try:
        target_id = int(context.args[0])
        reason = " ".join(context.args[1:]).strip()

        submitted_requests.discard(target_id)
        waiting_for_photo.discard(target_id)

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

        await update.message.reply_text(f"✅ Пользователю {target_id} отправлено отклонение с причиной.")

    except ValueError:
        await update.message.reply_text("❌ Неверный ID. Используй числовой ID.")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

async def cmd_approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /approve [ID] [кастомный текст]
    """
    if update.effective_user.id != ADMIN_ID:
        return

    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "📝 Формат:\n"
            "/approve [ID пользователя] [текст]\n\n"
            "Пример:\n"
            "/approve 987654321 Фото одобрено! Напишите @sunrisseq для получения доступа."
        )
        return

    try:
        target_id = int(context.args[0])
        custom_text = " ".join(context.args[1:]).strip()

        submitted_requests.discard(target_id)
        waiting_for_photo.discard(target_id)

        await context.bot.send_message(
            chat_id=target_id,
            text=f"✅ <b>Поддержка:</b>\n\n{custom_text}",
            parse_mode="HTML",
            reply_markup=approved_contact_keyboard(),
        )

        await update.message.reply_text(f"✅ Пользователю {target_id} отправлено одобрение с текстом.")

    except ValueError:
        await update.message.reply_text("❌ Неверный ID. Используй числовой ID.")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

async def cmd_getfileid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /getfileid — отправить в ответ на фото или документ
    Либо просто отправить фото/документ с подписью /getfileid
    """
    if update.effective_user.id != ADMIN_ID:
        return

    # Если команда как reply на сообщение
    if update.message.reply_to_message:
        replied = update.message.reply_to_message

        if replied.photo:
            file_id = replied.photo[-1].file_id
            await update.message.reply_text(
                f"🖼 PHOTO FILE_ID:\n<code>{file_id}</code>",
                parse_mode="HTML"
            )
            return

        if replied.document:
            file_id = replied.document.file_id
            await update.message.reply_text(
                f"📎 DOCUMENT FILE_ID:\n<code>{file_id}</code>",
                parse_mode="HTML"
            )
            return

    await update.message.reply_text(
        "ℹ️ Использование:\n"
        "1) Ответь командой <code>/getfileid</code> на фото или файл\n"
        "или\n"
        "2) Отправь фото/документ с подписью <code>/getfileid</code>",
        parse_mode="HTML"
    )

# ─── АДМИН: ОТПРАВИТЬ СВОЁ ФОТО ──────────────────────────────────────────────

async def admin_reply_photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Фото + подпись:
    /replyphoto [ID] [текст]
    ИЛИ
    /getfileid
    """
    if update.effective_user.id != ADMIN_ID:
        return

    caption = update.message.caption or ""

    # Режим получения file_id
    if caption.strip().startswith("/getfileid"):
        if update.message.photo:
            file_id = update.message.photo[-1].file_id
            await update.message.reply_text(
                f"🖼 PHOTO FILE_ID:\n<code>{file_id}</code>",
                parse_mode="HTML"
            )
        return

    if not update.message.photo:
        await update.message.reply_text("❌ Прикрепи фото с подписью: /replyphoto [ID] [текст]")
        return

    parts = caption.split(maxsplit=2)

    if len(parts) < 2:
        await update.message.reply_text(
            "📝 Формат:\n"
            "Отправь фото с подписью:\n"
            "/replyphoto [ID пользователя] [текст]\n\n"
            "Пример:\n"
            "/replyphoto 123456789 Вот ваш туториал"
        )
        return

    try:
        target_id = int(parts[1])
        reply_text = parts[2] if len(parts) > 2 else "📸 Сообщение от поддержки"
        photo = update.message.photo[-1].file_id

        await context.bot.send_photo(
            chat_id=target_id,
            photo=photo,
            caption=f"💬 Поддержка:\n\n{reply_text}",
        )

        await update.message.reply_text(f"✅ Фото отправлено пользователю {target_id}")

    except ValueError:
        await update.message.reply_text("❌ Неверный ID. Используй числовой ID.")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при отправке фото: {e}")

# ─── АДМИН: ОТПРАВИТЬ СВОЙ ФАЙЛ / ДОКУМЕНТ ───────────────────────────────────

async def admin_reply_document_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Документ + подпись:
    /replydoc [ID] [текст]
    ИЛИ
    /getfileid
    """
    if update.effective_user.id != ADMIN_ID:
        return

    caption = update.message.caption or ""

    # Режим получения file_id
    if caption.strip().startswith("/getfileid"):
        if update.message.document:
            file_id = update.message.document.file_id
            await update.message.reply_text(
                f"📎 DOCUMENT FILE_ID:\n<code>{file_id}</code>",
                parse_mode="HTML"
            )
        return

    if not update.message.document:
        await update.message.reply_text("❌ Прикрепи файл с подписью: /replydoc [ID] [текст]")
        return

    parts = caption.split(maxsplit=2)

    if len(parts) < 2:
        await update.message.reply_text(
            "📝 Формат:\n"
            "Отправь файл с подписью:\n"
            "/replydoc [ID пользователя] [текст]\n\n"
            "Пример:\n"
            "/replydoc 123456789 Вот ваш PDF"
        )
        return

    try:
        target_id = int(parts[1])
        reply_text = parts[2] if len(parts) > 2 else "📎 Сообщение от поддержки"
        document = update.message.document.file_id

        await context.bot.send_document(
            chat_id=target_id,
            document=document,
            caption=f"💬 Поддержка:\n\n{reply_text}",
        )

        await update.message.reply_text(f"✅ Файл отправлен пользователю {target_id}")

    except ValueError:
        await update.message.reply_text("❌ Неверный ID. Используй числовой ID.")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при отправке файла: {e}")

# ─── ОБЫЧНЫЕ ТЕКСТЫ ОТ ПОЛЬЗОВАТЕЛЕЙ ─────────────────────────────────────────

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text if update.message.text else ""

    if user_id == ADMIN_ID and text.startswith("/"):
        return

    if user_id in waiting_for_photo:
        await update.message.reply_text(
            "📸 Жду именно <b>фото / скрин</b>, не текст! Прикрепи изображение.",
            parse_mode="HTML",
        )
        return

    if user_id != ADMIN_ID:
        _, username, full_name = build_user_info(update)
        await notify_admin_text(context, user_id, username, full_name, text)

    await update.message.reply_text(
        WRONG_INPUT_TEXT,
        parse_mode="HTML",
        reply_markup=main_keyboard()
    )

# ─── ОБРАБОТКА ПОЛЬЗОВАТЕЛЬСКОГО ФОТО ────────────────────────────────────────

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id, username, full_name = build_user_info(update)

    # Фото от админа без спец-подписи
    if user_id == ADMIN_ID:
        await update.message.reply_text(
            "📸 Для отправки своего фото пользователю:\n"
            "отправь фото с подписью\n"
            "<code>/replyphoto [ID] [текст]</code>\n\n"
            "Чтобы получить file_id:\n"
            "<code>/getfileid</code> в подписи к фото",
            parse_mode="HTML",
        )
        return

    # Уже отправил заявку
    if user_id in submitted_requests:
        await update.message.reply_text(
            ALREADY_SUBMITTED_TEXT,
            parse_mode="HTML",
        )
        return

    if user_id not in waiting_for_photo:
        await update.message.reply_text(
            "🤔 Сначала нажми кнопку <b>«Получить доступ»</b> в инструкции.",
            parse_mode="HTML",
            reply_markup=main_keyboard(),
        )
        return

    waiting_for_photo.discard(user_id)
    submitted_requests.add(user_id)

    try:
        photo = update.message.photo[-1].file_id

        caption = (
            f"📸 <b>Фото от пользователя</b>\n"
            f"👤 {full_name} ({username})\n"
            f"🆔 <code>{user_id}</code>\n\n"
            f"✏️ Ответить текстом: <code>/reply {user_id} [текст]</code>\n"
            f"📷 Отправить своё фото: фото + подпись <code>/replyphoto {user_id} [текст]</code>\n"
            f"📎 Отправить свой файл: файл + подпись <code>/replydoc {user_id} [текст]</code>\n"
            f"✅ Одобрить с текстом: <code>/approve {user_id} [текст]</code>\n"
            f"❌ Отклонить с причиной: <code>/reject {user_id} [причина]</code>"
        )

        await context.bot.send_photo(
            chat_id=ADMIN_CHANNEL_ID,
            photo=photo,
            caption=caption[:1024],
            parse_mode="HTML",
            reply_markup=photo_moderation_keyboard(user_id),
        )

    except Exception as e:
        logger.error(f"Не удалось отправить фото в админ-канал: {e}")
        submitted_requests.discard(user_id)

        await update.message.reply_text(
            "❌ Ошибка при обработке фото. Попробуйте ещё раз позже.",
            reply_markup=main_keyboard(),
        )
        return

    await update.message.reply_text(
        PHOTO_RECEIVED_TEXT,
        parse_mode="HTML",
        reply_markup=main_keyboard()
    )

# ─── ОБРАБОТКА ПОЛЬЗОВАТЕЛЬСКОГО СКРИНА КАК FILE/DOCUMENT ────────────────────

async def document_image_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id, username, full_name = build_user_info(update)

    # Документ от админа без спец-подписи
    if user_id == ADMIN_ID:
        await update.message.reply_text(
            "📎 Для отправки своего файла пользователю:\n"
            "отправь документ с подписью\n"
            "<code>/replydoc [ID] [текст]</code>\n\n"
            "Чтобы получить file_id:\n"
            "<code>/getfileid</code> в подписи к документу",
            parse_mode="HTML",
        )
        return

    # Уже отправил заявку
    if user_id in submitted_requests:
        await update.message.reply_text(
            ALREADY_SUBMITTED_TEXT,
            parse_mode="HTML",
        )
        return

    if user_id not in waiting_for_photo:
        await update.message.reply_text(
            "🤔 Сначала нажми кнопку <b>«Получить доступ»</b> в инструкции.",
            parse_mode="HTML",
            reply_markup=main_keyboard(),
        )
        return

    waiting_for_photo.discard(user_id)
    submitted_requests.add(user_id)

    try:
        document = update.message.document.file_id
        file_name = update.message.document.file_name or "image_file"

        caption = (
            f"🖼 <b>Скрин/файл от пользователя</b>\n"
            f"👤 {full_name} ({username})\n"
            f"🆔 <code>{user_id}</code>\n"
            f"📄 Файл: <code>{file_name}</code>\n\n"
            f"✏️ Ответить текстом: <code>/reply {user_id} [текст]</code>\n"
            f"📷 Отправить своё фото: фото + подпись <code>/replyphoto {user_id} [текст]</code>\n"
            f"📎 Отправить свой файл: файл + подпись <code>/replydoc {user_id} [текст]</code>\n"
            f"✅ Одобрить с текстом: <code>/approve {user_id} [текст]</code>\n"
            f"❌ Отклонить с причиной: <code>/reject {user_id} [причина]</code>"
        )

        await context.bot.send_document(
            chat_id=ADMIN_CHANNEL_ID,
            document=document,
            caption=caption[:1024],
            parse_mode="HTML",
        )

        await context.bot.send_message(
            chat_id=ADMIN_CHANNEL_ID,
            text=f"🛠 Модерация для пользователя <code>{user_id}</code>",
            parse_mode="HTML",
            reply_markup=photo_moderation_keyboard(user_id),
        )

    except Exception as e:
        logger.error(f"Не удалось отправить document image в админ-канал: {e}")
        submitted_requests.discard(user_id)

        await update.message.reply_text(
            "❌ Ошибка при обработке файла. Попробуйте ещё раз позже.",
            reply_markup=main_keyboard(),
        )
        return

    await update.message.reply_text(
        PHOTO_RECEIVED_TEXT,
        parse_mode="HTML",
        reply_markup=main_keyboard()
    )

# ─── ЗАПУСК ───────────────────────────────────────────────────────────────────

def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN не найден. Добавь переменную BOT_TOKEN в Railway Variables.")

    app = Application.builder().token(BOT_TOKEN).build()

    # Команды
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("reply", cmd_reply))
    app.add_handler(CommandHandler("reject", cmd_reject))
    app.add_handler(CommandHandler("approve", cmd_approve))
    app.add_handler(CommandHandler("getfileid", cmd_getfileid))

    # Кнопки
    app.add_handler(CallbackQueryHandler(callback_handler))

    # ВАЖНО: спец-хендлеры админа должны стоять ВЫШЕ обычных обработчиков
    app.add_handler(MessageHandler(
        filters.PHOTO & filters.CaptionRegex(r"^/replyphoto\b"),
        admin_reply_photo_handler
    ))

    app.add_handler(MessageHandler(
        filters.PHOTO & filters.CaptionRegex(r"^/getfileid\b"),
        admin_reply_photo_handler
    ))

    app.add_handler(MessageHandler(
        filters.Document.ALL & filters.CaptionRegex(r"^/replydoc\b"),
        admin_reply_document_handler
    ))

    app.add_handler(MessageHandler(
        filters.Document.ALL & filters.CaptionRegex(r"^/getfileid\b"),
        admin_reply_document_handler
    ))

    # Обычные пользовательские медиа
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))

    # Скрины как document (png/jpg/webp и т.д.)
    app.add_handler(MessageHandler(filters.Document.IMAGE, document_image_handler))

    # Текст
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    logger.info("Бот запускается...")
    app.run_polling()

if __name__ == "__main__":
    main()
