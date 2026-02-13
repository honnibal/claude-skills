---
name: tighten-types
description: Analyze Python code and tighten type annotations. Finds missing attribute types, replaces loose dicts with Pydantic models, adds overloads, and removes redundant in-body annotations.
argument-hint: "[file, directory, or description of what to focus on]"
disable-model-invocation: true
---

# Tighten Python Type Annotations

You are now in type-tightening mode. Systematically review Python source files,
identify weak or missing type annotations, and propose precise fixes.

## Scope

$ARGUMENTS

- If the user names specific files or directories, scope your work to those.
- If no argument is given, work through the Python files in the current project.
- For large codebases, use `AskUserQuestion` to let the user choose which
  modules or packages to start with. Don't try to do everything at once.

## Workflow

1. **Survey** — Glob for `*.py` files in scope. Read each file (or batch of
   related files). Build a mental model of the module's types before proposing
   changes.
2. **Analyse** — For each file, apply the checklist below. Collect all findings
   before editing so you can see cross-cutting patterns (e.g. the same dict
   shape appearing in several places suggests a single shared model).
3. **Edit** — Make changes file by file. After editing a file, briefly
   summarize what changed and why. Group related changes into a single pass
   over each file rather than making many small edits.
4. **Verify** — After editing, run the project's type checker if one is
   configured (look for `mypy.ini`, `pyproject.toml [tool.mypy]`,
   `pyrightconfig.json`, or similar). Report any new errors introduced by your
   changes and fix them before moving on.

Use `TaskCreate` to track progress across files when there are more than a
handful.

## Checklist — What to Look For

Work through these categories in order for each file.

### 1. Missing class attribute annotations

Classes frequently have attributes assigned in `__init__` (or other methods)
with no type annotation on the class body or the assignment. Add annotations.

```python
# Before
class Pipeline:
    def __init__(self, nlp, name):
        self.nlp = nlp
        self.name = name
        self._cache = {}

# After
class Pipeline:
    nlp: Language
    name: str
    _cache: dict[str, Any]

    def __init__(self, nlp: Language, name: str) -> None:
        self.nlp = nlp
        self.name = name
        self._cache = {}
```

- Prefer importing concrete types from the library that defines them
  (`Language`, `Doc`, `Span`, etc.) over using generic stand-ins.
- Use `__slots__` contents as a hint for which attributes exist.

### 2. Import types from third-party libraries

Don't reinvent type aliases when the library already exports them. For example:

- spaCy: `Language`, `Doc`, `Span`, `Token`, `Vocab`, `Example`
- Pydantic: `BaseModel`, `Field`, `ConfigDict`
- FastAPI / Starlette: `Request`, `Response`, `JSONResponse`
- PyTorch: `Tensor`, `Module`, `nn.Parameter`
- numpy: `np.ndarray`, `np.floating`, `np.integer`

When you see `Any` or a vague annotation that could be replaced by one of
these, do so. Use `TYPE_CHECKING` imports to avoid runtime import cycles:

```python
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from spacy.language import Language
```

### 3. Structured dicts → Pydantic models (or TypedDicts)

Look for dictionaries that are constructed, passed around, or destructured with
an assumed set of keys. These are candidates for a Pydantic `BaseModel` or a
`TypedDict`.

**Signals that a dict has assumed structure:**

- Literal string keys used consistently across construction and access sites
- Multiple functions that accept or return the same dict shape
- Dict values are accessed with `.get("key")` or `["key"]` using literal keys
- A function builds a dict incrementally then returns it
- Docstrings or comments describe the dict's expected keys

**Choosing between Pydantic and TypedDict:**

- Prefer `BaseModel` when the dict crosses a system boundary (API
  request/response, config files, serialisation) or would benefit from
  validation.
- Prefer `TypedDict` when the value is an internal data structure that is never
  validated or serialised, and you want to avoid the overhead of model
  instantiation. TypedDict is also appropriate when you need to pass the
  structure to code that expects a plain dict.
- If unsure, ask the user via `AskUserQuestion`.

When creating a model, place it near the code that uses it — in the same module
or in a `_types.py` / `models.py` file if it's shared across modules. Don't
create a single giant types file.

### 4. `@overload` for narrowable unions

Look for functions whose return type is a union, where the specific return type
can be determined from the arguments. Add `@overload` signatures.

