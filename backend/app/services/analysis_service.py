import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from utils.text_analyzer import TextAnalyzer
from utils.image_analyzer import ImageAnalyzer
from app.errors import AnalysisError

logger = logging.getLogger(__name__)

class AnalysisService:
    def __init__(self, max_workers=2):
        self._executor = ThreadPoolExecutor(max_workers=max_workers)

    def analyze(self, filepath, extracted_text):
        text_features = {}
        image_features = {}
        errors = []

        def _text_task():
            return TextAnalyzer().analyze(extracted_text)

        def _image_task():
            return ImageAnalyzer().analyze(filepath)

        futures = {
            self._executor.submit(_text_task): "text",
            self._executor.submit(_image_task): "image",
        }

        for future in as_completed(futures):
            task_name = futures[future]
            try:
                result = future.result()
                if task_name == "text":
                    text_features.update(result)
                else:
                    image_features.update(result)
            except Exception as exc:
                logger.exception("%s analysis failed", task_name)
                errors.append(f"{task_name} analysis failed: {exc}")

        if not text_features and not image_features:
            raise AnalysisError("All analysis modules failed.")

        return text_features, image_features, errors
