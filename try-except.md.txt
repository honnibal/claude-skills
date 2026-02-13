---
name: try-except
description: Audit try/except blocks for overly broad scope, by-catch risk, and catches of built-in exceptions that should be conditional checks. Tightens each block so the try covers only the operation that can actually fail.
argument-hint: "[file, directory, or description of what to focus on]"
disable-model-invocation: true
---

# Interrogate Try/Except Usage

You are now in try/except audit mode. Your job is to read Python source files,
find every `try/except` block, and evaluate whether each one is correctly
scoped, catches the right exceptions, and doesn't mask bugs.

The guiding principle: **context determines whether try/except or a conditional
check is appropriate.** Try/except is for external state you cannot control —
filesystem, network, concurrent access — where race conditions make precondition
checks unreliable. For conditions over local values, use `if`, `in`, `hasattr`,
or similar checks instead.

Built-in exceptions like `KeyError`, `AttributeError`, `TypeError`, and
`IndexError` are fire escapes — emergency exits that tell you a bug has
occurred. Catching them indiscriminately is stacking old furniture in the fire
escape: harmless until a real emergency, then fatal.

## Scope

$ARGUMENTS

- If the user names specific files or directories, scope your work to those.
- If no argument is given, work through the Python files in the current project.
- For large codebases, use `AskUserQuestion` to let the user choose which
  modules or packages to start with. Don't try to do everything at once.

## Workflow

1. **Find all try/except blocks.** Grep for `try:` across the files in scope.
   Read each file that contains them.

2. **Classify each block.** For every try/except, work through the analysis
   checklist below. Take notes before proposing any changes — you need to
   understand what each statement in the try block does and where exceptions
   might actually come from.

3. **Propose changes.** For each block that has problems, explain the issue and
   show the fix. Group your changes by file. Apply the edits after presenting
   them.

4. **Verify.** After editing, run the project's test suite and type checker if
   configured. Your changes alter control flow — they can break things. Confirm
   they don't.

Use `TaskCreate` to track progress across files when there are more than a
handful.

## Analysis Checklist

Work through these checks for every `try/except` block, in order.

### 1. Is try/except the right mechanism?

Try/except is appropriate in two situations:

**A. External state you cannot check in advance.** The operation interacts with
something outside your process where a precondition check would be unreliable
(TOCTOU races) or impossible:

- Filesystem access (`open()`, `path.read_text()`, `os.stat()`)
- Network calls (`requests.get()`, `socket.connect()`, `urllib.urlopen()`)
- Database operations
- Subprocess execution

**B. Functions whose API does validation as parsing.** Many functions have no
cheap way to check whether the input is valid — the only way to find out is to
attempt the operation. The function's exception **is** its validation API, and
try/except is the intended usage:

- `json.loads(text)` — you can't check whether a string is valid JSON without
  parsing it. Catching `json.JSONDecodeError` is correct.
- `datetime.strptime(s, fmt)` — you can't check whether a string matches a
  date format without parsing it. Catching `ValueError` is correct.
- `int(s)` / `float(s)` on external input — regex validation is fragile and
  duplicates the parser's logic. Catching `ValueError` is correct.
- `pydantic.BaseModel.model_validate(data)` — the whole point is
  validate-by-parsing. Catching `ValidationError` is correct.
- `ipaddress.ip_address(s)`, `uuid.UUID(s)`, `re.compile(pattern)` — same
  principle: the constructor **is** the validator.

The key distinction: these functions raise **their own domain-specific
exceptions** (or `ValueError` as a documented part of their API). This is
fundamentally different from catching `KeyError` on a dict lookup, where the
exception is a generic signal that something is missing and could come from
anywhere in the call stack.

Even when try/except is the right mechanism, the try block must still be
**tightly scoped** — contain only the parsing/external call, not surrounding
logic. The by-catch risk is lower (a `json.JSONDecodeError` is unlikely to come
from unrelated code) but not zero, and a tight block makes the intent clear.

**Try/except is not appropriate** for conditions over local values where a
simple check suffices:

