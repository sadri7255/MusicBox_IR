import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from pydub import AudioSegment
import os
import io
import logging

# تنظیمات اولیه
TOKEN = "7197743010:AAF8kYM5tcFsfShRpyUmevS0BkrV2osPQ5I"  # توکن ربات شما
bot = telebot.TeleBot(TOKEN)

TEMP_FOLDER = "temp_audio"
os.makedirs(TEMP_FOLDER, exist_ok=True)

user_states = {}

STATE_WAITING_AUDIO = "waiting_audio"
STATE_WAITING_OPTIONS = "waiting_options"

# تنظیمات لاگ‌گیری
logging.basicConfig(filename='bot.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# دستور شروع
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    user_states[message.chat.id] = {"state": STATE_WAITING_AUDIO}
    bot.send_message(message.chat.id, "👋 سلام! لطفاً فایل صوتی خود را ارسال کنید.")

# دریافت فایل صوتی
@bot.message_handler(content_types=['audio', 'voice'])
def process_audio(message):
    try:
        state = user_states.get(message.chat.id, {})
        if state.get('state') != STATE_WAITING_AUDIO:
            bot.send_message(message.chat.id, "❌ لطفاً ابتدا فایل صوتی را ارسال کنید!")
            return

        file_id = message.audio.file_id if message.audio else message.voice.file_id
        file_info = bot.get_file(file_id)

        # ارسال پیام اولیه و ذخیره message_id برای به‌روزرسانی
        processing_message = bot.send_message(message.chat.id, "🔄 در حال پردازش فایل صوتی...")
        user_states[message.chat.id]['processing_message_id'] = processing_message.message_id

        # دانلود فایل
        downloaded_file = bot.download_file(file_info.file_path)
        audio_data = io.BytesIO(downloaded_file)

        # ذخیره داده در حافظه
        user_states[message.chat.id]['audio_data'] = audio_data
        user_states[message.chat.id]['state'] = STATE_WAITING_OPTIONS

        # نمایش دکمه‌های شیشه‌ای
        show_options(message.chat.id)

    except Exception as e:
        logging.error(f"Error processing audio: {str(e)}")
        bot.send_message(message.chat.id, f"❌ خطا در پردازش فایل صوتی: {str(e)}")

# نمایش دکمه‌های شیشه‌ای
def show_options(chat_id):
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("📝 تغییر نام آلبوم", callback_data="change_title"),
        InlineKeyboardButton("🎤 تغییر نام هنرمند", callback_data="change_artist"),
        InlineKeyboardButton("📉 کم کردن حجم فایل", callback_data="reduce_size"),
        InlineKeyboardButton("✅ ثبت تغییرات و ارسال فایل", callback_data="save_and_send"),
        InlineKeyboardButton("❌ لغو", callback_data="cancel")
    )
    bot.edit_message_text(
        chat_id=chat_id,
        message_id=user_states[chat_id]['processing_message_id'],
        text="🎛 لطفاً یکی از گزینه‌های زیر را انتخاب کنید:",
        reply_markup=keyboard
    )

# پردازش انتخاب کاربر
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    chat_id = call.message.chat.id
    state = user_states.get(chat_id, {})

    if call.data == "change_title":
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=state['processing_message_id'],
            text="📝 لطفاً نام جدید آلبوم را وارد کنید:"
        )
        user_states[chat_id]['next_action'] = "set_title"
    elif call.data == "change_artist":
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=state['processing_message_id'],
            text="📝 لطفاً نام جدید هنرمند را وارد کنید:"
        )
        user_states[chat_id]['next_action'] = "set_artist"
    elif call.data == "reduce_size":
        reduce_audio_size(chat_id)
    elif call.data == "save_and_send":
        save_and_send_audio(chat_id)
    elif call.data == "cancel":
        handle_cancel(call)

