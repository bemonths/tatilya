"""Hata nesnesinin mesajını/yerel değişkenlerini kaydetmeden teşhis bilgisi."""
import traceback
from pathlib import Path


def diagnostic(exc):
    frames = traceback.extract_tb(exc.__traceback__)
    # Exception mesajları, kaynak satırı, tam dosya yolları ve locals sır içerebilir.
    return {
        "exception_type": type(exc).__name__,
        "technical_message": "Beklenmeyen hata; konumlar için traceback alanına bakın.",
        "traceback": [{"file": Path(frame.filename).name, "line": frame.lineno,
                       "function": frame.name} for frame in frames[-20:]],
    }
