import os

os.environ.setdefault("DJANGO_SECRET_KEY", "test-only-insecure-key")

from .settings import *  # noqa: E402, F403

# Per-process memory cache so tests never read or wipe the dev server's file cache.
CACHES = {
    alias: {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": alias} for alias in CACHES  # noqa: F405
}
