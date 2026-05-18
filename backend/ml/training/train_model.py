"""
Model Training Script
Train and save a scikit-learn classifier on labelled certificate features.

Usage:
    python -m ml.training.train_model --data data/features.csv --output ml/models/classifier.pkl
"""

import argparse
import pickle
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report, confusion_matrix
import os


FEATURE_COLUMNS = [
    'text_authenticity_score',
    'image_authenticity_score',
    'has_dates',
    'has_registration_number',
    'has_hospital_name',
    'has_doctor_name',
    'diagnosis_count',
    'ela_score',
    'noise_inconsistency_score',
    'copy_move_detected',
    'font_consistency_score',
    'has_phone_number',
    'unusual_char_ratio',
    'text_length',
    'ela_suspicious_regions',
    'metadata_software_detected',
]
LABEL_COLUMN = 'label'  # 1 = genuine, 0 = fake


def load_data(csv_path: str):
    df = pd.read_csv(csv_path)
    X = df[FEATURE_COLUMNS].fillna(0).values
    y = df[LABEL_COLUMN].values
    return X, y


def build_model():
    pipeline = Pipeline([
        ('scaler', StandardScaler()),
        ('clf', GradientBoostingClassifier(n_estimators=100, max_depth=4, random_state=42))
    ])
    return pipeline


def train(data_path: str, output_path: str):
    print(f"Loading data from {data_path}")
    X, y = load_data(data_path)

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    model = build_model()
    print("Training model...")
    model.fit(X_train, y_train)

    cv_scores = cross_val_score(model, X_train, y_train, cv=5, scoring='f1')
    print(f"Cross-validation F1: {cv_scores.mean():.3f} ± {cv_scores.std():.3f}")

    y_pred = model.predict(X_test)
    print("\nTest Set Results:")
    print(classification_report(y_test, y_pred, target_names=['Fake', 'Genuine']))
    print("Confusion Matrix:")
    print(confusion_matrix(y_test, y_pred))

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'wb') as f:
        pickle.dump(model, f)
    print(f"\nModel saved to {output_path}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Train certificate classifier')
    parser.add_argument('--data', required=True, help='Path to features CSV')
    parser.add_argument('--output', default='ml/models/classifier.pkl', help='Output model path')
    args = parser.parse_args()
    train(args.data, args.output)
