# dicom-insight

A small Python library that turns raw DICOM metadata into a structured summary and a human-readable explanation.

It is designed for developer tooling, dataset QA, PACS ingestion checks, and demos where you want to answer a simple question quickly:

> What does this DICOM file or study look like from metadata alone?

## Why it exists

Medical imaging workflows are full of metadata that is technically rich but hard to inspect quickly. `dicom-insight` provides:

- a clean Python API
- a CLI for quick inspection
- deterministic heuristics that work without a cloud dependency
- an optional provider interface for LLM-powered explanations and anomaly detection
- deep clinical reasoning using Google Gemini 3.1

## Installation

This project uses [uv](https://github.com/astral-sh/uv) for dependency management.

1. **Install uv**:
   ```powershell
   powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```

2. **Sync dependencies**:
   ```bash
   uv sync
   ```

## Quick start

```python
from dicom_insight import analyze_file, analyze_path
from dicom_insight.llm import GeminiProvider

# AI-powered clinical analysis
provider = GeminiProvider(api_key="YOUR_GOOGLE_API_KEY", model="gemini-3.1-pro")
report = analyze_path("./study_folder", provider=provider, deep_context=True)

print(report.ai_summary)       # High-level protocol synthesis
print(report.technical_anomalies) # AI-detected metadata inconsistencies
```

## AI-Powered Insights

`dicom-insight` leverages LLMs (specializing in Gemini 3.1) to move beyond simple metadata listing:

- **Intelligent Summarization**: Infers clinical protocols (e.g., "CT Head Stroke Protocol") by synthesizing multiple series.
- **Technical Anomaly Detection**: Identifies subtle metadata "smells" like mismatched slice spacing or inconsistent reconstruction kernels.
- **Deep Metadata Context**: Use the `--deep-context` flag to provide the LLM with the full richness of the DICOM header while maintaining smart deduplication for large studies.

## CLI

```bash
# Basic summary
uv run dicom-insight ./study_folder

# AI-powered summary (requires GOOGLE_API_KEY env var)
uv run dicom-insight ./study_folder

# Deep metadata analysis for clinical reasoning
uv run dicom-insight ./study_folder --deep-context

# JSON output
uv run dicom-insight ./study_folder --json
```

## LLM Configuration

The library is provider-agnostic. While Gemini is the recommended engine, you can implement custom providers via the `ExplanationProvider` protocol.

```python
from dicom_insight.llm import GeminiProvider
import os

provider = GeminiProvider(api_key=os.environ["GOOGLE_API_KEY"], model="gemini-3.1-pro")
```

## Limits

- No pixel data inspection.
- Heuristics are deterministic; AI insights are probabilistic.
- Orientation detection remains conservative.

