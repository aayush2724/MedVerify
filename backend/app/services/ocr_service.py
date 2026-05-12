import logging
from utils.ocr_engine import OCREngine
from app.errors import OCRError

logger = logging.getLogger(__name__)

class OCRService:
    def __init__(self):
        self.engine = OCREngine()

    def extract(self, processed_image):
        try:
            text = self.engine.extract_text(processed_image)
            if not text or len(text.strip()) < 10:
                raise OCRError("Insufficient text extracted.", error_code="INSUFFICIENT_TEXT", retryable=False)
            return text
        except OCRError:
            raise
        except Exception as exc:
            logger.exception("OCR failed")
            raise OCRError(f"OCR error: {exc}")
