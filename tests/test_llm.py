from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from dicom_insight import analyze_file
from dicom_insight.llm import GeminiError, GeminiProvider


def _fake_gemini_response(monkeypatch: pytest.MonkeyPatch, captured: dict[str, Any], text: str) -> None:
    def fake_post(
        url: str, *, headers: dict[str, str], json: dict[str, Any], timeout: float
    ) -> httpx.Response:
        captured["url"] = url
        captured["headers"] = headers
        captured["payload"] = json
        response = httpx.Response(
            status_code=200,
            json={"candidates": [{"content": {"parts": [{"text": text}]}}]},
            request=httpx.Request("POST", url),
        )
        return response

    monkeypatch.setattr(httpx, "post", fake_post)


def test_api_key_is_not_exposed_in_repr() -> None:
    provider = GeminiProvider(api_key="super-secret-key")
    assert "super-secret-key" not in repr(provider)


def test_query_uses_header_not_url(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}
    _fake_gemini_response(monkeypatch, captured, "> [!NOTE]\nLooks fine.")

    provider = GeminiProvider(api_key="super-secret-key")
    result = provider._query_gemini("system", "user")

    assert result == "> [!NOTE]\nLooks fine."
    assert "super-secret-key" not in captured["url"]
    assert captured["headers"]["x-goog-api-key"] == "super-secret-key"


def test_summarize_success_path(monkeypatch: pytest.MonkeyPatch, dicom_file) -> None:
    captured: dict[str, Any] = {}
    _fake_gemini_response(monkeypatch, captured, "> [!NOTE]\nUnremarkable study.")

    provider = GeminiProvider(api_key="k")
    report = analyze_file(dicom_file, provider=provider)

    assert report.ai_summary == "> [!NOTE]\nUnremarkable study."
    assert not report.warnings


def test_gemini_error_on_http_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_post(*args: Any, **kwargs: Any) -> httpx.Response:
        raise httpx.ConnectError("boom")

    monkeypatch.setattr(httpx, "post", fake_post)
    provider = GeminiProvider(api_key="k")
    with pytest.raises(GeminiError):
        provider._query_gemini("system", "user")


def test_summarize_payload_is_redacted(monkeypatch: pytest.MonkeyPatch, dicom_file) -> None:
    """The JSON sent to Gemini must never contain direct patient identifiers."""
    captured: dict[str, Any] = {}
    _fake_gemini_response(monkeypatch, captured, "ok")

    provider = GeminiProvider(api_key="k")
    report = analyze_file(dicom_file, provider=provider, deep_context=True)
    assert report.ai_summary == "ok"

    sent_text = json.dumps(captured["payload"])
    assert "Doe^John" not in sent_text
    assert "PID12345" not in sent_text
    assert "ACC00042" not in sent_text
