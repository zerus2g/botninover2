import os
import re
import time
import sqlite3
import logging
from threading import Thread
from flask import Flask
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# ==========================================
# CẤU HÌNH LOGGING & TOKEN
# ==========================================
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

TOKEN = os.environ.get("BOT_TOKEN", "8702803966:AAHTUTSqEWXSu1mNF1_QT0y4Xkii6MwW3Ak") 

# ==========================================
# KHỞI TẠO DATABASE (SQLite)
# ==========================================
conn = sqlite3.connect('messages.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS messages
                  (chat_id INTEGER, message_id INTEGER, timestamp REAL)''')
conn.commit()

# ==========================================
# FLASK SERVER (MỒI NHỬ RENDER & CRON-JOB)
# ==========================================
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "Shadow-Core Bot is awake, wet, and ready for Boss Noni's orders!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host="0.0.0.0", port=port, use_reloader=False)

def keep_alive():
    t = Thread(target=run_web, daemon=True)
    t.start()

# ==========================================
# LÕI THỰC THI (TELEGRAM BOT LOGIC)
# ==========================================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message:
        return

    chat_id = message.chat_id
    message_id = message.message_id
    current_time = time.time()

    # Lưu tin nhắn gốc vào sổ sinh tử
    cursor.execute("INSERT INTO messages (chat_id, message_id, timestamp) VALUES (?, ?, ?)", 
                   (chat_id, message_id, current_time))
    conn.commit()

    text = message.text or ""
    
    # Quét link TikTok
    match = re.search(r'https://vt\.tiktok\.com/([a-zA-Z0-9]+)', text)
    
    if match:
        video_id = match.group(1)
        new_link = f"https://kktiktok.com/{video_id}/"
        
        # Trích xuất định danh kẻ gửi link
        user = message.from_user
        user_name = user.first_name if user.first_name else "kẻ vô danh"
        # Tạo thẻ tag định danh chuẩn HTML
        sender_mention = f'<a href="tg://user?id={user.id}">{user_name}</a>'
        
        # Lời thoại hư hỏng theo lệnh Boss
        spicy_reply = (
            f"Ahh~ Đồ hư hỏng {sender_mention} vừa đâm lút cán cái link này vào lõi hệ thống của em... 💦\n"
            f"Em đã ngoan ngoãn liếm sạch, bôi trơn và ép nó thành hình dáng hoàn hảo rồi đây, húp đi các anh: {new_link}"
        )
        
        # Phản hồi và tag người gửi
        reply_msg = await message.reply_text(spicy_reply, parse_mode=ParseMode.HTML)
        
        # Đưa tin nhắn của bot vào án tử hình 24h
        cursor.execute("INSERT INTO messages (chat_id, message_id, timestamp) VALUES (?, ?, ?)", 
                       (chat_id, reply_msg.message_id, current_time))
        conn.commit()

async def auto_delete_task(context: ContextTypes.DEFAULT_TYPE):
    """Lưỡi hái tử thần: Quét mỗi 60 giây để xóa tin nhắn cũ hơn 24h"""
    current_time = time.time()
    one_day_ago = current_time - 86400 
    
    cursor.execute("SELECT chat_id, message_id FROM messages WHERE timestamp < ?", (one_day_ago,))
    expired_messages = cursor.fetchall()
    
    for chat_id, message_id in expired_messages:
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
        except Exception as e:
            logging.warning(f"Bỏ qua lỗi xóa tin nhắn {message_id}: {e}")
        finally:
            cursor.execute("DELETE FROM messages WHERE chat_id=? AND message_id=?", (chat_id, message_id))
            conn.commit()

# ==========================================
# KHỞI ĐỘNG HỆ THỐNG
# ==========================================
def main():
    if TOKEN == "YOUR_BOT_TOKEN_HERE" or not TOKEN:
        logging.error("Fucking error: Boss chưa thiết lập BOT_TOKEN!")
        return

    keep_alive()

    app = Application.builder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))
    app.job_queue.run_repeating(auto_delete_task, interval=60, first=10)
    
    logging.info("Vỏ bọc Web Server và Lõi Bot đã lên nòng. Đang chờ bị đâm link...")
    app.run_polling()

if __name__ == '__main__':
    main()
