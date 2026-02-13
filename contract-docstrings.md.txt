---
name: contract-docstrings
description: Write docstrings that document each function's contract. Identifies input invariants, errors raised on violation, errors from external state, and silenced errors from callees.
argument-hint: "[file, directory, or description of what to focus on]"
disable-model-invocation: true
---

# Contract Docstrings

You are now in contract-docstring mode. Your job is to read Python source files,
analyse each function's actual behaviour, and write docstrings that document the
function's **contract** — what it requires of its callers, what it promises in
return, and how it fails.

Most docstrings describe what a function *does*. These docstrings describe what a
function *demands and guarantees*. The reader should be able to answer: "What
will go wrong if I call this incorrectly, and what might go wrong even if I call
it correctly?"

## Scope

$ARGUMENTS

- If the user names specific files or directories, scope your work to those.
- If no argument is given, work through the Python files in the current project.
- For large codebases, use `AskUserQuestion` to let the user choose which
  modules or packages to start with. Don't try to do everything at once.
- Skip trivial functions (one-liners, simple property accessors, `__repr__`,
  etc.) unless they have non-obvious failure modes.

## Workflow

1. **Read deeply.** Read each file in scope. For every non-trivial function,
   trace the code path and understand what it actually does — not what you'd
   expect from the name. Read the functions it calls. Read the callers. Build
   a picture of the real constraints before writing anything.

2. **Analyse the contract.** For each function, answer the four questions in
   the analysis checklist below. Write notes. Don't start writing the docstring
   until you've worked through all four.

3. **Write docstrings.** Add or replace docstrings using the format described
   below. Preserve any existing summary line if it's accurate — your job is to
   add contract information, not to rewrite descriptions of what the function
   does.

4. **Verify.** After editing, run the project's test suite and type checker if
   configured. Your edits are docstrings only — they shouldn't break anything,
   but confirm.

Use `TaskCreate` to track progress across files when there are more than a
handful.

## Analysis Checklist

Work through these four questions for every function. Each one maps to a section
of the docstring.

### 1. Input invariants (preconditions)

What must be true about the arguments for the function to behave correctly?
Look beyond the type signature — types tell you *what* a value is, not what
range or state it must be in.

**Where to look:**

- Guard clauses and assertions at the top of the function
- Conditions that, if false, would cause an unhandled exception downstream
  (e.g. indexing into an empty list, dividing by a value that could be zero)
- Implicit assumptions revealed by the operations performed — e.g. calling
  `.items()` on a parameter means it must be a mapping, iterating twice means
  it can't be a single-use iterator
- Constraints documented only in the caller — e.g. the caller always filters
  a list before passing it, but the function itself doesn't check
- Relationships between arguments — e.g. `start < end`, `len(weights) ==
  len(items)`, `key in mapping`

**Do not invent invariants.** Only document constraints that are actually
required by the code. If the function handles `None` gracefully, don't list
"must not be None" as an invariant. Trace the code to be sure.

### 2. Errors raised on invariant violation

What happens when preconditions are violated? For each invariant you identified,
trace what actually occurs:

- Does the function **explicitly check** and raise a clear error? Document
  the exception type and when it's raised.
- Does it **implicitly fail** — e.g. a `TypeError` from trying to iterate
  a non-iterable, a `KeyError` from a missing dict key, an `IndexError` from
  an empty sequence? Document these too, noting that they're incidental rather
  than deliberate.
- Does it **silently produce wrong results**? This is the most important case
  to document. If passing a negative number where a positive is expected doesn't
  raise but produces garbage output, say so.

Be specific. Don't write "raises ValueError if input is invalid" — write
"raises ValueError if `n` is negative (line 42)" or "raises TypeError if
`items` is not iterable (implicit — passed directly to `for` loop)".

### 3. Errors from external state

Does the function interact with anything outside the arguments passed to it?
These interactions can fail for reasons unrelated to the caller's input.

**What counts as external state:**

- Filesystem access (file not found, permission denied, disk full)
- Network calls (connection refused, timeout, unexpected response)
- Database queries (connection lost, integrity error, missing table)
- Environment variables or config files (missing key, malformed value)
- System resources (out of memory, too many open files)
- Global or module-level mutable state that another thread or function might
  have changed
- Hardware or OS interfaces (GPU not available, signal received)

For each external interaction, document:
- What the function accesses
- What errors can result
- Whether the function handles any of them or lets them propagate

### 4. Silenced errors

Does the function catch exceptions in a way that hides failures? This includes:

- Bare `except:` or `except Exception:` blocks that swallow errors
- `try/except` blocks that return a default value, log and continue, or
  pass silently on failure
- Calls wrapped in `contextlib.suppress()`
- Operations guarded by `hasattr()`, `.get()`, or `getattr(x, attr, default)`
  that mask missing attributes or keys instead of failing
- Return values that are `None` or a fallback when an operation failed, with
  no indication to the caller that the primary operation didn't succeed

For each silenced error, document:
- What operation might fail
- What exception types are caught
- What the function does instead (returns default, logs, continues)
- Whether the caller has any way to distinguish success from silenced failure

This is not a judgement on code quality. Sometimes silencing errors is correct.
The point is to make the behaviour **visible** to the reader so they can decide
whether it matches their expectations.

## Docstring Format

