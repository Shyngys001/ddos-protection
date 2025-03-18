import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier

# Генерируем фейковые данные для тренировки (обычно берут датасет)
X_train = np.random.rand(1000, 5)
y_train = np.random.choice([0, 1], size=1000)  # 0 - нормальный трафик, 1 - DDoS

# Обучаем модель
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# Сохраняем
joblib.dump(model, "ai_model.pkl")
print("✅ AI-модель обучена и сохранена!")