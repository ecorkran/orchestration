---
docType: taskList
layer: project
dateCreated: 20260223
---

# Code Review Tasks: Model Selection Feature

## Critical Issues

- [ ] **Refactor duplicated model resolution logic**
  - [ ] Create `src/orchestration/cli/commands/common.py` with shared utilities
  - [ ] Implement `resolve_model_with_template()` for review commands
  - [ ] Implement `resolve_model()` for spawn and other commands
  - [ ] Update `review.py` to import from common
  - [ ] Update `spawn.py` to import from common
  - [ ] Verify all tests still pass

- [ ] **Reduce review.py file size (currently 369 lines, target ≤300)**
  - [ ] Extract helper functions to `src/orchestration/cli/commands/review_helpers.py`:
    - `_resolve_cwd()`, `_resolve_verbosity()`, `_resolve_rules_content()`, `_resolve_model()`
  - [ ] Extract display functions to `src/orchestration/review/display.py`:
    - `_display_terminal()`, `_display_json()`, `_write_file()`, `_VERDICT_COLORS`, `_SEVERITY_COLORS`
  - [ ] Update imports in review.py
  - [ ] Verify all tests still pass

## Quality Suggestions

- [ ] **Verify unused import**: Check if `logging` in review.py:1 is needed
  - If unused, remove it
  - If used elsewhere in module, document why

## Verification

- [ ] Run full test suite: `pytest tests/`
- [ ] Check type safety: `pyright --pythonversion 3.12`
- [ ] Check code style: `ruff check src/ tests/`
- [ ] Verify no new warnings introduced
- [ ] Verify review.py ≤300 lines (excluding whitespace)
- [ ] Verify no duplicate functions across common.py, review.py, spawn.py

## Notes

- Review document: `906-review.model-selection-feature.md`
- Changes do not affect functionality, only code organization
- No API changes required
- All existing tests should continue to pass
