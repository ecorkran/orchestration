---
docType: review
layer: project
reviewType: code
slice: tool-use-discipline-and-diagnosability-for-non-sdk-agents
project: squadron
verdict: PASS
sourceDocument: project-documents/user/slices/267-slice.tool-use-discipline-and-diagnosability-for-non-sdk-agents.md
aiModel: moonshotai/kimi-k2.7-code
status: complete
dateCreated: 20260908
dateUpdated: 20260908
reviewedSha: 495f0b3e30b73482a4f2903b9ef515590ed7171c
toolsSuppressedReason: run-suppressed
findings:
  - id: F001
    severity: pass
    category: design-principles
    summary: "Tool-use guidance is composed once at the agent boundary"
    location: "src/squadron/tools/guidance.py#compose_system_prompt"
  - id: F002
    severity: pass
    category: correctness
    summary: "SDK one-shot dispatch now routes allowed_tools through provider translation"
    location: "src/squadron/pipeline/actions/dispatch.py#one_shot_dispatch_with_telemetry"
  - id: F003
    severity: pass
    category: error-handling
    summary: "Degraded review artifacts retain raw model output at all verbosities"
    location: "src/squadron/review/persistence.py#format_review_markdown"
  - id: F004
    severity: note
    category: style
    summary: "Local import inside parser test deviates from standard grouping"
    location: "tests/review/test_parsers.py"
  - id: F005
    severity: note
    category: testing
    summary: "Byte-identical snapshot fixture is hidden by the diff filter"
    location: "tests/review/test_persistence.py"
---

# Review: code — slice 267

**Verdict:** PASS
**Model:** moonshotai/kimi-k2.7-code

## Findings

### [PASS] Tool-use guidance is composed once at the agent boundary

The new `compose_system_prompt` helper centralizes the tool-use discipline block and appends it to the caller’s instructions only when tools are actually available. This avoids duplicating the composition logic across call sites and means no tool-passing caller can accidentally omit the guidance block.

### [PASS] SDK one-shot dispatch now routes allowed_tools through provider translation

Removing the one-shot `ValueError` guard and letting `ClaudeSDKProvider` translate canonical tool names into SDK vocabulary is the right fix for #75, matching the behavior already wired up in slice 265. The persistent SDK-session path still rejects per-step `allowed_tools` with a clear error message.

### [PASS] Degraded review artifacts retain raw model output at all verbosities

UNKNOWN verdicts and fallback parses now embed the raw response in the markdown artifact even when prompts were not captured, and the prose no longer falsely points the reader at a `-vv`-only appendix. Judge paths with a score-derived override are correctly excluded.

### [NOTE] Local import inside parser test deviates from standard grouping

The new `test_debug_log_written_on_unknown_verdict` imports `json` inside the test body rather than at the module top with the other standard-library imports. Moving it to the top would keep the file consistent with the project’s import grouping convention.

### [NOTE] Byte-identical snapshot fixture is hidden by the diff filter

`test_clean_pass_artifact_is_byte_identical_to_the_pre_change_snapshot` references `tests/review/fixtures/clean_pass_artifact.md`, which was excluded from the diff by the `:!*.md` filter. Please confirm the fixture is committed and matches the current clean-pass output before merging.
