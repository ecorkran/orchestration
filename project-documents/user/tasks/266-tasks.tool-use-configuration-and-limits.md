---
docType: tasks
slice: tool-use-configuration-and-limits
project: squadron
lld: user/slices/266-slice.tool-use-configuration-and-limits.md
dependencies: [261, 262, 263, 265]
projectState: >
  Slice 266 design complete and review-addressed (CONCERNS resolved 20260905:
  the capability gate is resolve_effective_tools in the caller, not the agent;
  four tool-passing AgentConfig sites enumerated; SC1a enumeration test added).
  Slices 261-265 shipped the tool stack, dispatch/review wiring, and tool
  observability. Final slice of the 260 initiative (5/6 complete).
dateCreated: 20260905
dateUpdated: 20260905
status: not_started
---

## Context Summary

- Working on the **tool-use-configuration-and-limits** slice (266), the last
  slice of initiative 260. Parent:
  `260-slices.non-sdk-agent-tool-use-openai-compatible-agentic-loop.md`, entry 6.
- Two independent halves, both configuration of the tool boundary:
  - **Configuration half (Parts A-B):** a `tool_use` capability on models.toml
    aliases plus a `--no-tools` review flag, combined by one shared helper.
  - **Bounds half (Parts C-G):** five input-validation fixes plus a package
    split, all in `builtin.py` / `limits.py`.
- **Order is fixed by the design.** Item (a), the jail re-check, is the only
  security item and lands first among the bounds (D5). The `builtin.py` split
  lands last so every preceding diff stays readable against the current file.
  The configuration half is independent of the bounds half and goes first
  because Part A's helper is the slice's central contract.
- **Effort 3/5** overall. Raised from the slice plan's 1/5 by the bounds work.

### Commit checkpoints

The standing CLAUDE.md rule (commit per task) applies throughout. Three points
must be **isolated commits** rather than folded into neighbouring work, because
each is a diff someone will need to read on its own:

- **T13-T14** (the jail re-check) — the only security fix in the slice.
- **T23** (the `builtin.py` split) — a pure move; any logic change sharing this
  commit defeats the review that the ordering exists to enable.
- **T10a** (the suppression field) — touches five files across four layers.

### Grounding notes (read before starting — verified against the code 20260905)

Facts established while resolving the design review. Some correct earlier
statements in the architecture doc:

