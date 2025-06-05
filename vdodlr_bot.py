import telebot
from yt_dlp import YoutubeDL
import os

# Replace 'YOUR_TELEGRAM_BOT_TOKEN' with your actual bot token from BotFather
TOKEN = '7859865766:AAFaBo2zJqBQK7f7dnT6zol_05Cp_zizMNI'
bot = telebot.TeleBot(TOKEN)

# yt-dlp download options
YDL_OPTIONS = {
    'format': 'bestvideo+bestaudio/best',
    'outtmpl': 'downloads/%(title)s.%(ext)s',
    'noplaylist': True,
    'quiet': True,
}

# Ensure a downloads folder exists
if not os.path.exists('downloads'):
    os.makedirs('downloads')

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "Hello! Send me a video link, and I'll download it for you.")

@bot.message_handler(func=lambda message: True)
def download_video(message):
    url = message.text
    chat_id = message.chat.id
    bot.send_message(chat_id, "Downloading... Please wait.")

    # Download video with yt-dlp
    with YoutubeDL(YDL_OPTIONS) as ydl:
        try:
            info = ydl.extract_info(url, download=True)
            video_title = ydl.prepare_filename(info)
            
            # Send video to user
            with open(video_title, 'rb') as video_file:
                bot.send_video(chat_id, video_file)
            
            # Clean up
            os.remove(video_title)
        
        except Exception as e:
            bot.send_message(chat_id, f"Failed to download video. Error: {e}")

# Start polling
print("Bot is running...")
bot.polling(none_stop=True)
