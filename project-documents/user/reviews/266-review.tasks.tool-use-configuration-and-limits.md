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
reviewedSha: bbc5e24c686a1596dbdb7486e7031a5a440f3481
findings:
  - id: F001
    severity: concern
    category: task-scope-overlap
    summary: "T6 and T10 both claim ownership of the review-client gate test"
    location: "project-documents/user/tasks/266-tasks.tool-use-configuration-and-limits.md:149-156"
  - id: F002
    severity: pass
    category: uncategorized
    summary: "All Technical Scope items and success criteria trace to tasks"
    location: "project-documents/user/tasks/266-tasks.tool-use-configuration-and-limits.md"
  - id: F003
    severity: pass
    category: uncategorized
    summary: "Sequencing matches design constraints (D5) and dependency order"
    location: "project-documents/user/tasks/266-tasks.tool-use-configuration-and-limits.md:76-462"
  - id: F004
    severity: pass
    category: uncategorized
    summary: "Test-with pattern and commit checkpoints"
    location: "project-documents/user/tasks/266-tasks.tool-use-configuration-and-limits.md:35-45"
  - id: F005
    severity: note
    category: uncategorized
    summary: "No NFR/load-test requirement applies to this slice"
    location: "unverified"
---

# Review: tasks — slice 266

**Verdict:** RESOLVED (all findings addressed 20260905)
**Model:** claude-sonnet-5

## Findings

### [CONCERN] T6 and T10 both claim ownership of the review-client gate test

T6 (test-with T5) already asserts "SC1 for the review path" in `tests/tools/test_effective_tools.py`. T10 then lists "one gate test per site: review client, dispatch, summary one-shot, metrology audit (SC1)" — explicitly re-including review client alongside the three sites (dispatch, summary-oneshot, audit) that actually get their first test coverage in T10. A junior AI implementing T10 has no clear instruction on whether to skip the review-client case (already covered), duplicate it, or reconcile it with T6's version in the same file. Recommend narrowing T10's bullet to "dispatch, summary one-shot, metrology audit (SC1)" and having it reference T6's existing review-client case for the enumeration/completeness assertion only.

### [PASS] All Technical Scope items and success criteria trace to tasks

Configuration half (tool_use field, gate helper, four call sites, suppression persistence, --no-tools flag) → T1–T12b. Bounds half (jail re-check, pattern cap, truncation marker, result cap, list_files walk bound, package split) → T13–T24. Close-out (limits.py docstring, full gate, manual verification, DEVLOG) → T25–T28. No SC (SC1–SC12) is left without a corresponding implementation+test task pair, and no task introduces work outside the slice's declared Technical Scope — the Out-of-Scope items (config plumbing for limits.py, `--no-tools` on `sq run`, capability probe, bash sandboxing) have no matching tasks, as expected.

### [PASS] Sequencing matches design constraints (D5) and dependency order

Part A (gate helper) precedes Part B (the four call sites) since T5/T7-T9 depend on T3. Within the bounds half, the jail re-check (T13-T15) lands first as the sole security item per D5, and the `builtin.py` split (T23-T24) lands last so preceding diffs stay legible against the current file, exactly as the design requires. T11 (`--no-tools`) correctly follows T10a (the persistence field it depends on) rather than preceding it. No circular dependencies found.

### [PASS] Test-with pattern and commit checkpoints

Every implementation task is immediately followed by its test task (T3/T4, T5/T6, T7-9/T10, T10a/T10b, T11/T12, T13-14/T15, T16-17/T18, T19/T20, T21/T22, T23/T24) — no batching of tests at the end. The standing per-task commit rule plus explicit isolated-commit call-outs for T13-14, T23, and T10a (each a diff that needs independent review) satisfies the distributed-checkpoint requirement.

### [NOTE] No NFR/load-test requirement applies to this slice

The slice design's bounds work (SC9, "cannot exhaust `agent.max_history_chars`") is a resource-bound correctness property, not a throughput/latency NFR, and is appropriately verified by a unit test (T19/T20) rather than a `tests/load/` load test. No restated NFR in the slice design calls for a load test or CI-gating task, so their absence here is not a gap.

## Resolution — 20260905 (re-review)

**F001 — fixed as recommended, with one addition.** The overlap was real: T6
asserted SC1 for the review path, then T10 re-listed the review client among
"one gate test per site," leaving a junior AI no way to tell whether to skip,
duplicate, or reconcile.

- **T6** now states explicitly that it owns the review-client case, and names
  `tests/tools/test_effective_tools.py` outright. Its previous "(or a review-side
  test module, matching where the existing review-client tests live)" was a second
  source of the same ambiguity — two tasks with an unclear boundary, in a file
  neither one definitively named.
- **T10** is narrowed to the three sites T7-T9 add (dispatch, summary one-shot,
  metrology audit) and told not to duplicate or rewrite T6's case. Its title
  changed from "all four call sites" to "the remaining call sites" so the scope
  reads correctly at a glance.

The addition: T10's success criterion said "all four gate tests green," which is
the property that actually matters and must survive the narrowing. Rather than
drop it, it now reads that all four sanctioned sites are covered **across T6 and
T10** — three added here, plus T6's, which must still pass. Otherwise narrowing
T10 would have quietly removed the only place the four-site total was asserted.

F002-F004 were PASS and F005 a NOTE agreeing no load test applies; no action.
