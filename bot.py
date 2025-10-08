import os
import logging
import yt_dlp
from fastapi import FastAPI, Request
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.error import Forbidden

# ------------------- إعدادات البوت -------------------
TOKEN = "8495219196:AAHtkROKcUr0bWL2fnLYPPT6tU0oqk3u2zs"
ADMIN_ID = 5581457665
CHANNEL_USERNAME = "Qd3Qd"
CHANNEL_LINK = "https://t.me/qd3qd"
PORT = int(os.environ.get("PORT", 10000))
USERS_FILE = "users.txt"

WEBHOOK_PATH = f"/webhook/{TOKEN}"
WEBHOOK_URL = f"https://x-o-bot.onrender.com{WEBHOOK_PATH}"
# ------------------------------------------------------

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

fastapi_app = FastAPI()
application = Application.builder().token(TOKEN).build()

# ------------------- دالة الاشتراك -------------------
async def check_subscription(user_id, context):
    try:
        member = await context.bot.get_chat_member(f"@{CHANNEL_USERNAME}", user_id)
        if member.status in ["left", "kicked"]:
            return False
    except Forbidden:
        return False
    except Exception as e:
        logger.error(f"خطأ بالاشتراك: {e}")
        return False
    return True

# ------------------- أمر /start -------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user:
        return

    user_id = user.id
    is_subscribed = await check_subscription(user_id, context)

    if not is_subscribed:
        buttons = [
            [InlineKeyboardButton(f"📢مَـدار @{CHANNEL_USERNAME}", url=CHANNEL_LINK)],
            [InlineKeyboardButton("✅ تم", callback_data="check_sub")]
        ]
        await update.message.reply_text(
            "⚠️ حبي اشترك بالقناة 😎",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return

    await update.message.reply_text(
        "هااا، شنو تحب تسمع اليوم؟ 😎\nاكتب اسم الأغنية وخلي ألقاها إلك 🎧"
    )

# ------------------- إعادة تحقق الاشتراك -------------------
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "check_sub":
        user_id = query.from_user.id
        is_subscribed = await check_subscription(user_id, context)
        if is_subscribed:
            await query.edit_message_text("هااا، شنو تحب تسمع اليوم؟ 😎 اكتب اسم الأغنية 🎶")
        else:
            await query.edit_message_text("❌ بعدك ما مشترك حبي، اشترك ورجع جرب.")

# ------------------- البحث عن أغاني -------------------
async def search_song(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()
    await update.message.reply_text("🔎 لحظة حبي خلي أدوّرلك ...")

    ydl_opts = {"quiet": True, "noplaylist": True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            search = ydl.extract_info(f"ytsearch5:{query}", download=False)["entries"]

        if not search:
            await update.message.reply_text("😕 ما لكيت شي بهالاسم حبي.")
            return

        buttons = []
        for video in search:
            title = video.get("title", "بدون عنوان")
            duration = video.get("duration_string", "??:??")
            video_id = video.get("id")
            buttons.append([
                InlineKeyboardButton(f"{title} ({duration})", callback_data=f"dl|{video_id}")
            ])

        await update.message.reply_text(
            "🎧 لكيتلك هاي الأغاني، اختار وحده:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    except Exception as e:
        logger.error(e)
        await update.message.reply_text("❌ صار خطأ حبي، جرب غير اسم.")

# ------------------- تحميل الأغنية -------------------
async def download_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    video_id = query.data.split("|")[1]
    url = f"https://www.youtube.com/watch?v={video_id}"

    await query.edit_message_text("⏳ لحظة حبي حتى أحمل الأغنية 🔥")

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": "song.%(ext)s",
        "quiet": True,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192"
        }]
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get("title", "أغنية")
            file_path = "song.mp3"

        await query.edit_message_text("✅ حملتلك الأغنية، استمتع بيها 🎶🔥")
        await context.bot.send_audio(chat_id=query.message.chat_id, audio=open(file_path, "rb"), title=title)
        os.remove(file_path)
    except Exception as e:
        logger.error(f"تحميل فشل: {e}")
        await query.edit_message_text("❌ فشل التحميل، جرب غير وحدة حبي.")

# ------------------- Handlers -------------------
application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(button_callback))
application.add_handler(CallbackQueryHandler(download_audio, pattern="^dl\\|"))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_song))

# ------------------- Webhook -------------------
@fastapi_app.post(WEBHOOK_PATH)
async def webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return {"ok": True}

@fastapi_app.on_event("startup")
async def startup():
    await application.initialize()
    await application.bot.set_webhook(WEBHOOK_URL)
    logger.info(f"✅ Webhook set: {WEBHOOK_URL}")

@fastapi_app.get("/")
async def root():
    return {"status": "Bot Running"}
