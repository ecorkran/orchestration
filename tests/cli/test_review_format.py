"""Tests for structured findings in review frontmatter formatting."""

from __future__ import annotations

from datetime import datetime

import pytest
import yaml

from squadron.cli.commands.review import _display_terminal
from squadron.review.models import (
    ReviewFinding,
    ReviewResult,
    Severity,
    Verdict,
)
from squadron.review.persistence import (
    SliceInfo,
    format_review_markdown,
    yaml_escape,
)

SLICE_INFO: SliceInfo = {
    "index": 143,
    "name": "Structured Review Findings",
    "slice_name": "structured-review-findings",
    "design_file": ("project-documents/user/slices/143-slice.structured-review-findings.md"),
    "task_files": ["143-tasks.structured-review-findings.md"],
    "arch_file": ("project-documents/user/architecture/140-arch.pipeline-foundation.md"),
    "project": "squadron",
}


def _make_result_with_structured_findings() -> ReviewResult:
    return ReviewResult(
        verdict=Verdict.CONCERNS,
        findings=[
            ReviewFinding(
                severity=Severity.CONCERN,
                title="Missing error handling",
                description="No try/except.",
                file_ref="src/foo.py:10",
                category="error-handling",
                location="src/foo.py:10",
            ),
            ReviewFinding(
                severity=Severity.NOTE,
                title="Variable name unclear",
                description="Variable x is vague.",
                category="naming",
            ),
        ],
        raw_output="raw",
        template_name="code",
        input_files={},
        timestamp=datetime(2026, 3, 30, 12, 0, 0),
        model="opus",
    )


def _make_result_no_findings() -> ReviewResult:
    return ReviewResult(
        verdict=Verdict.PASS,
        findings=[],
        raw_output="raw",
        template_name="code",
        input_files={},
        timestamp=datetime(2026, 3, 30, 12, 0, 0),
        model="opus",
    )


class TestFrontmatterFindings:
    """Test structured findings block in YAML frontmatter."""

    def test_findings_block_present(self) -> None:
        result = _make_result_with_structured_findings()
        md = format_review_markdown(result, "code", SLICE_INFO)
        assert "findings:" in md

    def test_finding_has_required_fields(self) -> None:
        result = _make_result_with_structured_findings()
        md = format_review_markdown(result, "code", SLICE_INFO)
        assert "  - id: F001" in md
        assert "    severity: concern" in md
        assert "    category: error-handling" in md
        assert '    summary: "Missing error handling"' in md

    def test_finding_with_location(self) -> None:
        result = _make_result_with_structured_findings()
        md = format_review_markdown(result, "code", SLICE_INFO)
        assert '    location: "src/foo.py:10"' in md

    def test_finding_without_location_omits_field(self) -> None:
        result = _make_result_with_structured_findings()
        md = format_review_markdown(result, "code", SLICE_INFO)
        # Second finding (F002) has no location — check it's not emitted
        lines = md.split("\n")
        f002_idx = next(i for i, line in enumerate(lines) if "id: F002" in line)
        # Lines between F002 and the closing --- should not have location
        f002_block = []
        for line in lines[f002_idx:]:
            if line.strip() == "---":
                break
            if line.startswith("  - id:") and "F002" not in line:
                break
            f002_block.append(line)
        assert not any("location:" in entry for entry in f002_block)

    def test_summary_with_double_quotes_escaped(self) -> None:
        result = ReviewResult(
            verdict=Verdict.CONCERNS,
            findings=[
                ReviewFinding(
                    severity=Severity.CONCERN,
                    title='Variable "x" unclear',
                    description="Rename it.",
                    category="naming",
                ),
            ],
            raw_output="raw",
            template_name="code",
            input_files={},
            timestamp=datetime(2026, 3, 30, 12, 0, 0),
            model="opus",
        )
        md = format_review_markdown(result, "code", SLICE_INFO)
        assert r'summary: "Variable \"x\" unclear"' in md

    def test_frontmatter_is_valid_yaml(self) -> None:
        result = _make_result_with_structured_findings()
        md = format_review_markdown(result, "code", SLICE_INFO)
        # Extract frontmatter between --- markers
        parts = md.split("---")
        frontmatter_text = parts[1]
        data = yaml.safe_load(frontmatter_text)
        assert data["docType"] == "review"
        assert data["verdict"] == "CONCERNS"
        assert isinstance(data["findings"], list)
        assert len(data["findings"]) == 2
        assert data["findings"][0]["id"] == "F001"
        assert data["findings"][0]["severity"] == "concern"

    def test_no_findings_block_when_empty(self) -> None:
        result = _make_result_no_findings()
        md = format_review_markdown(result, "code", SLICE_INFO)
        assert "findings:" not in md

    def test_prose_body_unchanged(self) -> None:
        result = _make_result_with_structured_findings()
        md = format_review_markdown(result, "code", SLICE_INFO)
        assert "### [CONCERN] Missing error handling" in md
        assert "### [NOTE] Variable name unclear" in md


class TestYamlEscape:
    """Test yaml_escape helper."""

    def test_escapes_double_quotes(self) -> None:
        assert yaml_escape('hello "world"') == 'hello \\"world\\"'

    def test_no_quotes_unchanged(self) -> None:
        assert yaml_escape("hello world") == "hello world"

    def test_escapes_backslash(self) -> None:
        assert yaml_escape("path\\to\\file") == "path\\\\to\\\\file"


class TestTerminalDegradedOutput:
    """A degraded parse must not read as a clean review in the terminal (issue #72)."""

    @staticmethod
    def _result(*, fallback_used: bool) -> ReviewResult:
        return ReviewResult(
            verdict=Verdict.CONCERNS,
            findings=[],
            raw_output="the model's prose findings live here",
            template_name="code",
            input_files={},
            timestamp=datetime(2026, 3, 30, 12, 0, 0),
            model="opus",
            fallback_used=fallback_used,
        )

    def test_degraded_review_does_not_claim_no_findings(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _display_terminal(self._result(fallback_used=True))
        out = capsys.readouterr().out
        assert "No specific findings" not in out
        assert "degraded" in out.lower()

    def test_degraded_review_points_at_the_raw_response(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _display_terminal(self._result(fallback_used=True))
        assert "raw response" in capsys.readouterr().out.lower()

    def test_genuinely_clean_review_still_reports_no_findings(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _display_terminal(self._result(fallback_used=False))
        out = capsys.readouterr().out
        assert "No specific findings" in out
        assert "degraded" not in out.lower()

    def test_review_with_findings_is_never_marked_degraded(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _display_terminal(_make_result_with_structured_findings())
        out = capsys.readouterr().out
        assert "Missing error handling" in out
        assert "degraded" not in out.lower()
