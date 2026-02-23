# Project Guidelines for Claude

## General Development Rules

### Meta-Guide: Guide to the rules
- If the first item in a list or sublist is in this file `enabled: false`, ignore that section.

### Guiding Behavior
* Always resist adding complexity.  Ensure that it is truly necessary and adds significant value.
* Never use silent fallback values.
* Never use cheap "hacks" or well-known anti-patterns to a solution.

### Project Structure
- Always refer to `guide.ai-project.000-process` and follow links as appropriate.
- For UI/UX tasks, always refer to `guide.ui-development.ai`.
- General Project guidance is in `project-documents/ai-project-guide/project-guides/`.
- Relevant 3rd party tool information is in `project-documents/ai-project-guide/tool-guides/`.

#### Project-Specific File Locations
- **Regular Development** (template instances): Use `project-documents/user/` for all project-specific files.
- **Monorepo Template Development** (monorepo active): Use `project-artifacts/` for project-specific files (use directly, e.g. `project-artifacts/` not `project-artifacts/user/`).

### General Guidelines (IMPORTANT)
- Filenames for project documents may use ` ` or `-` separators. Ignore case in all filenames, titles, and non-code content.  Reference `file-naming-conventions`.
- Use checklist format for all task files.  Each item and subitem should have a `[ ]` "checkbox".
- After completing a task or subtask, make sure it is checked off in the appropriate file(s).  Use the task-check subagent if available.
- Keep 'success summaries' concise and minimal -- they burn a lot of output tokens.
- **Preserve User-Provided Concept sections** - When editing project documents (concept, spec, feature, architecture, slice designs), NEVER modify or remove sections titled "## User-Provided Concept". These contain the human's original vision and must be preserved exactly as written. You may add new sections or edit AI-generated sections, but user concept sections are sacred.
- never include usernames, passwords, API keys, or similar sensitive information in any source code or comments.  At the very least it must be loaded from environment variables, and the .env used must be included in .gitignore.  If you find any code in violation of this, you must raise an issue with Project Manager.

### Document Standards
- **All markdown files must include YAML frontmatter.** Minimum: `docType` field. See `file-naming-conventions` for full metadata spec. **Exception:** Public-facing docs (`docs/`, root `README.md`) are exempt — these target external readers and should not include internal metadata.
- **Dates in YAML**: Use `YYYYMMDD` format (no dashes). Example: `dateCreated: 20260217`
- **Document naming**: Use periods (`.`) as primary separators, hyphens (`-`) for secondary grouping: `[document-type].[subject].[additional-info].md`
- **3-digit index system (000-999)**: Files use indices for lineage tracing and categorization. Related documents share a base index. See `file-naming-conventions` for reserved ranges and initiative-based numbering.
  - 000-009: Core process guides
  - 050-099: Project-level architecture
  - 100-799: Initiative working space (claim base at increments of 10)
  - 900-999: Operational (reviews, analysis, maintenance)
- **File size limits**: Target ~350 lines for non-architecture project documents. If a file exceeds this by >33% (~465 lines), split using `-1.md`, `-2.md` suffix convention.
- **Living Document Pattern**: Human and AI collaborate on a single evolving file. Sections titled `## User-Provided Concept` are sacred and must never be modified by AI. See `guide.ai-project.000-process` for details.
- **Modular rules**: Additional platform-specific rules may exist in `project-guides/rules/`. Consult if working in a technology not covered by the rules loaded here.

### MCP (Model Context Protocol)
- Always use context7 (if available) to locate current relevant documentation for specific technologies or tools in use.
- Do not use smithery Toolbox (toolbox) for general tasks. Project manager will guide its use.

