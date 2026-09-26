# 🧠🔎 dicom-insight

A small Python library that turns raw DICOM metadata into a structured summary and a human-readable explanation.

It is designed for developer tooling, dataset QA, PACS ingestion checks, and demos where you want to answer a simple question quickly:

> What does this DICOM file or study look like from metadata alone?

## Why it exists

Medical imaging workflows are full of metadata that is technically rich but hard to inspect quickly. `dicom-insight` provides:

- a clean Python API
- a CLI for quick inspection
- deterministic heuristics that work without a cloud dependency
- an optional provider interface for LLM-powered explanations and anomaly detection
- an optional, redaction-aware integration with Google Gemini for deeper clinical reasoning

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

print(report.ai_summary)  # High-level protocol synthesis
print(report.technical_anomalies)  # AI-detected metadata inconsistencies
```

## AI-Powered Insights

`dicom-insight` can optionally call out to an LLM (Gemini by default) to move beyond simple metadata listing:

- **Intelligent Summarization**: Infers clinical protocols (e.g., "CT Head Stroke Protocol") by synthesizing multiple series.
- **Technical Anomaly Detection**: Identifies subtle metadata "smells" like mismatched slice spacing or inconsistent reconstruction kernels.
- **Deep Metadata Context**: Use the `--deep-context` flag to provide the LLM with the full richness of the DICOM header while maintaining smart deduplication for large studies.

The specific Gemini model used is whatever you pass as `model=` (see below);
availability and naming of Gemini model versions are controlled by Google and
may change independently of this project.

## Privacy & PHI

DICOM headers routinely carry Protected Health Information (PHI) — patient
name, patient ID, birth date, accession number, referring physician, and so
on. When you configure a `GeminiProvider` (or set `GOOGLE_API_KEY`), that
metadata is sent to a third-party LLM API over the network.

To reduce that exposure, `dicom_insight.llm.GeminiProvider` **always** passes
the report through `dicom_insight.privacy.redact_report_for_llm` before
sending it to Gemini, which strips direct identifiers such as `PatientName`,
`PatientID`, `PatientBirthDate`, `AccessionNumber`, and referring/performing
physician names from the payload — regardless of whether `--deep-context` is
set.

This is a **best-effort redaction, not full DICOM de-identification** (see
DICOM PS3.15 Annex E for what a complete de-identification profile involves).
It does not touch what is displayed *locally* (e.g. via `--tags`), only what
is sent to the LLM. Before pointing this at real patient data:

- Confirm your use case, data-sharing agreements, and applicable regulations
  (HIPAA, GDPR, etc.) permit sending de-identified imaging metadata to
  Google's Gemini API.
- Treat `--deep-context` / `--tags` as opt-in features for QA and development
  workflows, not a guarantee of compliance.
- Review `dicom_insight/privacy.py` if you need to extend the redaction list
  for your institution's specific tag usage.

## Building executables

You can produce a standalone executable using [PyInstaller](https://pyinstaller.org) — no Python installation required on the target machine.

### Prerequisites

Install the dev dependencies (includes PyInstaller):

```bash
uv sync --group dev
```

### Build

A ready-to-use spec file is included in the repository root:

```bash
uv run pyinstaller dicom_insight.spec
```

The executable is written to `dist/dicom-insight` (or `dist/dicom-insight.exe` on Windows).

### Platform-specific builds

PyInstaller only produces executables for the OS you build on, so to get all three platform binaries you need to run the command on each system:

| Platform | Command | Output |
|---|---|---|
| Linux | `uv run pyinstaller dicom_insight.spec` | `dist/dicom-insight` |
| macOS | `uv run pyinstaller dicom_insight.spec` | `dist/dicom-insight` |
| Windows | `uv run pyinstaller dicom_insight.spec` | `dist\dicom-insight.exe` |

Pre-built binaries for Linux, Windows, and macOS are also attached to every [GitHub Release](https://github.com/dvisionlab/dicom-insight/releases).

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

# Decode pixel data and report basic intensity statistics (slower, more memory)
uv run dicom-insight ./study_folder --pixels
```

### Setting the `GOOGLE_API_KEY` environment variable

The CLI automatically detects the `GOOGLE_API_KEY` environment variable and enables AI-powered features when it is present.

**Linux / macOS**

Set the variable for the current shell session:

```bash
export GOOGLE_API_KEY="your_api_key_here"
```

To make it permanent, add the line above to your `~/.bashrc`, `~/.zshrc`, or the appropriate shell configuration file, then reload it:

```bash
source ~/.bashrc
```

**Windows (Command Prompt)**

Set the variable for the current session:

```cmd
set GOOGLE_API_KEY=your_api_key_here
```

To set it permanently via the system settings:

```cmd
setx GOOGLE_API_KEY "your_api_key_here"
```

**Windows (PowerShell)**

Set the variable for the current session:

```powershell
$env:GOOGLE_API_KEY = "your_api_key_here"
```

To set it permanently for the current user:

```powershell
[System.Environment]::SetEnvironmentVariable("GOOGLE_API_KEY", "your_api_key_here", "User")
```

> **Note:** After using `setx` or `SetEnvironmentVariable`, you need to open a new terminal window for the change to take effect.

## LLM Configuration

The library is provider-agnostic. While Gemini is the recommended engine, you can implement custom providers via the `ExplanationProvider` protocol.

```python
from dicom_insight.llm import GeminiProvider
import os

provider = GeminiProvider(api_key=os.environ["GOOGLE_API_KEY"], model="gemini-3.1-pro")
```

## Pixel Data Statistics

Pass `--pixels` (CLI) or `include_pixels=True` (`analyze_file`/`analyze_path`) to decode `PixelData`
and compute basic intensity statistics per series: shape, dtype, min/max/mean/std, and whether the
image is constant (e.g. blank). This is opt-in and off by default because decoding pixel data is
significantly slower and more memory-intensive than reading metadata alone. Only a representative
instance per series is analyzed, keeping folder-wide scans affordable.

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup, linting (`ruff`), type
checking (`mypy`), and how to run the test suite.

## Limits

- Pixel inspection is limited to basic intensity statistics on a representative instance; no
  full pixel-level analysis, rendering, or viewer capabilities.
- Heuristics are deterministic; AI insights are probabilistic.
- Orientation detection remains conservative.

