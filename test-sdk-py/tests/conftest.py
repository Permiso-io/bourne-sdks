"""Shared HTTP capture for usability tests (no real network)."""

from __future__ import annotations

import json
from collections.abc import Iterator
from unittest.mock import MagicMock, patch

import pytest

from permiso_custom_hooks import PermisoCustomHooksConfig


def _ok_response() -> MagicMock:
    resp = MagicMock()
    resp.status = 200
    resp.read.return_value = json.dumps({}).encode("utf-8")
    resp.__enter__ = MagicMock(return_value=resp)
    resp.__exit__ = MagicMock(return_value=False)
    return resp


@pytest.fixture
def base_config() -> PermisoCustomHooksConfig:
    return PermisoCustomHooksConfig(api_key="test-key", base_url="https://api.example.com")


@pytest.fixture
def captured_http() -> Iterator[list[dict]]:
    store: list[dict] = []

    def _side_effect(request: MagicMock) -> MagicMock:
        store.append(json.loads(request.data.decode("utf-8")))
        return _ok_response()

    with patch("urllib.request.urlopen", side_effect=_side_effect):
        yield store
