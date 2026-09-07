---
docType: slice-design
project: squadron
slice: 267-slice.tool-use-discipline-and-diagnosability-for-non-sdk-agents
parent: 260-slices.non-sdk-agent-tool-use-openai-compatible-agentic-loop.md
dependencies: [262, 265, 266]
interfaces:
  - name: compose_system_prompt
    module: squadron.tools.guidance
    contract: >-
      Returns the system prompt a tool-enabled non-SDK agent runs with: the caller's
      instructions plus the shared tool-use guidance block, or the instructions unchanged
      when no tools are offered. Called from exactly one place, OpenAICompatibleAgent's
      constructor, so no tool-passing caller can skip it.
dateCreated: 20260907
dateUpdated: 20260907
status: not_started
---

# Slice Design: Tool-Use Discipline and Diagnosability for Non-SDK Agents

## Parent Documents

- Architecture: `260-arch.non-sdk-agent-tool-use-openai-compatible-agentic-loop.md`
- Slice Plan: `260-slices.non-sdk-agent-tool-use-openai-compatible-agentic-loop.md`, entry 7

## Overview

Slices 261–266 made the mechanics of non-SDK tool use work and made every state of it
recordable. Slice 266's live verification then showed what the mechanics alone produce: a
tool-enabled `kimi27` code review read the injected diff, made zero tool calls, and returned a
confident FAIL about a `NameError` that does not exist ([#82](https://github.com/ecorkran/squadron/issues/82)).
Every wrong finding had the same shape — a claim about a symbol whose definition lay outside
the hunk. The model was never told that a diff is partial context, or that an assertion of
absence needs the file open in front of it.

That is a prompt problem, and it has a structural cause. The review template's system prompt
describes *what* to review; nothing describes *when to reach for a tool*. Non-SDK dispatch is
worse: it sends an empty system prompt
([#40](https://github.com/ecorkran/squadron/issues/40)). Squadron owns the tools, so squadron
must own the guidance for using them — once, not per template.

Alongside the discipline gap, three diagnosability gaps surfaced in the same runs. An UNKNOWN
review discards the model's response while its own message says to consult it
([#61](https://github.com/ecorkran/squadron/issues/61)). A tool-enabled review that made zero
calls is only detectable by opening the persisted artifact. And an empty final turn is now
refused with its `finish_reason` captured ([#84](https://github.com/ecorkran/squadron/issues/84)),
but nothing acts on that reason yet.

The SDK side has its own version of the discipline gap. Every SDK review sends the template
prompt as its *entire* system prompt, replacing the Claude Code CLI's own prompt and the
tool-use discipline it carries ([#85](https://github.com/ecorkran/squadron/issues/85)). This is
the third appearance of one defect: the metrology audit had it (fixed in `f5b09ce`, audit
only), dispatch has it (#40), and reviews were never covered.

Finally, dispatch still rejects `allowed_tools` on SDK profiles
([#75](https://github.com/ecorkran/squadron/issues/75)) even though slice 265 built the
canonical-to-Claude translation and the review path already uses it — so the same pipeline
YAML cannot run under both an SDK and a non-SDK model.

## Value

- **A tool-enabled non-SDK review becomes comparable to an SDK one.** The initiative's
  completion criterion (initiative plan, entry 7) is that a capable model, given tools, uses
  them and returns results not substandard to the SDK path. This slice supplies the missing
  half of that: the instruction to verify before asserting.
- **A confident wrong FAIL stops being silent.** Zero tool calls on a tool-enabled review is
  printed at `-v`; an UNKNOWN verdict keeps the evidence needed to say why.
- **One pipeline YAML runs under any model.** A step declaring `allowed_tools` no longer
  fails on an SDK alias.
- **SDK reviews get the CLI's own discipline back**, with the template appended rather than
  replacing it.
- **#40, #61, #68, #75, #82, #84, #85 close** — the open issues standing between "merged" and
  "usable" for initiative 260.

## Technical Scope

### In Scope

**Discipline**

1. A shared tool-use guidance block, owned by the tools package (`squadron/tools/guidance.py`),
   composed into the system prompt of every tool-enabled non-SDK agent.
2. Non-SDK dispatch sends no system message when it has nothing to say, rather than an empty
   one; the guidance block is its baseline system prompt whenever tools are offered (#40,
   second angle).
3. SDK one-shot dispatch uses the CLI's default system prompt when no explicit `system_prompt`
   is supplied (#40, first angle).
3a. SDK reviews send the CLI's default system prompt with the template prompt *appended*
   (#85). `use_default_system_prompt` stops meaning "preset, discard instructions": when
   instructions are also present they ride the preset's `append` field.

**Diagnosability**

4. The parser's UNKNOWN branch writes the debug log like its two sibling branches (#61).
5. A degraded review — resolved verdict UNKNOWN, or `fallback_used` — persists the raw
   response in its artifact at every verbosity (#61).
6. `sq review` prints a tool-use line at `-v`, visibly distinct when tools were offered and
   none were called.
7. The empty-final-turn cause is acted on: a live re-run captures `finish_reason`; if it is
   `length`, an `agent.max_output_tokens` config key is added and sent on the request (#84).

**Dispatch parity**

8. `one_shot_dispatch_with_telemetry` translates `allowed_tools` for SDK profiles instead of
   raising (#75).

**Verification and closure**

9. #68 is verified subsumed by 265 + this slice and closed with the evidence.

### Out of Scope

- **SDK reviewer Bash restriction** (#69). On the SDK path `allowed_tools` is a permission
  hint, not an availability gate; that is an SDK-path concern the initiative excludes.
- **Token accounting** (#36, #33).
- **The SDK session dispatch path.** A persistent session's tool set is fixed when it connects
  (`_connect_lazy_session` builds one `ClaudeAgentOptions` with `bypassPermissions`), so a
  per-step `allowed_tools` cannot narrow it. That rejection stays; its message is reworded to
  state this reason. See D6.
- **Downgrading absence-shaped findings in the parser** (#82, option 2). Prompt guidance is
  the cause-level fix; a parser heuristic keyed on `toolCallsMade == 0` would be a second
  mechanism for the same problem and is deferred until the live A/B shows the prompt is not
  enough.
- **Composing the guidance block into SDK agents.** The architecture's "no SDK-path
  regression" goal holds. The Claude CLI carries its own tool discipline — which is exactly
  why #85 restores that prompt instead of adding squadron's block on top of it.

## Architecture

### Where the guidance block is composed

Slice 266 could not gate capability at the agent because the agent never sees the alias. The
guidance block has no such constraint: it depends only on the *effective* tool list, which is
already on `AgentConfig` by the time the agent is constructed. So there is a genuine
chokepoint, and this slice uses it instead of editing four call sites and adding a second
enumeration test.

```
template / step / audit    -->  resolve_effective_tools (266 gate, unchanged)
                                        |
                                        v
                             AgentConfig.instructions, .allowed_tools
                                        |
                                        v
                     OpenAICompatibleAgent.__init__   <-- the composition point
                        system = compose_system_prompt(instructions, allowed_tools)
                                        |
                                        v
                          history[0] = {"role": "system", "content": system}
```

`compose_system_prompt(instructions, tools)`:

- `tools` empty (never declared, or emptied by the gate): returns `instructions` unchanged.
  A suppressed run therefore carries no guidance — the test in SC1 asserts exactly this.
- `tools` non-empty: returns `instructions` followed by the guidance block under its own
  `## Tool Use` heading. An empty or `None` `instructions` yields the block alone.

The block is appended, not prepended: the template's own rules (verdict consistency, finding
format) stay first, where the model weights them most. The system message is built once at
construction, so prefix caching is unaffected.

The SC1a enumeration test from 266 is untouched; it guards the gate, and the gate is still
where it was.

### The guidance block

Model-agnostic, short, and phrased around "the tools listed" rather than naming `read_file`,
because the same block serves a review (`read_file`, `list_files`, `grep`) and a design
dispatch (`read_file`, `write_file`). The effective tool names are rendered into it so the
model sees what it actually has. Substance, to be worded at implementation:

- The prompt may contain a diff or excerpts. A diff shows changed lines and a few lines of
  context; it cannot show a definition, an earlier assignment, a type narrowing, or a
  justifying comment that sits outside the hunk. A hunk cannot prove absence.
- Before asserting that something is missing, undefined, unhandled, unnarrowed, or
  unjustified, open the file with the tools available and confirm it. If it cannot be
  confirmed, say so explicitly rather than asserting it.
- Use a tool when a claim depends on code not in front of you. Do not read files a claim does
  not depend on — reading everything is the failure that preceded this one (#81).
- If the task asks for a file to be created or changed, do it with the tools. A description
  of a file is not the file.

The constraint from #82 is preserved on both sides: the diff stays the anchor, and tool-call
count is not a goal.

### Diagnosability

**Raw response retention (#61).** Two changes, one per layer:

- `parse_review_output`'s UNKNOWN branch calls `_write_debug_log` with `fallback_used=True`
  and `findings_parsed=0`, matching its siblings. This runs at every verbosity; it is evidence
  retention, not verbosity-gated output.
- `format_review_markdown` embeds the raw response when the result is degraded: the
  *resolved* verdict is UNKNOWN, or `fallback_used` is set. This keys on the resolved verdict
  deliberately: a judge template's raw parse is always UNKNOWN (its verdict is score-derived,
  see `ReviewResult.to_dict`), and keying on the raw parse would embed every judge's response.
  A clean review's artifact is byte-for-byte unchanged. The `-vv` prompt appendix is
  unchanged and renders the raw response once, not twice, when both apply.

The two user-facing strings that currently promise `-vv` (the "Findings Not Parsed" body in
persistence and the "re-run with -vv" hint in the CLI) are corrected, because they become
false.

**Zero-call surfacing.** `_display_terminal` prints one line at verbosity ≥ 1 whenever the
result carries tool telemetry, in three forms so the three states 265/266 record stay
distinct on the terminal too:

| State | Line |
|---|---|
| tools given, calls > 0 | `Tools: read_file, list_files, grep — 12 calls` |
| tools given, calls == 0 | `Tools: read_file, list_files, grep — 0 calls (offered, none used)` in warning style |
| suppressed | `Tools: suppressed (reason=run-suppressed)` |

The review client additionally logs a WARNING when tools were given and none were called.
`sq run -v` already renders `tools=3/0 calls` per step through the executor, so the pipeline
side needs no change.

**Empty final turn (#84).** Slice 266 made the empty turn a refused, logged error carrying
`finish_reason` and `reasoning_chars`. What remains is evidence-gated, per the project's
debugging rule: the live re-run in the walkthrough captures the cause. If `finish_reason` is
`length`, an `agent.max_output_tokens` config key is registered in `config/keys.py` (int,
default `None`, meaning the parameter is omitted and the provider's default applies) and
`_stream_turn` passes it as `max_tokens`. If the cause is anything else, or the empty turn
does not recur, the key is not added and the observation is recorded on #84.

### Dispatch parity (#75)

`one_shot_dispatch_with_telemetry` raises when `allowed_tools` is non-empty and the profile
is SDK. That guard predates slice 265, whose `translate_tool_names` now runs inside
`ClaudeSDKProvider.create_agent` for every `AgentConfig` that sets `allowed_tools` — the
review client already relies on it. Removing the guard is the whole fix: the canonical names
reach the provider, and the provider translates or raises on an unmapped name exactly as it
does for reviews.

The session path keeps its rejection (Out of Scope). Its message changes from "does not yet
support them" to the actual reason: a persistent session's tools are fixed at connect time.

### `#40` on the SDK side

`one_shot_dispatch_with_telemetry` sets `use_default_system_prompt=True` when the profile is
SDK and no `system_prompt` was supplied, matching the precedent in `executor.py` and
`run.py`. An explicit `system_prompt` still wins. For non-SDK profiles, an empty
`system_prompt` becomes `instructions=None` so the agent sends no system message; with tools,
the guidance block is then the whole system prompt — #40's "what baseline should non-SDK
dispatch get" is answered as: the tool-use guidance when tools are offered, nothing
otherwise.

### The SDK side (#85)

`ClaudeSDKProvider.create_agent` builds the preset as `{"type": "preset", "preset":
"claude_code"}` and ignores `instructions` when the flag is set. The installed SDK's
`SystemPromptPreset` has an optional `append` field, so the change is:

```
use_default_system_prompt  instructions   system_prompt sent
False                      None           (none)
False                      str            str                      -- unchanged
True                       None / ""      preset                   -- unchanged (audit)
True                       str            preset + append=str      -- new
```

`run_review_with_profile` sets the flag. The template prompt, structured-output instructions,
and rules are unchanged and still reach the model, now appended to the CLI's prompt rather
than replacing it. Non-SDK providers never read the flag. The audit's row is unchanged, so
its measurements stay comparable.

The `-vvv` prompt log and the `-vv` artifact appendix record `system_prompt` as squadron
composed it; the CLI's preset text is not squadron's to capture. The appendix gains one line
stating the preset was used, so a reader knows the recorded text is the appended part.

## Integration Points

- **`src/squadron/tools/guidance.py`** (new) — the block text and `compose_system_prompt`.
  Exported from `squadron.tools`.
- **`src/squadron/providers/openai/agent.py`** — constructor composes the system message.
  `_stream_turn` gains the conditional `max_tokens` (only if #84 evidence warrants it).
- **`src/squadron/providers/openai/provider.py`** — reads `agent.max_output_tokens`
  alongside the other `agent.*` keys (same condition).
- **`src/squadron/config/keys.py`** — `agent.max_output_tokens` (same condition).
- **`src/squadron/pipeline/actions/dispatch.py`** — SDK guard removed; SDK default system
  prompt; empty non-SDK instructions become `None`; session-path message reworded.
- **`src/squadron/review/parsers.py`** — UNKNOWN branch writes the debug log.
- **`src/squadron/review/persistence.py`** — degraded results embed the raw response.
- **`src/squadron/review/review_client.py`** — WARNING on zero calls;
  `use_default_system_prompt=True` on the review config (#85).
- **`src/squadron/providers/sdk/provider.py`** — preset carries `append` when instructions
  are present (#85).
- **`src/squadron/core/models.py`** — `use_default_system_prompt` docstring updated to the
  table above.
- **`src/squadron/cli/commands/review.py`** — tool line at `-v`; `-vv` hint corrected.

Nothing in `review_client.py`, `summary_oneshot.py`, or `metrology/audit.py` changes for the
guidance block — that is the point of composing it at the agent.

## Success Criteria

- **SC1** — Every tool-enabled `OpenAICompatibleAgent` runs with the guidance block in its
  system message; an agent whose tools were emptied by the gate (either suppression reason)
  or never declared runs without it. Verified at the agent, with and without caller
  instructions.
- **SC2** — The block names the effective tools it was composed with, and the template's own
  instructions precede it.
- **SC3** — A parse that yields UNKNOWN with no findings writes a debug-log entry containing
  the raw output.
- **SC4** — A review persisted with resolved verdict UNKNOWN, or with `fallback_used`, contains
  the raw response at verbosity 0; a clean review's artifact is unchanged; a judge review
  with a score-derived verdict does not embed its raw response.
- **SC5** — `sq review ... -v` prints a tool line for each of the three telemetry states, and
  the zero-call form is visually distinct from the used form.
- **SC6** — A dispatch step with `allowed_tools` on an SDK profile builds an `AgentConfig`
  carrying the canonical names, and the SDK provider receives them translated; an unmapped
  name still raises.
- **SC7** — SDK one-shot dispatch with no explicit `system_prompt` sets
  `use_default_system_prompt=True`; a non-SDK one sends no system message when it has no
  instructions and no tools.
- **SC7a** — An SDK review's `ClaudeAgentOptions.system_prompt` is the `claude_code` preset
  with the composed template prompt in `append`; the audit's options are unchanged (preset,
  no `append`); a non-SDK review's system message is unchanged.
- **SC8** — The empty-final-turn cause has been captured live and either (a) `finish_reason`
  was `length` and `agent.max_output_tokens` is wired and tested, or (b) the observation is
  recorded on #84 and no key was added.
- **SC9** — #68 is closed with a comment citing the artifact fields (`toolsGiven`,
  `toolCallsMade`) that make the silent downgrade it describes impossible.
- **SC10 (live acceptance)** — The same model reviewing the same diff with and without tools
  (`--no-tools` A/B): the tools run records `toolCallsMade > 0`, and neither its findings
  nor its verdict assert the absence of a symbol the repository defines. This is the
  initiative's usability bar and is not satisfied by a green suite.
- **SC11** — Full gate set green: `ruff format`, `ruff check`, `pytest`, `pyright` with no new
  errors.

## Design Decisions

**D1 — The guidance block is composed at the agent, not the four call sites.**
The slice plan says "at every tool-passing site." That wording came from 266, where the gate
had no chokepoint because the agent cannot see the alias. The block depends only on the
effective tool list, which the agent does see, so the agent's constructor is a true
chokepoint: no caller can pass tools and skip it, and no enumeration test is needed to keep
it honest. One function, one call.

**D2 — Non-SDK only.** The architecture's design goal "no SDK-path regression" stands. The
Claude CLI supplies its own discipline through the preset prompt where it is used (audit)
and through the model's training elsewhere. Composing the block into SDK agents would change
every SDK review's prompt for no identified gain.

**D2a — SDK reviews restore the CLI prompt via preset + append; they do not get squadron's
block.** Two mechanisms for two providers, chosen by what each already has: the CLI ships a
tool discipline, so the fix is to stop discarding it; non-SDK models ship none, so squadron
supplies one. Appending rather than replacing keeps every template's rules in force. This is
an SDK-path behavior change, so it is verified live (walkthrough §2a), not only by the suite.

**D3 — Degraded reviews keep their raw response at every verbosity.** The plan asks for
`-v`. Evidence retention should not depend on a flag when the alternative is losing the
evidence: an UNKNOWN artifact reading "No specific findings." is misleading at verbosity 0
too. Clean reviews are unaffected, so the cost is confined to exactly the artifacts that need
it.

**D4 — `max_tokens` is gated on evidence.** The cause of the observed empty turn is unknown.
Adding a config key for a hypothesis contradicts the project's rule against speculative
fixes; the walkthrough captures the cause first.

**D5 — Absence-shaped findings are not downgraded by the parser.** A prompt fix addresses the
cause. A parser heuristic would be a second mechanism, keyed on a count that #82 itself warns
against treating as a goal. Revisit only if SC10 fails with the guidance in place.

**D6 — The session dispatch path keeps rejecting `allowed_tools`.** Its tool set is fixed at
connect; honoring a per-step list would require either reconnecting per step or silently
ignoring the declaration — the latter is the no-op-with-prose failure 263 exists to prevent.
The message now says why.

## Risks

- **Prompt-driven behavior is provable only live.** The suite proves the block is present;
  only SC10 proves it changes what the model does. If the A/B still shows zero calls or an
  absence claim, the fallback is D5's parser downgrade, tracked as a follow-up issue rather
  than absorbed here.
- **`max_tokens` semantics differ across OpenAI-compatible backends** — some count reasoning
  tokens against it, some do not. Mitigated by D4: the key exists only if the observed cause
  is `length`, and its default omits the parameter.

## Verification Walkthrough

Steps marked *(live)* need a real model and a plain terminal; `sq run` and `sq review` live
runs are executed outside a Claude Code session. `kimi27` (`moonshotai/kimi-k2.7-code`, via
openrouter) is the verification model, as in 266.

### 1. The block is composed exactly when tools are offered

```bash
uv run pytest tests/tools/test_guidance.py tests/providers/openai/test_agent.py -v
```

Expect: an agent built with `allowed_tools=[read_file, grep]` has a system message ending in
the `## Tool Use` block naming both tools, preceded by the caller's instructions; an agent
built with `allowed_tools=[]` and `tools_suppressed_reason="run-suppressed"` has the caller's
instructions only; an agent with neither instructions nor tools has no system message (SC1,
SC2).

### 2. Zero calls are visible at `-v` *(live)*

```bash
uv run sq review code <slice> --model kimi27 -v
```

Expect a `Tools:` line after the verdict panel. With the guidance in place the count should
be non-zero; if it is zero the line renders in warning style and a WARNING appears on
stderr (SC5). Confirm the same three values in the artifact's `toolsGiven` /
`toolCallsMade` frontmatter.

### 2a. SDK reviews carry the CLI prompt *(live)*

```bash
uv run pytest tests/providers/sdk/test_provider.py tests/review/test_review_client.py -k "preset or default_system_prompt" -v
uv run sq review code <slice> --model sonnet -v
```

The unit tests assert the preset-plus-append shape (SC7a). The live run is the before/after:
compare its findings with the most recent SDK review of the same slice on `main`. Expect no
regression in verdict or finding quality, and record the two finding counts here. Check the
`-k` selector matched tests.

### 3. The A/B — the initiative's acceptance *(live)*

```bash
uv run sq review code <slice> --model kimi27 --no-tools -v
uv run sq review code <slice> --model kimi27 -v
```

Compare the two artifacts. The tools run must record `toolCallsMade > 0`. Read every finding
in both: none in the tools run may claim a symbol is undefined, unbound, unnarrowed, or
unjustified when the repository defines it — the #82 shape. Record the finding counts and
any absence claims in this section when done (SC10).

### 4. An UNKNOWN review keeps its evidence

```bash
uv run pytest tests/review/test_parsers.py tests/review/test_persistence.py -k "unknown or raw_response or degraded" -v
```

Expect: the UNKNOWN branch writes a debug-log entry with the raw output; a persisted UNKNOWN
result contains the raw response at verbosity 0; a clean PASS is byte-identical to before; a
judge result with a score does not embed its raw response (SC3, SC4). Confirm each `-k`
selector matched tests — a selector matching nothing reports success for a suite it never
ran (266's lesson).

### 5. Dispatch accepts `allowed_tools` on an SDK profile

```bash
uv run pytest tests/pipeline/actions/test_dispatch.py -v
```

Expect: a step with `allowed_tools: [read_file]` on an `sdk` profile builds a config and the
provider receives `["Read"]`; an unmapped canonical name still raises from the provider; an
SDK one-shot with no `system_prompt` sets `use_default_system_prompt=True` (SC6, SC7).

Then *(live)*, from a plain terminal, run any pipeline whose step declares `allowed_tools`
with an SDK alias:

```bash
uv run sq run test-p4 <slice> --model sonnet -v
```

Expect the step to run and its result line to carry a `tools=` segment, not the former
vocabulary error.

### 6. The empty-final-turn cause *(live)*

Re-run the review that produced #84:

```bash
uv run sq review code 266 --model kimi27 -v
```

If the empty turn recurs, the CLI now exits 1 with
`Model returned an empty final turn (finish_reason=..., reasoning_chars=...)`. Record the
values on #84. If `finish_reason` is `length`, implement the `agent.max_output_tokens` key
and re-run; otherwise close the loop on #84 with the observation (SC8).

### 7. Close #68

Run a `tasks` review through a non-SDK alias and confirm the artifact's frontmatter carries
`toolsGiven` and `toolCallsMade`. Comment on #68 citing the fields and the slices that added
them (265, 266, 267), then close (SC9).

### 8. Full gate set

```bash
uv run ruff format . && uv run ruff check . && uv run pytest -q && uv run pyright
```

All green; pyright shows no errors beyond the two pre-existing `mcp_bridge.py` ones (#74).

## Effort

3/5. The code is small — one new module, a handful of edits — but the acceptance is a live
A/B against model behavior, and the #84 item may need a second live iteration.
