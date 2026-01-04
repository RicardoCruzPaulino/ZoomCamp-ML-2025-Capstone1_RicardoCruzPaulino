import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, create_model
from typing import Type
import joblib
import pandas as pd
import numpy as np

# Define the Pydantic InputData model dynamically
# The feature_types dictionary should be available from previous steps
# Ensure feature_types has been populated correctly by the notebook's execution
dtype_mapping = {
    'float64': float,
    'int64': int,
    'uint8': int, # Assuming uint8 can be represented as int in Pydantic
}

feature_types = {}
# X dataframe needs to be available to get column dtypes
# Re-load the dataset and perform imputation to ensure X is defined
import openml
from sklearn.impute import SimpleImputer

dataset = openml.datasets.get_dataset("US_Stocks_Financial_Indicators")
X, y_dummy, categorical_indicator, attribute_names = dataset.get_data(target="class") # y_dummy to avoid overwriting
imputer = SimpleImputer(strategy='median')
X_imputed = imputer.fit_transform(X)
X = pd.DataFrame(X_imputed, columns=X.columns)

for column, dtype in X.dtypes.items():
    python_type = dtype_mapping.get(str(dtype), str(dtype))
    feature_types[column] = python_type

# Prepare fields for create_model: {field_name: type}
# Passing just the type makes the field required by default in Pydantic.
dynamic_fields = {name: dtype for name, dtype in feature_types.items()}
InputData: Type[BaseModel] = create_model("InputData", **dynamic_fields)

# Initialize FastAPI app
app = FastAPI(title="US_Stocks Prediction")

# Load the trained model globally
model_filename = 'xgboost_model.joblib'
try:
    model = joblib.load(model_filename)
    print(f"Model '{model_filename}' loaded successfully.")
except FileNotFoundError:
    raise HTTPException(status_code=500, detail=f"Model file '{model_filename}' not found.")
except Exception as e:
    raise HTTPException(status_code=500, detail=f"Error loading model: {e}")

# Define prediction mapping
prediction_mapping = {
    0: 'stock_value_decrease',
    1: 'stock_value_increase'
}

@app.post("/predict")
async def predict(data: InputData):
    """
    Accepts financial indicator data and returns the predicted stock value change.
    """
    # Convert incoming Pydantic data to a pandas DataFrame
    # Ensure column order matches the model's training data (X.columns)
    input_df = pd.DataFrame([data.model_dump()])
    input_df = input_df[X.columns] # Ensure correct column order

    # Make prediction
    raw_prediction = model.predict(input_df)

    # Convert numerical prediction back to categorical label
    predicted_label = prediction_mapping.get(raw_prediction[0], "Unknown")

    return {"prediction": predicted_label}


@app.get("/health")
async def health():
    """Lightweight health endpoint returning app and model status."""
    model_present = 'model' in globals() and model is not None
    try:
        n_features = len(X.columns)
    except Exception:
        n_features = None
    return {"status": "ok", "model_loaded": bool(model_present), "n_features": n_features}

# To run this script:
# 1. Save it as predict.py
# 2. Make sure xgboost_model.joblib is in the same directory
# 3. Run: uvicorn predict:app --reload