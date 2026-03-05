"""Prompt builder for the code review template."""

from __future__ import annotations


def code_review_prompt(inputs: dict[str, str]) -> str:
    """Build the code review prompt with conditional sections.

    Handles three scoping modes:
    - ``diff`` present: review changed files relative to a git ref
    - ``files`` present: review files matching a glob pattern
    - neither: agent surveys project structure
    """
    cwd = inputs.get("cwd", ".")
    diff = inputs.get("diff")
    files = inputs.get("files")

    sections: list[str] = [
        f"Review code in the project at: {cwd}",
        "",
    ]

    if diff:
        sections.append(
            f"Run `git diff {diff}` to identify changed files, "
            "then review those files for quality and correctness."
        )
    if files:
        sections.append(f"Focus your review on files matching the pattern: {files}")
    if not diff and not files:
        sections.append(
            "Survey the project structure using Glob and Grep to identify "
            "the most important areas to review. Focus on recently modified "
            "or core source files."
        )

    sections.append("")
    sections.append(
        "Apply the project conventions from CLAUDE.md and language-specific "
        "best practices. Report your findings using the severity format "
        "described in your instructions."
    )

    return "\n".join(sections)
