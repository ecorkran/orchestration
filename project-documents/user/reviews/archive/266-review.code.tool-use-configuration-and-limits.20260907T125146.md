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
toolsSuppressedReason: model-capability
findings:
  - id: F001
    severity: pass
    category: uncategorized
    summary: "Capability gate is centralized and test-covered"
    location: "src/squadron/tools/effective.py"
  - id: F002
    severity: pass
    category: uncategorized
    summary: "Alias capability preserves default-allow backward compatibility"
    location: "src/squadron/models/aliases.py:190-209"
  - id: F003
    severity: pass
    category: uncategorized
    summary: "Tool jail closes symlink escape routes in walk-based tools"
    location: "src/squadron/tools/builtin/_shared.py:41-60"
  - id: F004
    severity: pass
    category: uncategorized
    summary: "Builtin tool refactor keeps modules within the ~300-line guideline"
    location: "src/squadron/tools/builtin/__init__.py"
  - id: F005
    severity: pass
    category: uncategorized
    summary: "SC1a enumeration guard prevents new un-gated AgentConfig sites"
    location: "tests/tools/test_effective_tools.py:434-477"
  - id: F006
    severity: note
    category: uncategorized
    summary: "Audit gate test does not exercise the actual `run_audit` path"
    location: "tests/tools/test_effective_tools.py:355-371"
---

# Review: code — slice 266

**Verdict:** PASS
**Model:** moonshotai/kimi-k2.7-code

## Findings

### [PASS] Capability gate is centralized and test-covered

`resolve_effective_tools` provides a single chokepoint for the model `tool_use` capability and run-level `--no-tools` suppression, with stable `SuppressionReason` values and a clear truth table. The accompanying tests verify all four combinations, distinguish the reasons, and ensure `None`/`[]` declared sets are not misreported as suppression.

### [PASS] Alias capability preserves default-allow backward compatibility

`model_allows_tools` returns `True` for unknown aliases, `None` names, and aliases that omit `tool_use`, so existing behavior is unchanged. The parser only accepts a boolean value and leaves absence distinguishable from an explicit `true`.

### [PASS] Tool jail closes symlink escape routes in walk-based tools

`contained_in_jail` re-resolves walk-discovered entries against the jail root and logs refusals at `WARNING`. Both `grep` and `list_files` apply it, closing the symlink-file and symlink-directory escape routes that `_resolve_in_jail` cannot catch.

### [PASS] Builtin tool refactor keeps modules within the ~300-line guideline

The former 613-line `builtin.py` is split into focused submodules (`_shared`, `bash_tool`, `file_tools`, `search_tools`) while preserving the public import surface and backward-compatible `_resolve_in_jail` alias.

### [PASS] SC1a enumeration guard prevents new un-gated AgentConfig sites

The AST-based scan enumerates every `AgentConfig(allowed_tools=...)` construction in `src/squadron` and fails unless the file is in the sanctioned list. This mechanically prevents future call sites from bypassing the gate.

### [NOTE] Audit gate test does not exercise the actual `run_audit` path

`test_audit_gate_applies_to_the_fixed_tool_constant` tests `resolve_effective_tools` with `list(_AUDIT_ALLOWED_TOOLS)` rather than calling `run_audit`. The SC1a enumeration guard provides indirect assurance that `metrology/audit.py` routes through the gate, but there is no integration test for audit suppression end-to-end.
