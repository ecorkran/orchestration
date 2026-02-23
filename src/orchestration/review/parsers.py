"""Parse agent markdown output into structured ReviewResult."""

from __future__ import annotations

import re

from orchestration.review.models import (
    ReviewFinding,
    ReviewResult,
    Severity,
    Verdict,
)

_VERDICT_MAP: dict[str, Verdict] = {
    "PASS": Verdict.PASS,
    "CONCERNS": Verdict.CONCERNS,
    "FAIL": Verdict.FAIL,
}

_SEVERITY_MAP: dict[str, Severity] = {
    "PASS": Severity.PASS,
    "CONCERN": Severity.CONCERN,
    "FAIL": Severity.FAIL,
}

# Matches "## Summary" section followed by a verdict keyword (possibly bold)
_SUMMARY_RE = re.compile(
    r"##\s+Summary\s*\n+\s*(?:.*?\b)?(?:\*{0,2})(PASS|CONCERNS|FAIL)(?:\*{0,2})\b",
    re.IGNORECASE,
)

# Matches finding blocks: "### [SEVERITY] Title" or "### SEVERITY Title"
_FINDING_RE = re.compile(
    r"###\s+\[?(PASS|CONCERN|FAIL)\]?\s+(.+?)(?=\n###\s+\[?(?:PASS|CONCERN|FAIL)|\n##\s+|\Z)",
    re.DOTALL | re.IGNORECASE,
)


def _extract_verdict(text: str) -> Verdict:
    """Parse verdict from the ## Summary section."""
    match = _SUMMARY_RE.search(text)
    if match is None:
        return Verdict.UNKNOWN
    keyword = match.group(1).upper()
    return _VERDICT_MAP.get(keyword, Verdict.UNKNOWN)


def _extract_findings(text: str) -> list[ReviewFinding]:
    """Parse ### [SEVERITY] Title blocks into ReviewFinding list."""
    findings: list[ReviewFinding] = []
    for match in _FINDING_RE.finditer(text):
        severity_str = match.group(1).upper()
        severity = _SEVERITY_MAP.get(severity_str)
        if severity is None:
            continue
        title = match.group(2).strip().split("\n")[0]
        # Description is everything after the title line
        full_block = match.group(0)
        lines = full_block.split("\n")
        description = "\n".join(lines[1:]).strip()
        findings.append(
            ReviewFinding(
                severity=severity,
                title=title,
                description=description,
            )
        )
    return findings


def parse_review_output(
    raw_output: str,
    template_name: str,
    input_files: dict[str, str],
) -> ReviewResult:
    """Parse agent markdown output into a structured ReviewResult.

    Falls back to UNKNOWN verdict if the output doesn't follow expected format.
    """
    verdict = _extract_verdict(raw_output)
    findings = _extract_findings(raw_output)

    return ReviewResult(
        verdict=verdict,
        findings=findings,
        raw_output=raw_output,
        template_name=template_name,
        input_files=input_files,
    )
