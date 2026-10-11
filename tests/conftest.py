import os

import httpx
import keyring
import pytest
from keyring.backend import KeyringBackend
from keyring.errors import PasswordDeleteError


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


REAL_HANDLE_REQUEST = httpx.HTTPTransport.handle_request
LOCAL = ("127.0.0.1", "localhost")


@pytest.fixture(autouse=True)
def no_real_http(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Test gerçek HTTP ağına bağlanmaya çalıştı; MockTransport kullanın.")
    async def async_forbidden(*args, **kwargs):
        raise AssertionError("Test gerçek HTTP ağına bağlanmaya çalıştı; ASGITransport kullanın.")
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbidden)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", async_forbidden)


@pytest.fixture
def local_network(monkeypatch):
    """GÖREV-16: a test that needs a local fake proxy (or a local page) may connect to 127.0.0.1 only: through a proxy on 127.0.0.1, or
    straight to 127.0.0.1. Anything else is still refused."""
    def local_only(self, request):
        proxy = getattr(getattr(self, "_pool", None), "_proxy_url", None)
        host = proxy.host.decode("ascii") if proxy is not None else request.url.host
        if host not in LOCAL:
            raise AssertionError(f"Test yerel olmayan bir adrese bağlanmaya çalıştı: {host}")
        return REAL_HANDLE_REQUEST(self, request)
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", local_only)


class MemoryKeyring(KeyringBackend):
    """GÖREV-16: tests never touch Windows Credential Manager; secrets live in memory for one test."""

    priority = 1

    def __init__(self):
        super().__init__()
        self.values = {}

    def get_password(self, service, username):
        return self.values.get((service, username))

    def set_password(self, service, username, password):
        self.values[(service, username)] = password

    def delete_password(self, service, username):
        if (service, username) not in self.values:
            raise PasswordDeleteError("yok")
        del self.values[(service, username)]


@pytest.fixture(autouse=True)
def memory_keyring():
    previous = keyring.core._keyring_backend
    backend = MemoryKeyring()
    keyring.set_keyring(backend)
    yield backend
    keyring.core._keyring_backend = previous