### Code Structure
- Keep code short; commits semantic.
- Keep source files to max 300 lines (excluding whitespace) when possible.
- Keep functions & methods to max 50 lines (excluding whitespace) when possible.
- Avoid hard-coded constants - declare a constant.
- Avoid hard-coded and duplicated values -- factor them into common object(s).
- Provide meaningful but concise comments in _relevant_ places.
- **Never use silent fallback values** - If a parameter/property fails to load, fail explicitly with an error or use an obviously-placeholder value (e.g., "ERROR: Failed to load", "MISSING_CONFIG"). Silent fallbacks that look like real data (e.g., `text || "some default text"`) make debugging nearly impossible. Use assertions, throw exceptions, or log errors instead.

### File and Shell Commands
- When performing file or shell commands, always confirm your current location first.

### Builds and Source Control
- After all changes are made, ALWAYS build the project.
- If available, git add and commit *from project root* at least once per task (not per child subitem)

- Log warnings to `project-documents/user/tasks/950-tasks.maintenance.md`. Write in raw markdown format, with each warning as a list item, using a checkbox in place of standard bullet point. Note that this path is affected by `monorepo active` mode.

## Python Development Rules

### General
* Target Python 3.12+ for production (stability & ecosystem compatibility).
* Note: Python 3.14+ is acceptable for isolated services needing specific features (e.g., free-threading), but verify ML library support first.

### Typing & Validation
- Use built-in types: `list`, `dict`, `tuple`, not `List`, `Dict`, `Tuple`
- Use `|` for union types: `str | None` not `Optional[str]` or `Union[str, None]`
- Use `Self` (from `typing`) for return types of fluent methods/factories (3.11+).
- Type hint all function signatures and class attributes
- Use `@dataclass` for internal data transfer objects (DTOs) and configuration.
- Use `Pydantic` for all external boundaries (API inputs/outputs, file parsing, environment variables).
- Import Policy: Keep `from __future__ import annotations` for 3.12/3.13 projects to resolve forward references cleanly. (Remove only once strictly on 3.14+).

### Code Style & Structure
- Follow PEP 8 with 88-character line length
- Formatter: Use `ruff` for both linting and formatting (replaces Black/Isort/Flake8 due to speed).
- Use descriptive variable names; avoid single letters (except `x`, `i` in short loops/comprehensions).
- Prefer `f-strings` exclusively; avoid `.format()` or `%`.
- Use `pathlib` and its `Path` for all file/path operations, not `os.path.join` or similar
- One class per file for models/services; group related tiny utilities in `utils.py` or specific modules.

### Functions & Error Handling
- Small, single-purpose functions (max 20 lines preferred)
- Use early returns (`guard clauses`) to flatten nesting.
- Explicit exception handling: catch specific errors (`ValueError`), never bare `except:`.
- Use `try/except` blocks narrowly around the specific line that might fail.
- Use context managers (`with`) for resource management (files, locks, connections).

### Modern Python Patterns
- Use `match/case` for structural pattern matching (parsing dictionaries, complex conditions).
- Use `walrus operator (:=)` sparingly—only when it significantly reduces duplication.
- Comprehensions over `map`/`filter` when clear
- Use generator expressions `(x for x in y)` for large sequences to save memory.
- Use `itertools` for efficient looping and `functools.partial`/`reduce` where appropriate.
- Use `Enum` (specifically `StrEnum` in 3.11+) for constants/choices.

### Testing & Quality
- Write tests alongside implementation
- Use `pytest` exclusively.
- Use `conftest.py` for shared fixtures; keep individual test files clean.
- Parametrize tests (`@pytest.mark.parametrize`) to cover edge cases.
- Mock external I/O boundaries; test internal logic with real data.
- Static Analysis: Strict `mypy` or `pyright` (VS Code Pylance “Strict” mode). Zero errors policy.
- Docstrings for public APIs (Google or NumPy style)

### Dependencies & Imports
* Package Manager: Use `uv` for all projects (replaces Poetry/Pipenv for speed and standard compliance).
- Pin direct dependencies in `pyproject.toml`.
- Group imports: Standard Lib -> Third Party -> Local Application.
- Use absolute imports (`from myapp.services import ...`) over relative (`from ..services import ...`).
- No wildcard imports (`from module import *`).

