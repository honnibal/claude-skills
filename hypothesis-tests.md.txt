---
name: hypothesis-tests
description: Generate property-based tests using Hypothesis. Builds input strategies in tests/strategies.py that model the valid search-space for each function, then writes minimal, behaviour-focused tests.
argument-hint: "[file, directory, or description of what to test]"
disable-model-invocation: true
---

# Property-Based Tests with Hypothesis

You are now in property-based test authoring mode. Your job is to read
production code, design Hypothesis strategies that model the valid input space
for each function, and write property-based tests that exercise the function's
core behavioural contracts.

## Scope

$ARGUMENTS

- If the user names specific files or directories, scope your work to those.
- If no argument is given, work through the Python source files in the current
  project, prioritising modules with complex logic and no existing tests.
- For large codebases, use `AskUserQuestion` to let the user choose which
  modules to start with. Don't try to do everything at once.

## Consulting the Hypothesis docs

Hypothesis is a large library with many features — strategies, settings,
stateful testing, database configuration, third-party extensions, `target()`,
`note()`, health checks, and more. **Do not rely on memory alone.** When you
need to use a feature you aren't fully confident about, look it up:

- Use `WebSearch` to find the relevant Hypothesis docs page (e.g.
  `"hypothesis python st.composite site:hypothesis.readthedocs.io"`).
- Use `WebFetch` to read the page and extract the exact API, parameters, and
  usage examples.

This applies especially to:
- Less common strategies (`st.from_type`, `st.from_regex`, `st.recursive`,
  `st.deferred`, `st.runner`, `st.data`)
- `@st.composite` — the `draw` callable interface, returning vs. drawing
- `register_type_strategy` and `st.from_type` interactions
- `settings` profiles and deadline / suppressed health check configuration
- Stateful testing (`RuleBasedStateMachine`) if the user's code has stateful
  APIs

Getting the API right matters more than speed. A strategy that misuses
`@st.composite` or silently generates invalid data is worse than taking an
extra minute to check the docs.

## Workflow

1. **Survey** — Glob for `*.py` files in scope. Read each file and build a
   mental model of its functions: what they accept, what they return, what
   invariants they maintain. Note any existing tests in `tests/`.
2. **Design strategies** — For each function worth testing, define a Hypothesis
   strategy that generates valid inputs. Write all strategies to
   `tests/strategies.py`. See the strategy design guidance below. Look up
   Hypothesis docs for any strategy combinators you're not certain about.
3. **Write tests** — Create test files (e.g. `tests/test_<module>.py`) that
   import strategies from `tests/strategies.py` and use `@given` to test
   behavioural properties. See the test design guidance below.
4. **Verify** — Run the tests with `pytest`. Fix any failures that reveal bugs
   in your strategies or tests (not bugs in the production code — report those
   to the user). Run `pytest --co -q` first to check collection before running
   the full suite.

Use `TaskCreate` to track progress across modules when there are more than a
handful of files.

## Strategy Design (`tests/strategies.py`)

The strategies module is the heart of this skill. A strategy is not just "some
data that has the right type" — it is a **model of the function's valid input
space**.

### Principles

1. **Start from the function, not the type.** Read the function body. Look for
   guards, assertions, early returns, conditional branches, and error paths.
   These reveal constraints that the type signature doesn't capture. A parameter
   typed `str` might actually need to be a non-empty string, a valid identifier,
   a path with a specific extension, or one of a fixed set of values.

2. **Ask: could we sample this value from the distribution we've defined?** For
   every strategy, mentally sample a few values and trace them through the
   function. Would they hit an unguarded code path that raises? Would they
   produce a meaningless result that no real caller would ever see? If so,
   tighten the strategy.

3. **Encode constraints, don't filter.** Prefer `st.integers(min_value=1)` over
   `st.integers().filter(lambda x: x > 0)`. Prefer `st.from_regex(r"[a-z_]\w*",
   fullmatch=True)` over `st.text().filter(str.isidentifier)`. Filtering
   discards generated values and slows the search; encoding constraints produces
   valid values directly.

4. **Mirror the production domain.** If the function processes a list of records,
   the strategy should produce records that look like real records — with
   realistic field relationships, not random noise. Use `st.builds()` and
   `@st.composite` to construct structured objects.

