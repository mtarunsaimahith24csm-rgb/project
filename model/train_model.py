import pandas as pd
import joblib
import json

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


# Load dataset
data = pd.read_csv("data/student_data.csv")

print("Dataset loaded successfully!")
print("Number of students:", len(data))


# Features used by the model
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


# Create Random Forest model
model = RandomForestRegressor(
    n_estimators=200,
    random_state=42
)


# Train model
print("Training model...")

model.fit(X_train, y_train)


# Make predictions
predictions = model.predict(X_test)


# Calculate evaluation metrics
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


# Feature importance
feature_importance = {}

for feature, importance in zip(
    features,
    model.feature_importances_
):
    feature_importance[feature] = float(importance)


# Create evaluation information
evaluation_data = {
    "mae": float(mae),
    "rmse": float(rmse),
    "r2_score": float(r2),
    "feature_importance": feature_importance
}


# Save model
joblib.dump(
    model,
    "model/student_model.pkl"
)


# Save evaluation metrics
with open(
    "model/model_metrics.json",
    "w"
) as file:

    json.dump(
        evaluation_data,
        file,
        indent=4
    )


# Display results
print()
print("Model Training Completed!")
print("--------------------------------")
print(f"MAE  : {mae:.2f}")
print(f"RMSE : {rmse:.2f}")
print(f"R²   : {r2:.2f}")
print("--------------------------------")

print()
print("Feature Importance:")

for feature, importance in feature_importance.items():

    print(
        f"{feature}: {importance:.4f}"
    )


print()
print("Model saved successfully!")
print("Location: model/student_model.pkl")

print()
print("Evaluation metrics saved successfully!")
print("Location: model/model_metrics.json")