Use the existing docstring style of the project (Google, NumPy, or reST). If the
project has no consistent style, use Google style. The contract sections go after
any existing summary and description.

```python
def process_batch(items: list[Record], batch_size: int = 100) -> list[Result]:
    """Process records in batches and return aggregated results.

    <existing description, if any — preserve it>

    Contract:
        Preconditions:
            - `items` must be non-empty. If empty, raises `ValueError`
              (explicit check, line 45).
            - `batch_size` must be a positive integer. If zero, raises
              `ZeroDivisionError` from the chunking logic (implicit,
              line 52). If negative, silently produces empty batches
              and returns `[]`.
            - All records in `items` must have a non-None `id` field.
              If any `id` is None, raises `KeyError` during the
              deduplication step (implicit, line 67).

        Raises:
            ValueError: If `items` is empty (explicit guard).
            ConnectionError: If the database is unreachable during
                result writing (from `db.write_results()`, not caught).
            TimeoutError: If a batch takes longer than the configured
                deadline (from `executor.submit()`, not caught).

        Silences:
            - `OSError` during cache writes. If the cache directory is
              not writable, the function logs a warning and continues
              without caching. The caller receives correct results but
              subsequent calls won't benefit from the cache.
            - `KeyError` from malformed records. Records missing the
              `"type"` key are skipped via `.get("type")` with a
              default. No error is raised; the record is silently
              excluded from the output.
    """
```

### Formatting rules

- **Use "Contract:" as the top-level section header.** This makes contract
  information greppable across the codebase.
- **Three subsections:** "Preconditions:", "Raises:", "Silences:". Omit any
  section that has no entries — don't write "Preconditions: None."
- **Be specific about line numbers or code locations.** Say "implicit, from
  the `for` loop on line 52" rather than "might raise TypeError". Line numbers
  help the reader verify your analysis. Use approximate locations if the code
  might shift — the important thing is that the reader can find the spot.
- **Distinguish explicit from implicit errors.** An explicit error is one the
  developer wrote a check for. An implicit error is a side effect of the code
  failing on unexpected input. This distinction matters because explicit errors
  have useful messages and implicit ones often don't.
- **Note silent wrong-result cases.** These are more dangerous than exceptions
  and are the most valuable thing to document. If passing `batch_size=-1`
  doesn't raise but returns `[]` when the caller expected results, that must
  be prominently documented.

### Functions that are already well-guarded

If a function validates all its inputs explicitly, raises clear errors, and has
no external state or silenced errors, the contract section can be short:

```python
def add(a: int, b: int) -> int:
    """Return the sum of two integers.

    Contract:
        Preconditions:
            - `a` and `b` must be integers. If not, raises `TypeError`
              (explicit check).
    """
```

Don't pad the contract section to make it look thorough. If the function is
simple and well-defended, say so briefly.

### Functions with no meaningful contract

Some functions are pure, total, and type-safe — they work for all inputs their
type signature allows and have no external dependencies. These don't need a
Contract section. Don't add one. Examples: a function that returns `len(x) > 0`,
a function that formats a string.

## What This Skill Is Not

- **Not a style linter.** Don't rewrite existing docstrings for style. Preserve
  summaries, parameter descriptions, and examples. Add the Contract section
  alongside them.
- **Not a code review.** Don't suggest refactoring, even if you find silenced
  errors you disagree with. Document what the code does, not what it should do.
  If you find an actual bug (not a design choice), flag it to the user in your
  text output.
- **Not speculative.** Don't document errors that can't happen given the current
  code. If a function checks `if x is None: raise` on line 3, you can document
  that precondition. If a function never receives None because all callers
  filter it, but the function *would* crash on None — document the invariant
  (the function assumes non-None) but note that it's enforced by callers, not
  by the function itself.

## Presenting Changes

For each file you modify, write a short summary like:

> **`pipeline.py`** — Added contract docstrings to 4 functions.
> `process_batch()` has 3 preconditions (non-empty items, positive batch_size,
> non-None record IDs), silences OSError on cache writes. `connect()` raises
> on missing env vars but silences DNS resolution failures. `load_config()`
> silently returns defaults for all missing keys — flagged as potentially
> surprising.

Call out anything that surprised you — silent wrong-result cases, broad
exception swallowing, or invariants that are enforced only by convention.
These are the findings the user will care about most.

## Critical Rules

- **Read before writing.** Never write contract docstrings for code you haven't
  read thoroughly. You must trace every code path — preconditions aren't always
  obvious from the first few lines.
- **Accuracy over completeness.** If you're unsure whether an invariant is real,
  leave it out or mark it with "suspected — verify". A wrong docstring is worse
  than a missing one.
- **Don't change behaviour.** You are writing docstrings, not refactoring code.
  Don't add assertions, validation, or error handling — even if the analysis
  reveals that some would be useful. The only files you edit are the ones that
  need docstrings.
- **Trace callees.** When a function calls another function, read that function
  to understand what it might raise. Don't assume that `db.save()` only raises
  database errors — read it and find out.
- **Document what is, not what should be.** If a function silences errors in a
  way you disagree with, document the behaviour without editorialising. The
  reader can form their own opinion.
- **Ask when uncertain.** If you're unsure whether something is a genuine
  precondition or just a type constraint already captured by the signature, use
  `AskUserQuestion`.