### Async & Performance
- Use `async`/`await` for I/O-bound operations (DB, API calls).
- Use `asyncio.TaskGroup` (3.11+) for safer concurrent task management.
- Profile before optimizing (use `py-spy` or `cProfile`).
- Use `functools.cache` or `lru_cache` for expensive pure functions.

### Security & Best Practices
- Secrets: Never commit secrets. Use `.env` files (loaded via `pydantic-settings`).
- Input: Validate everything entering the system via Pydantic.
- SQL: Always use parameterized queries (never f-string SQL).
- Randomness: Use `secrets` module for security tokens, `random` only for simulations.

## React & Next.js Rules

### Components & Naming
- Use functional components
- Prefer **client components** (`"use client"`) for interactive UI - use server components only when specifically beneficial
- Name in PascalCase under `src/components/`
- Keep them small, typed with interfaces
- Stack: React + Tailwind 4 + Radix primitives (no ShadCN)

### React and Next.js Structure
- Use App Router in `app/` (works for both React and Next.js projects)
- **Authentication**: Don't implement auth from scratch - use established providers (Auth0, Clerk, etc.) or consult with PM first
- Use `.env` for secrets and configuration

### State Management
- **Local state**: Use React's built-in hooks (`useState`, `useReducer`, `useContext`)
- **Global state**: For complex global state needs, consider Zustand or Jotai
- **Server state**: Use TanStack Query (React Query) for API data fetching, caching, and synchronization

### Forms
- Use `react-hook-form` with Zod schema validation
- Integrate with Radix form primitives for accessible form controls
- Example pattern:
  ```tsx
  const schema = z.object({ email: z.string().email() });
  const form = useForm({ resolver: zodResolver(schema) });
  ```

### Icons
- Prefer `lucide-react`; name icons in PascalCase
- Custom icons in `src/components/icons`

### Toast Notifications
- Use `react-toastify` in client components
- `toast.success()`, `toast.error()`, etc.

### Tailwind Usage
- **Always use Tailwind 4** - configure in `globals.css` using CSS variables and `@theme`
- **Never use Tailwind 3** patterns or `tailwind.config.ts` / `tailwind.config.js` files
- If a tailwind config file exists, there should be a very good reason it's not in `globals.css`
- Use Tailwind utility classes (mobile-first, dark mode with `dark:` prefix)
- For animations, prefer Framer Motion

### Radix Primitives
- Use Radix primitives directly for accessible, unstyled components
- Style them with Tailwind and semantic color system
- Do not use ShadCN - use raw Radix primitives instead

### Code Style
- Use `eslint` unless directed otherwise
- Use `prettier` if working in languages it supports

### File & Folder Names
- Routes in kebab-case (e.g. `app/dashboard/page.tsx`)
- Sort imports (external → internal → sibling → styles)

### Testing
- Prefer `vitest` over jest

### Builds
- Use `pnpm` not `npm`
- After all changes are made, ALWAYS build the project with `pnpm build`. Allow warnings, fix errors
- If a `package.json` exists, ensure the AI-support script block from `snippets/npm-scripts.ai-support.json` is present before running `pnpm build`

## Code Review Rules

### Purpose

These rules provide **quick reference for lightweight, ad-hoc code reviews** during active development—spot-checking code, reviewing changes before commit, or quick quality checks.

**For comprehensive, systematic code reviews** (e.g., when user requests a formal code review, directory crawl reviews, or thorough quality audits), use the detailed methodology in:

**→ `project-documents/ai-project-guide/project-guides/guide.ai-project.090-code-review.md`**

### Quick Reference

#### File Naming

**Review documents:**
- Location: `user/reviews/`
- Pattern: `nnn-review.{name}.md`
- Range: nnn is 900-939

