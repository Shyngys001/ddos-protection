import os
import time
import logging
import random
import threading
import requests
from flask import Flask, request, jsonify, abort, render_template
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TELEGRAM_BOT_TOKEN = "7818122772:AAEYZgEmdLxrNWpBHchD84vuhsbQ9JMnUgE"
ADMIN_CHAT_ID = "1050963411"

logging.basicConfig(filename="ddos.log", level=logging.INFO)

ip_requests = {}  # Хранит запросы от IP-адресов
blocked_ips = set()  # Список заблокированных IP
attack_logs = []  # Лог атак

# 🔥 Настройки защиты
REQUEST_LIMIT = 5  # Максимум запросов за время
TIME_WINDOW = 5  # Окно времени (сек)  
AI_THRESHOLD = 0.2  # Порог ИИ-детекции (случайный блок)

# --- Flask ---
app = Flask(__name__)

# 🔥 Функция отправки уведомлений в Telegram
def send_telegram_alert(ip, fake=False):
    """Отправляет уведомление в Telegram о блокировке IP"""
    attack_type = "ФЕЙКОВАЯ DDoS-атака" if fake else "⚠️ DDoS-атака"
    message = f"{attack_type}! IP {ip} заблокирован."
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": ADMIN_CHAT_ID, "text": message}
    
    try:
        requests.post(url, json=payload)
        print(f"✅ Отправлено в Telegram: {message}")
    except Exception as e:
        print(f"❌ Ошибка Telegram: {e}")

# 🔥 Определение IP клиента
def get_client_ip():
    return request.headers.get("X-Forwarded-For", request.remote_addr) or "unknown"

@app.route("/fake_attack", methods=["POST"])
def fake_attack():
    """Создаёт фейковую DDoS-атаку"""
    fake_ip = f"{random.randint(1, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}"
    attack_logs.append({"ip": fake_ip, "time": time.ctime(), "fake": True})
    blocked_ips.add(fake_ip)
    send_telegram_alert(fake_ip, fake=True)
    return jsonify({"status": "fake_attack_created", "ip": fake_ip})

@app.route("/get_ips", methods=["GET"])
def get_ips():
    """Возвращает список реальных и фальшивых атак"""
    return jsonify({
        "incoming": list(ip_requests.keys()),
        "blocked": list(blocked_ips),
        "fake_attacks": attack_logs
    })

@app.route("/")
def index():
    """Главная страница с логами атак и управлением блокировкой"""
    return render_template("index.html", logs=attack_logs, blocked_ips=list(blocked_ips))

# --- Telegram Bot ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Я бот для мониторинга DDoS.\n"
                                    "/blocked - показать заблокированные IP\n"
                                    "/unblock <IP> - разблокировать IP")

async def blocked_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = "Заблокированные IP:\n" + "\n".join(blocked_ips) if blocked_ips else "Список пуст."
    await update.message.reply_text(msg)

async def unblock_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Использование: /unblock <IP>")
        return
    ip = context.args[0]
    if ip in blocked_ips:
        blocked_ips.discard(ip)
        logging.info(f"[Bot] IP {ip} разблокирован.")
        await update.message.reply_text(f"IP {ip} разблокирован.")
    else:
        await update.message.reply_text("IP не найден в списке блокировки.")

def create_telegram_application():
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("blocked", blocked_command))
    application.add_handler(CommandHandler("unblock", unblock_command))
    return application

# --- Запуск ---
def run_flask():
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)

if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    application = create_telegram_application()
    application.run_polling()
