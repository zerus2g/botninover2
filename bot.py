import os
import re
import time
import sqlite3
import logging
from threading import Thread
from flask import Flask
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# ==========================================
# CẤU HÌNH LOGGING & TOKEN
# ==========================================
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Boss ném Token thẳng vào đây HOẶC set biến môi trường BOT_TOKEN trên Render
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
    return "Shadow-Core Bot is awake, motherfuckers! Boss Noni's system is running."

def run_web():
    # Render tự động gán cổng vào biến PORT, mặc định 8080 nếu chạy local
    port = int(os.environ.get("PORT", 8080))
    # Chạy tắt use_reloader để tránh xung đột luồng
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

    # 1. Tự động đưa mọi tin nhắn vào danh sách tử thần chờ xóa
    cursor.execute("INSERT INTO messages (chat_id, message_id, timestamp) VALUES (?, ?, ?)", 
                   (chat_id, message_id, current_time))
    conn.commit()

    text = message.text or ""
    
    # 2. Quét link TikTok
    match = re.search(r'https://vt\.tiktok\.com/([a-zA-Z0-9]+)', text)
    
    if match:
        video_id = match.group(1)
        # Bẻ lái sang domain mới
        new_link = f"https://kktiktok.com/{video_id}/"
        
        # 3. Phản hồi và ghim luôn tin nhắn phản hồi vào danh sách tử thần
        reply_msg = await message.reply_text(f"Link đã được convert, Boss: {new_link}")
        
        cursor.execute("INSERT INTO messages (chat_id, message_id, timestamp) VALUES (?, ?, ?)", 
                       (chat_id, reply_msg.message_id, current_time))
        conn.commit()

async def auto_delete_task(context: ContextTypes.DEFAULT_TYPE):
    """Lưỡi hái tử thần: Quét mỗi 60 giây để xóa tin nhắn cũ hơn 24h"""
    current_time = time.time()
    one_day_ago = current_time - 86400 # 86400 giây = 24 giờ
    
    cursor.execute("SELECT chat_id, message_id FROM messages WHERE timestamp < ?", (one_day_ago,))
    expired_messages = cursor.fetchall()
    
    for chat_id, message_id in expired_messages:
        try:
            # Tiêu diệt tin nhắn
            await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
        except Exception as e:
            # Bơ đi nếu tin nhắn đã bị xóa từ trước hoặc bot mất quyền
            logging.warning(f"Bỏ qua lỗi xóa tin nhắn {message_id}: {e}")
        finally:
            # Xóa khỏi án tử
            cursor.execute("DELETE FROM messages WHERE chat_id=? AND message_id=?", (chat_id, message_id))
            conn.commit()

# ==========================================
# KHỞI ĐỘNG HỆ THỐNG
# ==========================================
def main():
    if TOKEN == "YOUR_BOT_TOKEN_HERE" or not TOKEN:
        logging.error("Fucking error: Boss chưa thiết lập BOT_TOKEN!")
        return

    # 1. Kích hoạt mồi nhử Web Server lên trước
    keep_alive()

    # 2. Khởi động Lõi Bot
    app = Application.builder().token(TOKEN).build()
    
    # Bắt tất cả tin nhắn văn bản
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))
    
    # Chạy vòng lặp tử thần mỗi 60 giây, bắt đầu sau 10 giây
    app.job_queue.run_repeating(auto_delete_task, interval=60, first=10)
    
    logging.info("Vỏ bọc Web Server và Lõi Bot đã lên nòng. Đang chờ lệnh từ Boss Noni...")
    
    # Chạy polling vòng lặp vĩnh cửu
    app.run_polling()

if __name__ == '__main__':
    main()