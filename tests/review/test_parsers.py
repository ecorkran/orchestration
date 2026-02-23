"""Tests for review result parser."""

from __future__ import annotations

import pytest

from orchestration.review.models import Severity, Verdict
from orchestration.review.parsers import parse_review_output

WELL_FORMED_PASS = """\
## Summary
PASS

## Findings

### [PASS] Clean module structure
Package layout follows project conventions and separation of concerns.

### [PASS] Good test coverage
All critical paths have unit tests.
"""

WELL_FORMED_CONCERNS = """\
## Summary
CONCERNS

## Findings

### [CONCERN] Missing error handling
The runner does not handle SDK timeout errors gracefully.

### [PASS] Clean module structure
Package layout follows project conventions.

### [FAIL] Security issue
User input is not sanitized at the API boundary.
File: src/api/handler.py:42
"""

WELL_FORMED_FAIL = """\
## Summary
FAIL

## Findings

### [FAIL] Critical bug in auth
Token validation is bypassed when header is empty.

### [FAIL] SQL injection risk
Query parameters are interpolated directly.
"""


class TestVerdictExtraction:
    """Test verdict parsing across all verdict strings."""

    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("## Summary\nPASS\n", Verdict.PASS),
            ("## Summary\nCONCERNS\n", Verdict.CONCERNS),
            ("## Summary\nFAIL\n", Verdict.FAIL),
            ("## Summary\n\nPASS\n", Verdict.PASS),
            ("##  Summary \nFAIL\n", Verdict.FAIL),
            ("## Summary\n**PASS**\n", Verdict.PASS),
            ("## Summary\n**CONCERNS**\n", Verdict.CONCERNS),
            ("## Summary\n**FAIL**\n", Verdict.FAIL),
        ],
    )
    def test_verdict_values(self, text: str, expected: Verdict) -> None:
        result = parse_review_output(text, "test", {})
        assert result.verdict == expected


class TestWellFormedOutput:
    """Test parsing well-formed agent output."""

    def test_pass_verdict_with_findings(self) -> None:
        result = parse_review_output(WELL_FORMED_PASS, "arch", {"input": "a.md"})
        assert result.verdict == Verdict.PASS
        assert len(result.findings) == 2
        assert all(f.severity == Severity.PASS for f in result.findings)

    def test_concerns_verdict_mixed_findings(self) -> None:
        result = parse_review_output(WELL_FORMED_CONCERNS, "code", {"cwd": "."})
        assert result.verdict == Verdict.CONCERNS
        assert len(result.findings) == 3
        severities = [f.severity for f in result.findings]
        assert Severity.CONCERN in severities
        assert Severity.PASS in severities
        assert Severity.FAIL in severities

    def test_fail_verdict(self) -> None:
        result = parse_review_output(WELL_FORMED_FAIL, "code", {})
        assert result.verdict == Verdict.FAIL
        assert len(result.findings) == 2
        assert all(f.severity == Severity.FAIL for f in result.findings)

    def test_finding_titles(self) -> None:
        result = parse_review_output(WELL_FORMED_CONCERNS, "code", {})
        titles = [f.title for f in result.findings]
        assert "Missing error handling" in titles
        assert "Security issue" in titles

    def test_finding_descriptions(self) -> None:
        result = parse_review_output(WELL_FORMED_CONCERNS, "code", {})
        concern = next(f for f in result.findings if f.severity == Severity.CONCERN)
        assert "timeout" in concern.description.lower()


class TestBracketOptionalFindings:
    """Test parsing findings without brackets (real agent output format)."""

    def test_no_brackets(self) -> None:
        text = """\
## Summary
**PASS**

## Findings

### PASS Good structure
Clean layout.

### CONCERN Missing tests
No tests for edge cases.

### FAIL Security hole
SQL injection possible.
"""
        result = parse_review_output(text, "code", {})
        assert result.verdict == Verdict.PASS
        assert len(result.findings) == 3
        severities = [f.severity for f in result.findings]
        assert Severity.PASS in severities
        assert Severity.CONCERN in severities
        assert Severity.FAIL in severities

    def test_mixed_brackets_and_no_brackets(self) -> None:
        text = """\
## Summary
CONCERNS

## Findings

### [PASS] With brackets
Description.

### CONCERN Without brackets
Description.
"""
        result = parse_review_output(text, "arch", {})
        assert len(result.findings) == 2


class TestMalformedOutput:
    """Test parsing malformed agent output."""

    def test_missing_summary(self) -> None:
        result = parse_review_output("Some text without a summary section.", "arch", {})
        assert result.verdict == Verdict.UNKNOWN

    def test_empty_output(self) -> None:
        result = parse_review_output("", "arch", {})
        assert result.verdict == Verdict.UNKNOWN
        assert result.findings == []

    def test_partial_output_findings_only_bracketed(self) -> None:
        text = "### [FAIL] Something wrong\nDescription here.\n"
        result = parse_review_output(text, "code", {})
        assert result.verdict == Verdict.UNKNOWN
        assert len(result.findings) == 1
        assert result.findings[0].severity == Severity.FAIL

    def test_partial_output_findings_only_unbracketed(self) -> None:
        text = "### FAIL Something wrong\nDescription here.\n"
        result = parse_review_output(text, "code", {})
        assert result.verdict == Verdict.UNKNOWN
        assert len(result.findings) == 1
        assert result.findings[0].severity == Severity.FAIL

    def test_summary_without_findings(self) -> None:
        text = "## Summary\nPASS\n\nNo specific findings.\n"
        result = parse_review_output(text, "arch", {})
        assert result.verdict == Verdict.PASS
        assert result.findings == []


class TestUnknownFallback:
    """Test UNKNOWN fallback preserves raw output."""

    def test_raw_output_preserved(self) -> None:
        raw = "This is completely unstructured agent output."
        result = parse_review_output(raw, "tasks", {"input": "x"})
        assert result.verdict == Verdict.UNKNOWN
        assert result.raw_output == raw
        assert result.template_name == "tasks"
        assert result.input_files == {"input": "x"}

    def test_metadata_preserved_on_success(self) -> None:
        result = parse_review_output(
            WELL_FORMED_PASS, "arch", {"input": "a.md", "against": "b.md"}
        )
        assert result.template_name == "arch"
        assert result.input_files == {"input": "a.md", "against": "b.md"}
        assert result.raw_output == WELL_FORMED_PASS
