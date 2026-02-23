# Template Authoring Guide

This guide explains how review templates work and how to create custom ones.

> **Note:** Custom user-defined templates are a planned future feature. Currently, templates must be added to the source code. This guide documents the template system for contributors and future extension.

## Overview

A review template is a YAML file that defines:
- What the review agent should look for (system prompt)
- What tools it can use
- What inputs it requires
- How the review prompt is constructed

## YAML Schema

```yaml
# Required fields
name: string              # Unique template identifier
description: string       # Short description shown in `review list`
system_prompt: |          # Multi-line system prompt for the review agent
  Instructions for the reviewer...

allowed_tools: [string]   # SDK tools the agent can use
                          # Common: Read, Glob, Grep, Bash

permission_mode: string   # SDK permission mode
                          # "bypassPermissions" for read-only reviews
                          # "acceptEdits" if the agent needs write access

setting_sources: null | [string]
                          # null: no project settings loaded
                          # [project]: loads CLAUDE.md and project rules

# Input definitions
inputs:
  required:
    - name: string        # Input key name
      description: string # Description shown in help
  optional:
    - name: string
      description: string
      default: string     # Default value if not provided

# Prompt construction (exactly one required)
prompt_template: |        # String template with {input_name} placeholders
  Review {input} against {against}...

# OR
prompt_builder: module.path.function_name
                          # Dotted path to a Python callable
                          # Receives dict[str, str] of inputs, returns str

# Optional
hooks: null | object      # SDK hook configuration (schema ready, not yet wired)
```

## Prompt construction

Templates use exactly one of two prompt construction methods:

### prompt_template (inline)

A string with `{placeholder}` references to input names. Simple and suitable for most templates.

```yaml
prompt_template: |
  Review the following document:
  **Input:** {input}
  **Reference:** {against}
  Evaluate alignment and report findings.
```

### prompt_builder (Python callable)

A dotted path to a Python function for complex prompt logic. The function receives a `dict[str, str]` of inputs and returns a string.

```yaml
prompt_builder: orchestration.review.builders.code.code_review_prompt
```

The corresponding Python function:

```python
def code_review_prompt(inputs: dict[str, str]) -> str:
    """Build a code review prompt with conditional sections."""
    parts = ["Review the code in the project."]

    if diff_ref := inputs.get("diff"):
        parts.append(f"Focus on changes since git ref: {diff_ref}")

    if file_pattern := inputs.get("files"):
        parts.append(f"Scope: files matching {file_pattern}")

    return "\n\n".join(parts)
```

Use `prompt_builder` when:
- The prompt has conditional sections based on which inputs are provided
- You need to read files or perform logic before constructing the prompt
- The template string approach would be too complex

## Example: annotated template

```yaml
name: arch
description: "Architectural review - evaluate document against architecture/HLD"

system_prompt: |
  You are an architectural reviewer. Your task is to evaluate whether a design
  document aligns with a parent architecture document.

  Report your findings using this format:

  ## Summary
  [PASS | CONCERNS | FAIL]

  ## Findings

  ### [PASS|CONCERN|FAIL] Finding title
  Description with specific references.

allowed_tools: [Read, Glob, Grep]
permission_mode: bypassPermissions
setting_sources: null

inputs:
  required:
    - name: input
      description: "Document to review"
    - name: against
      description: "Architecture document to review against"
  optional:
    - name: cwd
      description: "Working directory for file reads"
      default: "."

prompt_template: |
  Review the following document for architectural alignment:

  **Input document:** {input}
  **Architecture document:** {against}

  Read both documents, then evaluate the input against the architecture.
```

## Built-in templates

### arch

Reviews a document against an architecture reference. Uses `Read`, `Glob`, `Grep` tools. Does not load project settings (`setting_sources: null`).

### tasks

Reviews a task breakdown against its parent slice design. Same tool set and permissions as `arch`.

### code

Reviews project code. Uses `Read`, `Glob`, `Grep`, and `Bash` tools. Loads project settings (`setting_sources: [project]`), which means `CLAUDE.md` rules are available to the review agent. Uses a `prompt_builder` for conditional diff/files/survey sections.

## Output format

All review agents are instructed to produce output in this format:

```markdown
## Summary
PASS | CONCERNS | FAIL

## Findings

### [PASS|CONCERN|FAIL] Finding title
Description of the finding.
```

The parser (`orchestration.review.parsers`) extracts:
- **Verdict** from the `## Summary` section
- **Findings** from `### [SEVERITY] Title` blocks

Both bracketed (`### [PASS] Title`) and unbracketed (`### PASS Title`) formats are accepted. Bold verdicts (`**PASS**`) are also recognized.

## Registration

Templates are registered in the template registry at runtime:

```python
from orchestration.review.templates import register_template, load_template

# Load from YAML file
template = load_template(Path("my-template.yaml"))
register_template(template)
```

Built-in templates are loaded automatically from `src/orchestration/review/templates/builtin/` when any review command runs.