| Instead of catching...     | Use this check instead          |
|----------------------------|---------------------------------|
| `KeyError` on `d[key]`    | `if key in d:` or `d.get(key)`  |
| `AttributeError` on `x.y` | `if hasattr(x, "y"):` or check the type |
| `IndexError` on `lst[i]`  | `if i < len(lst):`              |
| `TypeError` on an operation | check the type or use an overload |

These built-in exceptions are **generic** — they can be raised by any code at
any depth. Catching them creates by-catch risk: the `except KeyError` intended
for a dict lookup might catch a `KeyError` raised five function calls deep in a
completely unrelated operation, silently masking a real bug.

The question to ask is: **does the function I'm calling document this exception
as part of its interface, or am I catching a side effect of something going
wrong?** If `json.loads` raises `JSONDecodeError`, that's its API telling you
the input was invalid. If `prepare_query()` raises `KeyError`, that's a bug.

### 2. Is the try block minimally scoped?

The try block should contain **only the operation that can raise the expected
exception** — nothing more. Every additional statement is a potential source of
by-catch.

**What to look for:**

- **Setup statements before the risky operation.** Variable assignments,
  transformations, or function calls that appear before the line that actually
  interacts with external state. Move them above the `try`.

- **Processing after the risky operation.** Code that uses the result of the
  risky operation but can't itself raise the caught exception type. Move it
  after the try/except (or into an `else` block).

- **Multiple independent risky operations.** If the try block contains two
  unrelated operations that might both raise (e.g. opening a file and then
  parsing it), consider splitting into two try/except blocks so each has its
  own error handling.

**Example — too wide:**

```python
# Bad: the entire block is wrapped. prepare_query() and process_rows()
# could raise KeyError from internal bugs, silently caught.
try:
    query = prepare_query(params)
    conn = db.connect(host)
    rows = conn.execute(query)
    result = process_rows(rows)
except (ConnectionError, KeyError):
    result = default_result()
```

```python
# Good: only the operation that involves external state is in the try.
query = prepare_query(params)
try:
    conn = db.connect(host)
    rows = conn.execute(query)
except ConnectionError:
    result = default_result()
else:
    result = process_rows(rows)
```

Note that `KeyError` was also removed from the except clause — it was there
to catch errors from `prepare_query()`, which is a local logic function that
should not have its errors silenced.

### 3. Is the except clause too broad?

Check what exception types are caught. Rank them from most to least dangerous:

1. **Bare `except:`** — catches everything including `SystemExit`,
   `KeyboardInterrupt`, and `GeneratorExit`. Almost never correct.
2. **`except Exception:`** — catches all standard exceptions. Appropriate only
   at top-level entry points (CLI main, web request handlers, task runners)
   where you genuinely need a catch-all to log and continue. Anywhere else,
   it silences bugs.
3. **`except (ExcA, ExcB, ExcC):`** with a long tuple — the more types you
   catch, the more by-catch risk. Each type should have a clear justification
   tied to a specific operation in the try block.
4. **`except SpecificError:`** — good, but verify it's the right specific
   error for the operation in the try block.

For each caught exception type, ask: "Which exact line in the try block can
raise this, and is there another line that might also raise it unintentionally?"

### 4. Does the handler mask failure?

Look at what happens in the except block:

- **`pass`** — the error is completely swallowed. Is the caller aware that this
  operation can silently fail?
- **Returns a default value** — the caller can't distinguish success from
  failure. Is this intentional and documented?
- **Logs and continues** — better than `pass`, but still silences the error
  for the caller. Check whether the log message includes enough context to
  debug.
- **Re-raises or raises a different exception** — usually fine, but check that
  the replacement exception preserves the original context (`raise X from e`).
- **Retries** — check that there's a limit and a backoff, and that the retry
  makes sense for the exception type.

### 5. Are there nested try/except blocks?

Nested try/except is not inherently wrong, but it often signals that the outer
block is too wide. Check whether the inner try/except could be moved out, or
whether the whole structure could be simplified.

## Common Patterns to Flag

These are patterns that are frequently wrong. Not all instances are bugs — some
are intentional and appropriate — but each one deserves scrutiny.

### `except KeyError` on a dict access

```python
# Suspect — by-catch risk from any KeyError in compute_value()
try:
    value = cache[compute_key(item)]
except KeyError:
    value = compute_value(item)
    cache[compute_key(item)] = value
```

