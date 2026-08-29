# Built from the REPOSITORY ROOT, not from backend/.
#
#     docker build -f backend/Dockerfile .
#
# `app/errors.py` imports `shared.constants.error_codes`, and `shared/` is a
# sibling of `backend/`. A backend-scoped context cannot see it, so the image
# would build fine and then crash on the first import.
FROM python:3.11-slim

# System dependencies for OpenCV, Tesseract, and the container healthcheck.
#
# libgl1 is not optional despite requirements.txt asking for
# opencv-python-headless: rapidocr-onnxruntime depends on the *full*
# opencv-python, pip installs both, and the non-headless build wins the `cv2`
# import — which needs libGL.so.1. Without this the image builds cleanly and
# then dies on the first import.
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-hin \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgl1 \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Dependencies first: this layer stays cached across code changes, and the
# spaCy model download is slow enough that re-running it on every build hurts.
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && python -m spacy download en_core_web_sm

COPY backend/ .
COPY shared/ ./shared/

# The uploads directory is a mount point for a named volume in production. It
# is created and owned here so the non-root user can still write to it when the
# volume is empty on first boot.
RUN mkdir -p /app/uploads \
    && adduser --disabled-password --gecos "" appuser \
    && chown -R appuser:appuser /app
USER appuser

ENV FLASK_ENV=production \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

EXPOSE 5000

# Liveness only — a database blip must not get a healthy container killed.
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD curl -fsS http://localhost:5000/api/health || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", "run:app", "-c", "gunicorn.conf.py"]
