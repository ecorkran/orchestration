---
docType: review
layer: project
reviewType: code
slice: tool-use-configuration-and-limits
project: squadron
verdict: PASS
sourceDocument: project-documents/user/slices/266-slice.tool-use-configuration-and-limits.md
aiModel: moonshotai/kimi-k2.7-code
status: complete
dateCreated: 20260906
dateUpdated: 20260906
reviewedSha: a4d1aaf50ccdc71152a3a95955351b448c199e39
toolsSuppressedReason: run-suppressed
findings:
  - id: F001
    severity: pass
    category: design
    summary: "Capability gate is centralized and reason-preserving"
    location: "src/squadron/tools/effective.py:1"
  - id: F002
    severity: pass
    category: structure
    summary: "Tool module split respects file-size guidelines and improves jail coverage"
    location: "src/squadron/tools/builtin/__init__.py:1"
  - id: F003
    severity: pass
    category: design
    summary: "Resolver preserves alias capability without breaking unpack semantics"
    location: "src/squadron/pipeline/resolver.py:38"
  - id: F004
    severity: pass
    category: testing
    summary: "Tests include behavioral coverage and mechanical call-site guards"
    location: "tests/tools/test_effective_tools.py:1"
---

# Review: code — slice 266

**Verdict:** PASS
**Model:** moonshotai/kimi-k2.7-code

## Findings

### [PASS] Capability gate is centralized and reason-preserving

The `resolve_effective_tools` gate centralizes model-capability and run-level suppression logic, returning a stable `SuppressionReason` enum value so telemetry can distinguish "model-capability", "run-suppressed", and both. All sanctioned call sites (review client, dispatch, summary one-shot, metrology audit) route through it, and the empty/None declared-tools case correctly avoids announcing a suppression when nothing was declared.

### [PASS] Tool module split respects file-size guidelines and improves jail coverage

The former 613-line `builtin.py` is split into a focused package (`_shared.py`, `bash_tool.py`, `file_tools.py`, `search_tools.py`), bringing each file under the ~300-line guideline while keeping the public import surface unchanged. New symlink containment via `contained_in_jail`, the `MAX_LIST_ENTRIES` cap, the `MAX_PATTERN_CHARS` cap, and per-file read-truncation markers are all logged at WARNING so escapes/bounds are observable rather than silent.

### [PASS] Resolver preserves alias capability without breaking unpack semantics

`ResolvedModel` carries `tool_use` through the resolution pipeline while `ModelResolver.resolve()` keeps returning the original `(model_id, profile)` tuple. This avoids breaking every existing `model_id, profile = resolve(...)` unpack while giving new tool-aware callers `resolve_full()`.

### [PASS] Tests include behavioral coverage and mechanical call-site guards

The test suite covers the gate truth table, the `--no-tools` CLI flag end-to-end, tool-result capping, symlink jail escapes, listing-entry bounds, grep pattern/read-truncation bounds, and an AST-based enumeration guard that fails if a new `AgentConfig(..., allowed_tools=...)` site bypasses the gate.
