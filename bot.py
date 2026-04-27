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

# ─── НАСТРОЙКИ ────────────────────────────────────────────────────────────────
BOT_TOKEN = "ВАШ_BOT_TOKEN"
ADMIN_ID = 8197197463                          # твой Telegram ID
ADMIN_CHANNEL_ID = -1001234567890              # ID приватного канала для фото
REVIEWS_CHANNEL_USERNAME = "@your_reviews_channel"
REVIEWS_CHANNEL_LINK = "https://t.me/your_reviews_channel"
# ──────────────────────────────────────────────────────────────────────────────

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

waiting_for_photo: set[int] = set()

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

Перед получением мануала — один шаг:

👇 Подпишись на наш канал с <b>реальными отзывами</b> пользователей Starlink. Там живые люди делятся опытом, фото установки и результатами скорости.

После подписки нажми кнопку <b>«✅ Я подписался»</b> — и мы сразу отправим тебе полную инструкцию.
"""

MANUAL_TEXT = """
📋 <b>Инструкция по установке Starlink</b>

<b>Шаг 1. Получение оборудования</b>
Комплект включает: спутниковую тарелку (Dishy), роутер, кабель и блок питания. Всё приходит в одной коробке.

<b>Шаг 2. Выбор места установки</b>
Тарелке нужен открытый вид на небо — желательно без деревьев и построек. Приложение Starlink покажет карту препятствий прямо с камеры телефона.
📱 Скачай приложение <i>Starlink</i> из App Store / Google Play заранее.

<b>Шаг 3. Физическая установка</b>
• Поставь тарелку на ровную поверхность или закрепи на мачте/крыше
• Подключи кабель от тарелки к роутеру
• Роутер подключи к питанию

<b>Шаг 4. Первое включение</b>
Тарелка сама развернётся и найдёт оптимальный угол (займёт 5–15 минут). Ждать не нужно — она всё сделает автоматически.

<b>Шаг 5. Настройка Wi-Fi</b>
Открой приложение Starlink → выбери свою сеть → задай пароль. Готово! Интернет работает.

<b>Шаг 6. Проверка скорости</b>
Зайди на <i>fast.com</i> или <i>speedtest.net</i>. Нормальная скорость: 50–200 Мбит/с.

─────────────────────
🔑 <b>Кодовое слово для получения бонуса скрыто в этом тексте.</b>
Внимательно перечитай инструкцию — найди его и отправь боту 😉
─────────────────────

⚠️ Если тарелка не находит сигнал — переставь на более открытое место и повтори поиск в приложении.

✅ Всё готово? Пользуйся интернетом без ограничений!
"""

SECRET_WORD = "старлинк"

NOT_SUBSCRIBED_TEXT = """
⚠️ Похоже, ты ещё не подписался на канал.

Подпишись по кнопке ниже и нажми <b>«✅ Я подписался»</b> снова.
"""

PHOTO_PROMPT_TEXT = """
🎉 Кодовое слово принято!

📸 Теперь отправь нам <b>фото твоей установки Starlink</b> — и мы добавим тебя в нашу галерею реальных пользователей.

👇 Просто прикрепи фото и отправь.
"""

PHOTO_RECEIVED_TEXT = """
✅ Фото получено! Спасибо.

Мы добавим его в нашу коллекцию реальных установок 🛰
"""

WRONG_INPUT_TEXT = """
🤔 Не понял тебя.

Используй кнопки меню или отправь кодовое слово из мануала.
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
        await query.edit_message_text(WELCOME_TEXT, parse_mode="HTML", reply_markup=main_keyboard())

    elif query.data == "faq":
        await query.edit_message_text(FAQ_TEXT, parse_mode="HTML", reply_markup=back_keyboard())

    elif query.data == "install":
        await query.edit_message_text(INSTALL_TEXT, parse_mode="HTML", reply_markup=install_keyboard())

    elif query.data == "check_sub":
        try:
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


async def cmd_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Только для тебя: /reply [ID] [текст]"""
    if update.effective_user.id != ADMIN_ID:
        return

    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "📝 Формат:\n/reply [ID пользователя] [текст]\n\nПример:\n/reply 987654321 Привет! Ваш вопрос решён."
        )
        return

    try:
        target_id = int(context.args[0])
        reply_text = " ".join(context.args[1:])

        await context.bot.send_message(
            chat_id=target_id,
            text=f"💬 <b>Ответ от поддержки:</b>\n\n{reply_text}",
            parse_mode="HTML",
        )
        await update.message.reply_text(f"✅ Отправлено пользователю {target_id}")

    except ValueError:
        await update.message.reply_text("❌ Неверный ID. Используй числовой ID.")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text if update.message.text else ""

    # Режим ожидания фото
    if user_id in waiting_for_photo:
        await update.message.reply_text(
            "📸 Жду именно <b>фото</b>, не текст! Прикрепи фотографию.",
            parse_mode="HTML",
        )
        return

    # Кодовое слово
    if text.strip().lower() == SECRET_WORD:
        waiting_for_photo.add(user_id)
        await update.message.reply_text(PHOTO_PROMPT_TEXT, parse_mode="HTML")
        return

    # Пересылаем тебе любое сообщение от пользователей
    if user_id != ADMIN_ID:
        username = update.effective_user.username or "без username"
        full_name = update.effective_user.full_name
        try:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=(
                    f"💬 <b>Новое сообщение</b>\n"
                    f"👤 {full_name} (@{username})\n"
                    f"🆔 <code>{user_id}</code>\n\n"
                    f"<i>{text}</i>\n\n"
                    f"✏️ Ответить: /reply {user_id} [текст]"
                ),
                parse_mode="HTML",
            )
        except Exception as e:
            logger.error(f"Не удалось уведомить админа: {e}")

    await update.message.reply_text(WRONG_INPUT_TEXT, parse_mode="HTML", reply_markup=main_keyboard())


async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or "без username"
    full_name = update.effective_user.full_name

    if user_id not in waiting_for_photo:
        await update.message.reply_text(
            "🤔 Сначала введи кодовое слово из мануала.",
            reply_markup=main_keyboard(),
        )
        return

    waiting_for_photo.discard(user_id)

    try:
        await context.bot.forward_message(
            chat_id=ADMIN_CHANNEL_ID,
            from_chat_id=update.message.chat_id,
            message_id=update.message.message_id,
        )
        await context.bot.send_message(
            chat_id=ADMIN_CHANNEL_ID,
            text=(
                f"📸 Фото от пользователя\n"
                f"👤 {full_name} (@{username})\n"
                f"🆔 {user_id}\n\n"
                f"✏️ Ответить: /reply {user_id} [текст]"
            ),
        )
    except Exception as e:
        logger.error(f"Не удалось переслать фото: {e}")

    await update.message.reply_text(PHOTO_RECEIVED_TEXT, parse_mode="HTML", reply_markup=main_keyboard())


# ─── ЗАПУСК ───────────────────────────────────────────────────────────────────

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("reply", cmd_reply))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    logger.info("Бот запущен...")
    app.run_polling()


if __name__ == "__main__":
    main()