**Task files:**
- Location: `user/tasks/`
- Pattern: `nnn-tasks.code-review.{filename}.md`
- Use the **same nnn value** for all files in one review session to group them together

**Example:** Review session 905
- Review doc: `905-review.dashboard-refactor.md`
- Task files: `905-tasks.code-review.header.md`, `905-tasks.code-review.sidebar.md`

All files with `905` are part of the same review batch.

#### Review Checklist Categories

When reviewing code, systematically check:

1. **Bugs & Edge Cases** - Potential bugs, unhandled cases, race conditions, memory leaks
2. **Hard-coded Elements** - Magic numbers, strings, URLs that should be configurable
3. **Artificial Constraints** - Assumptions limiting future expansion, fixed limits
4. **Code Duplication** - Repeated patterns that should be abstracted
5. **Component Structure** - Single responsibility, logical hierarchy
6. **Design Patterns** - Best practices, performance optimization, error handling
7. **Type Safety** - Proper typing, documentation of complex logic
8. **Performance** - Unnecessary re-renders, inefficient data fetching, bundle size
9. **Security** - Input validation, auth/authz, XSS protection
10. **Testing** - Coverage of critical paths, edge cases, error states
11. **Accessibility** - ARIA labels, keyboard navigation, screen readers (UI-specific)
12. **Platform-Specific** - React/TypeScript/NextJS best practices, deprecated patterns

#### Quick Process

1. **Create review doc** in `user/reviews/nnn-review.{name}.md`
2. **Apply checklist** systematically to each file
3. **Create task files** in `user/tasks/nnn-tasks.code-review.{filename}.md` for issues found
4. **Prioritize** findings: P0 (critical) → P1 (quality) → P2 (best practices) → P3 (enhancements)

#### YAML Frontmatter

All code review files should include:
```yaml
---
layer: project
docType: review
---
```

### For Detailed Reviews

**Use the comprehensive guide** when you need:
- Full methodology and templates
- Directory crawl review process
- Detailed questionnaire with specific questions
- Step-by-step workflow
- Quality assessment criteria

**→ See: `guide.ai-project.090-code-review.md`**

## Testing Rules

### General Testing Philosophy

- **Write tests as you go** - Create unit tests while completing tasks, not at the end
- **Not strict TDD** - AI development doesn't require test-first, but tests should accompany implementation
- **Focus on value** - Test critical paths, edge cases, and business logic; don't test trivial code

### Python Testing

#### Test Framework
- Use `pytest` (industry standard)
- Place tests in `tests/` directory or `test_*.py` files
- Use fixtures for test data and setup

#### Test Organization
```
project/
├── src/
│   └── module.py
└── tests/
    └── test_module.py
```

#### Assertions
- Use pytest assertions: `assert result == expected`
- Use pytest-parametrize for multiple test cases
- Mock external dependencies at boundaries

### Best Practices

#### When to Write Tests
- ✅ **During implementation** - Write tests as you build features
- ✅ **After bug fixes** - Add tests to prevent regression
- ✅ **Before refactoring** - Tests verify behavior stays consistent
- ❌ **Not at the very end** - Waiting until feature is "done" leads to skipped tests

#### Test Quality
- **Arrange-Act-Assert** pattern: Set up → Execute → Verify
- **One concept per test**: Each test should verify one thing
- **Readable test names**: Test name should describe what's being tested
- **Avoid test interdependence**: Tests should run independently in any order

#### Mocking and Stubbing
- Mock external services (APIs, databases, file system)
- Don't mock internal business logic - test it directly
- Use dependency injection to make mocking easier

### Running Tests

#### Commands
```bash
pnpm test              # Run all tests
pnpm test:watch        # Watch mode
pnpm test:coverage     # Coverage report

pytest                 # Run all tests
pytest -v              # Verbose output
pytest --cov           # Coverage report
```

#### CI/CD Integration
- Tests should run automatically on commit/PR
- Build should fail if tests fail
- Don't skip failing tests - fix them or remove them
