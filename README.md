# dicom-insight

A small Python library that turns raw DICOM metadata into a structured summary and a human-readable explanation.

It is designed for developer tooling, dataset QA, PACS ingestion checks, and demos where you want to answer a simple question quickly:

> What does this DICOM file or study look like from metadata alone?

## Why it exists

Medical imaging workflows are full of metadata that is technically rich but hard to inspect quickly. `dicom-insight` provides:

- a clean Python API
- a CLI for quick inspection
- deterministic heuristics that work without a cloud dependency
- an optional provider interface for LLM-powered explanations

## Installation

This project uses [uv](https://github.com/astral-sh/uv) for dependency management.

1. **Install uv** (if you haven't already):
   ```powershell
   powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```
   *For other OS/methods, see [uv documentation](https://docs.astral.sh/uv/getting-started/installation/).*

2. **Sync dependencies**:
   ```bash
   uv sync
   ```

## Quick start

```python
from dicom_insight import analyze_file, analyze_path

report = analyze_file("./ct_head.dcm")
print(report.summary)
print(report.explanation)

study_report = analyze_path("./study_folder")
print(study_report.to_json())
```

## Example output

```text
CT head — 1 images, 512×512, 1 mm

CT series of the head Series description: HEAD W/O CONTRAST. Acquisition summary: 1 instance, matrix 512×512, slice thickness 1 mm. Likely viewing plane: axial. No clear sign of contrast usage was found in the available metadata.
```

## CLI

You can run the CLI directly using `uv run`:

```bash
uv run dicom-insight ./study_folder
uv run dicom-insight ./study_folder --json
```

## LLM hook

The library includes a tiny provider protocol so you can swap in an external model without changing the analysis layer.

```python
from dicom_insight import analyze_file
from dicom_insight.llm import TemplateLLMProvider

report = analyze_file("./ct_head.dcm", provider=TemplateLLMProvider(style="concise"))
print(report.explanation)
```

For production, you would replace `TemplateLLMProvider` with an adapter for OpenAI, Azure OpenAI, Ollama, or any internal inference endpoint.

## Limits

- It does **not** inspect pixel data semantics.
- It infers context from metadata only.
- Contrast detection is heuristic.
- Orientation detection is intentionally conservative.
