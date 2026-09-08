---
docType: tasks
slice: tool-use-discipline-and-diagnosability-for-non-sdk-agents
project: squadron
lld: user/slices/267-slice.tool-use-discipline-and-diagnosability-for-non-sdk-agents.md
dependencies: [262, 265, 266]
projectState: >
  Slice 267 design complete and review round 1 addressed (CONCERNS resolved
  20260907: SC7b live regression conditions, D4 max_tokens derivation). Slices
  261-266 shipped the non-SDK tool stack; 267 is the close-out slice of
  initiative 260 and owns #40, #61, #68, #75, #82, #84, #85.
dateCreated: 20260907
dateUpdated: 20260908
status: in_progress
---

## Context Summary

- Working on the **tool-use-discipline-and-diagnosability-for-non-sdk-agents**
  slice (267), close-out of initiative 260. Parent:
  `260-slices.non-sdk-agent-tool-use-openai-compatible-agentic-loop.md`, entry 7.
- Four independent parts plus a live-verification part:
  - **Part A — Discipline:** one guidance block in `squadron/tools/guidance.py`,
    composed once in `OpenAICompatibleAgent.__init__` (D1, D2).
  - **Part B — Dispatch parity and #40:** SDK guard removed, SDK default system
    prompt, empty non-SDK instructions become `None`, session message reworded (D6).
  - **Part C — SDK reviews (#85):** preset + `append` (D2a).
  - **Part D — Diagnosability (#61):** UNKNOWN debug log, degraded artifacts
    embed the raw response, `Tools:` line at `-v` (D3).
  - **Part E — Live verification:** the walkthrough's live steps, the #84
    evidence loop (D4), and the SC10 A/B that is the initiative's acceptance.
- **Effort 3/5.** Code is small; acceptance is live and may need a second
  iteration on #84.
- **Next:** none in initiative 260. Issue #86 (jail root for slice/arch/tasks
  reviews) is out of scope; workaround `--cwd .` from repo root.

### Commit checkpoints

Per-task commit is the default. The PM's standing preference for this
initiative: prompt-affecting changes (Parts A and C) are confirmed by a live
run before their commits are treated as final, so keep them on the slice
branch and do not merge until Part E's live steps are recorded. Parts B and D
are suite-provable and commit normally.

### Grounding notes (verified against the code 20260907)

- **Composition point:** `OpenAICompatibleAgent.__init__`
  ([agent.py:117-160](src/squadron/providers/openai/agent.py#L117-L160)) appends
  the system message only when `system_prompt is not None`. The provider passes
  `config.instructions` at
  [provider.py:76](src/squadron/providers/openai/provider.py#L76) and reads the
  three `agent.*` keys at lines 62-66. The agent must receive the effective tool
  list to compose — check how `allowed_tools` reaches the constructor today
  before adding a parameter.
- **SDK guard to remove:**
  [dispatch.py:122-127](src/squadron/pipeline/actions/dispatch.py#L122-L127).
  **Session-path message to reword:**
  [dispatch.py:277-286](src/squadron/pipeline/actions/dispatch.py#L277-L286).
  `instructions=system_prompt` at line 136 is where `""` must become `None`.
- **Existing tests that must change:** `test_sdk_profile_one_shot_rejects_allowed_tools`
  ([test_dispatch.py:522](tests/pipeline/actions/test_dispatch.py#L522)) asserts
  the guard this slice removes; `test_default_system_prompt_wins_over_instructions`
  ([test_provider.py:108](tests/providers/sdk/test_provider.py#L108)) asserts the
  preset-discards-instructions behavior #85 replaces. Both are rewritten, not
  deleted.
- **SDK preset:** [sdk/provider.py:51-54](src/squadron/providers/sdk/provider.py#L51-L54).
  Installed `claude-agent-sdk` 0.1.38 `SystemPromptPreset` has
  `append: NotRequired[str]`.
- **Parser branches:** the UNKNOWN branch is
  [parsers.py:503-513](src/squadron/review/parsers.py#L503-L513); its siblings
  call `_write_debug_log` (signature at parsers.py:416).
- **Persistence:** the `-vv` promise is
  [persistence.py:274-278](src/squadron/review/persistence.py#L274-L278); the raw
  response renders only inside the `system_prompt is not None` appendix
  (persistence.py:285-305). `ReviewResult.to_dict` resolves a judge's verdict
  from its score — key SC4 on the *resolved* verdict.
- **CLI:** the `-vv` hint is
  [review.py:134-136](src/squadron/cli/commands/review.py#L134-L136);
  `_display_terminal` is review.py:108. The review client reads
  `tools_given` / `tool_calls_made` at
  [review_client.py:225-228](src/squadron/review/review_client.py#L225-L228).
- **Precedent for the #40 flag:** `metrology/audit.py:634` sets
  `use_default_system_prompt=True`; `executor.py` and `run.py` are the dispatch
  precedents the design cites — confirm both before copying.
- **Live runs** are executed by the PM from a plain terminal, prefixed
  `uv run`. `sq run` refuses inside a Claude Code session. Models: `kimi27`
  (`moonshotai/kimi-k2.7-code`) and `sonnet`.

---

## Part 0 — Branch

- [x] **T0. Create the slice branch**
  - [x] `cf config get git.integration_branch` is empty, so the target is `main`.
  - [x] `git checkout -b 267-slice.tool-use-discipline-and-diagnosability-for-non-sdk-agents main`
  - [x] Set the slice design's `status` to `in_progress`.
  - [x] **Success:** on the new branch, working tree clean.
  - Effort: 1/5

---

## Part A — The guidance block (D1, D2)

- [x] **T1. Write `squadron/tools/guidance.py`**
  - [x] New module owning the block text and
    `compose_system_prompt(instructions: str | None, tools: list[str] | None) -> str | None`.
  - [x] Empty or `None` `tools` → return `instructions` unchanged (including
    `None`). Non-empty → `instructions` followed by a blank line and the block
    under a `## Tool Use` heading; `None`/`""` instructions yield the block alone.
  - [x] Render the effective tool names into the block, comma-separated, so
    the model sees what it has. Do not name specific tools in the prose; the
    same block serves reviews and design dispatch.
  - [x] Substance, per the design's "The guidance block" section: a diff is
    partial context and cannot prove absence; before asserting something is
    missing, undefined, unhandled, unnarrowed, or unjustified, open the file
    with the tools or say "unverified"; use a tool only when a claim depends on
    unseen code; if the task asks for a file to be created or changed, do it
    with the tools. Keep it short; tool-call count is not a goal (#82).
  - [x] Export `compose_system_prompt` from `squadron.tools` (`__init__.py`).
  - [x] **Success:** module under ~80 lines; the four substance points are all
    present; no tool name appears in the prose body.
  - Effort: 2/5

- [x] **T2. Test `compose_system_prompt`** *(test-with T1)*
  - [x] New `tests/tools/test_guidance.py`.
  - [x] Cases: `(None, None)` → `None`; `("x", [])` → `"x"`; `("x", None)` →
    `"x"`; `("x", ["read_file", "grep"])` starts with `"x"`, contains
    `## Tool Use`, contains both tool names, and the heading comes after `"x"`;
    `(None, ["read_file"])` → block alone, no leading blank line.
  - [x] **Success:** tests pass; SC2's "instructions precede the block" is
    asserted by position, not by substring presence alone.
  - Effort: 1/5

- [x] **T3. Compose in `OpenAICompatibleAgent.__init__`**
  - [x] Give the constructor access to the effective tool list (whatever form
    the provider already passes — do not add a second source of truth) and
    replace the direct `system_prompt` append at agent.py:159-160 with
    `compose_system_prompt(system_prompt, <effective tools>)`.
  - [x] The system message is built once at construction; nothing in the turn
    loop changes.
  - [x] Do not touch `resolve_effective_tools` or its four call sites; the
    SC1a enumeration test in `tests/tools/test_effective_tools.py` stays as is.
  - [x] **Success:** `history[0]` is the composed prompt when tools are
    non-empty; unchanged behavior when tools are empty; no system message when
    both are absent.
  - Effort: 2/5

- [x] **T4. Test composition at the agent** *(test-with T3)*
  - [x] In `tests/providers/openai/test_agent.py`, beside
    `test_system_prompt_prepended_to_history`: an agent built with
    `allowed_tools=[read_file, grep]` has a system message ending in the block
    naming both, preceded by the caller's instructions; an agent with
    `allowed_tools=[]` and `tools_suppressed_reason="run-suppressed"` has the
    caller's instructions only; an agent with neither has an empty history.
  - [x] One test goes through `OpenAICompatibleProvider.create_agent` with an
    `AgentConfig`, not the constructor directly, so the provider's plumbing is
    covered.
  - [x] Run `uv run pytest tests/tools/test_effective_tools.py` and confirm it
    is untouched and green.
  - [x] **Success:** SC1 and SC2 hold at the agent; SC1a test unchanged.
  - Effort: 2/5

---

## Part B — Dispatch parity and #40 (D6)

- [x] **T5. Non-SDK dispatch sends no empty system message**
  - [x] In `one_shot_dispatch_with_telemetry`, when the profile is non-SDK and
    `system_prompt` is empty, pass `instructions=None` (dispatch.py:136). With
    tools, the guidance block then becomes the whole system prompt via T3.
  - [x] **Success:** a non-SDK step with no `system_prompt` and no tools builds
    an `AgentConfig` with `instructions=None` (SC7, second half).
  - Effort: 1/5

- [x] **T6. SDK one-shot dispatch uses the default system prompt**
  - [x] Same function: when the profile is SDK and no explicit `system_prompt`
    was supplied, set `use_default_system_prompt=True`. An explicit
    `system_prompt` still wins (flag stays `False`).
  - [x] Confirm the `executor.py` / `run.py` precedent the design cites before
    copying its condition; if the precedent differs from the design, stop and
    report.
  - [x] **Precedent:** metrology/audit.py:634 sets `use_default_system_prompt=True`; confirmed as the real precedent and implemented as designed.
  - [x] **Success:** SC7, first half.
  - Effort: 1/5

- [x] **T7. Remove the SDK `allowed_tools` guard; reword the session message**
  - [x] Delete the `ValueError` block at dispatch.py:122-127 and its comment.
    The canonical names reach `AgentConfig.allowed_tools`;
    `ClaudeSDKProvider.create_agent` translates or raises on an unmapped name.
  - [x] Session path (dispatch.py:277-286): keep the rejection; change the
    message from "does not yet support them" to the reason — a persistent
    session's tool set is fixed when it connects. Update the comment above it
    to match (it currently says slice 265 owns the wiring).
  - [x] **Success:** no SDK guard in the one-shot path; session message states
    the fixed-at-connect reason.
  - Effort: 1/5

- [x] **T8. Dispatch tests** *(test-with T5-T7)*
  - [x] Rewrite `test_sdk_profile_one_shot_rejects_allowed_tools` into a test
    that a step with `allowed_tools: [read_file]` on an SDK profile builds an
    `AgentConfig` carrying the canonical name, and that the SDK provider
    receives `["Read"]` (mock `create_agent` and inspect the options, or reuse
    the pattern `tests/providers/sdk/test_translation.py` uses).
  - [x] Add: an unmapped canonical name still raises from the provider.
  - [x] Add: SDK one-shot with no `system_prompt` → `use_default_system_prompt`
    is `True`; with explicit `system_prompt` → `False` and `instructions` set.
  - [x] Add: non-SDK one-shot with empty `system_prompt` → `instructions is None`.
  - [x] Update `test_sdk_session_path_rejects_allowed_tools` (test_dispatch.py:501)
    to the reworded message if it asserts on text.
  - [x] **Success:** SC6 and SC7 asserted; `uv run pytest tests/pipeline/actions` (1255 passed, 2 skipped) green.
  - Effort: 2/5

---

## Part C — SDK reviews carry the CLI prompt (#85, D2a)

- [x] **T9. Preset carries `append` when instructions are present**
  - [x] In `ClaudeSDKProvider.create_agent` (sdk/provider.py:51-54): when
    `use_default_system_prompt` is set and `instructions` is a non-empty
    string, send `{"type": "preset", "preset": "claude_code", "append": instructions}`.
    `None` or `""` instructions keep the bare preset (audit row unchanged).
  - [x] Update the `use_default_system_prompt` docstring in `core/models.py:52`
    to the design's four-row truth table.
  - [x] **Success:** the four rows of the table are each reachable and produce
    the stated shape.
  - Effort: 1/5

- [x] **T10. SDK provider tests** *(test-with T9)*
  - [x] Rewrite `test_default_system_prompt_wins_over_instructions`
    (test_provider.py:108) to assert preset + `append`.
  - [x] Add a test for each remaining row: `False/None` → no `system_prompt`
    kwarg; `False/str` → the string; `True/None` and `True/""` → bare preset
    with no `append` key.
  - [x] **Success:** SC7a's shape assertions; `test_default_system_prompt_uses_preset`
    still passes unchanged.
  - Effort: 1/5

- [x] **T11. Review client sets the flag; appendix notes the preset**
  - [x] In `run_review_with_profile` (review_client.py:170), set
    `use_default_system_prompt=True` on the review `AgentConfig` when the
    provider is SDK. Non-SDK providers never read the flag; leave it `False`
    there so the intent is explicit in the config.
  - [x] Carry a "preset used" fact onto `ReviewResult` (one boolean, populated
    with the other prompt-capture fields at verbosity ≥ 2) and have
    `format_review_markdown`'s `### System Prompt` section print one line
    stating the `claude_code` preset was used and the recorded text is the
    appended part.
  - [x] Confirm `metrology/audit.py:625-634` is untouched.
  - [x] **Success:** SDK review config has the flag; non-SDK review config does
    not; `-vv` artifact of an SDK review carries the preset line.
  - Effort: 2/5

- [x] **T12. Review client tests** *(test-with T11)*
  - [x] In `tests/review/test_review_client.py`: SDK profile → the `AgentConfig`
    handed to `create_agent` has `use_default_system_prompt=True` and
    `instructions` equal to the composed template prompt; non-SDK profile →
    flag `False`, `instructions` unchanged from today's assertion.
  - [x] In `tests/review/test_persistence.py`: the preset line appears in the
    appendix only when the boolean is set.
  - [x] Run the design's §2a selector and confirm it matches tests:
    `uv run pytest tests/providers/sdk/test_provider.py tests/review/test_review_client.py -k "preset or default_system_prompt" -v`.
    Name new tests so the selector catches them.
  - [x] **Success:** SC7a fully asserted; selector reports collected tests > 0.
  - Effort: 1/5

- [ ] **T13. Commit Parts A-C** as separate commits per part, on the slice
  branch. Do not merge (see Commit checkpoints).
  - Effort: 1/5

---

## Part D — Diagnosability (#61, D3)

- [x] **T14. Parser UNKNOWN branch writes the debug log**
  - [x] In the `elif verdict is Verdict.UNKNOWN:` branch (parsers.py:503), call
    `_write_debug_log(..., findings_parsed=0, fallback_used=True, raw_output=raw_output)`
    after the existing warning, matching the two sibling branches.
  - [x] Do not set the result's `fallback_used` from this branch unless the
    siblings do — check before changing the return value.
  - [x] **Success:** UNKNOWN-with-no-findings writes an entry at every verbosity.
  - Effort: 1/5

- [x] **T15. Parser test** *(test-with T14)*
  - [x] In `tests/review/test_parsers.py`, find how the sibling branches' debug
    log is asserted (patch `_DEBUG_LOG_PATH` to `tmp_path`) and add the UNKNOWN
    case: raw output with no `## Summary` verdict and no findings produces an
    entry containing the raw output.
  - [x] Name it so `-k "unknown"` matches (walkthrough §4).
  - [x] **Success:** SC3.
  - Effort: 1/5

- [x] **T16. Degraded artifacts embed the raw response; fix the `-vv` promise**
  - [x] In `format_review_markdown`: when the *resolved* verdict is UNKNOWN or
    `result.fallback_used`, add a `### Raw Response` section carrying
    `result.raw_output` at every verbosity. Compute the resolved verdict the
    same way the frontmatter does (verdict override / score-derived), not from
    the raw parse — a judge with a score must not embed.
  - [x] When the `-vv` appendix is also present, render the raw response once:
    the appendix's own `### Raw Response` is skipped when the degraded section
    already printed it (or vice versa — pick one and comment why).
  - [x] Replace the "present when the review ran at `-vv` or higher" sentence
    (persistence.py:274-278) with text that is true: the raw response is in
    this artifact.
  - [x] Add a body section for the UNKNOWN case too — today an UNKNOWN with no
    findings falls through to "No specific findings.", which is the misleading
    line D3 names.
  - [x] **Success:** a clean PASS artifact is byte-identical to before; an
    UNKNOWN or `fallback_used` artifact contains the raw response once at
    verbosity 0 and once at verbosity 2.
  - Effort: 2/5

- [x] **T17. Persistence tests** *(test-with T16)*
  - [x] In `tests/review/test_persistence.py`: (1) UNKNOWN result at verbosity 0
    contains the raw response; (2) `fallback_used` result contains it; (3) a
    clean PASS's markdown equals a snapshot captured *before* T16 (take the
    snapshot first, on the T13 commit); (4) a judge result with a score and raw
    parse UNKNOWN does not contain its raw response; (5) degraded result with
    `system_prompt` set contains `### Raw Response` exactly once.
  - [x] Name tests so `-k "raw_response or degraded"` matches (walkthrough §4).
  - [x] **Success:** SC4; both §4 selectors report collected tests > 0.
  - Effort: 2/5

- [x] **T18. `Tools:` line at `-v`; client WARNING; hint corrected**
  - [x] In `_display_terminal` (review.py:108), after the verdict panel and
    only at `verbosity >= 1`, print one line when the result carries tool
    telemetry, in the three forms from the design's table: names + count;
    names + `0 calls (offered, none used)` in warning style (`bold yellow`,
    matching the degraded line); `suppressed (reason=...)`. A result with no
    telemetry at all prints nothing.
  - [x] Replace the "re-run with -vv to capture it" hint (review.py:134-136)
    with text pointing at the artifact's raw response section.
  - [x] In `run_review_with_profile` after `result.tool_calls_made` is set
    (review_client.py:253): `_logger.warning` when `tools_given` is non-empty
    and `tool_calls_made == 0`.
  - [x] **Success:** three distinct lines; no line at verbosity 0; WARNING on
    zero calls.
  - Effort: 2/5

- [x] **T19. CLI and client tests** *(test-with T18)*
  - [x] In `tests/review/test_cli_review.py` or `tests/cli/test_review_format.py`
    (whichever already drives `_display_terminal` with a captured console):
    one test per form, plus verbosity 0 prints no `Tools:` line, plus a
    telemetry-less result prints none at `-v`.
  - [x] In `tests/review/test_review_client.py`: `caplog` asserts the WARNING
    on tools-given-zero-calls and its absence when calls > 0.
  - [x] **Success:** SC5 asserted; the zero-call test checks the style, not
    only the text.
  - Effort: 1/5

- [ ] **T20. Commit Part D** (one commit per T14/T16/T18 pair with its tests).
  - Effort: 1/5

---

## Part E — Live verification and #84 (D4)

Steps marked *(live)* are run by the PM from a plain terminal. Transcribe each
result into the design's Verification Walkthrough under an `Observed:` line,
as slices 265 and 266 did. `<slice>` is 267's own diff unless the PM names
another.

- [ ] **T21. Walkthrough §1 and §4 — unit confirmation**
  - [ ] `uv run pytest tests/tools/test_guidance.py tests/providers/openai/test_agent.py -v`
  - [ ] `uv run pytest tests/review/test_parsers.py tests/review/test_persistence.py -k "unknown or raw_response or degraded" -v`
  - [ ] **Success:** both green; each `-k` selector collected > 0 tests.
  - Effort: 1/5

- [ ] **T22. Walkthrough §2 — zero calls visible** *(live)*
  - [ ] `uv run sq review code <slice> --model kimi27 -v`
  - [ ] Record the `Tools:` line and the artifact's `toolsGiven` /
    `toolCallsMade` values. If calls are zero, the warning form and a stderr
    WARNING must both appear.
  - [ ] Also open a real degraded artifact (F004): find or produce one with
    resolved verdict UNKNOWN or `fallback_used` (re-running the review that
    produced #84 in T26 is a likely source), and confirm `### Raw Response`
    appears exactly once at verbosity 0 and exactly once at `-vv`. If no
    degraded artifact arises from any Part E run, say so under `Observed:`
    and rely on T17.
  - [ ] **Success:** SC5 observed live; values transcribed; degraded-artifact
    check recorded.
  - Effort: 1/5

- [ ] **T23. Walkthrough §2a — SDK before/after** *(live)*
  - [ ] Locate the most recent SDK review of `<slice>` on `main` (the "before").
    If none exists, run one on `main` before switching to the slice branch.
  - [ ] `uv run sq review code <slice> --model sonnet -v` on the slice branch.
  - [ ] Check SC7b's three conditions against the before: verdict not worse;
    every `location:` resolves; no nonexistent path or symbol cited. Record
    both finding counts.
  - [ ] **Success:** all three conditions hold; counts transcribed. A failure
    on any condition stops the slice — report to the PM.
  - Effort: 2/5

- [ ] **T24. Walkthrough §3 — the SC10 A/B** *(live)*
  - [ ] `uv run sq review code <slice> --model kimi27 --no-tools -v` then the
    same without `--no-tools`.
  - [ ] Tools run must record `toolCallsMade > 0`. Read every finding in both
    artifacts; none in the tools run may claim a symbol is undefined, unbound,
    unnarrowed, or unjustified when the repository defines it.
  - [ ] Record finding counts and any absence claims in the design's §3.
  - [ ] If the tools run shows zero calls or an absence claim: do not add a
    parser heuristic (D5). File a follow-up issue for D5's parser downgrade,
    link it from the design's Risks section, and report to the PM.
  - [ ] **Success:** SC10 observed and transcribed, or the follow-up issue
    filed and the failure reported.
  - Effort: 2/5

- [ ] **T25. Walkthrough §5 — SDK pipeline dispatch** *(live)*
  - [ ] `uv run pytest tests/pipeline/actions/test_dispatch.py -v` (unit half).
  - [ ] `uv run sq run test-p4 <slice> --model sonnet -v` from a plain terminal
    on a pipeline whose step declares `allowed_tools`.
  - [ ] **Success:** the step runs and its result line carries a `tools=`
    segment, not the former vocabulary error.
  - Effort: 1/5

- [ ] **T26. Walkthrough §6 — capture the #84 cause** *(live)*
  - [ ] `uv run sq review code 266 --model kimi27 -v`
  - [ ] If the empty turn recurs, record `finish_reason` and `reasoning_chars`
    from the exit-1 message as a comment on #84. If it does not recur, record
    that on #84 too.
  - [ ] **Success:** #84 carries the observation. Decide T27 from it.
  - Effort: 1/5

- [ ] **T27. Conditional: `agent.max_output_tokens`** *(only if T26 observed `finish_reason=length`)*
  - [ ] Register `agent.max_output_tokens` in `config/keys.py` beside the three
    `agent.*` keys (int, default `None` = parameter omitted). The description
    records D4's derivation: exceed the observed `reasoning_chars` converted to
    tokens plus a full review's output, within the model's documented output
    limit, assuming reasoning tokens count against `max_tokens`.
  - [ ] Read it in `OpenAICompatibleProvider.create_agent` beside the other
    keys (provider.py:62-66) and pass it to the agent; `_stream_turn`
    (agent.py:247) sends `max_tokens=` only when set.
  - [ ] Tests in `tests/providers/openai/test_provider.py` and `test_agent.py`:
    unset → no `max_tokens` kwarg on the request; set → the value is sent.
  - [ ] Re-run T26's command with the derived value in
    `~/.config/squadron/config.toml` and record the outcome on #84.
  - [ ] If T26 showed any other cause or no recurrence: do not add the key.
    Write an `Observed:` line under the design's §6 stating the observed
    `finish_reason` (or "did not recur") and that no key was added, then mark
    this task `[x]` with the note "not needed — see #84".
  - [ ] **Success:** the design's §6 carries an `Observed:` line naming which
    SC8 branch was taken; branch (a) additionally has the key, tests, and the
    re-run result on #84.
  - Effort: 2/5

- [ ] **T28. Close #68** *(live)*
  - [ ] Run a `tasks` review through a non-SDK alias (`uv run sq review tasks
    267 --model kimi27 --cwd .` — the `--cwd .` works around #86) and confirm
    the artifact's frontmatter carries `toolsGiven` and `toolCallsMade`.
  - [ ] Comment on #68 citing those fields and slices 265, 266, 267, then close.
  - [ ] **Success:** SC9.
  - Effort: 1/5

---

## Part F — Close-out

- [ ] **T29. Full gate set**
  - [ ] `uv run ruff format .` — immediately before committing.
  - [ ] `uv run ruff check .`
  - [ ] `uv run pytest -q`
  - [ ] `uv run pyright` — no new errors beyond the two pre-existing
    `mcp_bridge.py` ones (#74).
  - [ ] **Success:** all green (SC11).
  - Effort: 1/5

- [ ] **T30. Slice close-out**
  - [ ] Transcribe every `Observed:` line from Part E into the design's
    Verification Walkthrough; none of §2, §2a, §3, §5, §6 may still read as an
    expectation.
  - [ ] Write the DEVLOG entry per `prompt.ai-project.system.md`, "Session
    State Summary". Include which SC8 branch was taken and the SC10 outcome.
  - [ ] Mark slice 267 complete in the slice design and in
    `260-slices.non-sdk-agent-tool-use-openai-compatible-agentic-loop.md`
    entry 7; the initiative is then closed, so update its status too.
  - [ ] Close #40, #61, #75, #82, #85 with a comment naming the commit; #84
    per T26/T27; #68 per T28.
  - [ ] Mark any dropped or skipped item `[x]` with a note before closing.
  - [ ] Merge the slice branch into `main`; do not delete the branch.
  - [ ] **Success:** DEVLOG entry present; slice plan reads 7/7; issues closed.
  - Effort: 1/5

---

## Task Review

**Round 1 — 20260907, `sq review tasks 267 --model kimi3`, verdict CONCERNS.**
Artifact: `reviews/267-review.tasks.tool-use-discipline-and-diagnosability-for-non-sdk-agents.md`
(reviewedSha `6aaa75b`, 8 tool calls).

| Finding | Disposition |
|---|---|
| F001–F003 (PASS) | No action. |
| F004 (CONCERN) — no live check of a degraded artifact | **Addressed.** T22 opens a real degraded artifact and confirms `### Raw Response` once at each verbosity. |
| F005 (CONCERN) — T27's negative exit had no artifact | **Addressed.** Both exits now write an `Observed:` line under the design's §6. |
| F006 (NOTE) — grounding anchors unverifiable from the jail | **Not a task gap.** The reviewer's jail was `project-documents/user` (#86); anchors were verified from the repo root. |
