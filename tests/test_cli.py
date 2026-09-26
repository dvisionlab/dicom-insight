from __future__ import annotations

from pathlib import Path

import pytest

from dicom_insight.cli import build_parser, main


def test_build_parser_defaults() -> None:
    args = build_parser().parse_args(["some/path"])
    assert args.path == Path("some/path")
    assert args.json is False
    assert args.tags is False
    assert args.deep_context is False


def test_build_parser_flags() -> None:
    args = build_parser().parse_args(["some/path", "--json", "--tags", "--deep-context"])
    assert args.json is True
    assert args.tags is True
    assert args.deep_context is True


def test_main_json_output(
    dicom_file: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    exit_code = main([str(dicom_file), "--json"])
    out = capsys.readouterr().out
    assert exit_code == 0
    assert '"kind": "file"' in out
    assert '"modality": "CT"' in out


def test_main_markdown_output(
    dicom_file: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    exit_code = main([str(dicom_file)])
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "## Details" in out


def test_main_tags_flag_shows_tag_detail(
    dicom_file: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    exit_code = main([str(dicom_file), "--tags"])
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "## Tag Detail" in out


def test_main_without_api_key_does_not_use_gemini(
    dicom_file: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    main([str(dicom_file), "--json"])
    out = capsys.readouterr().out
    assert '"ai_summary": null' in out
