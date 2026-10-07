import os

import httpx
import pytest


def _annotation(text):
    # GitHub workflow command data must stay on one line.
    return text.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


@pytest.hookimpl(trylast=True)
def pytest_terminal_summary(terminalreporter):
    """On GitHub Actions also list failing tests as annotations; job logs need a signed-in viewer, annotations do not."""
    if os.environ.get("GITHUB_ACTIONS") != "true":
        return
    for report in terminalreporter.stats.get("failed", []) + terminalreporter.stats.get("error", []):
        lines = [line for line in (report.longreprtext or "").splitlines() if line.strip()]
        errors = [line[1:].strip() for line in lines if line.startswith("E ")]
        detail = " | ".join(part for part in (errors[0] if errors else "", lines[-1] if lines else report.outcome) if part)
        terminalreporter.write_line(f"::error::{_annotation(f'{report.nodeid} ({report.when}): {detail}'[:900])}")


@pytest.fixture(autouse=True)
def no_real_http(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Test gerçek HTTP ağına bağlanmaya çalıştı; MockTransport kullanın.")
    async def async_forbidden(*args, **kwargs):
        raise AssertionError("Test gerçek HTTP ağına bağlanmaya çalıştı; ASGITransport kullanın.")
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbidden)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", async_forbidden)
