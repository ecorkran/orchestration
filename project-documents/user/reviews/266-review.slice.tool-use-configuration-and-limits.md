---
docType: review
layer: project
reviewType: slice
slice: tool-use-configuration-and-limits
project: squadron
verdict: CONCERNS
sourceDocument: project-documents/user/slices/266-slice.tool-use-configuration-and-limits.md
aiModel: claude-sonnet-5
status: complete
dateCreated: 20260903
dateUpdated: 20260905
reviewedSha: 34dc3e026aeeeb7ef9db4a4276318404499fc8f0
findings:
  - id: F001
    severity: concern
    category: hidden-dependency
    summary: "Dispatch-path enforcement site is asserted but never located"
    location: "project-documents/user/slices/266-slice.tool-use-configuration-and-limits.md#Architecture"
  - id: F002
    severity: note
    category: documentation-completeness
    summary: "Shared resolution helper not reflected in frontmatter `interfaces`"
    location: "project-documents/user/slices/266-slice.tool-use-configuration-and-limits.md:7"
  - id: F003
    severity: note
    category: error-handling
    summary: "Operator-observability of bounds items (b)-(d) relies on inference from architecture's baseline logging, not stated explicitly"
    location: "project-documents/user/slices/266-slice.tool-use-configuration-and-limits.md#Bounds: one shape, five sites"
  - id: F004
    severity: pass
    category: alignment
    summary: "Effective-tools formula matches architecture and slice plan exactly"
    location: "project-documents/user/slices/266-slice.tool-use-configuration-and-limits.md:125"
  - id: F005
    severity: pass
    category: scope
    summary: "Bounds/limits scope expansion is explicitly authorized upstream, not scope creep"
    location: "project-documents/user/slices/266-slice.tool-use-configuration-and-limits.md#Overview"
  - id: F006
    severity: pass
    category: solid-dip
    summary: "Capability resolution kept out of the agent, preserving layering (DIP)"
    location: "project-documents/user/slices/266-slice.tool-use-configuration-and-limits.md#D3"
---

# Review: slice — slice 266

**Verdict:** CONCERNS (all findings addressed 20260905 — see Resolution)
**Model:** claude-sonnet-5

## Findings

### [CONCERN] Dispatch-path enforcement site is asserted but never located

D1 and the "Architecture" section both argue the design achieves "one enforcement site, no caller can forget it" by putting the gate at `OpenAICompatibleAgent.__init__`. But the same section then states the agent "must not read models.toml" and that "the capability is resolved *by the caller* and passed down" (confirmed again as D3). Those two claims are inconsistent: if intersection with `tool_use`/`--no-tools` happens in the caller before `AgentConfig` is built, then the actual gate is distributed across every `AgentConfig`-constructing call site, not centralized in the agent — which is precisely the "caller can forget" failure mode the design claims to have eliminated. The agent merely materializes whatever `allowed_tools` it's handed; it cannot detect an un-gated list.

Given that, the dispatch path (`_dispatch_via_agent`, per the architecture doc's Current State and slice plan's 265 observability note) is the one caller most likely to be missed, since dispatch's `AgentConfig` construction today (per the architecture doc) doesn't populate `allowed_tools` at all — a new code path has to be added. Yet the Integration Points section names `review_client.py`, `cli/commands/review.py`, `agent.py`, `limits.py`, and `builtin.py`, but never names the dispatch-action file that must call `resolve_effective_tools`. SC1 requires dispatch-path coverage, and the Verification Walkthrough's only nod to it is a generic `pytest -k tool_use_capability` filter with no named test module or dispatch construction site. If the dispatch caller is added later without going through the helper, `tool_use = false` silently fails to gate `sq run` — exactly the scenario D1 says must not happen.

### [NOTE] Shared resolution helper not reflected in frontmatter `interfaces`

`interfaces: []` is empty, but the slice introduces `resolve_effective_tools(...)` explicitly as a cross-module contract ("One function, in the tools package... dispatch uses it too"). Since this function is the actual enforcement point per the finding above, listing it under `interfaces` would make its "every caller must use this" requirement discoverable to future slices touching dispatch or other `AgentConfig` construction sites, rather than living only in prose.

