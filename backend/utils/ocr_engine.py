"""
OCR Engine
Text extraction with a three-tier engine chain, tried in order:

    Google Vision (opt-in)  ->  Tesseract  ->  RapidOCR (ONNX)

RapidOCR matters because it is pip-installable and needs no system binary. On a
host without Tesseract, Tesseract's failure used to be swallowed and this class
returned an empty string, which silently drove every document's text score to
zero and made the whole pipeline classify genuine documents as fake. The chain
now falls through to a working engine instead, and `last_engine` records which
one produced the text so a result stays explainable.

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



# RapidOCR loads ~15 MB of ONNX models, so build it once per process.
_rapid_ocr = None
_RAPID_AVAILABLE = None


def _get_rapid_ocr():
    global _rapid_ocr, _RAPID_AVAILABLE
    if _RAPID_AVAILABLE is None:
        try:
            from rapidocr_onnxruntime import RapidOCR  # noqa: PLC0415
            _rapid_ocr = RapidOCR()
            _RAPID_AVAILABLE = True
            logger.info("RapidOCR engine initialised.")
        except Exception as exc:
            logger.warning("RapidOCR unavailable: %s", exc)
            _RAPID_AVAILABLE = False
    return _rapid_ocr


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
        self.last_engine = None

    def extract_text(self, image: np.ndarray) -> str:
        """Extract text from a preprocessed OpenCV image.

        Walks the engine chain until one returns usable text. An engine that
        returns only whitespace counts as a failure, not a result — otherwise a
        half-working engine would mask a working one further down the chain.
        """
        self.last_engine = None
        errors = []

        if self.use_google_vision:
            try:
                text = self._google_vision_ocr(image)
                if text and text.strip():
                    self.last_engine = "google_vision"
                    return text
            except Exception as exc:
                errors.append(f"google_vision: {exc}")
                logger.warning("Google Vision OCR failed (%s), trying Tesseract.", exc)

        try:
            text = self._tesseract_ocr(image)
            if text and text.strip():
                self.last_engine = "tesseract"
                return text
            errors.append("tesseract: returned no text")
        except Exception as exc:
            errors.append(f"tesseract: {exc}")
            logger.info("Tesseract unavailable (%s), falling back to RapidOCR.", exc)

        try:
            text = self._rapid_ocr(image)
            if text and text.strip():
                self.last_engine = "rapidocr"
                return text
            errors.append("rapidocr: returned no text")
        except Exception as exc:
            errors.append(f"rapidocr: {exc}")
            logger.warning("RapidOCR failed: %s", exc)

        logger.error("All OCR engines failed or returned nothing: %s", "; ".join(errors))
        return ""

    def _rapid_ocr(self, image: np.ndarray) -> str:
        """RapidOCR (PaddleOCR models via ONNX) — no system binary required."""
        engine = _get_rapid_ocr()
        if engine is None:
            raise RuntimeError("RapidOCR is not installed")

        result, _ = engine(image)
        if not result:
            return ""
        # Each row is [box, text, confidence]; keep reading order as returned.
        return "\n".join(row[1] for row in result if len(row) > 1 and row[1]).strip()

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
