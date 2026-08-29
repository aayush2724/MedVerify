import multiprocessing
import os

bind = f"0.0.0.0:{os.environ.get('PORT', '5000')}"

# Each worker loads spaCy, scikit-learn and OpenCV into its own address space —
# roughly 300-400 MB apiece. The usual (2 x cores + 1) rule assumes cheap
# workers and will exhaust the RAM of a small VPS here, so the default is
# modest and deliberately overridable per host.
_default_workers = min(3, multiprocessing.cpu_count() * 2 + 1)
workers = int(os.environ.get("WEB_CONCURRENCY", _default_workers))

worker_class = "sync"
timeout = int(os.environ.get("GUNICORN_TIMEOUT", "180"))  # OCR + live drug lookups
graceful_timeout = 30
keepalive = 5
max_requests = 1000        # recycle workers to bound memory growth
max_requests_jitter = 100
preload_app = False        # each worker loads its own model; preload forks badly with OpenCV
accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("LOG_LEVEL", "info")
