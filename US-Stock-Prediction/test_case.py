import requests
import json
import random
import pandas as pd
from sklearn.impute import SimpleImputer
import openml

# Assuming predict.py is running on localhost:8000
base_url = "http://127.0.0.1:8000"
predict_url = f"{base_url}/predict"
health_url = f"{base_url}/health"

# Re-load X and extract feature types to ensure 'feature_types' is defined
dtype_mapping = {
    'float64': float,
    'int64': int,
    'uint8': int, # Assuming uint8 can be represented as int in Pydantic
}

# Load dataset to get X
dataset = openml.datasets.get_dataset("US_Stocks_Financial_Indicators")
X, y_dummy, categorical_indicator, attribute_names = dataset.get_data(target="class") # y_dummy to avoid overwriting
imputer = SimpleImputer(strategy='median')
X_imputed = imputer.fit_transform(X)
X = pd.DataFrame(X_imputed, columns=X.columns)

feature_types = {}
for column, dtype in X.dtypes.items():
    python_type = dtype_mapping.get(str(dtype), str(dtype))
    feature_types[column] = python_type

# Generate sample input data based on the features defined in InputData model
# All features are expected to be floats
sample_input = {}
for feature_name, dtype in feature_types.items():
    if dtype == float:
        sample_input[feature_name] = random.uniform(0.01, 1000.0) # Generate random float values
    elif dtype == int:
        sample_input[feature_name] = random.randint(0, 100) # Generate random int values
    else:
        sample_input[feature_name] = 0.0 # Default to 0.0 for unknown types

# Convert the sample input to JSON format
json_data = json.dumps(sample_input)
print("Sample Input Data:")
print(json.dumps(sample_input, indent=2))

headers = {'Content-Type': 'application/json'}

try:
    # Check health endpoint first
    h = requests.get(health_url, timeout=5)
    if h.status_code != 200:
        print(f"Health check failed: {h.status_code} - {h.text}")
    else:
        print("Health response:", h.json())

    # Send the POST request to /predict
    response = requests.post(predict_url, data=json_data, headers=headers, timeout=30)
    response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)

    # Print the response
    print("Prediction Response:")
    print(json.dumps(response.json(), indent=2))

except requests.exceptions.ConnectionError:
    print(f"Error: Could not connect to the FastAPI service at {base_url}. Is predict.py running?")
except requests.exceptions.RequestException as e:
    print(f"An error occurred during the request: {e}")