**Common patterns:**

- A boolean or `Literal` flag that selects the return type:

```python
# Before
def load(path: str, as_bytes: bool = False) -> str | bytes: ...

# After
@overload
def load(path: str, as_bytes: Literal[False] = ...) -> str: ...
@overload
def load(path: str, as_bytes: Literal[True]) -> bytes: ...
def load(path: str, as_bytes: bool = False) -> str | bytes: ...
```

- An input type that determines the output type:

```python
# Before
def process(text: str | Doc) -> str | Doc: ...

# After
@overload
def process(text: str) -> str: ...
@overload
def process(text: Doc) -> Doc: ...
def process(text: str | Doc) -> str | Doc: ...
```

- A string flag / enum that selects behaviour:

```python
# Before
def read_input(source: str, mode: str) -> str | Path: ...

# After
@overload
def read_input(source: str, mode: Literal["text"]) -> str: ...
@overload
def read_input(source: str, mode: Literal["path"]) -> Path: ...
def read_input(source: str, mode: str) -> str | Path: ...
```

Also look for arguments that are unions where one variant can be narrowed by
another argument (e.g. a format flag that tells you the first argument is a
string vs. a path). The same `@overload` technique applies.

Don't add overloads speculatively — only when the narrowing relationship is
clear from the implementation.

### 5. Redundant in-body type annotations

Type annotations inside function bodies (not on the initial declaration of a
local variable) often indicate that a type was too loose upstream. Investigate
and fix the root cause rather than papering over it.

**Signals:**

- `x: SomeType = some_function(...)` where `some_function` already returns
  `SomeType` — the annotation is redundant. Remove it, but first check whether
  the function's return type is actually annotated. If not, annotate the
  function instead.
- `x: SomeType = y.attr` where the annotation narrows a union — find out why
  `y.attr` has a union type and whether it can be tightened at the source.
- `assert isinstance(x, SomeType)` used to narrow — consider whether the
  parameter type or upstream return type could be tightened to avoid the need
  for the assertion.
- A local variable re-annotated after a conditional — consider whether the
  branches can be restructured so the type is naturally narrow.

**Do not remove annotations on initial declarations** — `items: list[str] = []`
is fine and conventional. The concern is with re-annotations and casts that
compensate for loose types elsewhere.

### 6. Other improvements (lower priority)

- Replace `Optional[X]` with `X | None` (Python 3.10+ style).
- Replace `typing.List`, `typing.Dict`, etc. with built-in generics.
- Add `-> None` return annotations to `__init__` and other methods that lack
  return types.
- Use `Self` (from `typing` in 3.11+ or `typing_extensions`) for methods that
  return `self`.
- Use `collections.abc` types (`Sequence`, `Mapping`, `Iterable`) instead of
  concrete types in function parameters where appropriate.
- Mark parameters that should not be modified as `Final`.

Only apply these if you're already touching the file. Don't do a sweep purely
for style modernisation unless the user asks for it.

## Presenting Changes

For each file you modify, write a short summary like:

> **`pipeline.py`** — Added attribute annotations to `Pipeline` class.
> Introduced `PipelineConfig` (Pydantic model) to replace the config dict
> passed between `load_config()` and `Pipeline.__init__()`. Added `@overload`
> to `Pipeline.process()` to narrow `str → str` and `Doc → Doc` variants.
> Removed 2 redundant in-body annotations that were compensating for the
> untyped config dict.

## Critical Rules

- **Read before editing.** Never propose type changes to code you haven't read.
  Understand the data flow before tightening a type.
- **Don't break runtime behaviour.** Type annotation changes should be
  invisible at runtime. Be careful with Pydantic model introductions — they
  change runtime behaviour (validation, attribute access). Make sure call sites
  are updated.
- **Preserve public API compatibility.** Don't change the signature of public
  functions in ways that would break callers. Overloads add precision without
  breaking anything. Changing a parameter from `dict` to `SomeModel` is a
  breaking change — flag it and ask the user.
- **Run the type checker.** If the project has mypy/pyright configured, run it
  after your changes. Don't introduce new type errors.
- **Ask when uncertain.** If you're unsure whether a dict should become a
  Pydantic model or TypedDict, or whether an overload is justified, use
  `AskUserQuestion`.
