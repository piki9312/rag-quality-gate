# Windows PowerShell Command Guide

This guide lists Windows PowerShell equivalents for common onboarding and gate commands.

Run commands from the repository root unless noted otherwise.

## UTF-8 Note

If Japanese text looks garbled in PowerShell output, set UTF-8 for the current session:

```powershell
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$OutputEncoding = [System.Text.UTF8Encoding]::new()
chcp 65001
```

This does not change RQG behavior. It only affects console display.

## Virtual Environment

Bash:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
pip install -e ".[dev]"
```

PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -e ".[dev]"
```

If script execution is blocked, use this for the current PowerShell process:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## Environment Variables

Bash:

```bash
export RQG_API_KEY="your-api-key"
```

PowerShell:

```powershell
$env:RQG_API_KEY = "your-api-key"
```

The value applies only to the current PowerShell session.

## Onboarding Demo

Bash:

```bash
python -m rqg.demo.onboarding_quickstart
python -m rqg.demo.onboarding_quickstart --profile wiki
```

PowerShell:

```powershell
python -m rqg.demo.onboarding_quickstart
python -m rqg.demo.onboarding_quickstart --profile wiki
```

Outputs are written under `demo_runs/onboarding_quickstart/<run-id>/`.

## validate-pack

Bash:

```bash
rqg validate-pack --pack-dir packs/hr
rqg validate-pack --pack-dir packs/hr --output runs/quality/pack-validation.json
```

PowerShell:

```powershell
rqg validate-pack --pack-dir packs/hr
rqg validate-pack --pack-dir packs/hr --output runs\quality\pack-validation.json
```

External RAG mode with an API key environment variable:

Bash:

```bash
export RQG_API_KEY="your-api-key"
rqg validate-pack --pack-dir packs/hr --endpoint https://rag.example.com/search --api-key-env RQG_API_KEY
```

PowerShell:

```powershell
$env:RQG_API_KEY = "your-api-key"
rqg validate-pack --pack-dir packs/hr --endpoint https://rag.example.com/search --api-key-env RQG_API_KEY
```

## eval / check / gate

Bash:

```bash
rqg eval packs/hr/cases.csv --docs packs/hr/documents --mock --index-dir index --log-dir runs/quality
rqg check --log-dir runs/quality --config .rqg.yml
rqg gate packs/hr/cases.csv --docs packs/hr/documents --mock --index-dir index --log-dir runs/quality --config .rqg.yml
```

PowerShell:

```powershell
rqg eval packs\hr\cases.csv --docs packs\hr\documents --mock --index-dir index --log-dir runs\quality
rqg check --log-dir runs\quality --config .rqg.yml
rqg gate packs\hr\cases.csv --docs packs\hr\documents --mock --index-dir index --log-dir runs\quality --config .rqg.yml
```

Multi-line PowerShell commands use the backtick continuation character:

```powershell
rqg gate packs\hr\cases.csv `
  --docs packs\hr\documents `
  --mock --index-dir index --log-dir runs\quality `
  --config .rqg.yml
```

## gate-report.json

Bash:

```bash
cat runs/quality/gate-report.md
cat runs/quality/gate-decision.json
cat runs/quality/gate-report.json
python -m json.tool runs/quality/gate-report.json
```

PowerShell:

```powershell
Get-Content runs\quality\gate-report.md
Get-Content runs\quality\gate-decision.json
Get-Content runs\quality\gate-report.json
python -m json.tool runs\quality\gate-report.json
```

`gate-report.json` is the machine-readable bundle for downstream consumers. Keep existing fields stable when integrating it into CI, dashboards, or review automation.
