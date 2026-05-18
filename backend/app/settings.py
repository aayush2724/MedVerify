"""
Runtime settings manager.
Persists adjustable config (e.g. confidence thresholds) to a JSON file so
changes survive backend restarts without requiring a DB migration.
"""
import json
import os
import threading
import logging

logger = logging.getLogger(__name__)

_SETTINGS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "runtime_settings.json")
_lock = threading.Lock()

_DEFAULTS = {
    "confidence_threshold_genuine": 0.75,
    "confidence_threshold_suspicious": 0.45,
}


def _load() -> dict:
    if os.path.exists(_SETTINGS_PATH):
        try:
            with open(_SETTINGS_PATH, "r") as f:
                data = json.load(f)
                return {**_DEFAULTS, **data}
        except Exception as exc:
            logger.warning("Could not read runtime settings: %s", exc)
    return dict(_DEFAULTS)


def _save(data: dict) -> None:
    try:
        with open(_SETTINGS_PATH, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as exc:
        logger.error("Could not write runtime settings: %s", exc)


def get_thresholds() -> dict:
    with _lock:
        s = _load()
        return {
            "genuine": s["confidence_threshold_genuine"],
            "suspicious": s["confidence_threshold_suspicious"],
        }


def set_thresholds(genuine: float, suspicious: float) -> dict:
    genuine = round(max(0.0, min(1.0, float(genuine))), 3)
    suspicious = round(max(0.0, min(genuine - 0.01, float(suspicious))), 3)
    with _lock:
        s = _load()
        s["confidence_threshold_genuine"] = genuine
        s["confidence_threshold_suspicious"] = suspicious
        _save(s)
    return {"genuine": genuine, "suspicious": suspicious}
