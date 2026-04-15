"""Template regression tests: compare examples/*/expected-output.md with generated reports."""

import json
import re
import subprocess
from pathlib import Path

import pytest

EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "jamovi_outputs"


def _list_examples() -> list[Path]:
    return [p for p in EXAMPLES_DIR.iterdir() if p.is_dir()]


def _extract_numbers(text: str) -> list[float]:
    """Extract all numeric values from markdown text for tolerant comparison."""
    pattern = re.compile(r"-?\d+\.\d+|-?\d+")
    return [float(m) for m in pattern.findall(text)]


class TestExampleDirectoryStructure:
    @pytest.mark.parametrize("example_dir", _list_examples(), ids=lambda p: p.name)
    def test_example_has_required_files(self, example_dir: Path):
        assert (example_dir / "data.csv").exists(), f"Missing data.csv in {example_dir}"
        assert (example_dir / "jobfile.json").exists(), f"Missing jobfile.json in {example_dir}"
        assert (example_dir / "expected-output.md").exists(), f"Missing expected-output.md in {example_dir}"

    @pytest.mark.parametrize("example_dir", _list_examples(), ids=lambda p: p.name)
    def test_expected_output_contains_apa_tables(self, example_dir: Path):
        text = (example_dir / "expected-output.md").read_text(encoding="utf-8")
        assert "Table " in text, f"Expected APA table numbering in {example_dir}"
        assert re.search(r"\*[^*]+\*", text), f"Expected italicized title in {example_dir}"


JAMOVI_AVAILABLE = False
try:
    import jamovi  # noqa: F401

    JAMOVI_AVAILABLE = True
except Exception:
    pass


@pytest.mark.skipif(not JAMOVI_AVAILABLE, reason="jamovi not installed in this environment")
class TestGeneratedOutputRegression:
    """Run actual jamovi analyses and compare generated Markdown with expected outputs."""

    @pytest.mark.parametrize("example_dir", _list_examples(), ids=lambda p: p.name)
    def test_generated_markdown_matches_expected(self, example_dir: Path):
        jobfile = example_dir / "jobfile.json"
        spec = json.loads(jobfile.read_text(encoding="utf-8"))
        basename = spec.get("output", {}).get("basename", example_dir.name)
        expected_path = example_dir / "expected-output.md"

        # Run analysis via PowerShell wrapper
        script = Path(__file__).resolve().parent.parent / "scripts" / "invoke-jamovi-project.ps1"
        result = subprocess.run(
            ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(script), "-JobFile", str(jobfile)],
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert result.returncode == 0, f"Jamovi run failed:\n{result.stderr}\n{result.stdout}"

        output_dir = OUTPUT_DIR / basename
        md_files = list(output_dir.glob("*.md"))
        assert md_files, f"No Markdown report generated in {output_dir}"

        generated = md_files[0].read_text(encoding="utf-8")
        expected = expected_path.read_text(encoding="utf-8")

        # Structural checks
        expected_tables = re.findall(r"^Table \d+$", expected, re.MULTILINE)
        generated_tables = re.findall(r"^Table \d+$", generated, re.MULTILINE)
        assert len(generated_tables) >= len(expected_tables), (
            f"Expected {len(expected_tables)} APA tables, found {len(generated_tables)}"
        )

        # Tolerant numeric comparison
        expected_nums = _extract_numbers(expected)
        generated_nums = _extract_numbers(generated)
        assert len(generated_nums) >= len(expected_nums), (
            f"Expected {len(expected_nums)} numeric values, found {len(generated_nums)}"
        )
        for i, (exp, gen) in enumerate(zip(expected_nums, generated_nums)):
            assert gen == pytest.approx(exp, abs=0.05), (
                f"Numeric mismatch at position {i}: expected {exp}, got {gen}"
            )
