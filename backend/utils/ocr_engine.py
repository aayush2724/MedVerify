"""
OCR Engine
Wraps Tesseract OCR with optional Google Vision API fallback.
Supports English and Hindi (eng+hin) for Indian medical certificates.
"""
import logging
import os

import cv2
import numpy as np
import pytesseract
from PIL import Image

logger = logging.getLogger(__name__)


# Auto-detect Tesseract on Windows
if os.name == 'nt':
    _win_tesseract_paths = [
        r'C:\Program Files\Tesseract-OCR\tesseract.exe',
        r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
        os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Programs', 'Tesseract-OCR', 'tesseract.exe'),
    ]
    for _path in _win_tesseract_paths:
        if os.path.isfile(_path):
            pytesseract.pytesseract.tesseract_cmd = _path
            logger.info(f"Found Tesseract at: {_path}")
            break



class OCREngine:
    def __init__(
        self,
        use_google_vision: bool = False,
        lang: str = "eng",
    ):
        # Support bilingual certificates (e.g. "eng+hin")
        self.lang = lang
        self.use_google_vision = use_google_vision and bool(
            os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        )

    def extract_text(self, image: np.ndarray) -> str:
        """Extract text from a preprocessed OpenCV image."""
        if self.use_google_vision:
            try:
                return self._google_vision_ocr(image)
            except Exception as exc:
                logger.warning("Google Vision OCR failed (%s), falling back to Tesseract.", exc)
        try:
            return self._tesseract_ocr(image)
        except Exception as exc:
            logger.warning("Tesseract OCR unavailable (%s); returning empty text.", exc)
            return ""

    def _tesseract_ocr(self, image: np.ndarray) -> str:
        """Tesseract OCR with binarisation pre-step."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        pil_image = Image.fromarray(thresh)
        config = "--oem 3 --psm 6"
        text: str = pytesseract.image_to_string(pil_image, lang=self.lang, config=config)
        return text.strip()

    def _google_vision_ocr(self, image: np.ndarray) -> str:
        """Google Cloud Vision API OCR (higher accuracy for poor scans)."""
        from google.cloud import vision  # noqa: PLC0415

        client = vision.ImageAnnotatorClient()
        _, buffer = cv2.imencode(".png", image)
        content = buffer.tobytes()
        vision_image = vision.Image(content=content)
        response = client.text_detection(image=vision_image)
        if response.error.message:
            raise RuntimeError(f"Google Vision error: {response.error.message}")
        texts = response.text_annotations
        return texts[0].description if texts else ""

    def extract_text_with_positions(self, image: np.ndarray) -> list:
        """Returns a list of word dicts with bounding-box positions."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        pil_image = Image.fromarray(gray)
        data = pytesseract.image_to_data(pil_image, output_type=pytesseract.Output.DICT)
        words = []
        for i, text in enumerate(data["text"]):
            if text.strip():
                words.append(
                    {
                        "text": text,
                        "left": data["left"][i],
                        "top": data["top"][i],
                        "width": data["width"][i],
                        "height": data["height"][i],
                        "conf": data["conf"][i],
                    }
                )
        return words
