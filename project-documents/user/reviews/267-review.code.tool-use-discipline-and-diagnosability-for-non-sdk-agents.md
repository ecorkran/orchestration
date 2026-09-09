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
toolsGiven: [read_file, list_files, grep]
toolCallsMade: 14
findings:
  - id: F001
    severity: pass
    category: maintainability
    summary: "Degraded review messaging is centralized and consistent"
    location: "src/squadron/review/persistence.py:175"
  - id: F002
    severity: pass
    category: design
    summary: "Tool-use guidance is composed at the agent constructor boundary"
    location: "src/squadron/providers/openai/agent.py:193"
  - id: F003
    severity: pass
    category: correctness
    summary: "SDK preset appends template instructions instead of replacing them"
    location: "src/squadron/providers/sdk/provider.py:55"
  - id: F004
    severity: pass
    category: observability
    summary: "UNKNOWN verdict degradation is visible in terminal and artifact"
    location: "src/squadron/cli/commands/review.py:159"
  - id: F005
    severity: pass
    category: testing
    summary: "Test coverage accompanies the implementation"
    location: "tests/tools/test_guidance.py:1"
---

# Review: code — slice 267

**Verdict:** PASS
**Model:** moonshotai/kimi-k2.7-code

## Findings

### [PASS] Degraded review messaging is centralized and consistent

The new `_findings_not_parsed_section` helper unifies the two degraded paths (verdict-without-findings and UNKNOWN-without-findings) so both prose sections stay consistent; only the cause varies. This avoids the drift risk that issue #72 and #61 fixed independently.

### [PASS] Tool-use guidance is composed at the agent constructor boundary

Moving composition into `OpenAICompatibleAgent.__init__` via `tools.compose_system_prompt` means no caller that passes tools can accidentally ship an agent without the discipline block (design D1). The block names only the effective tools, keeping the prose tool-agnostic.

### [PASS] SDK preset appends template instructions instead of replacing them

`ClaudeSDKProvider.create_agent` now sends the `claude_code` preset with `append=config.instructions` when `use_default_system_prompt` is true. This resolves #85: reviews get both the CLI's tool-use discipline and their own instructions, and the empty-instructions case stays a bare preset as documented.

### [PASS] UNKNOWN verdict degradation is visible in terminal and artifact

`_display_terminal` now distinguishes the "no verdict and no findings" UNKNOWN case from a clean no-findings review, and `format_review_markdown` embeds the raw response for degraded reviews at the default verbosity. The previous `-vv`-only promise is replaced by an accurate pointer to the saved artifact.

### [PASS] Test coverage accompanies the implementation

New tests cover guidance composition, SDK preset append behavior, dispatch one-shot SDK tool acceptance, UNKNOWN verdict debug logging, degraded raw-response embedding, and terminal tool telemetry. They mock external boundaries and assert on observable signals rather than implementation details.
