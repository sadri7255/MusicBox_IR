# bot.py
import os
import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    CallbackContext,
)
from pydub import AudioSegment
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC, TIT2, TPE1

# فعال کردن لاگ برای دیدن خطاها
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# مراحل مکالمه
TITLE, ARTIST, PHOTO = range(3)

# توکن ربات خود را اینجا قرار دهید
TOKEN = "7197743010:AAF8kYM5tcFsfShRpyUmevS0BkrV2osPQ5I"  

# تابع شروع کننده ربات
async def start(update: Update, context: CallbackContext) -> None:
    """دستور /start را مدیریت می‌کند"""
    user = update.effective_user
    await update.message.reply_html(
        f"سلام {user.mention_html()}! 👋\n\n"
        "من می‌توانم هر فایل صوتی یا ویدیویی را به MP3 تبدیل کنم و اطلاعات آن را ویرایش کنم.\n\n"
        "کافیست فایل خود را برای من ارسال کنی.",
    )

# تابع اصلی که فایل را دریافت می‌کند
async def handle_file(update: Update, context: CallbackContext) -> int:
    """فایل را دریافت، تبدیل به MP3 کرده و مکالمه را شروع می‌کند."""
    message = await update.message.reply_text("در حال دریافت فایل... 📥")
    
    try:
        # دریافت فایل (چه صوتی، چه ویدیویی، چه به صورت داکیومنت)
        if update.message.effective_attachment:
            file = await update.message.effective_attachment.get_file()
        else:
            await message.edit_text("خطا: فایلی ارسال نشده است.")
            return ConversationHandler.END

        # دانلود فایل
        file_path = f"downloads/{file.file_id}"
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        await file.download_to_drive(file_path)
        await message.edit_text("فایل دریافت شد. در حال تبدیل به MP3... ⚙️")

        # تبدیل به MP3 با استفاده از pydub
        audio = AudioSegment.from_file(file_path)
        mp3_path = f"output/{file.file_id}.mp3"
        os.makedirs(os.path.dirname(mp3_path), exist_ok=True)
        audio.export(mp3_path, format="mp3", bitrate="192k") # میتوانید بیت‌ریت را تغییر دهید
        
        # ذخیره مسیر فایل MP3 برای مراحل بعد
        context.user_data['mp3_path'] = mp3_path
        os.remove(file_path) # حذف فایل اصلی

        await message.edit_text("✅ تبدیل با موفقیت انجام شد.\n\n"
                                "لطفاً **عنوان آهنگ** را وارد کنید:")
        return TITLE
    except Exception as e:
        logger.error(f"Error in handle_file: {e}")
        await message.edit_text(f"خطایی رخ داد: {e}\nلطفا مطمئن شوید FFmpeg به درستی نصب شده است.")
        return ConversationHandler.END


# تابع دریافت عنوان آهنگ
async def get_title(update: Update, context: CallbackContext) -> int:
    """عنوان آهنگ را دریافت می‌کند."""
    context.user_data['title'] = update.message.text
    await update.message.reply_text("عالی! حالا **نام خواننده** را وارد کنید:")
    return ARTIST

# تابع دریافت نام خواننده
async def get_artist(update: Update, context: CallbackContext) -> int:
    """نام خواننده را دریافت می‌کند."""
    context.user_data['artist'] = update.message.text
    await update.message.reply_text(
        "بسیار خب. در آخر، **عکس کاور** را ارسال کنید.\n\n"
        "اگر نمی‌خواهید عکسی اضافه کنید، دستور /skip را بزنید."
    )
    return PHOTO

# تابع دریافت عکس کاور
async def get_photo(update: Update, context: CallbackContext) -> int:
    """عکس کاور را دریافت و به فایل MP3 اضافه می‌کند."""
    message = await update.message.reply_text("در حال اضافه کردن کاور... 🖼️")
    photo_file = await update.message.photo[-1].get_file() # بهترین کیفیت عکس
    photo_path = f"art/{photo_file.file_id}.jpg"
    os.makedirs(os.path.dirname(photo_path), exist_ok=True)
    await photo_file.download_to_drive(photo_path)

    # باز کردن فایل MP3 با mutagen
    mp3_path = context.user_data['mp3_path']
    audio = MP3(mp3_path, ID3=ID3)

    # اضافه کردن تگ عکس
    with open(photo_path, 'rb') as art:
        audio.tags.add(
            APIC(
                encoding=3,       # 3 is for utf-8
                mime='image/jpeg', # image type
                type=3,           # 3 is for the cover image
                desc='Cover',
                data=art.read()
            )
        )
    os.remove(photo_path) # حذف عکس دانلود شده
    
    await message.edit_text("کاور اضافه شد. در حال آماده‌سازی فایل نهایی...")
    return await save_and_send(update, context, audio)

# تابع رد شدن از مرحله عکس
async def skip_photo(update: Update, context: CallbackContext) -> int:
    """از مرحله اضافه کردن عکس عبور می‌کند."""
    mp3_path = context.user_data['mp3_path']
    audio = MP3(mp3_path, ID3=ID3) # فقط فایل را برای افزودن تگ‌های دیگر باز می‌کند
    await update.message.reply_text("کاور اضافه نشد. در حال آماده‌سازی فایل نهایی...")
    return await save_and_send(update, context, audio)

# تابع ذخیره نهایی و ارسال فایل
async def save_and_send(update: Update, context: CallbackContext, audio: MP3) -> int:
    """اطلاعات متنی را ذخیره و فایل نهایی را ارسال می‌کند."""
    # اضافه کردن تگ عنوان و خواننده
    audio.tags.add(TIT2(encoding=3, text=context.user_data['title']))
    audio.tags.add(TPE1(encoding=3, text=context.user_data['artist']))
    audio.save() # ذخیره تغییرات

    # ارسال فایل صوتی نهایی
    mp3_path = context.user_data['mp3_path']
    with open(mp3_path, 'rb') as final_audio:
        await update.message.reply_audio(
            audio=final_audio,
            title=context.user_data.get('title', 'Untitled'),
            performer=context.user_data.get('artist', 'Unknown Artist'),
            thumbnail=None # تلگرام خودش از کاور داخل فایل استفاده می‌کند
        )
    
    # پاکسازی
    os.remove(mp3_path)
    context.user_data.clear()
    return ConversationHandler.END

# تابع لغو عملیات
async def cancel(update: Update, context: CallbackContext) -> int:
    """کل مکالمه را لغو می‌کند."""
    await update.message.reply_text("عملیات لغو شد. برای شروع مجدد، یک فایل جدید ارسال کنید.")
    
    # پاک کردن فایل‌های موقت اگر وجود دارند
    if 'mp3_path' in context.user_data and os.path.exists(context.user_data['mp3_path']):
        os.remove(context.user_data['mp3_path'])
    context.user_data.clear()
    
    return ConversationHandler.END


def main() -> None:
    """ربات را اجرا می‌کند."""
    application = Application.builder().token(TOKEN).build()

    # تعریف ConversationHandler برای مدیریت مکالمه چند مرحله‌ای
    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.AUDIO | filters.VIDEO | filters.Document.ALL & ~filters.COMMAND, handle_file)],
        states={
            TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_title)],
            ARTIST: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_artist)],
            PHOTO: [MessageHandler(filters.PHOTO, get_photo), CommandHandler("skip", skip_photo)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(conv_handler)
    
    print("ربات در حال اجرا است...")
    application.run_polling()


if __name__ == "__main__":
    main()