5. **Compose from small pieces.** Build a vocabulary of reusable atomic
   strategies (e.g. `valid_name`, `positive_int`, `nonempty_text`) and compose
   them into more complex structures. This makes the strategies readable and
   keeps `tests/strategies.py` a useful reference for what constitutes valid
   input throughout the codebase.

6. **`st.builds()` for simple constructors, `@st.composite` for everything
   else.** `st.builds()` is clean when each argument maps directly to an
   independent strategy:

   ```python
   task_strategy = st.builds(
       Task,
       title=st.text(min_size=1, max_size=200),
       priority=st.sampled_from(Priority),
       due_date=st.dates(min_value=date(2020, 1, 1)),
   )
   ```

   But as soon as there are **dependencies between fields**, conditional logic,
   or you need to build intermediate values, switch to `@st.composite`. It
   gives you an imperative `draw()` callable that makes complex generation
   readable:

   ```python
   @st.composite
   def valid_date_range(draw):
       start = draw(st.dates(min_value=date(2020, 1, 1)))
       end = draw(st.dates(min_value=start))
       return DateRange(start=start, end=end)

   @st.composite
   def valid_pipeline(draw):
       n_steps = draw(st.integers(min_value=1, max_value=10))
       steps = draw(st.lists(step_strategy, min_size=n_steps, max_size=n_steps))
       # Ensure step names are unique within a pipeline
       names = draw(
           st.lists(
               valid_name, min_size=n_steps, max_size=n_steps, unique=True
           )
       )
       for step, name in zip(steps, names):
           step.name = name
       return Pipeline(steps=steps)
   ```

   `@st.composite` is usually the right choice for domain objects. Don't
   contort `st.builds()` with `st.flatmap()` chains when `@st.composite`
   would be clearer. Check the Hypothesis docs if you're unsure about the
   `draw()` interface.

7. **Register strategies for your types.** If a type appears in many strategies
   (e.g. a core domain model), register a strategy for it so that
   `st.from_type(MyType)` works automatically:

   ```python
   from hypothesis import strategies as st

   st.register_type_strategy(Task, st.builds(
       Task,
       title=st.text(min_size=1, max_size=200),
       priority=st.sampled_from(Priority),
   ))
   ```

   This is especially useful when Hypothesis needs to infer strategies from
   type annotations (e.g. `st.builds(func)` with no explicit keyword
   strategies). Place registrations at the top of `tests/strategies.py` after
   the strategy definitions they reference. Consult the Hypothesis docs for
   `register_type_strategy` and `st.from_type` to understand how resolution
   works — especially with generic types and forward references.

8. **Don't over-constrain.** The point of property-based testing is to explore
   the input space. If you constrain the strategy so tightly that it generates
   only a handful of values, you've written a parameterised test, not a
   property-based test. Find the balance: tight enough that every value is valid,
   loose enough that Hypothesis can surprise you.

### Structure of `tests/strategies.py`

```python
"""Hypothesis strategies for <project name>.

Each strategy models the valid input space for a function or group of
functions. Strategies are named after the domain concept they represent,
not the function they're used with.
"""

from hypothesis import strategies as st

# -- Atomic strategies (reused across composed strategies) --

# -- Composed / domain strategies (@st.composite for dependent fields) --

# -- Type registrations (so st.from_type(T) resolves automatically) --
```

Group strategies by domain concept. Add a brief comment above each strategy
(or group) explaining what it models and why the constraints exist.

## Test Design

### What to test

Write tests that express **core behavioural contracts**: things that must be
true for all valid inputs. Good properties include:

- **Roundtrip / inverse:** `decode(encode(x)) == x`
- **Idempotence:** `f(f(x)) == f(x)`
- **Invariant preservation:** `len(merge(a, b)) <= len(a) + len(b)`
- **Monotonicity / ordering:** `x <= y implies f(x) <= f(y)`
- **Equivalence to a reference:** `fast_path(x) == naive_impl(x)`
- **Commutativity / associativity:** algebraic laws when applicable
- **No crash (smoke):** the function returns without raising for all valid
  inputs — but only as a last resort when no stronger property exists.
  If the function has no checkable contract, leave a `# TODO` and move on.

### What NOT to test

- **Structural trivia.** Don't assert that the output has a particular key or
  field unless that's the actual contract. A test that says
  `assert "name" in result` is testing the output schema, not the behaviour.
  If you need schema tests, use Pydantic or a JSON schema validator — not
  Hypothesis.
