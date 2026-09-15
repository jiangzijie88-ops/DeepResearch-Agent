"""Offline test defaults: never load developer secrets or call real HTTP APIs."""

import httpx
import pytest
import requests


def pytest_configure(config):
    patch = pytest.MonkeyPatch()
    patch.setenv("PYTHON_DOTENV_DISABLED", "1")
    patch.setenv("LLM_PROVIDER", "openai")
    patch.setenv("OPENAI_API_KEY", "test-key-not-a-real-secret")
    patch.setenv("OPENAI_MODEL", "test-model")
    config._offline_env_patch = patch


def pytest_unconfigure(config):
    patch = getattr(config, "_offline_env_patch", None)
    if patch is not None:
        patch.undo()


@pytest.fixture(autouse=True)
def block_real_http(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("Real HTTP is disabled in pytest; use a fake transport.")

    async def blocked_async(*args, **kwargs):
        raise AssertionError("Real HTTP is disabled in pytest; use a fake transport.")

    monkeypatch.setattr(requests.Session, "request", blocked)
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", blocked)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", blocked_async)
