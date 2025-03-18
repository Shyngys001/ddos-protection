import os
import time
import logging
import random
import joblib
import pandas as pd
import numpy as np
from flask import Flask, request, jsonify, abort

# Настройки
REQUEST_LIMIT = 10  # Больше допустимых запросов = DDoS
TIME_WINDOW = 5  # Время в секундах
LOG_FILE = "traffic_logs.csv"

# AI-модель (если есть)
MODEL_FILE = "ai_model.pkl"
ai_model = joblib.load(MODEL_FILE) if os.path.exists(MODEL_FILE) else None

# Храним запросы
ip_requests = {}

# Запуск Flask
app = Flask(__name__)

# Функция логирования запросов
def log_request(ip, user_agent, headers, ddos_label):
    df = pd.DataFrame([{
        "timestamp": time.time(),
        "ip": ip,
        "user_agent": user_agent,
        "headers": str(headers),
        "is_ddos": ddos_label
    }])
    df.to_csv(LOG_FILE, mode="a", header=not os.path.exists(LOG_FILE), index=False)

# Определяем IP
def get_client_ip():
    return request.headers.get("X-Forwarded-For", request.remote_addr)

# AI-детекция DDoS
def detect_ddos(ip, user_agent, headers):
    if ai_model is None:
        return random.choice([0, 1])  # Если модели нет, случайное поведение

    features = np.array([[len(user_agent), len(headers), int(ip.split(".")[-1])]])
    return ai_model.predict(features)[0]

@app.before_request
def block_ddos():
    ip = get_client_ip()
    user_agent = request.headers.get("User-Agent", "Unknown")
    headers_count = len(request.headers)

    now = time.time()
    ip_requests.setdefault(ip, []).append(now)

    # Чистим старые запросы
    ip_requests[ip] = [t for t in ip_requests[ip] if t > now - TIME_WINDOW]

    # AI-анализ + лимит
    is_ddos = len(ip_requests[ip]) > REQUEST_LIMIT or detect_ddos(ip, user_agent, request.headers)
    
    log_request(ip, user_agent, request.headers, int(is_ddos))

    if is_ddos:
        abort(403)

@app.route("/")
def home():
    return "🔥 Сервер работает!"

if __name__ == "__main__":
    app.run(port=5000, debug=False)