### [NOTE] Operator-observability of bounds items (b)-(d) relies on inference from architecture's baseline logging, not stated explicitly

Item (a) explicitly mandates a WARNING log (SC5/D6). Items (b) pattern-cap rejection, (b') truncation marker, (c) tool-result cap, and (d) list_files entry cap specify only model-visible error results/markers (SC7-SC10) with no explicit log-level commitment. The architecture's "Loop visibility via logging" principle (every tool call/result logged at DEBUG, summaries at INFO under `-vv`) likely covers this by inheritance, but the slice doc doesn't say so — it would be worth one sentence confirming these four bounds trip at minimum the existing DEBUG-level tool-result logging, so an operator scanning `-vv` output can distinguish "model repeatedly hits the pattern cap" from routine tool use, consistent with the project's Failure-Mode Enumeration rule (observable, not silent).

### [PASS] Effective-tools formula matches architecture and slice plan exactly

`Effective tools = declared ∩ (capability allows), emptied entirely by --no-tools` is a verbatim match to both the architecture's anticipated-slice description and the slice plan item 6. No drift between planning layers.

### [PASS] Bounds/limits scope expansion is explicitly authorized upstream, not scope creep

The five-item "bounds half" (jail re-check, pattern cap, truncation marker, tool-result cap, list_files walk cap, plus the `builtin.py` split) maps one-to-one to the parent slice plan's "Scope expanded 20260903" section (260-slices doc, item 6, items a-e), including matching rationale (surfaced by 265's review) and matching risk/effort adjustment (1/5 → 3/5). This is traceable scope growth, not undocumented creep.

### [PASS] Capability resolution kept out of the agent, preserving layering (DIP)

D3's rule that the agent receives a resolved model id and never performs alias lookup correctly keeps `models.toml`/config concerns out of the provider layer, consistent with the architecture's existing separation between config-layer alias resolution and the agent's execution responsibilities. (This same decision is what produces the Finding above — the layering is correct, but its interaction with the "single enforcement site" claim needs reconciling.)

## Resolution — 20260905

All three actionable findings addressed in the slice design (`dateUpdated: 20260905`).

**F001 — dispatch-path enforcement site.** Confirmed as a real contradiction and fixed by
correcting the design, not by patching prose. The "one enforcement site at
`OpenAICompatibleAgent.__init__`" claim is withdrawn: D3 makes it impossible, since the agent
receives a resolved model id and cannot see the alias. The gate is now stated to be
`resolve_effective_tools` itself, living in the caller.

Two corrections to the design's factual premises came out of reading the code:

- The design (inheriting the architecture's Current State) said dispatch does not populate
  `allowed_tools` and would need a new code path. It does populate it, at
  [dispatch.py:117](src/squadron/pipeline/actions/dispatch.py#L117). This is a change to an
  existing assignment.
- There are **four** tool-passing `AgentConfig` sites, not the two the design named:
  `review_client.py:138`, `dispatch.py:109`, `pipeline/summary_oneshot.py:68`, and
  `metrology/audit.py:608`. All four are now enumerated in the design and in scope. The other
  three sites (`providers/auth.py:234`, `server/routes/agents.py:49` and `:179`) pass no tools
  and are explicitly out of scope.

Since the layering denies a structural chokepoint, the "caller can forget" risk is closed by a
test instead: new **SC1a** requires a test that enumerates every `AgentConfig` construction
setting `allowed_tools` and fails if one is not sanctioned. SC1 now names all four sites, and
walkthrough step 2 names the test module rather than a generic `-k` filter.

**F002 — `interfaces` frontmatter.** `resolve_effective_tools` is now declared there with its
"every caller must route through it" contract and a pointer to SC1a.

**F003 — bounds observability.** A paragraph after the bounds table states that (b), (b'), (c)
and (d) trip the architecture's baseline DEBUG tool logging in addition to their model-visible
markers, so an operator on `-vv` can distinguish repeated cap hits from routine tool use.

No finding was deferred.
