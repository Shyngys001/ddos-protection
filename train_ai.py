import joblib
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier

# Загружаем данные
df = pd.read_csv("requests_log.csv")

# Преобразуем timestamp в формат datetime
df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s")

# Вычисляем количество запросов за 5 секунд для каждого IP
df["requests_per_5sec"] = df.groupby("ip")["timestamp"].transform(
    lambda x: x.diff().dt.total_seconds().fillna(0).rolling(3).count()
)

# Добавляем флаг DDoS-атаки (если больше 3 запросов за 5 секунд)
df["is_ddos"] = (df["requests_per_5sec"] > 3).astype(int)

# Формируем X (фичи) и y (метки)
X = df[["requests_per_5sec"]]
y = df["is_ddos"]

# Обучаем модель
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X, y)

# Сохраняем модель
joblib.dump(model, "ai_model.pkl")

print("✅ AI-модель переобучена на реальных данных и сохранена!")