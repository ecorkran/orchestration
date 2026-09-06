---
docType: slice-design
project: squadron
slice: 266-slice.tool-use-configuration-and-limits
parent: 260-slices.non-sdk-agent-tool-use-openai-compatible-agentic-loop.md
dependencies: [261, 262, 263, 265]
interfaces:
  - name: resolve_effective_tools
    module: squadron.tools
    contract: >-
      Sole gate for tool-use capability. Every AgentConfig construction site that passes
      a non-empty allowed_tools must route through it; see Architecture, "The call sites
      that must use it". Enforced by SC1a.
dateCreated: 20260903
dateUpdated: 20260905
status: complete
---

# Slice Design: Tool-Use Configuration and Limits

## Parent Documents

- Architecture: `260-arch.non-sdk-agent-tool-use-openai-compatible-agentic-loop.md`
- Slice Plan: `260-slices.non-sdk-agent-tool-use-openai-compatible-agentic-loop.md`, entry 6

## Overview

Slices 261–265 built the tool stack, wired it into dispatch and reviews, and made tool use
observable. Two gaps remain, and they sit on opposite sides of the same call.

**Gap 1 — no control over *whether* a model is offered tools.** Every model reaching the
agentic loop is handed schemas if its template or step declares `allowed_tools`. A model whose
tool-calling is broken — emitting malformed protocol, looping on a single call — has no way to
be marked as such short of editing every template that might route to it. And there is no way
to run the same review twice, once with tools and once without, which is exactly the comparison
slice 265's tools-enabled persistence field was built to support.

**Gap 2 — no bound on *what a model may hand a tool*.** The tools themselves bound their
outputs (`MAX_READ_BYTES`, `MAX_OUTPUT_BYTES`, `GREP_TIMEOUT_S`) but not their inputs. Slice
265's code review and its live verification runs surfaced five instances of one shape: a
model-supplied value reaching a tool with nothing checking it. One of them is a containment
break — `grep` resolves only its initial `path` against the jail and then opens every candidate
the walk yields, so a symlink inside the jail pointing outside it returns contents that
`read_file` would refuse for the same target.

Both halves land here because both are configuration of the tool boundary, and because the
bounds work concentrates in `builtin.py` and `limits.py` — the same two files, five times over.
`limits.py` already records in its own docstring that making its constants configurable is this
slice's job.

## Value

- **A model with broken tool-calling can be marked once, in one place**, instead of being
  worked around per template.
- **Baseline-vs-tools comparison becomes a flag, not a config edit.** `--no-tools` makes the
  A/B run mechanical; slice 265's recorded tools-enabled field makes the two runs
  distinguishable afterward.
- **The jail actually contains.** Item (a) closes a path by which a review of an untrusted
  working tree could read files outside it.
- **A single tool call can no longer consume the whole history budget**, which was observed
  live, not hypothesized.

## Technical Scope

### In Scope

**Configuration half:**

1. `tool_use: bool` optional field on models.toml aliases (default `true`), parsed alongside
   `private` / `cost_tier` / `notes`.
2. Capability enforcement via a shared `resolve_effective_tools` helper, applied at all four
   tool-passing call sites so it covers `sq review`, the pipeline `summary` action, `sq run`
   dispatch, and the metrology audit alike.
3. `--no-tools` flag on `sq review` (both subcommands that accept `--model`), emptying the
   effective tool set for one run.
4. Effective-tools resolution recorded and logged so a suppressed tool set is visible, not
   silent.

**Bounds half:**

5. (a) Per-candidate jail re-check in `grep` and `list_files`.
6. (b) `grep` pattern length cap, pre-compilation; plus removal of `grep`'s silent
   past-256KB match loss.
7. (c) Per-tool-result size cap before the result enters history.
8. (d) Bounded `list_files` walk — cap work, not just output.
9. (e) Split `builtin.py` into `builtin/file_tools.py` + `builtin/search_tools.py`.

### Out of Scope