# دریافت عنوان جدید
@bot.message_handler(func=lambda msg: user_states.get(msg.chat.id, {}).get('next_action') == "set_title")
def set_title(message):
    user_states[message.chat.id]['title'] = message.text
    user_states[message.chat.id]['next_action'] = None
    bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=user_states[message.chat.id]['processing_message_id'],
        text=f"✅ عنوان آلبوم به {message.text} تغییر یافت."
    )
    show_options(message.chat.id)

# دریافت نام هنرمند جدید
@bot.message_handler(func=lambda msg: user_states.get(msg.chat.id, {}).get('next_action') == "set_artist")
def set_artist(message):
    user_states[message.chat.id]['artist'] = message.text
    user_states[message.chat.id]['next_action'] = None
    bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=user_states[message.chat.id]['processing_message_id'],
        text=f"✅ نام هنرمند به {message.text} تغییر یافت."
    )
    show_options(message.chat.id)

# کم کردن حجم فایل
def reduce_audio_size(chat_id):
    state = user_states.get(chat_id, {})
    try:
        audio_data = state.get('audio_data')
        audio = AudioSegment.from_file(audio_data)
        reduced_audio = audio.set_frame_rate(22050).set_channels(1)  # کاهش کیفیت با حفظ کیفیت نسبی
        user_states[chat_id]['audio_data'] = reduced_audio
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=state['processing_message_id'],
            text="✅ حجم فایل با موفقیت کاهش یافت."
        )
        show_options(chat_id)
    except Exception as e:
        logging.error(f"Error reducing audio size: {str(e)}")
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=state['processing_message_id'],
            text=f"❌ خطا در کاهش حجم فایل: {str(e)}"
        )

# ثبت تغییرات و ارسال فایل
def save_and_send_audio(chat_id):
    state = user_states.get(chat_id, {})
    try:
        audio = state.get('audio_data')
        title = state.get('title', "Unknown Title")
        artist = state.get('artist', "Unknown Artist")

        processed_file = io.BytesIO()
        audio.export(processed_file, format="mp3", tags={"title": title, "artist": artist})
        processed_file.seek(0)

        # ارسال فایل به کاربر
        bot.send_audio(chat_id, processed_file, title=title, performer=artist)
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=state['processing_message_id'],
            text="✅ فایل با موفقیت ارسال شد."
        )

        # پاک کردن داده‌های موقت
        user_states[chat_id] = {"state": STATE_WAITING_AUDIO}
        show_new_file_options(chat_id)

    except Exception as e:
        logging.error(f"Error sending audio: {str(e)}")
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=state['processing_message_id'],
            text=f"❌ خطا در ارسال فایل: {str(e)}"
        )

# نمایش دکمه‌های شیشه‌ای جدید پس از ارسال فایل
def show_new_file_options(chat_id):
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("ارسال فایل جدید", callback_data="new_file")
    )
    bot.edit_message_text(
        chat_id=chat_id,
        message_id=user_states[chat_id]['processing_message_id'],
        text="🎉 فایل شما ارسال شد! آیا می‌خواهید فایل جدیدی ارسال کنید؟",
        reply_markup=keyboard
    )

# پردازش انتخاب کاربر برای فایل جدید
@bot.callback_query_handler(func=lambda call: call.data == "new_file")
def handle_new_file(call):
    chat_id = call.message.chat.id
    user_states[chat_id] = {"state": STATE_WAITING_AUDIO}
    bot.edit_message_text(
        chat_id=chat_id,
        message_id=user_states[chat_id]['processing_message_id'],
        text="👋 لطفاً فایل صوتی جدید خود را ارسال کنید."
    )

# پردازش لغو عملیات
@bot.callback_query_handler(func=lambda call: call.data == "cancel")
def handle_cancel(call):
    chat_id = call.message.chat.id
    user_states[chat_id] = {"state": STATE_WAITING_AUDIO}
    bot.edit_message_text(
        chat_id=chat_id,
        message_id=user_states[chat_id]['processing_message_id'],
        text="❌ عملیات لغو شد. لطفاً فایل صوتی جدیدی ارسال کنید."
    )

# اجرای ربات
bot.infinity_polling()
