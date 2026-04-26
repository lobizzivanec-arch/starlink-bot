import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)

# ─── ЛОГИ ─────────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)  # чтобы токен не светился в логах
logger = logging.getLogger(__name__)

# ─── НАСТРОЙКИ ────────────────────────────────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN")  # Railway Variables
ADMIN_CHANNEL_ID = -1003907521717
REVIEWS_CHANNEL_USERNAME = "@sunrisse4u"
REVIEWS_CHANNEL_LINK = "https://t.me/sunrisse4u"

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден. Добавь его в Railway -> Variables")

# ─── СОСТОЯНИЕ ────────────────────────────────────────────────────────────────
# Пользователи, которые ввели кодовое слово и ждут фото
waiting_for_photo: set[int] = set()

# ─── ТЕКСТЫ ───────────────────────────────────────────────────────────────────

WELCOME_TEXT = """
👋 <b>Здравствуйте!</b>

Мы помогаем с <b>настройкой Starlink</b>.

Если у вас возникли сложности с подключением, установкой или сигналом — выберите нужный раздел ниже.

👇 Нажмите кнопку:
"""

FAQ_TEXT = """
❓ <b>Часто задаваемые вопросы по Starlink</b>

<b>С чем мы можем помочь:</b>
• нет сигнала / слабый сигнал
• тарелка не подключается
• роутер не раздаёт интернет
• ошибки в приложении
• вопросы по установке и размещению

<b>Что понадобится для помощи:</b>
• фото тарелки
• фото места установки
• фото роутера / подключения
• при необходимости — скрин ошибки

💡 Чтобы получить пошаговую инструкцию и помощь — нажмите <b>«📦 Установка»</b>.
"""

INSTALL_TEXT = """
📦 <b>Инструкция по установке и помощь с настройкой</b>

Перед получением инструкции подпишитесь на наш канал с отзывами и примерами.

После подписки нажмите кнопку <b>«✅ Я подписался»</b> — и бот проверит подписку.
"""

MANUAL_TEXT = """
📋 <b>Краткая инструкция по установке Starlink</b>

<b>Шаг 1. Подготовьте оборудование</b>
В комплект обычно входят:
• тарелка
• роутер
• кабель
• блок питания

<b>Шаг 2. Выберите место установки</b>
Тарелке нужен максимально открытый обзор неба без деревьев, крыш и других препятствий.

<b>Шаг 3. Подключение</b>
• подключите тарелку к роутеру
• подключите роутер к питанию
• дождитесь запуска системы

<b>Шаг 4. Проверка</b>
Если есть проблемы с сигналом, подключением или интернетом — мы можем помочь по фото.

─────────────────────
🔑 <b>Кодовое слово для обращения за помощью:</b> <b>старлинк</b>
─────────────────────

Отправьте кодовое слово боту, и он попросит фото вашей установки.
"""

NOT_SUBSCRIBED_TEXT = """
⚠️ <b>Подписка не обнаружена</b>

Пожалуйста, подпишитесь на канал и нажмите <b>«✅ Я подписался»</b> ещё раз.
"""

PHOTO_PROMPT_TEXT = """
✅ <b>Кодовое слово принято!</b>

📸 Чтобы мы могли помочь с настройкой <b>Starlink</b>, отправьте <b>фото вашей установки</b> или оборудования.

<b>Что можно отправить:</b>
• тарелку Starlink
• место установки
• роутер / подключение
• общий вид оборудования
• скрин ошибки (если есть)

После отправки фото специалист посмотрит ваш случай и подскажет, что делать дальше.

👇 Просто прикрепите фото в этот чат.
"""

PHOTO_RECEIVED_TEXT = """
✅ <b>Фото отправлено!</b>

Ваш запрос принят.

⏳ <b>Ожидайте ответ специалиста.</b>
"""

WAIT_PHOTO_TEXT = """
📸 Пожалуйста, отправьте <b>именно фото</b>, а не текст.

Прикрепите фотографию оборудования или установки Starlink.
"""

WRONG_INPUT_TEXT = """
🤔 Не понял сообщение.

Используйте кнопки меню или отправьте <b>кодовое слово</b> из инструкции.
"""

# Кодовое слово
SECRET_WORD = "старлинк"

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
    user_id = query.from_user.id

    if query.data == "start":
        waiting_for_photo.discard(user_id)
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
            # Проверка подписки на канал
            member = await context.bot.get_chat_member(REVIEWS_CHANNEL_USERNAME, user_id)

            if member.status in ("member", "administrator", "creator"):
                await query.edit_message_text(
                    MANUAL_TEXT,
                    parse_mode="HTML",
                    reply_markup=back_keyboard(),
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

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip().lower() if update.message.text else ""

    # Если ждём фото, а пользователь отправил текст
    if user_id in waiting_for_photo:
        await update.message.reply_text(
            WAIT_PHOTO_TEXT,
            parse_mode="HTML",
        )
        return

    # Проверка кодового слова
    if text == SECRET_WORD:
        waiting_for_photo.add(user_id)
        await update.message.reply_text(
            PHOTO_PROMPT_TEXT,
            parse_mode="HTML",
        )
        return

    # Всё остальное
    await update.message.reply_text(
        WRONG_INPUT_TEXT,
        parse_mode="HTML",
        reply_markup=main_keyboard(),
    )

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    username = f"@{user.username}" if user.username else "без username"
    full_name = user.full_name

    if user_id not in waiting_for_photo:
        await update.message.reply_text(
            "🤔 Сначала откройте инструкцию, отправьте кодовое слово, а потом фото.",
            parse_mode="HTML",
            reply_markup=main_keyboard(),
        )
        return

    # Убираем из режима ожидания
    waiting_for_photo.discard(user_id)

    caption = (
        f"📩 Новый запрос на помощь с настройкой Starlink\n"
        f"👤 {full_name}\n"
        f"🔗 {username}\n"
        f"🆔 {user_id}"
    )

    try:
        # Пересылаем фото как есть
        await context.bot.forward_message(
            chat_id=ADMIN_CHANNEL_ID,
            from_chat_id=update.message.chat_id,
            message_id=update.message.message_id,
        )

        # Отдельно отправляем данные пользователя
        await context.bot.send_message(
            chat_id=ADMIN_CHANNEL_ID,
            text=caption,
        )

    except Exception as e:
        logger.error(f"Не удалось переслать фото в канал: {e}")

    await update.message.reply_text(
        PHOTO_RECEIVED_TEXT,
        parse_mode="HTML",
        reply_markup=main_keyboard(),
    )

# ─── ОБРАБОТЧИК ОШИБОК ───────────────────────────────────────────────────────

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Ошибка в обработчике:", exc_info=context.error)

# ─── ЗАПУСК ───────────────────────────────────────────────────────────────────

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    app.add_error_handler(error_handler)

    logger.info("Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()