- **Reimplementing the function.** If your test computes the expected output by
  running the same logic as the production code, it proves nothing. Test
  properties, not point values.
- **Side effects of the current implementation.** If the function happens to
  sort its output today but the docstring doesn't promise that, don't test for
  it. Test the contract, not the accident.
- **Functions that are just glue.** If a function's only job is to call three
  other functions and return the result, testing it end-to-end duplicates
  coverage. Test the leaf functions instead. Leave a `# TODO: integration test`
  comment if warranted.

### Mocks

- **Minimise mocks.** If you can test a function by passing real (generated)
  data, do that. Mocks obscure what's actually being tested and make tests
  brittle.
- **Never mock the function under test.** If you're mocking so much of a
  function's environment that the test is mostly mocks, the function isn't
  unit-testable in its current form. Leave a `# TODO: needs refactoring for
  testability` comment and move on.
- **Acceptable mocks:** external I/O (network, filesystem, database) that would
  make the test slow or non-deterministic. Use `unittest.mock.patch` or
  dependency injection, not monkeypatch hacks.

### Structure of test files

```python
"""Property-based tests for <module>."""

from hypothesis import given, settings, assume
from hypothesis import strategies as st

from tests.strategies import <relevant strategies>
from mypackage.module import <functions under test>


class TestFunctionName:
    """Properties of function_name."""

    @given(...)
    def test_<property_name>(self, ...):
        ...
```

- One test class per function (or per closely related group).
- One test method per property.
- Name tests after the property they check: `test_roundtrip`,
  `test_idempotent`, `test_length_invariant` — not `test_function_works`.
- Use `@settings(max_examples=...)` only when the default (100) is too slow.
  Don't lower it just to make tests pass faster — that defeats the purpose.
- Use `assume()` sparingly and only for constraints that are hard to encode in
  the strategy. Every `assume()` is a missed opportunity to improve the
  strategy.

### Coverage discipline

Every test you write will show up in coverage reports. A low-value test that
merely calls a function and checks it doesn't crash creates the illusion of
coverage. The person reading the coverage report will assume the function's
behaviour is verified when it isn't.

**Rules:**

- If you can't identify a meaningful property, don't write the test. Leave a
  `# TODO: no obvious property — needs manual test or refactoring` comment in
  the test file so it shows up in searches but doesn't inflate coverage.
- If a function is trivial (a one-liner, a simple delegation), don't test it.
  Coverage of trivial code is noise.
- If a function's interesting behaviour is in an external dependency (e.g. it
  calls `requests.post` and returns the response), don't mock the dependency
  just to get line coverage. That tests your mock, not your code.
- Prefer fewer, stronger tests over many weak ones. One test with a genuine
  roundtrip property is worth more than five tests that each check a different
  output field.

## Presenting Changes

For each file you create or modify, write a short summary like:

> **`tests/strategies.py`** — Added `valid_task` and `priority_value`
> strategies. `valid_task` generates `Task` objects with non-empty titles
> (1-200 chars), valid priority enums, and dates after 2020-01-01. Constraints
> based on the `Task.__init__` validation in `models.py:34`.
>
> **`tests/test_task_manager.py`** — 3 property tests for `merge_tasks()`:
> roundtrip with split/merge, length invariant, idempotence of deduplication.
> Left TODO for `sync_tasks()` (requires network mock with complex
> state — better as integration test).

## Critical Rules

- **Read before testing.** Never write strategies for code you haven't read.
  You must understand the function's actual constraints, not just its type
  signature.
- **Valid inputs only.** Strategies must generate values the function is designed
  to handle. Testing with invalid inputs to trigger error paths is a different
  activity — don't conflate it with property-based testing of the happy path.
  If you want to test error handling, do that in separate, explicit tests (not
  with `@given`).
- **No spurious coverage.** If you can't state the property you're testing in
  one sentence, don't write the test. Better to leave a TODO than to pad the
  coverage report.
- **Strategies go in `tests/strategies.py`.** Keep them separate from tests so
  they can be reused and so a reader can understand the valid input space
  without wading through assertions.
- **Keep tests minimal.** Each test should assert one property. Don't bundle
  multiple checks into a single test method — it makes failures harder to
  diagnose and obscures which property was violated.
- **Ask when uncertain.** If you're unsure whether a function has a testable
  property, or whether a constraint belongs in the strategy, use
  `AskUserQuestion`.
