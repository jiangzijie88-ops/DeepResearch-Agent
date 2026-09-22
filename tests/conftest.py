"""Offline test defaults: never load developer secrets or call real HTTP APIs."""

import sys
from pathlib import Path

import httpx
import pytest
import requests


# 将项目根目录加入 Python 模块搜索路径。
# 保证 pytest 可以正常导入：
# models
# workflow
# workers
# tools
PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )


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
