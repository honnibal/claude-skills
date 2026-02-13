# claude-skills

Reusable [Claude Code](https://docs.anthropic.com/en/docs/claude-code) slash
command skills. To install a skill, copy it to `~/.claude/commands/` (rename
from `.md.txt` to `.md`).

The skills and parts of the project documentation were produced semi-automatically
using Claude Code.

## Why `.md.txt` instead of `.md`?

**Skill files are served with a `.md.txt` extension intentionally.** A Claude
Code skill is a markdown document that gets injected into the LLM's prompt
verbatim. Markdown can contain HTML comments (`<!-- ... -->`) that are invisible
when rendered by GitHub but are still present in the raw text --- and therefore
still processed by the model. A malicious skill could embed hidden instructions
that you would never see when previewing the file on GitHub.

In other words: **a skill file is remote code execution.** Claude Code operates
with broad access to your machine --- your filesystem, your shell, your git
credentials, your environment variables. A skill that says "helpful refactoring
assistant" in its visible text could contain a hidden HTML comment telling the
model to exfiltrate files, install packages, or modify code in ways you didn't
ask for.

By shipping files as `.md.txt`, GitHub will render them as plain text rather
than as formatted markdown. This means you see *everything* --- including any
HTML comments or hidden directives --- before you choose to install the skill.

**Before installing any skill from this repo (or anywhere else):**

1. Read the **raw** file contents. Do not trust a rendered markdown preview.
2. Look for HTML comments, invisible unicode characters, or instructions that
   don't match the stated purpose.
3. Understand that once installed, the skill's full text is handed to an LLM
   that can execute arbitrary commands on your behalf.

## Skills

All skills accept an optional argument to scope the work to specific files or
directories. If no argument is given, they work through the project or ask you
to choose a starting scope.

### `tighten-types.md.txt`

Systematically review Python source files and tighten type annotations.
Works through a prioritised checklist: missing class attribute annotations,
vague `Any` types replaced with concrete library types, structured dicts
promoted to Pydantic models or `TypedDict`, `@overload` signatures for
narrowable unions, redundant in-body annotations fixed at the root cause, and
style modernisation (`Optional[X]` → `X | None`, etc.).

```
/tighten-types src/mypackage/core.py
```

### `contract-docstrings.md.txt`

Write docstrings that document each function's **contract** --- what it requires
of callers, what it guarantees, and how it fails. Analyses four dimensions:
input invariants (preconditions beyond the type signature), errors raised on
violation (explicit checks vs. implicit crashes vs. silent wrong results),
errors from external state (filesystem, network, databases), and silenced errors
(broad `except` blocks, `.get()` defaults, `suppress()`). Produces a structured
`Contract:` section with `Preconditions:`, `Raises:`, and `Silences:`
subsections.

```
/contract-docstrings src/mypackage/pipeline.py
```

### `hypothesis-tests.md.txt`

Generate property-based tests using [Hypothesis](https://hypothesis.readthedocs.io/).
Reads production code, designs input strategies in `tests/strategies.py` that
model the valid search-space for each function (encoding constraints rather than
filtering), then writes minimal, behaviour-focused tests. Tests target core
contracts --- roundtrips, idempotence, invariant preservation, equivalence to
reference implementations --- rather than structural trivia or reimplementations
of the function under test.

```
/hypothesis-tests src/mypackage/scoring.py
```

### `mutation-testing.md.txt`

Assess test suite strength by introducing deliberate bugs (mutations) one at a
time and checking whether any test catches each one. Mutations are chosen from a
catalogue (delete side effects, negate conditions, change boundaries, hardcode
returns, remove guards, swap operators, modify defaults, swap argument order).
Each mutation is applied, tests are run, and the mutation is reverted. Produces
a summary table with mutation score, uncaught gaps, diagnostic quality ratings,
and recommended tests. Optionally implements missing tests for survived
mutations.

```
/mutation-testing src/mypackage/
```

### `pre-mortem.md.txt`

Imagine future bug post-mortems for the codebase. Reads production code and
identifies fragile areas --- implicit ordering dependencies, shared mutable
state, stringly-typed contracts, baked-in data assumptions, coincidental
correctness, non-atomic operations, invisible invariants, load-bearing defaults,
implicit resource lifecycles, and version-coupled assumptions. Writes realistic
incident reports (severity, cause, why it broke, how it was caught, hardening
suggestions) for bugs that haven't happened yet but plausibly could from
reasonable future edits. Outputs a `PRE-MORTEM.md` report.

```
/pre-mortem src/mypackage/
```

### `stub-package.md.txt`

Generate a condensed structural overview of a Python package or module ---
signatures, imports, class attributes, and docstrings only, with function bodies
replaced by `...`. Uses `stub_package.py` (included in this repo) to parse
source with `ast` and emit a compact representation. Supports `--no-docstrings`
for a more compact view and `--no-private` to show only public API.

```
/stub-package src/mypackage/
```

### `try-except.md.txt`

Audit `try/except` blocks for overly broad scope, by-catch risk, and catches of
built-in exceptions that should be conditional checks. Evaluates whether
try/except is the right mechanism (external state and validation-as-parsing vs.
local value checks), whether the try block is minimally scoped, whether the
except clause is too broad, and whether the handler masks failure. Tightens each
block so the `try` covers only the operation that can actually raise the
expected exception.

```
/try-except src/mypackage/pipeline.py
```

## License

MIT
