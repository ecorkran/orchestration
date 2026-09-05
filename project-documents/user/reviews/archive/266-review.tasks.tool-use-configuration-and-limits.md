---
docType: review
layer: project
reviewType: tasks
slice: tool-use-configuration-and-limits
project: squadron
verdict: RESOLVED
sourceDocument: project-documents/user/tasks/266-tasks.tool-use-configuration-and-limits.md
aiModel: claude-sonnet-5
status: complete
dateCreated: 20260905
dateUpdated: 20260905
reviewedSha: 629dc1087a5d67723c26ec4fc0805e110fad6c33
findings:
  - id: F001
    severity: fail
    category: gap
    summary: "SC3/SC4 rely on a persisted field that doesn't distinguish suppressed from never-declared"
    location: "project-documents/user/tasks/266-tasks.tool-use-configuration-and-limits.md:202"
  - id: F002
    severity: pass
    category: sequencing
    summary: "Sequencing and test-with pairing are correct"
    location: "project-documents/user/tasks/266-tasks.tool-use-configuration-and-limits.md"
  - id: F003
    severity: pass
    category: coverage
    summary: "Full success-criteria coverage, no scope creep"
    location: "project-documents/user/tasks/266-tasks.tool-use-configuration-and-limits.md"
  - id: F004
    severity: note
    category: process
    summary: "Commit checkpoints are mostly implicit"
    location: "project-documents/user/tasks/266-tasks.tool-use-configuration-and-limits.md"
---

# Review: tasks — slice 266

**Verdict:** RESOLVED (all findings addressed 20260905)
**Model:** claude-sonnet-5

## Findings

### [FAIL] SC3/SC4 rely on a persisted field that doesn't distinguish suppressed from never-declared

T11 says to record tools-disabled by "reusing slice 265's tools-enabled field rather than adding a parallel one." No such boolean field exists — the only telemetry is `tools_given: list[str] | None` (review/models.py:73-77), and `OpenAICompatibleAgent.__init__` computes `requested_tools = allowed_tools or []` (agent.py:114) then only stamps `tools_given` when the list is non-empty (agent.py:398, `if not self._tools_given ...: return`). An empty list from suppression and an absent declaration both collapse to `tools_given: None` in the persisted `ReviewResult` — identical output. SC3's own wording ("the persisted review records tools as disabled") and SC4's ("distinguishable in telemetry from 'no tools were declared'") cannot be met by T5/T11 as scoped; they need a new field (e.g., threading `resolve_effective_tools`'s `reason` through `AgentConfig`/agent telemetry into `ReviewResult`/persistence), which T11 explicitly discourages adding. Recommend inserting a task before T11 that adds this field, and correcting T11's instruction.

### [PASS] Sequencing and test-with pairing are correct

Part ordering matches D5 (jail re-check first among bounds, package split last), and every implementation task is immediately followed by its test task (T4/T3, T6/T5, T10/T7-T9, T12/T11, T15/T13-T14, T18/T16-T17, T20/T19, T22/T21, T24/T23).

### [PASS] Full success-criteria coverage, no scope creep

SC1/SC1a/SC2/SC5-SC12 each map cleanly to tasks, and every task traces back to a design element (no orphaned scope creep). SC3/SC4 have nominal task coverage but see the FAIL finding above.

### [NOTE] Commit checkpoints are mostly implicit

Only T23 (the pure-move split) calls out "in its own commit." Other checkpoints rely on the standing CLAUDE.md rule to commit per task rather than being stated inline — not a blocker, but worth calling out given the design's own emphasis on isolating the jail-recheck and split diffs.

## Resolution — 20260905

**F001 (FAIL) — confirmed against the code and fixed.** The finding is correct in
every particular. T11's instruction to reuse "slice 265's tools-enabled field"
named a field that does not exist: the only telemetry is
`tools_given: list[str] | None` (`review/models.py:76`).

The underlying reason 265 left no room here: it distinguished **two** states —
offered-but-unused (`tools_given=[...]`, `tool_calls_made=0`) and never-offered
(both `None`). Suppression is a **third** state 265 never had to represent, and it
collapses into the second, because `_stamp_tool_telemetry` returns early on an
empty `_tools_given` (`agent.py:398`). A suppressed run and a no-tools-declared
run therefore persist identically, and SC3/SC4 were unreachable as scoped.

Added **T10a** (persist the suppression reason) and **T10b** (its tests), placed
before T11 so the field exists when `--no-tools` needs it. T10a threads
`resolve_effective_tools`'s `reason` along the same path 265 used for
`tools_given` — `AgentConfig` → `_stamp_tool_telemetry` → `review_client` →
`ReviewResult` → persistence — keeping the mechanism uniform rather than
inventing a parallel one. Two specifics called out in the task:

- The stamp must fire **even when `_tools_given` is empty**; the early return at
  `agent.py:398` is precisely what prevents it today.
- The field must land in **both** persistence forms. Markdown-frontmatter and
  `to_dict()` both, because a JSON-only field repeats issue #72's shape, where the
  artifact people actually read carried no evidence.

T5 and T12 were corrected to match: T5 now passes the reason onto `AgentConfig`
rather than only logging it (the INFO log alone does not satisfy SC4), and T12
asserts on the T10a field rather than on a non-existent one.

**F004 (NOTE) — addressed.** Added a "Commit checkpoints" section naming the three
points that must be isolated commits: T13-T14 (the only security fix), T23 (the
pure move), and T10a (five files across four layers). The standing per-task commit
rule covers the rest.

F002 and F003 were PASS; no action.

Task file is now 518 lines against the ~450 target — a 68-line overrun, under the
~100-line threshold that would require a split.

### Related

Design decision D4 (limits stay module constants, no config plumbing) is now
tracked as [issue #76](https://github.com/ecorkran/squadron/issues/76) for a future
enhancement, linked from D4 and from T25.
