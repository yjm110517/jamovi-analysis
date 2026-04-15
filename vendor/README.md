Project-scoped optional Python dependencies for jamovi project mode live under `vendor/jamovi-python`.

Current bundled packages:
- `python-docx`
- `markdown`

Runtime rules:
- `invoke-jamovi-project.ps1` and `preflight-jamovi-project.ps1` expose this directory through `JAMOVI_PROJECT_VENDOR_PATH`
- `run-jamovi-project.py` prepends the vendor path to `sys.path`
- the main analysis flow does not attempt runtime `pip install`

`weasyprint` is intentionally not vendored here. PDF export stays opt-in through environment capability checks and is removed from default exports when unavailable.