Fix: use `key = compute_key(item)` then `if key in cache:` / `else:`, or
`cache.get(key)`, or `cache.setdefault(key, ...)`.

### `except AttributeError` on attribute access

```python
# Suspect — catches AttributeError from anywhere inside some_method()
try:
    result = obj.some_method()
except AttributeError:
    result = fallback()
```

Fix: use `if hasattr(obj, "some_method"):` or check the type. If the intent
is duck-typing, use a protocol or ABC.

### `except TypeError` as a type switch

```python
# Suspect — TypeError from bugs in process() is silenced
try:
    return process(items)
except TypeError:
    return process([items])
```

Fix: use `isinstance()` to check the type explicitly.

### `except ValueError` on a conversion

The answer depends on whether the function being called documents this
exception as part of its validation API:

```python
# Correct — int() is a parser. ValueError is how it reports invalid input.
# This is appropriate when text comes from outside the system.
try:
    n = int(text)
except ValueError:
    n = 0

# Correct — json.loads is a parser. JSONDecodeError (a ValueError subclass)
# is its validation API. There is no way to check validity without parsing.
try:
    data = json.loads(raw)
except json.JSONDecodeError:
    data = None

# Correct — datetime.strptime does validation as parsing.
try:
    dt = datetime.strptime(s, "%Y-%m-%d")
except ValueError:
    dt = None
```

```python
# Suspect — text comes from internal logic. Why is it ever non-numeric?
# The ValueError signals a bug upstream, not invalid external input.
try:
    n = int(record.count_field)
except ValueError:
    n = 0
```

The question is: **is the value being parsed something the system received from
outside (user input, file content, API response), or something the system
produced internally?** For external input, the parser's exception is the
expected validation mechanism. For internal values, a ValueError means something
is already wrong upstream and catching it hides the real problem.

### `except Exception` in the middle of logic

```python
# Almost always wrong — silences all bugs in the entire block
try:
    result = complex_operation(data)
except Exception:
    logger.error("operation failed")
    result = None
```

Fix: identify the specific exceptions that `complex_operation` can raise from
external state, and catch only those.

## Presenting Changes

For each file you modify, write a summary like:

> **`pipeline.py`** — Tightened 3 try/except blocks.
> `load_data()`: moved `validate_schema(data)` out of the try block (was
> exposing its KeyError/TypeError to the except clause). `connect()`: replaced
> `except Exception` with `except ConnectionError`. `get_config()`: replaced
> try/except KeyError with `dict.get()` — the try block contained a call to
> `parse_value()` whose KeyError would have been silently caught.

Call out any blocks where you suspect the broad catch is **hiding an existing
bug** — cases where narrowing the except clause might cause currently-silenced
exceptions to surface. These are the most valuable findings. The user needs to
know about them before you change the error handling.

## Critical Rules

- **Read before editing.** Never propose changes to try/except blocks you
  haven't read in full context. You need to understand what every statement in
  the block does and what it might raise.
- **Trace callees.** When a function call appears inside a try block, read that
  function to understand what exceptions it can raise. A `KeyError` from
  `prepare_query()` is a bug; a `ConnectionError` from `db.connect()` is
  expected. You can't tell the difference without reading both.
- **Don't remove error handling blindly.** Narrowing a try/except might cause
  exceptions to propagate that were previously caught. This is usually
  desirable (it stops masking bugs), but it changes behaviour. Flag these
  cases to the user.
- **Preserve intentional broad catches.** Top-level entry points, plugin
  loaders, and task runners sometimes need `except Exception` to prevent one
  failure from crashing the whole system. These are appropriate if they log the
  exception and are at the boundary of the system. Don't narrow them.
- **Use else blocks.** When moving code out of a try block, consider whether it
  belongs in the `else` clause (runs only if no exception was raised) rather
  than after the entire try/except/else structure.
- **Run tests after changes.** Changes to exception handling alter control flow
  and can break things. Always verify.
- **Ask when uncertain.** If you're unsure whether a broad catch is intentional
  or accidental, use `AskUserQuestion` to ask the user before changing it.
