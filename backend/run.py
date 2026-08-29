"""
Development entry point.
For production, use gunicorn: gunicorn "app:create_app()" -c gunicorn.conf.py
"""
import os
import sys

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from app import create_app
from app.config import DevelopmentConfig, config_by_name

# The fallback has to be a config *class*. Falling back to the string
# "development" would hand `app.config.from_object` a name it cannot resolve,
# so an unrecognised FLASK_ENV would fail at boot instead of degrading to dev.
env = os.environ.get("FLASK_ENV", "development")
app = create_app(config_by_name.get(env, DevelopmentConfig))

if __name__ == "__main__":
    # debug=True is acceptable for local dev only.
    # In production FLASK_ENV=production disables this path entirely.
    app.run(
        debug=app.config.get("DEBUG", False),
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        use_reloader=True,
    )
