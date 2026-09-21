import pandas as pd
import joblib

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


# Load dataset
data = pd.read_csv("data/student_data.csv")


# Features
features = [
    "attendance",
    "study_hours",
    "previous_score",
    "assignment_score",
    "internal_score",
    "sleep_hours",
    "participation"
]

X = data[features]
y = data["final_score"]


# Split dataset
X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42
)


# Create model
model = RandomForestRegressor(
    n_estimators=200,
    random_state=42
)


# Train
model.fit(X_train, y_train)


# Predictions
predictions = model.predict(X_test)


# Evaluation
mae = mean_absolute_error(y_test, predictions)

mse = mean_squared_error(
    y_test,
    predictions
)

rmse = mse ** 0.5

r2 = r2_score(
    y_test,
    predictions
)


print("Model Training Completed!")
print("--------------------------------")
print(f"MAE  : {mae:.2f}")
print(f"RMSE : {rmse:.2f}")
print(f"R²   : {r2:.2f}")
print("--------------------------------")


# Save model
joblib.dump(
    model,
    "model/student_model.pkl"
)

print("Model saved successfully!")
print("Location: model/student_model.pkl")