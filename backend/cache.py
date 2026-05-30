import hashlib
import json
import os
import threading
from pathlib import Path
from typing import Any, Dict, Optional


DEFAULT_CACHE_FILE = Path(__file__).resolve().parent / ".cache" / "analyze_cache.json"
CACHE_FILE = Path(os.getenv("ANALYZE_CACHE_FILE", str(DEFAULT_CACHE_FILE)))

_cache_lock = threading.Lock()
_cache_data: Dict[str, Any] = {}
_cache_loaded = False


def make_cache_key(resume_text: str, job_description: str) -> str:
    resume_hash = hashlib.sha256((resume_text or "").encode("utf-8")).hexdigest()
    jd_hash = hashlib.sha256((job_description or "").encode("utf-8")).hexdigest()
    return f"{resume_hash}:{jd_hash}"


def get_cache(key: str) -> Optional[Dict[str, Any]]:
    ensure_cache_loaded()
    with _cache_lock:
        value = _cache_data.get(key)
        if isinstance(value, dict):
            return value
    return None


def set_cache(key: str, value: Dict[str, Any]) -> None:
    ensure_cache_loaded()
    with _cache_lock:
        _cache_data[key] = value
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        CACHE_FILE.write_text(json.dumps(_cache_data, ensure_ascii=False, indent=2), encoding="utf-8")


def ensure_cache_loaded() -> None:
    global _cache_loaded, _cache_data
    if _cache_loaded:
        return

    with _cache_lock:
        if _cache_loaded:
            return
        if CACHE_FILE.exists():
            try:
                loaded = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    _cache_data = loaded
            except Exception:
                _cache_data = {}
        _cache_loaded = True
