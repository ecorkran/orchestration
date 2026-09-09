---
docType: review
layer: project
reviewType: code
slice: tool-use-discipline-and-diagnosability-for-non-sdk-agents
project: squadron
verdict: CONCERNS
sourceDocument: project-documents/user/slices/267-slice.tool-use-discipline-and-diagnosability-for-non-sdk-agents.md
aiModel: claude-sonnet-5
status: complete
dateCreated: 20260908
dateUpdated: 20260908
reviewedSha: 495f0b3e30b73482a4f2903b9ef515590ed7171c
findings:
  - id: F001
    severity: concern
    category: error-handling
    summary: "Terminal output does not carry the genuinely-UNKNOWN degraded fix this diff adds to the persisted artifact"
    location: "src/squadron/cli/commands/review.py:162-176"
  - id: F002
    severity: note
    category: maintainability
    summary: "`format_review_markdown` keeps growing past the ~50-line function guideline, with two near-duplicate \"Findings Not Parsed\" blocks"
    location: "src/squadron/review/persistence.py:253-299"
  - id: F003
    severity: note
    category: naming
    summary: "Debug-log `fallback_used` field diverges from `ReviewResult.fallback_used` for the same event"
    location: "src/squadron/review/parsers.py:514-525"
  - id: F004
    severity: pass
    category: design
    summary: "Tool-use guidance composed once at the agent boundary"
    location: "src/squadron/tools/guidance.py"
  - id: F005
    severity: pass
    category: correctness
    summary: "SDK preset/append composition matches the documented truth table and is tested for all four rows"
    location: "src/squadron/providers/sdk/provider.py:47-61"
---

# Review: code — slice 267

**Verdict:** CONCERNS
**Model:** claude-sonnet-5

## Findings

### [CONCERN] Terminal output does not carry the genuinely-UNKNOWN degraded fix this diff adds to the persisted artifact

`parsers.py` has two distinct "nothing usable was parsed" paths: (a) a verdict *was* derived but findings failed to parse (`fallback_used=True`), and (b) no verdict and no findings at all — genuinely `Verdict.UNKNOWN` with `fallback_used` staying `False` (src/squadron/review/parsers.py:503-525). This diff explicitly closes the "false claim of cleanliness" gap for case (b) in the persisted markdown via the new `elif degraded:` branch in `format_review_markdown` (src/squadron/review/persistence.py:284-296), with commit history and comments citing issue #61 for exactly this fix.

`_display_terminal` was not given the same treatment. It only branches on `result.fallback_used` (src/squadron/cli/commands/review.py:163): a review that lands in case (b) — model returned unstructured prose, no `## Summary`, no findings — falls through to the `else` branch and prints `"  No specific findings."` even though the verdict is `UNKNOWN` and the model's response was never successfully parsed. `TestTerminalDegradedOutput` (tests/cli/test_review_format.py:170-214) only exercises `fallback_used=True/False`; there is no test for `verdict=UNKNOWN, fallback_used=False`, so this gap is untested and unfixed on the one output surface the diff's own comment calls "the terminal, where most reviews are actually read" (src/squadron/cli/commands/review.py:158).

### [NOTE] `format_review_markdown` keeps growing past the ~50-line function guideline, with two near-duplicate "Findings Not Parsed" blocks

The function is now ~205 lines (persistence.py:138-342), well past CLAUDE.md's "~50 lines, where practical" guidance, and this diff adds a fourth branch to an already-growing `if/elif/elif/else` chain. The `elif result.fallback_used:` (269-283) and `elif degraded:` (284-296) blocks both emit `## Findings Not Parsed` plus a similarly-shaped explanatory paragraph and only differ in wording — a small extraction (e.g. a helper taking the specific reason string) would remove the duplication and keep the branch list flat as more degraded states are inevitably added later.

### [NOTE] Debug-log `fallback_used` field diverges from `ReviewResult.fallback_used` for the same event

In the newly-added genuinely-unknown branch, `_write_debug_log` is called with `fallback_used=True` (parsers.py:523), while the `ReviewResult.fallback_used` the caller keeps for this same event is deliberately left `False` (per the comment at 516-517 and confirmed by `test_unknown_verdict_result_does_not_claim_fallback`). The two are tracking genuinely different things (log: "this was a degraded parse of some kind" vs. result: "findings were specifically un-derivable from a known verdict"), but sharing the field name `fallback_used` with opposite values for the same event is a trap for anyone correlating `review-debug.jsonl` entries against persisted `ReviewResult`/artifact state. Consider renaming the debug-log field (e.g. `degraded`) to decouple it from `ReviewResult.fallback_used`'s narrower meaning.

### [PASS] Tool-use guidance composed once at the agent boundary

`compose_system_prompt` is a small, pure, well-documented function, and `OpenAICompatibleAgent.__init__` composes it once after tool resolution (src/squadron/providers/openai/agent.py:193-198) rather than at each of the four call sites, so no tool-passing caller can skip the discipline block. Matches the stated D1 design and is covered by both direct unit tests (tests/tools/test_guidance.py) and provider-plumbing tests (tests/providers/openai/test_agent.py `TestToolUseGuidanceComposition`).

### [PASS] SDK preset/append composition matches the documented truth table and is tested for all four rows

The `use_default_system_prompt` × `instructions` truth table added to `AgentConfig`'s docstring (src/squadron/core/models.py:53-57) is implemented exactly as documented and each of the four rows has a corresponding test in tests/providers/sdk/test_provider.py, including the "empty string is not something to append" edge case.
