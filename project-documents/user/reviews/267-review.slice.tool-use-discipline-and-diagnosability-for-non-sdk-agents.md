---
docType: review
layer: project
reviewType: slice
slice: tool-use-discipline-and-diagnosability-for-non-sdk-agents
project: squadron
verdict: CONCERNS
sourceDocument: project-documents/user/slices/267-slice.tool-use-discipline-and-diagnosability-for-non-sdk-agents.md
aiModel: moonshotai/kimi-k3
status: complete
dateCreated: 20260907
dateUpdated: 20260907
reviewedSha: d6ff135c9908fcb472da0b3782dc3c100a3d829b
toolsGiven: [read_file, list_files, grep]
toolCallsMade: 28
findings:
  - id: F001
    severity: pass
    category: alignment
    summary: "Guidance-block composition point is architecturally sound and consistent with prior slices"
    location: "slices/267-slice.tool-use-discipline-and-diagnosability-for-non-sdk-agents.md:135-163"
  - id: F002
    severity: pass
    category: dependency-direction
    summary: "Dependency directions and integration points match the architecture's layer boundaries"
    location: "slices/267-slice.tool-use-discipline-and-diagnosability-for-non-sdk-agents.md:273-295"
  - id: F003
    severity: pass
    category: scope
    summary: "No scope creep relative to the slice plan — the one addition is documented"
    location: "slices/267-slice.tool-use-discipline-and-diagnosability-for-non-sdk-agents.md:36-55"
  - id: F004
    severity: pass
    category: error-handling
    summary: "Failure modes and diagnosability are handled explicitly, not left implicit"
    location: "slices/267-slice.tool-use-discipline-and-diagnosability-for-non-sdk-agents.md:193-226"
  - id: F005
    severity: concern
    category: nfr / goal-tension
    summary: "The \"no SDK-path regression\" goal is in real tension with the #85 preset+append change, and the live verification for it is weakly specified"
    location: "slices/267-slice.tool-use-discipline-and-diagnosability-for-non-sdk-agents.md:250-271"
  - id: F006
    severity: concern
    category: nfr
    summary: "The only new conditional NFR-relevant parameter (`agent.max_output_tokens`) has no stated target value or sizing guidance"
    location: "slices/267-slice.tool-use-discipline-and-diagnosability-for-non-sdk-agents.md:218-226"
  - id: F007
    severity: note
    category: informational
    summary: "Guidance-block wording is deferred to implementation by design; SC10 is the real acceptance"
    location: "slices/267-slice.tool-use-discipline-and-diagnosability-for-non-sdk-agents.md:165-190"
---

# Review: slice — slice 267

**Verdict:** CONCERNS
**Model:** moonshotai/kimi-k3

## Findings

### [PASS] Guidance-block composition point is architecturally sound and consistent with prior slices

The decision to compose the guidance block in `OpenAICompatibleAgent.__init__` (D1) is well-reasoned and correctly distinguishes this case from slice 266's capability gate: the block depends only on the effective tool list, which the agent does see, so a real chokepoint exists — unlike the alias-capability gate, which required an enumeration test. The doc explicitly leaves 266's SC1a enumeration test untouched and states why it is still needed (the gate stays where it was). This is consistent with the architecture's "single definition" principle and avoids a second, redundant enforcement mechanism.

### [PASS] Dependency directions and integration points match the architecture's layer boundaries

New code flows in the correct direction: `squadron.tools.guidance` is consumed by the provider layer (`providers/openai/agent.py`); dispatch/review changes live in their respective layers; the SDK translation stays at the SDK config edge (`providers/sdk/provider.py`), unchanged from 265's D2. No layer reaches upward. The declared dependencies `[262, 265, 266]` match the actual couplings: 262 supplies `_run_agentic_loop`/`_stream_turn`, 265 supplies `translate_tool_names` and the canonical vocabulary, 266 supplies `resolve_effective_tools` and `tools_suppressed_reason`.

### [PASS] No scope creep relative to the slice plan — the one addition is documented

Item 3a (#85, SDK preset + append) is the only scope not in the slice plan's entry 7 text, and the plan was amended 20260907 to record it ("Scope added 20260907: SDK reviews send the CLI's default system prompt… the plan text above saying SDK reviewers already inherit that prompt was wrong"). The Out-of-Scope section correctly carries forward the initiative's exclusions (#69, #36/#33, SDK session path, parser downgrade) and adds one new principled exclusion (guidance block on SDK agents, tied to the arch's "no SDK-path regression" goal).

### [PASS] Failure modes and diagnosability are handled explicitly, not left implicit

The three diagnosability items each name the concrete failure and its handling: UNKNOWN parse now writes the debug log at every verbosity (evidence retention, not a flag); degraded artifacts embed the raw response keyed on the *resolved* verdict (with the judge/score-derived carve-out explained); zero-call is surfaced both as a distinct terminal line and a WARNING log. The #84 empty-final-turn item is evidence-gated (D4) per the project's anti-speculative-fix rule rather than adding a config key for a hypothesis. This slice introduces no new long-lived I/O paths of its own (it reuses the existing streaming loop), so the hang/timeout/peer-disconnect surface is unchanged from 262 — acceptable at this layer.

### [CONCERN] The "no SDK-path regression" goal is in real tension with the #85 preset+append change, and the live verification for it is weakly specified

The architecture states as a design goal: "**No SDK-path regression.** `ClaudeSDKAgent` and `CodexAgent` paths are unchanged." D2a/D2 acknowledge #85 is "an SDK-path behavior change," and the doc mitigates by scoping the change to the review config only (audit path unchanged, non-SDK providers never read the flag — SC7a pins all three). That containment is good. However, the live check (walkthrough §2a, line ~416-421) reduces "no regression" to "compare its findings with the most recent SDK review of the same slice on main… record the two finding counts." Finding counts on a single subjective review are a weak proxy for a prompt-level change, and SC7a's "no regression in verdict or finding quality" is not an objective, checkable bar. Given the architecture elevates this to a stated goal, the slice should define a more concrete regression criterion (e.g., a fixed rubric, or explicitly accept the subjectivity and time-box it) rather than rest the goal on one eyeball comparison. Not blocking — the audit path (the arch's actual measurement surface) is verifiably unchanged — but the goal is only partially discharged.

### [CONCERN] The only new conditional NFR-relevant parameter (`agent.max_output_tokens`) has no stated target value or sizing guidance

The slice plan (entry 7) says for #84: "if it is `length`, `max_tokens` is sized against reasoning models on the request." The slice doc implements the evidence-gating well (D4, SC8) but drops the "sized against reasoning models" requirement — it registers `agent.max_output_tokens` as `int, default None` with no statement of what value it should take when set, and the Risks section notes that `max_tokens` semantics differ across backends (reasoning tokens counted or not) without giving the operator a way to reason about a correct value. The parent architecture doc itself states no numeric NFR for this path, so this is not a restatement violation; but for a parameter whose entire justification is a provider-specific failure mode, the absence of any target or derivation guidance is under-specification. SC8(a) ("`agent.max_output_tokens` is wired and tested") is satisfiable by wiring alone, without establishing the value is correct.

### [NOTE] Guidance-block wording is deferred to implementation by design; SC10 is the real acceptance

The block's substance is given as four bullets "to be worded at implementation," and SC1/SC2 test only presence, ordering, and tool-name rendering — not content. This is a deliberate and defensible choice (the Risks section is explicit that prompt-driven behavior is provable only live, and SC10's `--no-tools` A/B is the stated usability bar with a defined fallback in D5). It does mean the block's text is unreviewable at design time; that is accepted risk, recorded here so it is not mistaken for an omission.
