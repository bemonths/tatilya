import httpx
import pytest


@pytest.fixture(autouse=True)
def no_real_http(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Test gerçek HTTP ağına bağlanmaya çalıştı; MockTransport kullanın.")
    async def async_forbidden(*args, **kwargs):
        raise AssertionError("Test gerçek HTTP ağına bağlanmaya çalıştı; ASGITransport kullanın.")
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbidden)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", async_forbidden)