- **Dispatch already populates `allowed_tools`**
  ([dispatch.py:117](src/squadron/pipeline/actions/dispatch.py#L117)). The
  architecture's Current State said it did not. Part B is a change to an
  existing assignment, not a new code path.
- **Four `AgentConfig` sites pass tools**, not the two the original design
  named: `review_client.py:138`, `dispatch.py:109`,
  `pipeline/summary_oneshot.py:68`, `metrology/audit.py:608`. Three further
  sites (`providers/auth.py:234`, `server/routes/agents.py:49` and `:179`) pass
  no `allowed_tools` and are **out of scope** — the SC1a test must treat them as
  legitimately un-gated, not as violations.
- **The agent cannot be the gate.** It receives a resolved model id and must not
  read models.toml (D3). `OpenAICompatibleAgent.__init__`
  ([agent.py:114-140](src/squadron/providers/openai/agent.py#L114-L140))
  materializes whatever list it is handed.
- **`limits.py` constants are read as module attributes at call time**, never
  imported by value, so tests monkeypatch `limits.X`. Every new constant follows
  this or its tests cannot patch it.
- **Tool results enter history at
  [agent.py:358](src/squadron/providers/openai/agent.py#L358)**; the existing
  history budget guard is the block at
  [agent.py:360](src/squadron/providers/openai/agent.py#L360). Item (c) must
  truncate *before* the append, so the budget guard is not what stops it (SC9).

---

## Part A — The capability gate (do first)

- [ ] **T1. Add `tool_use` to the alias schema**
  - [ ] In `src/squadron/models/aliases.py`, add `tool_use: bool` to the
    `ModelAlias` TypedDict (aliases.py:33-43), beside `private` / `cost_tier`.
  - [ ] In `_extract_metadata` (aliases.py:51), parse it with the same
    `isinstance(val, bool)` guard the `private` field uses (aliases.py:58-60).
    Do not invent a new validation style.
  - [ ] Absent means default-allow. Do **not** write a default into the dict —
    absence must stay distinguishable from an explicit `true` so the SC2
    pass-through test can assert on it.
  - [ ] **Success:** an alias table with `tool_use = false` reads back `False`;
    an alias without the field has no `tool_use` key at all.
  - Effort: 1/5

- [ ] **T2. Document the field in shipped models.toml**
  - [ ] In `src/squadron/data/models.toml`, document `tool_use` in the header
    comment alongside the other optional metadata fields.
  - [ ] Set it on **no** shipped alias — default-true preserves current behavior
    for every existing user (SC2).
  - [ ] **Success:** the header documents the field; `grep 'tool_use' models.toml`
    returns only comment lines.
  - Effort: 1/5

- [ ] **T3. Write `resolve_effective_tools`**
  - [ ] New module in the tools package (not the review package — dispatch and
    the audit use it too). Signature per the design's Implementation Details:
    ```python
    def resolve_effective_tools(
        declared: list[str] | None,
        *,
        model_allows_tools: bool,
        suppressed: bool,
    ) -> tuple[list[str], str | None]:
    ```
  - [ ] Returns `(effective names, reason emptied or None)`. The reason string is
    what lets a call site announce suppression without re-deriving why.
  - [ ] Formula: `declared ∩ (capability allows)`, emptied entirely by
    `suppressed`. An already-empty or `None` `declared` yields `([], None)` —
    "nothing was declared" is not a suppression and must not be announced as one.
  - [ ] Export it from `squadron.tools` (`__init__.py`'s `__all__`, alongside
    `materialize` / `lookup`).
  - [ ] **Success:** the function is importable as
    `from squadron.tools import resolve_effective_tools`; each of the three
    inputs independently empties a non-empty declared set with a distinct reason.
  - Effort: 2/5

- [ ] **T4. Test `resolve_effective_tools`** *(test-with T3)*
  - [ ] New `tests/tools/test_effective_tools.py`.
  - [ ] Cover the truth table: declared-only (pass through), capability denies,
    `--no-tools` suppresses, both deny at once, and `declared=None` / `[]`.
  - [ ] Assert the reason is `None` exactly when nothing was emptied, and
    non-`None` with distinguishable text for capability-denial vs suppression —
    SC4 requires telemetry to tell those apart.
  - [ ] **Success:** all cases pass; no case returns a non-empty list when either
    denial applies.
  - Effort: 1/5

- [ ] **T5. Route the review client through the gate**
  - [ ] In `src/squadron/review/review_client.py`, pass
    `resolved_allowed_tools` (review_client.py:79) through
    `resolve_effective_tools` before it reaches `AgentConfig`
    (review_client.py:138).
  - [ ] Read the alias's `tool_use` in this layer — the config layer is where
    alias lookup belongs (D3). The agent must remain unchanged.
  - [ ] When the reason is non-`None`, log at INFO (SC4) **and** pass it onto
    `AgentConfig` for T10a to persist. The log alone does not satisfy SC4 —
    telemetry must carry it too.
  - [ ] **Success:** a `tool_use = false` model produces an empty
    `allowed_tools` on the constructed `AgentConfig` even when the template
    declares tools; an alias without the field is unaffected.
  - Effort: 2/5

- [ ] **T6. Test the review-path gate** *(test-with T5)*
  - [ ] In `tests/tools/test_effective_tools.py` (or a review-side test module,
    matching where the existing review-client tests live).
  - [ ] Assert SC1 for the review path and SC2 for the absent-field default.
  - [ ] Assert the INFO log fires on suppression and does **not** fire when
    nothing was declared.
  - [ ] **Success:** both cases green.
  - Effort: 1/5

---

## Part B — The remaining three call sites

Each site is its own task: they construct `AgentConfig` differently and a single
combined task would hide a missed one.

- [ ] **T7. Route dispatch through the gate**
  - [ ] In `src/squadron/pipeline/actions/dispatch.py`, route the step's
    `allowed_tools` (dispatch.py:117) through the helper.
  - [ ] The field is **already populated** here — this edits an existing
    assignment. Do not add a new code path.
  - [ ] Note the pre-existing SDK-profile guard on `allowed_tools` (issue #75);
    leave it alone, it is out of scope.
  - [ ] **Success:** `sq run` with a `tool_use = false` model offers no schemas;
    an unmarked model is unaffected.
  - Effort: 2/5

- [ ] **T8. Route the summary one-shot through the gate**
  - [ ] In `src/squadron/pipeline/summary_oneshot.py`, route `allowed_tools`
    (summary_oneshot.py:79) through the helper.
  - [ ] Preserve the existing `cwd=cwd if allowed_tools else None` coupling
    (summary_oneshot.py:78) — if the gate empties the set, `cwd` must go to
    `None` with it, or the agent's own `allowed_tools`/`cwd` consistency check
    (agent.py:115-119) reasons about a stale pairing.
  - [ ] **Success:** the pipeline `summary` action gates correctly and the
    cwd pairing still holds in both directions.
  - Effort: 2/5

- [ ] **T9. Route the metrology audit through the gate**
  - [ ] In `src/squadron/metrology/audit.py`, route `_AUDIT_ALLOWED_TOOLS`
    (audit.py:621) through the helper.
  - [ ] The list is a fixed module constant, but a `tool_use = false` model must
    still be gated — the capability describes the *model*, not the caller (D1).
  - [ ] **Success:** the audit path gates on capability; the constant itself is
    unchanged.
  - Effort: 2/5

- [ ] **T10. Test all four call sites plus the enumeration guard** *(test-with T7-T9)*
  - [ ] In `tests/tools/test_effective_tools.py`, one gate test per site:
    review client, dispatch, summary one-shot, metrology audit (SC1).
  - [ ] **The SC1a enumeration test.** Statically enumerate `AgentConfig(...)`
    constructions across `src/` that set `allowed_tools`, and assert the set
    equals the four sanctioned sites. Use AST parsing, not a regex over source
    text — a regex here would be the fragile-pattern-matching the project rules
    warn about.
  - [ ] The three no-tools sites (`providers/auth.py:234`,
    `server/routes/agents.py:49` and `:179`) must **not** be flagged: the test
    keys on the presence of the `allowed_tools` keyword, not on `AgentConfig`
    alone.
  - [ ] Give the failure message an explicit instruction — a future author must
    learn from the failure that the new site has to route through
    `resolve_effective_tools`, not merely that a count changed.
  - [ ] **Success:** all four gate tests green; adding a fifth tool-passing site
    fails the suite (verify by temporarily adding one, then removing it).
  - Effort: 3/5

- [ ] **T10a. Persist *why* a tool set is empty**
  - [ ] **There is no existing field for this.** Slice 265 distinguished two
    states — offered-but-unused (`tools_given=[...]`, `tool_calls_made=0`) and
    never-offered (both `None`). Suppression is a **third** state 265 never
    needed, and it currently collapses into the second: `_stamp_tool_telemetry`
    returns early on an empty `_tools_given`
    ([agent.py:398](src/squadron/providers/openai/agent.py#L398)), so a
    suppressed run and a no-tools-declared run persist identically. SC3 and SC4
    cannot be met without this task.
  - [ ] Thread `resolve_effective_tools`'s `reason` along the path 265 used for
    `tools_given`, so the mechanism stays uniform:
    1. Carry it on `AgentConfig` (`core/models.py:40-62`), beside
       `allowed_tools`.
    2. Stamp it into the final message's metadata in `_stamp_tool_telemetry`
       (agent.py:393-401). This branch must run **even when `_tools_given` is
       empty** — that is the whole point, and the existing early return at
       agent.py:398 is what currently prevents it.
    3. Read it back in `review_client.py` (~line 188, next to the `tools_given`
       read) onto a new `ReviewResult` field (`review/models.py:76`, beside the
       265 telemetry fields).
    4. Emit it in **both** persistence forms: the markdown frontmatter
       (`persistence.py:213`, beside `toolsGiven`) and `to_dict()`
       (`review/models.py:83`). A JSON-only field repeats issue #72's shape,
       where the artifact people actually read carried no evidence.
  - [ ] Absent when nothing was suppressed. A run that simply declared no tools
    must stay byte-for-byte unchanged — this field appears only when a
    non-empty declared set was emptied.
  - [ ] **Success:** three states are distinguishable in the persisted artifact:
    offered-and-used, offered-and-unused, and **suppressed with its reason**. A
    never-declared run's output is unchanged.
  - Effort: 3/5

- [ ] **T10b. Test the suppression field** *(test-with T10a)*
  - [ ] Assert all three states persist distinguishably, in **both** the markdown
    frontmatter and `to_dict()`.
  - [ ] Assert a never-declared run's artifact is unchanged against the
    pre-T10a output — this field must not leak into runs that were never gated.
  - [ ] Assert the capability-denied and `--no-tools` reasons are distinct in
    the persisted text, not merely both non-empty (SC4).
  - [ ] **Success:** all cases green; existing slice 265 telemetry tests pass
    untouched.
  - Effort: 2/5

- [ ] **T11. Add `--no-tools` to the review CLI**
  - [ ] In `src/squadron/cli/commands/review.py`, add the flag to both review
    subcommands that accept `--model`, threading it to the helper's
    `suppressed` argument.
  - [ ] Record the suppression via the T10a field (SC3). Do **not** try to reuse
    `tools_given` — an empty list there is indistinguishable from an absent one
    once it reaches persistence.
  - [ ] **Success:** `--no-tools` empties the effective set for one run and the
    persisted artifact records it as suppressed, with the reason; omitting the
    flag changes nothing.
  - Effort: 2/5

- [ ] **T12. Test `--no-tools` end to end** *(test-with T11)*
  - [ ] Assert the flag reaches the helper, that the persisted review records
    the suppression via the T10a field (SC3), and that the run is
    distinguishable from a no-tools-declared run by that field — not by model
    prose (SC4).
  - [ ] **Success:** both subcommands covered.
  - Effort: 2/5

---

## Part C — The jail re-check (security; first of the bounds)

- [ ] **T13. Re-resolve every grep candidate against the jail**
  - [ ] In `src/squadron/tools/builtin.py`, inside `_grep_candidates`
    (builtin.py:489-501), resolve each yielded entry and skip any that is not
    `is_relative_to` the jail root.
  - [ ] Placed inside the generator so both escape routes close at the single
    point candidates are produced: (1) a symlinked **file** whose target is
    outside the jail — `entry.is_file()` follows the link and returns true;
    (2) on Python ≤3.12, `rglob` recursing into symlinked **directories**.
  - [ ] `_grep_candidates` will need the jail root — it currently takes only
    `target` and `glob`. Thread `cwd` in from `_grep_factory` (builtin.py:503)
    rather than re-deriving it.
  - [ ] Keep the generator lazy. Its docstring records why it must not
    materialize the tree; a `sorted()` or list build here reintroduces the
    budget bug it warns about.
  - [ ] A refused candidate is **skipped silently to the model** (D6) — it looks
    like a file that did not match; surfacing "you were denied" invites probing
    for the boundary.
  - [ ] Log the refusal at WARNING, mirroring `_grep_timeout`'s treatment. This
    is the operator-visible half (SC5).
  - [ ] **Success:** a symlink inside the jail pointing outside it yields no
    content through `grep`, and logs at WARNING.
  - Effort: 3/5

- [ ] **T14. Apply the same guard to `list_files`**
  - [ ] In `_list_files_factory`'s `_walk` (builtin.py:404-430), filter the
    `rglob`/`glob` results (builtin.py:422) through the same containment check.
  - [ ] Share the check with T13 — extract it as a helper beside
    `_resolve_in_jail` (builtin.py:38). Two copies of a containment test is
    exactly the scattered-comparison the project rules forbid.
  - [ ] **Success:** `list_files` does not name entries outside the jail (SC6),
    with the same WARNING.
  - Effort: 2/5

- [ ] **T15. Test the jail against symlinks** *(test-with T13-T14)*
  - [ ] In `tests/tools/`, cover four cases: symlinked-file and
    symlinked-directory, each for `grep` and `list_files` (SC5, SC6).
  - [ ] Assert the WARNING is logged in each.
  - [ ] **The directory case must not pass vacuously.** `rglob`'s symlink
    recursion differs across Python ≤3.12 and later, so on a version that does
    not recurse, a naive test passes without exercising the guard. Assert the
    guard was reached — e.g. on the WARNING — rather than only on absent output.
    Note the version dependence in a comment.
  - [ ] `_resolve_in_jail` itself is unchanged and its existing tests must still
    pass untouched.
  - [ ] **Success:** all four cases green and meaningful on the project's
    supported Python versions.
  - Effort: 3/5

---

## Part D — Pattern cap and truncation marker

- [ ] **T16. Cap grep pattern length before compilation**
  - [ ] Add `MAX_PATTERN_CHARS` to `src/squadron/tools/limits.py` with a comment
    in the established style.
  - [ ] In `_search` (builtin.py:~521), check the length **before**
    `regex.compile` — the point is to not hand an unbounded pattern to the
    engine at all.
  - [ ] Return an error result telling the model to shorten it; do **not** raise.
    The model supplied the pattern and is the one that must correct it — same
    reasoning as the existing invalid-regex branch (builtin.py:~528).
  - [ ] Read the constant as `limits.MAX_PATTERN_CHARS` at call time so tests can
    monkeypatch it.
  - [ ] **Success:** an over-long pattern returns an error result before
    compilation (SC7); a normal pattern is unaffected.
  - Effort: 1/5

- [ ] **T17. Mark grep's truncated reads**
  - [ ] `_search` reads `handle.read(limits.MAX_READ_BYTES)` (builtin.py:~545)
    and searches only that prefix, so a match past the cap is reported as no
    match — a silent failure the project's no-fallback rule forbids.
  - [ ] Keep the bound; add the marker. When a file is truncated at the read cap,
    include a visible per-file notice **naming the file** so the model can narrow
    its own search.
  - [ ] Do not switch to line-wise scanning (D7) — it changes the timeout
    accounting the per-line `remaining` budget depends on (builtin.py:~556).
  - [ ] **Success:** a match beyond the read cap produces a marker naming the
    file; no match is dropped without one (SC8).
  - Effort: 2/5

- [ ] **T18. Test the pattern cap and truncation marker** *(test-with T16-T17)*
  - [ ] Monkeypatch `limits.MAX_PATTERN_CHARS` and `limits.MAX_READ_BYTES` to
    small values rather than building megabyte fixtures.
  - [ ] Assert the over-long pattern is rejected as a *returned result*, not a
    raised exception (SC7).
  - [ ] Assert a file whose only match sits past the read cap produces the marker
    naming that file (SC8).
  - [ ] Assert both bounds trip the baseline DEBUG tool logging, so an operator
    on `-vv` can distinguish repeated cap hits from routine tool use.
  - [ ] **Success:** all cases green.
  - Effort: 2/5

---

## Part E — Tool-result cap

- [ ] **T19. Cap a tool result before it enters history**
  - [ ] Add `MAX_TOOL_RESULT_CHARS` to `limits.py`, same style.
  - [ ] In `src/squadron/providers/openai/agent.py`, truncate with a visible
    marker at the append site (agent.py:358) — **before**
    `_append_history`, not inside it.
  - [ ] The existing history budget guard (agent.py:360) must **not** be what
    stops it. That guard is a whole-conversation backstop; this cap is
    per-result, and SC9 requires a single result to be unable to exhaust
    `agent.max_history_chars` on its own.
  - [ ] **Success:** an oversized single tool result is truncated with a marker
    and the budget guard does not fire.
  - Effort: 2/5

- [ ] **T20. Test the tool-result cap** *(test-with T19)*
  - [ ] Assert truncation happens **before** the append, and assert the budget
    guard did not fire — SC9 names this explicitly, so test the mechanism, not
    just the outcome.
  - [ ] Assert a normal-sized result is untouched.
  - [ ] **Success:** both cases green.
  - Effort: 2/5

---

## Part F — Bounded `list_files` walk

- [ ] **T21. Bound the work `list_files` does, not just its output**
  - [ ] Add `MAX_LIST_ENTRIES` to `limits.py`.
  - [ ] In `_walk` (builtin.py:419-423), stop consuming the iterator at the cap.
    Today `sorted(...)` materializes the entire tree before `_truncate` bounds
    the *bytes*, so a wide tree is fully walked no matter what is returned.
  - [ ] The cap applies to entries walked; `_truncate` on the output
    (builtin.py:425) stays as the byte-level bound. The two are different limits
    and both remain.
  - [ ] Emit a visible marker when the cap is hit — a short listing must stay
    distinguishable from a truncated one.
  - [ ] **Success:** a wide tree stops early (SC10).
  - Effort: 2/5

- [ ] **T22. Test bounded work** *(test-with T21)*
  - [ ] The test must demonstrate bounded **work**, not merely a bounded byte
    count — SC10 says so explicitly, and asserting only on returned bytes passes
    even with the current full-walk behavior.
  - [ ] Assert the walk stops early over a wide tree: count entries actually
    visited (e.g. instrument the iterator) rather than measuring output size.
  - [ ] Assert the cap marker appears.
  - [ ] **Success:** the test fails against the pre-T21 implementation. Verify
    this by stashing T21 — a test that passes both ways proves nothing.
  - Effort: 3/5

---

## Part G — Package split (last)

- [ ] **T23. Split `builtin.py` into a package**
  - [ ] Pure move, **no logic change**, in its own commit. `builtin.py` is 613
    lines against the ~300-line convention.
    ```
    tools/builtin/__init__.py     — registers all five descriptors; re-exports
    tools/builtin/_shared.py      — _resolve_in_jail, the T14 containment helper,
                                    _truncate, _error, _jail_violation, _guarded,
                                    arg coercion helpers
    tools/builtin/file_tools.py   — read_file, write_file, list_files
    tools/builtin/search_tools.py — grep
    ```
  - [ ] `bash` goes with the file tools or into its own module — decide from the
    line counts once the other three are placed.
  - [ ] The public import surface must not change:
    `squadron.tools.builtin.READ_FILE` and siblings keep resolving. Existing
    imports and tests are the contract.
  - [ ] Registration side effects must fire exactly once on import of
    `squadron.tools.builtin`, matching what `tools/__init__.py:12-15` documents.
    Double registration or a missed descriptor is the failure mode here.
  - [ ] **Success:** every module under ~300 lines; the existing test suite
    passes **without modification** (SC11).
  - Effort: 3/5

- [ ] **T24. Verify the split changed nothing** *(test-with T23)*
  - [ ] Confirm the import surface: `from squadron.tools.builtin import
    READ_FILE, WRITE_FILE, BASH, LIST_FILES, GREP` resolves.
  - [ ] Confirm `tools.list_tools()` returns the same names as before the split.
  - [ ] `wc -l src/squadron/tools/builtin/*.py` — all under the convention.
  - [ ] No test file may be edited in this task. If a test needs changing, the
    move was not pure — fix the move.
  - [ ] **Success:** suite green with zero test edits.
  - Effort: 1/5

---

## Part H — Close-out

- [ ] **T25. Record the limits decision in `limits.py`**
  - [ ] The module docstring says "Making these configurable is slice 266's job
    — this module deliberately has no config plumbing." Update it to record that
    the decision was **taken**, not skipped: constants stay module attributes
    with no config keys until someone needs to tune one (D4).
  - [ ] The wording must not read as unfinished work, or a future reader
    reopens a closed decision. Point it at
    [issue #76](https://github.com/ecorkran/squadron/issues/76), where the
    enhancement and its constraints are tracked.
  - [ ] **Success:** the docstring records the decision and its reasoning.
  - Effort: 1/5

- [ ] **T26. Full gate set**
  - [ ] `uv run ruff format .` — run immediately before committing.
  - [ ] `uv run ruff check .`
  - [ ] `uv run pytest -q`
  - [ ] `uv run pyright` — no **new** errors. Two pre-exist in
    `src/squadron/tools/mcp_bridge.py` (`MCPError`, issue #74's mcp 2.x symbol
    rename); they are not this slice's. If unsure whether an error is new,
    stash and re-run rather than guessing.
  - [ ] **Success:** all green (SC12).
  - Effort: 1/5

- [ ] **T27. Manual verification** *(needs a live model and a plain terminal)*
  - [ ] `sq run` refuses to execute inside a Claude Code session — these must be
    run from a plain terminal, prefixed `uv run` (a stale `sq` on PATH has
    produced misleading results before).
  - [ ] Add `tool_use = false` to a local alias in
    `~/.config/squadron/models.toml` and confirm it reads back `False`
    (walkthrough step 1).
  - [ ] Run the A/B pair (walkthrough step 3):
    ```bash
    uv run sq review code <slice> --model <alias> --no-tools -v
    uv run sq review code <slice> --model <alias> -v
    ```
    The first must show tools disabled and record it in the persisted review;
    the second must show tools given and a non-zero call count.
  - [ ] Confirm the two artifacts are distinguishable **by the recorded field**,
    not by reading model prose.
  - [ ] Transcribe the observed output into the design's Verification Walkthrough
    under an `Observed:` line, matching the idiom slice 265 used. Do not leave
    the steps reading as expectations.
  - Effort: 2/5

- [ ] **T28. Slice close-out**
  - [ ] Write the DEVLOG entry per `prompt.ai-project.system.md`, section
    "Session State Summary".
  - [ ] Mark slice 266 complete in the slice design and in
    `260-slices.non-sdk-agent-tool-use-openai-compatible-agentic-loop.md`. This
    is the last slice of the 260 initiative — the slice plan goes 6/6.
  - [ ] Mark any dropped or deliberately skipped item `[x]` before closing, so
    the checkbox state reflects the real outcome.
  - Effort: 1/5
