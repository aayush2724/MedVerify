import os
import json
import logging
import joblib
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class CertificateClassifier:
    _instance = None

    @classmethod
    def get_instance(cls, model_path: str, thresholds: Optional[Dict[str, float]] = None):
        if cls._instance is None:
            cls._instance = cls(model_path, thresholds=thresholds)
        return cls._instance

    def __init__(self, model_path: str = "", thresholds: Optional[Dict[str, float]] = None):
        self.model_path = model_path
        self.thresholds = thresholds or {"genuine": 0.75, "suspicious": 0.45}
        self.model = None
        self.metadata = {}
        
        if model_path and os.path.exists(model_path):
            self._load_model(model_path)

    def _load_model(self, model_path: str) -> None:
        try:
            self.model = joblib.load(model_path)
            
            # Load metadata if exists
            meta_path = f"{model_path}.meta.json"
            if os.path.exists(meta_path):
                with open(meta_path, 'r') as f:
                    self.metadata = json.load(f)
                logger.info("Loaded ML model metadata from %s", meta_path)
            
            logger.info("Loaded ML model version %s from %s", self.metadata.get('version', 'unknown'), model_path)
        except Exception as exc:
            logger.error("Failed to load model from %s: %s", model_path, exc)
            self.model = None

    def classify(self, features: Dict[str, Any]) -> Dict[str, Any]:
        confidence = 0.5
        if self.model is not None:
            try:
                feature_vector = self._build_feature_vector(features)
                proba = self.model.predict_proba([feature_vector])[0]
                confidence = float(proba[1])  # P(genuine)
            except Exception as exc:
                logger.warning("Model inference failed (%s) — using rule-based fallback.", exc)
                confidence = self._fallback_score(features)
        else:
            confidence = self._fallback_score(features)

        if confidence >= self.thresholds["genuine"]:
            status = "GENUINE"
        elif confidence >= self.thresholds["suspicious"]:
            status = "SUSPICIOUS"
        else:
            status = "FAKE"

        reasons = features.get("flags", [])
        if not reasons:
            reasons = ["No significant issues detected"]

        return {
            "status": status,
            "confidence": confidence,
            "reasons": reasons,
            "model_version": self.metadata.get('version', 'v1.0.0'),
            "features_used": features
        }

    def predict(self, text_features: Dict[str, Any], image_features: Dict[str, Any]) -> Dict[str, Any]:
        """Backward-compatible prediction API used by older tests and callers."""
        combined = {
            **text_features,
            **image_features,
            "flags": [
                *text_features.get("flags", []),
                *image_features.get("flags", []),
            ],
        }
        return self.classify(combined)

    def _fallback_score(self, features: Dict[str, Any]) -> float:
        text_score = float(features.get("text_authenticity_score", 0.5))
        image_score = float(features.get("image_authenticity_score", 0.5))
        return round(0.5 * text_score + 0.5 * image_score, 2)

    def _build_feature_vector(self, features: Dict[str, Any]) -> List[float]:
        # Expanded feature vector (11 + new ones)
        return [
            float(features.get("text_authenticity_score", 0.0)),
            float(features.get("image_authenticity_score", 0.0)),
            1.0 if features.get("has_dates") else 0.0,
            1.0 if features.get("has_registration_number") else 0.0,
            1.0 if features.get("has_hospital_name") else 0.0,
            1.0 if features.get("has_doctor_name") else 0.0,
            float(features.get("diagnosis_count", 0)),
            float(features.get("ela_score", 0.0)),
            float(features.get("noise_inconsistency_score", 0.0)),
            1.0 if features.get("copy_move_detected") else 0.0,
            float(features.get("font_consistency_score", 1.0)),
            # New features
            1.0 if features.get("has_phone_number") else 0.0,
            float(features.get("unusual_char_ratio", 0.0)),
            min(float(features.get("text_length", 0)) / 5000.0, 1.0),
            float(features.get("ela_suspicious_regions", 0)),
            1.0 if features.get("metadata_software_detected") else 0.0
        ]
