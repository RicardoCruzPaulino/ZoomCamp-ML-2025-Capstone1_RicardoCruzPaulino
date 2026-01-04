import pandas as pd
import numpy as np
import openml
from sklearn.impute import SimpleImputer
from sklearn.model_selection import train_test_split
from imblearn.over_sampling import SMOTE
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier
import joblib
from sklearn.pipeline import Pipeline

print("Starting model training script...")

# 1. Load the dataset
print("Loading dataset 'US_Stocks_Financial_Indicators' from OpenML...")
dataset = openml.datasets.get_dataset("US_Stocks_Financial_Indicators")
X, y, categorical_indicator, attribute_names = dataset.get_data(target="class")

# 2. Preprocess the target variable y
y = pd.Series(y, name='class', dtype='category')
# Explicitly set categories to ensure 'stock_value_decrease' maps to 0 and 'stock_value_increase' maps to 1
y = y.cat.set_categories(['stock_value_decrease', 'stock_value_increase'])
print("Dataset loaded and target variable preprocessed.")

# 3. Perform median imputation on X
print("Performing median imputation on features (X)...")
imputer = SimpleImputer(strategy='median')
X_imputed = imputer.fit_transform(X)
X = pd.DataFrame(X_imputed, columns=X.columns)
print("Imputation complete.")

# 4. Split data into training, validation, and testing sets (60-20-20 split)
print("Splitting data into 60% training, 20% validation, 20% testing sets (stratified)...")
X_train, X_temp, y_train, y_temp = train_test_split(X, y, test_size=0.4, random_state=42, stratify=y)
X_val, X_test, y_val, y_test = train_test_split(X_temp, y_temp, test_size=0.5, random_state=42, stratify=y_temp)
print(f"X_train shape: {X_train.shape}, y_train shape: {y_train.shape}")
print(f"X_val shape: {X_val.shape}, y_val shape: {y_val.shape}")
print(f"X_test shape: {X_test.shape}, y_test shape: {y_test.shape}")

# 5. Apply SMOTE to X_train and y_train
print("Applying SMOTE to the training data to address class imbalance...")
smote = SMOTE(random_state=42)
X_train_resampled, y_train_resampled = smote.fit_resample(X_train, y_train)
print("SMOTE application complete. Resampled training class distribution:")
print(y_train_resampled.value_counts())

# 6. Numerically encode the resampled target variable for XGBoost
y_train_resampled_encoded = y_train_resampled.cat.codes
print("Target variable for training encoded numerically for XGBoost.")

# 7. Define the XGBoost Classifier pipeline with the best hyperparameters
# Best parameters found during GridSearchCV for XGBClassifier:
# {'classifier__gamma': 0, 'classifier__learning_rate': 0.01, 'classifier__max_depth': 3, 'classifier__n_estimators': 100}
print("Defining XGBoost Classifier pipeline with best hyperparameters...")
pipeline = Pipeline([
    ('scaler', StandardScaler()),  # Scale features
    ('classifier', XGBClassifier(
        gamma=0,
        learning_rate=0.01,
        max_depth=3,
        n_estimators=100,
        random_state=42,
        eval_metric='logloss'     # Suppress deprecation warning
    ))
])
print("XGBoost pipeline created.")

# 8. Train the model using the resampled and encoded training data
print("Training XGBoost Classifier with best hyperparameters on resampled data...")
pipeline.fit(X_train_resampled, y_train_resampled_encoded)
print("Model training complete.")

# 9. Save the trained model to a joblib file
model_filename = 'xgboost_model.joblib'
print(f"Saving the trained model as '{model_filename}'...")
joblib.dump(pipeline, model_filename)
print(f"Trained model successfully saved as '{model_filename}'.")

print("Model training script finished.")