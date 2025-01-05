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
        reduced_audio = audio.set_frame_rate(16000).set_channels(1)  # کاهش کیفیت
        user_states[chat_id]['audio_data'] = reduced_audio
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=state['processing_message_id'],
            text="✅ حجم فایل با موفقیت کاهش یافت."
        )
        show_options(chat_id)
    except Exception as e:
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

        # بازگشت به حالت اولیه و نمایش دکمه‌های شیشه‌ای جدید
        user_states[chat_id] = {"state": STATE_WAITING_AUDIO}
        show_new_file_options(chat_id)

    except Exception as e:
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

# اجرای ربات
bot.infinity_polling()
