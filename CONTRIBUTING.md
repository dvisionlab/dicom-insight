# Contributing to dicom-insight

Thanks for your interest in improving `dicom-insight`! This project is small,
so the process is intentionally lightweight.

## Setup

This project uses [uv](https://github.com/astral-sh/uv) for dependency management.

```bash
uv sync --group dev
```

## Before opening a pull request

Run the same checks CI runs:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy dicom_insight
uv run pytest tests/ -v
```

If `ruff format` reports issues, run `uv run ruff format .` to fix them
in place.

## Guidelines

- Keep changes focused; prefer several small pull requests over one large one.
- Add or update tests for any behavior change (see `tests/`).
- Public functions and classes should keep their type hints accurate — `mypy`
  runs in CI.
- If you touch `dicom_insight/llm.py` or `dicom_insight/privacy.py`, keep in
  mind that this project sends metadata to a third-party LLM (Google Gemini)
  when a provider is configured. Any new field surfaced to a provider must go
  through `redact_report_for_llm` (or be reviewed for whether it could
  identify a patient) — see the "Privacy" section of the README.
- Commit messages and PR descriptions should explain *why*, not just *what*.

## Reporting issues

Please open a GitHub issue with steps to reproduce, the DICOM modality/source
involved (no real patient data, please — use anonymized or synthetic files),
and the command or code you ran.