- **Config-file plumbing for `limits.py` constants.** Decided during design (see Design
  Decisions §D4): the new caps are module constants beside the existing ones, monkeypatchable
  by tests, with no config keys. Adding a config surface for eight constants before anyone has
  asked to tune one is speculative.
- **`--no-tools` on `sq run`.** The comparison workflow this serves is review-scoped. A
  pipeline that should not use tools can omit `allowed_tools` from its step YAML, which is the
  existing mechanism.
- **A `tool_use` capability probe.** The field is operator-asserted, not detected.
- **Sandboxing depth for `bash`** — unchanged from the initiative's stated out-of-scope.

## Architecture

### Where the capability gate lives

The gate is `resolve_effective_tools` — a single function in the tools package — and it sits in
the **caller**, not the agent. `OpenAICompatibleAgent.__init__`
([agent.py:114-140](src/squadron/providers/openai/agent.py#L114-L140)) is where `allowed_tools`
becomes materialized executors, but it cannot be the gate: it receives an already-resolved model
id and must not read models.toml (D3). It materializes whatever list it is handed and has no way
to tell a gated list from an un-gated one.

So the enforcement site is one *function*, and the obligation is that every caller which passes
`allowed_tools` into `AgentConfig` routes through it. That obligation is not self-enforcing, so
this slice makes it explicit rather than assumed:

- The call sites are **enumerated**, not left to be discovered (below).
- A test asserts the enumeration is complete, so a new site added later fails loudly rather than
  silently skipping the gate (SC1a).

```
models.toml alias            template.allowed_tools        --no-tools
  tool_use: bool                (or step YAML)                 flag
        \                            |                          /
         \                           |                         /
          +----> resolve_effective_tools()  <-------------------+
                  (the gate — every caller below uses it)
                              |
                              v
                   AgentConfig.allowed_tools
                              |
                              v
              OpenAICompatibleAgent.__init__  --> tools.materialize
                  (materializes; does not gate)
```

Effective tools = `declared ∩ (capability allows)` , emptied entirely by `--no-tools`.

The resolution is a single function so all three inputs combine in exactly one place. Scattering
the `∩` across the review client and dispatch would be the "comparison values scattered across
code" the project rules forbid.

### The call sites that must use it

Four `AgentConfig` construction sites pass a non-empty `allowed_tools` today. All four are in
scope; none may be left to a later slice:

| Site | Line | Tools come from | Notes |
|---|---|---|---|
| `review/review_client.py` | [138](src/squadron/review/review_client.py#L138) | `resolved_allowed_tools` from the template | also the `--no-tools` entry point |
| `pipeline/actions/dispatch.py` | [109](src/squadron/pipeline/actions/dispatch.py#L109) | step YAML `allowed_tools` | **already populates `allowed_tools`** — this is a change to an existing path, not a new one |
| `pipeline/summary_oneshot.py` | [68](src/squadron/pipeline/summary_oneshot.py#L68) | step `allowed_tools` | the pipeline `summary` action |
| `metrology/audit.py` | [608](src/squadron/metrology/audit.py#L608) | module constant `_AUDIT_ALLOWED_TOOLS` | fixed list, but a `tool_use = false` model must still be gated |

The remaining three sites (`providers/auth.py:234`, `server/routes/agents.py:49` and `:179`) pass
no `allowed_tools` at all and are therefore out of scope — the completeness test must recognize
them as legitimately un-gated rather than flagging them.

**SC1a's test is what keeps this list honest.** It enumerates `AgentConfig(...)` constructions
that set `allowed_tools` and asserts each is on the sanctioned list — so adding a fifth site
without routing it through `resolve_effective_tools` fails the suite instead of silently
un-gating `tool_use = false`.

### Suppression must be visible

An emptied tool set is a silent behavior change unless it is announced. When resolution empties
a non-empty declared set, the reason is logged at INFO and recorded alongside slice 265's
existing `tools_given` telemetry — a run that was *denied* tools is distinguishable from one
that was never offered any. This is the same principle 265 established: "offered but unused"
had to be visually distinct from "not offered."

### Bounds: one shape, five sites

Every bounds item is the same fix — validate a model-supplied value before it reaches
something expensive or privileged:

| Item | Model-supplied input | Reaches | Bound added |
|---|---|---|---|
| (a) | `path`, `glob` (via walk) | open() on any candidate | re-resolve each candidate against jail |
| (b) | `pattern` | regex engine | pre-compile length cap |
| (b') | *(none — internal)* | truncated file read | visible marker or line-wise scan |
| (c) | tool result content | history budget | per-result byte cap |
| (d) | `path`, `pattern`, `recursive` | full tree materialization | entry cap during walk |

**Every bound is observable.** Item (a) logs at WARNING (SC5/D6) because a jail escape is a
security event. Items (b), (b'), (c) and (d) return a model-visible error result or truncation
marker, and each additionally trips the architecture's baseline tool logging — the tool call and
its result are logged at DEBUG, with per-run summaries at INFO under `-vv`. So an operator
scanning `-vv` output can tell "the model keeps hitting the pattern cap" from routine tool use,
satisfying the project's Failure-Mode Enumeration rule that a failure mode be observable rather
than silent. No bound trips without leaving a trace in both channels: the model sees the marker,
the operator sees the log.

### The jail re-check (item a)

`_resolve_in_jail` ([builtin.py:38](src/squadron/tools/builtin.py#L38)) is correct and stays as
written. The defect is that `grep` calls it once, on `path`
([builtin.py:519](src/squadron/tools/builtin.py#L519)), and then `_grep_candidates`
([builtin.py:489-501](src/squadron/tools/builtin.py#L489-L501)) yields entries from
`target.rglob(...)` that are opened with no further check. Two escape routes:

1. A symlinked **file** inside the jail whose target is outside it. `entry.is_file()` follows
   the link and returns true; the read returns foreign content.
2. On Python ≤3.12, `rglob` recurses into symlinked **directories**, so the walk itself can
   leave the jail.

Fix: resolve each yielded candidate and skip any that is not `is_relative_to` the jail root.
Placed inside `_grep_candidates` so both the file and directory cases are covered at the single
point where candidates are produced, and so `list_files` can use the same guard.

A skipped candidate is a *silent* skip by design here — it is indistinguishable to the model
from a file that does not match — but it is logged at WARNING, because a symlink escape attempt
in a review working tree is an operator-visible event. This mirrors `_grep_timeout`'s treatment.

### `grep`'s silent truncation (item b')

`_search` reads `handle.read(limits.MAX_READ_BYTES)` and searches only that prefix
([builtin.py:~552](src/squadron/tools/builtin.py#L552)). A match at byte 300,000 of a 400KB file
is reported as no match. That bound was added in 265 to close an unbounded read, and traded it
for a silent failure — which the project's no-silent-fallback rule forbids.

Resolution: keep the bound, add the marker. When a file is truncated at the read cap, the
result includes a visible per-file notice naming the file. Line-wise scanning with a bounded
buffer is the alternative; it is more code and changes the timeout accounting, so the marker is
the chosen fix. The model can then narrow its own search.

## Integration Points

- **`src/squadron/models/aliases.py`** — `ModelAlias` gains `tool_use: bool`; `_extract_metadata`
  parses it. Follows the existing `private` bool precedent exactly.
- **`src/squadron/data/models.toml`** — header comment documents the field. No alias sets it
  (default `true` preserves current behavior); operators set it on their own aliases.
- **`src/squadron/tools/`** — new `resolve_effective_tools` helper (the gate).
- **`src/squadron/providers/openai/agent.py`** — telemetry records suppression. The agent
  materializes; it does not gate.
- **`src/squadron/review/review_client.py`** — `run_review_with_profile` routes its
  `resolved_allowed_tools` ([review_client.py:79](src/squadron/review/review_client.py#L79))
  through the resolution helper.
- **`src/squadron/pipeline/actions/dispatch.py`** — routes the step's `allowed_tools`
  ([dispatch.py:117](src/squadron/pipeline/actions/dispatch.py#L117)) through the helper. The
  field is already populated here; this changes an existing assignment.
- **`src/squadron/pipeline/summary_oneshot.py`** — same, for the `summary` action
  ([summary_oneshot.py:79](src/squadron/pipeline/summary_oneshot.py#L79)).
- **`src/squadron/metrology/audit.py`** — same, for `_AUDIT_ALLOWED_TOOLS`
  ([audit.py:621](src/squadron/metrology/audit.py#L621)).
- **`src/squadron/cli/commands/review.py`** — `--no-tools` on both review subcommands.
- **`src/squadron/tools/limits.py`** — new constants: pattern cap, tool-result cap, list-files
  entry cap. Docstring's "slice 266's job" note updated to record the decision taken.
- **`src/squadron/tools/builtin.py` → `builtin/`** — package split (e).

## Implementation Details

### `builtin.py` split (item e)

Pure move, no logic change, done **last** within the slice so the preceding items' diffs stay
readable against the current file:

```
tools/builtin/__init__.py       — registers all five descriptors; re-exports public names
tools/builtin/_shared.py        — _resolve_in_jail, _truncate, _error, _jail_violation,
                                  _guarded, arg coercion helpers
tools/builtin/file_tools.py     — read_file, write_file, list_files
tools/builtin/search_tools.py   — grep
```

`bash` stays with the file tools or moves to its own module — a task-time call once the line
counts are known. The public import surface (`squadron.tools.builtin.READ_FILE`, etc.) must not
change; existing imports and tests are the contract.

### Effective-tools helper

One function, in the tools package (not the review package — dispatch uses it too):

```python
def resolve_effective_tools(
    declared: list[str] | None,
    *,
    model_allows_tools: bool,
    suppressed: bool,
) -> tuple[list[str], str | None]:
    """Return (effective tool names, reason they were emptied or None)."""
```

Returning the reason alongside the list is what makes suppression announceable at the call site
without the caller re-deriving why.

## Success Criteria

- **SC1** — An alias with `tool_use = false` is never offered tool schemas, even when the
  template or step declares `allowed_tools`. Verified at each of the four sanctioned call sites:
  review client, dispatch, summary one-shot, and metrology audit.
- **SC1a** — A test enumerates every `AgentConfig` construction that sets `allowed_tools` and
  fails if one is not among the sanctioned sites, so a future un-gated caller is caught by the
  suite rather than shipping a silent capability bypass.
- **SC2** — An alias with `tool_use` absent behaves exactly as today (tools passed through).
- **SC3** — `sq review code <slice> --no-tools` runs with an empty effective tool set, and the
  persisted review records tools as disabled.
- **SC4** — When resolution empties a non-empty declared set, the reason is logged at INFO and
  is distinguishable in telemetry from "no tools were declared."
- **SC5** — `grep` refuses a candidate reached through a symlink pointing outside the jail, and
  logs at WARNING. Covers both the symlinked-file and symlinked-directory cases.
- **SC6** — `list_files` applies the same containment check to the entries it names.
- **SC7** — A pattern longer than the cap is rejected before compilation, with an error result
  telling the model to shorten it (returned, not raised — the model supplied it).
- **SC8** — A `grep` hit on a file truncated at the read cap produces a visible truncation
  marker naming the file; no match is dropped without a marker.
- **SC9** — A single tool result larger than the cap is truncated with a visible marker before
  entering history, and cannot exhaust `agent.max_history_chars` on its own.
- **SC10** — `list_files` over a wide tree bounds the number of entries it walks, not merely
  the bytes it returns.
- **SC11** — After the split, every module in `tools/builtin/` is under the ~300-line
  convention, and the public import surface is unchanged (existing tests pass untouched).
- **SC12** — Full gate set green: `ruff format`, `ruff check`, `pytest`, `pyright` no new errors.

## Design Decisions

**D1 — Capability gate applies everywhere tools are offered, not review-only.**
The slice plan mentions the field in a review context, but `tool_use` describes the *model*, not
the review. A model that mishandles tool-call protocol mishandles it on the dispatch path too;
gating only reviews would leave `sq run` handing schemas to a model already marked broken.
Coverage is achieved by one shared helper plus an enumerated list of the four callers that pass
tools, not by a single structural chokepoint — D3 rules that out, since the agent cannot see the
alias. SC1a's enumeration test is what substitutes for the chokepoint the layering denies us.
*(Confirmed with PM 20260903.)*

**D2 — `--no-tools` is review-only and is a flag, not a second alias.**
Two aliases pointing at the same model would be indistinguishable in persisted results, which
records the resolved model — so the flag is the only mechanism that makes an A/B pair
readable afterward. It stays review-scoped because that is where the comparison workflow lives;
pipelines already control tools by declaring or omitting `allowed_tools` per step.
*(Confirmed with PM 20260903.)*

**D3 — Capability is resolved by the caller, passed to the agent; the agent does not read
models.toml.** The agent receives a resolved model id and has no business doing alias lookup.
Keeping the lookup in the config layer preserves that boundary.

**D4 — New limits are fixed constants in `limits.py`, not config keys.**
`limits.py`'s docstring flags configurability as this slice's decision; the decision is *not
yet*. All caps live in `limits.py` as module attributes — one home, monkeypatchable, read at
call time — but no config plumbing ships until someone needs to tune one. Adding eight config
keys speculatively is complexity the project rules tell us to resist. The docstring is updated
to record that this was decided, not overlooked. Tracked for later as
[issue #76](https://github.com/ecorkran/squadron/issues/76), which records the constraints any
future config surface must preserve. *(Confirmed with PM 20260903.)*

**D5 — Item (a) lands first within the slice.** It is the only security item. The rest is
hardening and can follow in any order; the `builtin.py` split lands last so earlier diffs stay
legible.

**D6 — A jail-refused candidate is skipped, not surfaced to the model as an error.**
To the model it is simply a file that did not match — surfacing "you were denied" invites
probing for the jail boundary. It is logged at WARNING for the operator, which is where an
escape attempt matters.

**D7 — `grep` truncation gets a marker rather than line-wise scanning.**
The marker satisfies the no-silent-fallback rule at a fraction of the cost, and does not disturb
the timeout accounting that the per-line `remaining` budget depends on.

## Risks

- **The `builtin.py` split touching five files at once could mask a behavior change in review.**
  Mitigated by ordering it last and requiring it be a pure move — no logic edits in the same
  commit, and the existing test suite passes without modification.
- **Python version dependence in the symlink-directory case.** The `rglob` recursion behavior
  differs across ≤3.12 and later. The per-candidate check makes the fix version-independent, but
  the *test* for the directory case must be written so it is meaningful on the project's
  supported versions rather than passing vacuously.

## Verification Walkthrough

Each step is a command to run and what to look for, with the result observed during
implementation. Steps marked *(manual)* need a live model and a plain terminal — `sq run`
refuses to execute inside a Claude Code session.

Test files are named directly rather than selected with `-k`: the original `-k` selectors
here did not match the tests that were written (`list_files_walk_bound` matched nothing;
`pattern_cap or truncation_marker` matched 1 of 8), and a selector that silently matches
nothing reports success for a suite it never ran.

### 1. Capability field parses and defaults

```bash
uv run python -c "
from squadron.models.aliases import get_all_aliases
a = get_all_aliases()
print({k: v.get('tool_use', '<absent>') for k, v in a.items()})"
```

Expect `<absent>` for every shipped alias — the field is documented in `models.toml` but set
on none of them, so existing behavior is unchanged (SC2).

Then add `tool_use = false` to a local alias and confirm it reads back:

```bash
uv run python -c "
from squadron.models.aliases import get_all_aliases, model_allows_tools
print(get_all_aliases()['<your-alias>']['tool_use'], model_allows_tools('<your-alias>'))"
```

**Observed:** a probe alias with `tool_use = false` read back `False`, and
`model_allows_tools` returned `False` for it and `True` for `opus` (no field). All shipped
aliases reported `<absent>`.

### 2. A `tool_use = false` model is never offered schemas

```bash
uv run pytest tests/tools/test_effective_tools.py -v
```

Expect the gate tests green: the helper truth table, one case per sanctioned call site —
review client, dispatch, summary one-shot, metrology audit (SC1) — the pass-through default
(SC2), and the call-site enumeration test that fails on an un-gated construction (SC1a).

**Observed:** 25 passed. The SC1a guard was verified by temporarily adding a fifth
tool-passing `AgentConfig` site: the suite failed, named the offending file, and told the
author to route it through `resolve_effective_tools`.

**Caveat discovered:** the capability must be read while the *alias name* is still known.
`resolve_model_alias` collapses an alias to a model id, and several aliases can share one id
while disagreeing on `tool_use` (`codex` and `codex-agent` both resolve to `gpt-5.3-codex`),
so there is no sound reverse lookup. The pipeline reads it via `ModelResolver.resolve_full`
and the review CLI reads it before resolution; a regression test pins that ordering.

### 3. `--no-tools` empties the effective set *(manual, live model)*

Run the same review twice from a plain terminal:

```bash
uv run sq review code <slice> --model <alias> --no-tools -v
uv run sq review code <slice> --model <alias> -v
```

The first must print a tools-disabled indication and record the suppression in the persisted
review; the second must show tools given and a non-zero call count. Confirm the two artifacts
are distinguishable by the recorded `toolsSuppressedReason` frontmatter field, **not** by
reading model prose.

**Observed 20260906**, three runs against `kimi27` (`moonshotai/kimi-k2.7-code`) via
openrouter. A third run was added beyond the pair above, because `--no-tools` and the alias
capability are different code paths that must produce *different* reason values:

| Run | Terminal | Persisted frontmatter |
|---|---|---|
| `--model kimi27 --no-tools` | `Review tools suppressed (reason=run-suppressed)` | `toolsSuppressedReason: run-suppressed` |
| `--model kimi27` | tool activity, then findings | `toolsGiven: [read_file, list_files, grep]`, `toolCallsMade: 45` |
| `--model notools` | `Review tools suppressed (reason=model-capability)` | `toolsSuppressedReason: model-capability` |

All three states are distinguishable from the recorded field alone, with no reference to
model prose (SC3, SC4). The tools run produced materially better findings than either
suppressed run — two real CONCERNs about project configuration that the tool-less runs did
not reach.

**Two defects found by this step**, both pre-existing and neither caused by this slice:

- The jail refusals fired correctly and visibly on `.venv/bin/python*` symlinks — the
  security fix working in production. But `grep` then exhausted its 5s budget on the literal
  pattern `CLAUDE.md` and reported *"Use a simpler or more anchored pattern"*. The pattern
  was not the problem: `.venv` is 21,402 of this repo's 29,373 entries, and `grep` spends the
  whole budget reading ~351 MB of virtualenv before reaching any project file. The advice is
  unfollowable, and the model retried twice. [Issue #79](https://github.com/ecorkran/squadron/issues/79).
- The run hit `Agentic loop history exceeded agent.max_history_chars (400000)` after 45 tool
  calls. `MAX_TOOL_RESULT_CHARS` (100,000) is 25% of the history budget, so four full-size
  results exhaust it. The guard behaved correctly; the two constants were never sized against
  each other. [Issue #80](https://github.com/ecorkran/squadron/issues/80).

Neither blocks the slice: both bounds did what they were built to do, and the failures are in
values and scope chosen elsewhere. Both are worth fixing before tool-using reviews are relied
on routinely.

### 4. The jail holds against a symlink

```bash
uv run pytest tests/tools/test_jail_symlinks.py -v
```

Expect refusals for both `grep` and `list_files`, for both the symlinked-file and
symlinked-directory cases, each with a WARNING logged (SC5, SC6).

**Observed:** 5 passed. Verified non-vacuous — with the guard removed, all four escape cases
fail.

**Caveat discovered:** on Python 3.13+ `rglob` yields a symlinked directory without
descending into it, and `is_file()` is `False` for that entry. Checking `is_file()` before
containment therefore skipped the escape *silently* instead of logging it, so the
containment check runs first in `_grep_candidates`. Each test asserts the guard was reached
via its WARNING rather than only that no content leaked — on 3.13+ the latter passes with no
guard at all.

### 5. Pattern cap and truncation marker

```bash
uv run pytest tests/tools/test_grep_bounds.py -v
```

An over-long pattern must be rejected before compilation with an error result, not an
exception (SC7). A match beyond the read cap must produce a visible marker naming the file
(SC8).

**Observed:** 8 passed. "Before compilation" is asserted directly by a spy on
`regex.compile` — asserting only on the returned message would still pass if the check ran
after compilation, which is the bug the bound exists to prevent.

### 6. One tool result cannot eat the history budget

```bash
uv run pytest tests/providers/openai/test_tool_result_cap.py -v
```

Assert the truncation happens before the append, and that the budget guard is *not* what
stops it (SC9).

**Observed:** 4 passed; 3 of the 4 fail with the cap removed. The tests set
`max_history_chars` generously so the budget guard cannot be what bounded the history, and
assert no `max_history_chars` warning fired.

### 7. `list_files` bounds work, not just output

```bash
uv run pytest tests/tools/test_list_files_bounds.py -v
```

The test must demonstrate bounded *work* — the walk stops early over a wide tree — rather
than only asserting the returned byte count (SC10).

**Observed:** 5 passed; 4 of the 5 fail against the pre-fix implementation. Bounded work is
asserted by wrapping `Path.glob`/`Path.rglob` and counting entries actually consumed, since
the pre-existing byte cap already bounded the output while `sorted()` drained the whole tree.

### 8. Split preserves the import surface

```bash
uv run python -c "
from squadron.tools.builtin import READ_FILE, WRITE_FILE, BASH, LIST_FILES, GREP
print('imports intact')"
wc -l src/squadron/tools/builtin/*.py
```

Every module under the ~300-line convention; imports resolve unchanged (SC11).

**Observed:** imports intact. `__init__.py` 61, `_shared.py` 200, `bash_tool.py` 103,
`file_tools.py` 234, `search_tools.py` 221 — all under 300, from a 690-line original. The
full suite passed with **zero test edits**, which is the actual proof the move was pure.

**Caveat discovered:** `bash` was given its own module (`bash_tool.py`) rather than joining
the file tools, which the design left open — `file_tools.py` is already the largest of the
four. The package-internal helpers lost their leading underscores (`_resolve_in_jail` →
`resolve_in_jail`): once they are imported across modules, `reportPrivateUsage` flags every
use, and the `_shared` module name already carries the privacy. `builtin._resolve_in_jail`
is still exported as an alias, because the jail's existing tests import it under that name.

### 9. Full gate set

```bash
uv run ruff format . && uv run ruff check . && uv run pytest -q && uv run pyright
```

All green; `pyright` shows no *new* errors (issue #74's `mcp_bridge.py` symbol-rename errors
pre-exist on main and are not this slice's).

**Observed:** ruff format and check clean; 3363 passed, 2 skipped; pyright reports exactly
the 2 pre-existing `mcp_bridge.py` errors.

**Caveat discovered:** pyright is load-bearing here, not a formality — it caught the review
CLI's computed capability being dropped, because `run_review_with_profile` had no parameter
to receive it and was re-deriving it from an already-resolved model id.

### Known issue affecting reruns

`tests/review/test_verbosity.py` invokes the review CLI, whose verbosity wiring calls
`setLevel` on named loggers and never restores them, leaking that state to every later test
in the process. A test asserting on DEBUG records can then fail depending on file order
(issue #78). It is pre-existing, not caused by this slice, and reproduces with this branch
stashed.

## Effort

3/5 — raised from the slice plan's original 1/5 by the bounds work. The configuration half is
small and follows established precedent (`private` bool, existing CLI flags). The bounds half is
five distinct fixes plus a package split, one of which is a security fix requiring
version-aware tests.
