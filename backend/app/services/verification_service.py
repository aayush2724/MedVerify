import os
import time
from concurrent.futures import ThreadPoolExecutor
from ..repositories.verification_repository import VerificationRepository
from ..repositories.audit_repository import AuditRepository
from ..errors import ProcessingError, OCR_EMPTY_RESULT, MODEL_INFERENCE_FAILED
from ..models import VerificationRecord

# Mocking imports based on project structure — actual imports might need adjustment
from ml.classifier import CertificateClassifier
from preprocessing.document_processor import DocumentProcessor
from utils.ocr_engine import OCREngine
from utils.text_analyzer import TextAnalyzer
from utils.image_analyzer import ImageAnalyzer

class VerificationService:
    _executor = ThreadPoolExecutor(max_workers=4)

    def __init__(self, db_session, model_path, model_version):
        self.repo = VerificationRepository(db_session)
        self.audit = AuditRepository(db_session)
        self.classifier = CertificateClassifier.get_instance(model_path)
        self.model_version = model_version
        self.thresholds = getattr(self.classifier, "thresholds", {"genuine": 0.75, "suspicious": 0.45})
        
        # Initialize engines once
        self.processor = DocumentProcessor()
        self.ocr = OCREngine()
        self.text_analyzer = TextAnalyzer()
        self.image_analyzer = ImageAnalyzer()

    def verify(self, filepath: str, original_filename: str, 
               user_id: str = None, ip_address: str = None) -> VerificationRecord:
        start_time = time.time()
        
        try:
            # 1. Run Pipeline
            results = self._run_pipeline(filepath)
            
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            # 2. Persist Result
            record_data = {
                "user_id": user_id,
                "filename": os.path.basename(filepath),
                "original_filename": original_filename,
                "extracted_text": results["extracted_text"],
                "status": results["classification"]["status"],
                "confidence": results["classification"]["confidence"],
                "confidence_threshold_used": self._threshold_for_status(results["classification"]["status"]),
                "reasons": results["classification"]["reasons"],
                "extracted_fields": results["analysis"]["text"].get("extracted_fields", {}),
                "text_score": results["analysis"]["text"].get("text_authenticity_score", 0),
                "image_score": results["analysis"]["image"].get("image_authenticity_score", 0),
                "ml_features": results["features"],
                "feature_extraction_metadata": {
                    "pipeline_timings": results["timings"],
                    "feature_count": len(results["features"]),
                    "text_length": len(results["extracted_text"] or ""),
                },
                "model_version": self.model_version,
                "processing_time_ms": processing_time_ms
            }
            
            record = self.repo.create(record_data)
            
            # 3. Audit Log
            self.audit.log(
                user_id=user_id,
                action='VERIFY',
                resource_type='VerificationRecord',
                resource_id=record.id,
                ip_address=ip_address,
                confidence_threshold_used=record.confidence_threshold_used,
                model_version=record.model_version,
                details={
                    "status": record.status,
                    "confidence": record.confidence,
                    "processing_time_ms": record.processing_time_ms,
                    "pipeline_timings": results["timings"],
                }
            )
            
            return record

        except Exception as e:
            # Audit the failure too
            self.audit.log(
                user_id=user_id,
                action='VERIFY_FAILED',
                ip_address=ip_address,
                model_version=self.model_version,
                details={"error": str(e), "filename": original_filename}
            )
            if isinstance(e, ProcessingError):
                raise e
            raise ProcessingError("VERIFICATION_PIPELINE_FAILED", str(e))

    def _run_pipeline(self, filepath: str) -> dict:
        timings = {}
        
        # Step 1: Preprocess
        s1 = time.time()
        processed_img = self.processor.preprocess(filepath)
        timings['preprocess'] = time.time() - s1
        
        # Step 2: OCR
        s2 = time.time()
        extracted_text = self.ocr.extract_text(processed_img)
        if not extracted_text or not extracted_text.strip():
            extracted_text = ""
        timings['ocr'] = time.time() - s2
        
        # Step 3: Parallel Analysis
        s3 = time.time()
        future_text = self._executor.submit(self.text_analyzer.analyze, extracted_text)
        future_image = self._executor.submit(self.image_analyzer.analyze, filepath)
        
        text_results = future_text.result()
        image_results = future_image.result()
        timings['analysis'] = time.time() - s3
        
        # Step 4: Classify
        s4 = time.time()
        # Build feature dict from the actual keys returned by each analyzer
        extracted_fields = text_results.get("extracted_fields", {})
        features = {
            # Text features
            "text_authenticity_score": text_results.get("text_authenticity_score", 0.0),
            "has_dates": bool(extracted_fields.get("dates")),
            "has_registration_number": bool(extracted_fields.get("registration_numbers")),
            "has_hospital_name": bool(extracted_fields.get("hospital_name")),
            "has_doctor_name": bool(extracted_fields.get("doctor_name")),
            "diagnosis_count": len(extracted_fields.get("diagnosis_keywords", [])),
            "has_phone_number": bool(extracted_fields.get("phone_numbers")),
            "text_length": text_results.get("raw_text_length", 0),
            "unusual_char_ratio": (
                len([c for c in (extracted_text or "") if ord(c) > 127])
                / max(len(extracted_text or ""), 1)
            ),
            # Image features
            "image_authenticity_score": image_results.get("image_authenticity_score", 0.0),
            "ela_score": image_results.get("ela_score", 0.0),
            "ela_suspicious_regions": image_results.get("ela_suspicious_regions", 0),
            "noise_inconsistency_score": image_results.get("noise_inconsistency_score", 0.0),
            "copy_move_detected": image_results.get("copy_move_detected", False),
            "font_consistency_score": image_results.get("font_consistency_score", 1.0),
            "metadata_software_detected": bool(image_results.get("metadata_flags")),
            # Combined flags for rule-based fallback
            "flags": text_results.get("flags", []) + image_results.get("flags", []),
        }
        classification = self.classifier.classify(features)
        timings['classify'] = time.time() - s4
        
        return {
            "extracted_text": extracted_text,
            "analysis": {
                "text": text_results,
                "image": image_results
            },
            "features": features,
            "classification": classification,
            "timings": timings
        }

    def _threshold_for_status(self, status: str) -> float:
        if status == "GENUINE":
            return float(self.thresholds.get("genuine", 0.75))
        if status == "SUSPICIOUS":
            return float(self.thresholds.get("suspicious", 0.45))
        return 0.0

    def get_record(self, record_id: str, user_id: str = None) -> VerificationRecord:
        record = self.repo.get_by_id_for_user(record_id, user_id) if user_id else self.repo.get_by_id(record_id)
        if not record:
            from ..errors import NotFoundError, RECORD_NOT_FOUND
            raise NotFoundError(RECORD_NOT_FOUND, f"Record {record_id} not found")
        return record

    def list_records(self, **filters) -> list:
        return self.repo.get_all(**filters)

    def get_dashboard_stats(self) -> dict:
        return self.repo.get_stats()
