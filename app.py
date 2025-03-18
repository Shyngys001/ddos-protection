import time
import logging
import threading
import requests
from flask import Flask, request, jsonify, abort, render_template
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# === Telegram Bot Config ===
TELEGRAM_BOT_TOKEN = "7818122772:AAEYZgEmdLxrNWpBHchD84vuhsbQ9JMnUgE"
ADMIN_CHAT_ID = "-4725219233"

# === Logging ===
logging.basicConfig(filename="ddos.log", level=logging.INFO)

# === Global Variables ===
ip_requests = {}  # Requests per IP
blocked_ips = set()  # Blocked IPs
attack_logs = []  # Attack logs

# === Security Config ===
REQUEST_LIMIT = 10  # Max requests before blocking
TIME_WINDOW = 5  # Seconds

app = Flask(__name__)

# === Function to send Telegram alerts ===
def send_telegram_alert(ip, reason):
    message = f"⚠️ DDoS Alert! IP {ip} заблокирован. Причина: {reason}"
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": ADMIN_CHAT_ID, "text": message}
    try:
        requests.post(url, json=payload)
        print(f"✅ Telegram Alert Sent: {message}")
    except Exception as e:
        print(f"❌ Telegram Error: {e}")

# === Get Client IP ===
def get_client_ip():
    if request.headers.get("X-Forwarded-For"):
        return request.headers.get("X-Forwarded-For").split(",")[0]  # Берем первый реальный IP
    return request.remote_addr or "unknown"

# === DDoS Detection Middleware ===
@app.before_request
def detect_ddos():
    ip = get_client_ip()
    now = time.time()
    timestamps = ip_requests.get(ip, [])
    timestamps.append(now)
    timestamps = [t for t in timestamps if t >= now - TIME_WINDOW]
    ip_requests[ip] = timestamps

    if ip in blocked_ips:
        abort(403)

    if len(timestamps) > REQUEST_LIMIT:
        blocked_ips.add(ip)
        attack_logs.append({"ip": ip, "time": time.ctime(now)})
        logging.info(f"[DDoS] IP {ip} заблокирован за превышение лимита запросов.")
        threading.Thread(target=send_telegram_alert, args=(ip, "Too many requests"), daemon=True).start()
        abort(403)

# === Routes ===
@app.route("/")
def index():
    return render_template("index.html", logs=attack_logs, blocked_ips=list(blocked_ips))

@app.route("/scan", methods=["GET"])
def scan():
    ip = get_client_ip()
    now = time.time()
    timestamps = ip_requests.get(ip, [])
    timestamps.append(now)
    ip_requests[ip] = [t for t in timestamps if t >= now - TIME_WINDOW]

    if ip in blocked_ips:
        return jsonify({"status": "blocked", "ip": ip})

    return jsonify({"status": "clean"})

@app.route("/get_ips", methods=["GET"])
def get_ips():
    return jsonify({
        "incoming": list(ip_requests.keys()),
        "blocked": list(blocked_ips),
        "fake_attacks": attack_logs
    })

# === Telegram Bot Handlers ===
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("DDoS Monitor Bot\n/blocked - Показать заблокированные IP\n/unblock <IP> - Разблокировать IP")

async def blocked_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = "Заблокированные IP:\n" + "\n".join(blocked_ips) if blocked_ips else "Нет заблокированных IP."
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

# === Создание Telegram-бота ===
app_telegram = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
app_telegram.add_handler(CommandHandler("start", start_command))
app_telegram.add_handler(CommandHandler("blocked", blocked_command))
app_telegram.add_handler(CommandHandler("unblock", unblock_command))

# === Запуск Flask & Telegram Bot ===
if __name__ == "__main__":
    threading.Thread(
        target=lambda: app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False),
        daemon=True
    ).start()
    app_telegram.run_polling()