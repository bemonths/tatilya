"""Internal diagnostics: sanitized message and traceback locations, without locals."""
import re
import traceback
from pathlib import Path


def safe_message(message):
    # Redact before truncation, so a secret crossing the limit is not partially saved.
    message = re.sub(r"(?i)(\b[a-z][a-z0-9+.-]*://)[^\s/]+@", r"\1[REDACTED]@", message)
    message = re.sub(r"(?i)\bBearer\s+[^\s\"',;<>]+", "Bearer [REDACTED]", message)
    message = re.sub(
        r"(?i)([\"']?\b(?:password|passwd|token|access_token|refresh_token|api[_-]?key|authorization)\b[\"']?\s*[:=]\s*)"
        r"(?:\"[^\"]*\"|'[^']*'|[^\s,;&<>]+)",
        r"\1[REDACTED]", message)
    message = re.sub(r"\b(?:ghp_|github_pat_|sk-)[a-zA-Z0-9_-]+", "[REDACTED]", message)
    return message[:500]


def diagnostic(exc):
    frames = traceback.extract_tb(exc.__traceback__)
    return {
        "exception_type": type(exc).__name__,
        "technical_message": safe_message(str(exc)),
        "traceback": [{"file": Path(frame.filename).name, "line": frame.lineno,
                       "function": frame.name} for frame in frames[-20:]],
    }
