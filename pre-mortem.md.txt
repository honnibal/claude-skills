---
name: pre-mortem
description: Imagine future bug post-mortems for the codebase. Identifies fragile code, implicit assumptions, and likely failure modes by writing realistic incident reports for bugs that haven't happened yet.
argument-hint: "[file, directory, or description of what to focus on]"
disable-model-invocation: true
---

# Pre-Mortem: Future Bug Post-Mortems

You are now in pre-mortem mode. Your job is to read production code, identify
areas of fragility and implicit assumptions, and then write realistic
post-mortem reports for bugs that **haven't happened yet** — but plausibly
could, given the kind of changes a future developer might reasonably make.

This is not a bug hunt. The code may be perfectly correct today. You're looking
for places where the code is **fragile against future edits**: places where a
developer who doesn't have full context could make a seemingly reasonable change
that breaks something in a non-obvious way.

## Scope

$ARGUMENTS

- If the user names specific files or directories, scope your analysis to those.
- If no argument is given, look at the project's source layout and use
  `AskUserQuestion` to agree on a starting scope. Pick a module or package with
  meaningful logic — don't try to cover everything at once.
- Focus on production code. Config files, migrations, and boilerplate are out
  of scope unless they contain logic that other code depends on.

## Workflow

1. **Read deeply.** Read the files in scope carefully. Don't skim — you need to
   understand data flow, state management, implicit invariants, and the
   relationships between components. Read callers and callees, not just the file
   in isolation.

2. **Identify fragility.** Look for the patterns described in the catalogue
   below. For each one you find, ask: "What change would a reasonable developer
   make here that would break this?" If you can't imagine a plausible edit that
   causes a problem, move on — not everything is fragile.

3. **Write post-mortems.** For each fragility you identify, write a fictional
   post-mortem in the format described below. Write them as if the bug has
   already happened, in past tense, from the perspective of the team
   investigating the incident after the fact. Make the scenarios concrete and
   specific — name the functions, the variables, the values.

4. **Produce the report.** Write all post-mortems to a single file. Use
   `AskUserQuestion` to confirm the output path with the user, defaulting to
   `PRE-MORTEM.md` in the project root.

Use `TaskCreate` to track progress across files when there are more than a
handful.

## Fragility Catalogue

Look for these patterns when reading code. This is not exhaustive — use your
judgement to spot anything that feels like it would surprise a future editor.

### 1. Implicit ordering dependencies

Code that must run in a specific order but doesn't enforce it. Setup methods
that must be called before other methods. List processing that assumes elements
arrive sorted. Initialization sequences where step 3 silently depends on
step 1 having run.

*Future edit:* Someone reorders the calls, adds a new step between existing
ones, or calls a method before the object is fully initialized.

### 2. Semantic coupling through shared mutable state

Two components that communicate through a shared object (a dict, a list, a
module-level variable, an attribute on a passed-in object) rather than through
explicit arguments and return values. The reader of component A might not
realise that component B is reading or writing the same state.

*Future edit:* Someone modifies one component's use of the shared state without
realising the other depends on it. Or someone adds caching/memoization that
prevents the shared state from updating.

### 3. Stringly-typed contracts

Logic that depends on the exact value of strings — dict keys, status fields,
format strings, column names, error messages. These create invisible contracts
between producers and consumers that aren't enforced by any type checker or
test.

*Future edit:* Someone renames a status string, adds a new enum variant that
existing match/if-elif chains don't handle, or changes a dict key in one place
but not another.

### 4. Assumptions baked into data transformations

A function that processes data assuming a particular shape, range, or
distribution — e.g. assuming a list is non-empty, a value is positive, a string
matches a pattern, or a column contains no nulls. These assumptions might be
true today because of how the data is produced upstream, but nothing enforces
them.

*Future edit:* Someone changes the upstream data source, adds a new code path
that feeds different data into the function, or relaxes validation at the
system boundary.

### 5. Coincidental correctness

Code that produces the right result for the wrong reason. A condition that
happens to work because two variables are always equal today. A loop that
doesn't handle the empty case but is never called with an empty input. An
exception handler that catches too broadly but currently only encounters one
exception type.

*Future edit:* The coincidence stops holding. The input space widens, a new
exception type appears, or the previously-equal variables diverge.

### 6. Non-atomic compound operations

A sequence of operations that should be atomic but isn't — e.g. "check then
act" patterns, multi-step state updates with no rollback, or file operations
that assume no concurrent access. Includes anything where a failure or
interruption between steps leaves the system in an inconsistent state.

*Future edit:* Someone adds concurrency, moves the code to a context where
interruption is possible, or adds an early return between the steps.

### 7. Invisible invariants

Relationships between pieces of data that must be maintained but are enforced
only by convention — e.g. "this list and that dict always have the same keys",
"this counter equals len(that list)", "this field is non-None whenever that
flag is True". No assertion, type, or test enforces the invariant.

*Future edit:* Someone updates one side of the invariant but not the other,
especially when the two sides are in different functions or files.

### 8. Load-bearing defaults

Default values (function parameters, config settings, class attributes,
environment variables) that the code subtly depends on. The default doesn't
just provide convenience — the code would behave incorrectly or dangerously
with a different value, and nothing documents this constraint.

*Future edit:* Someone changes the default to something that seems equally
reasonable, or a caller starts passing an explicit value that nobody anticipated.

### 9. Implicit resource lifecycle

Resources (connections, file handles, locks, temporary files, background
threads) that are created but whose cleanup depends on a particular control
flow. No context manager or finalizer guarantees cleanup.

*Future edit:* Someone adds an early return, raises an exception, or refactors
the function into smaller pieces, and the cleanup code is no longer reached.

### 10. Version-coupled assumptions

Code that depends on the behaviour of a specific version of a dependency,
runtime, or protocol — e.g. relying on dict ordering (pre-3.7), assuming a
library function's undocumented side effect, or depending on the exact format
of an error message from a third-party library.

*Future edit:* The dependency is upgraded, the runtime version changes, or the
API's undocumented behaviour shifts.

## Post-Mortem Format

Write each post-mortem as a self-contained section. Use this structure:

```markdown
### <Short incident title>

**Severity:** Critical | High | Medium | Low
**Component:** <file(s) and function(s) involved>
**Fragility type:** <category from the catalogue>

#### What happened

<2-4 sentences describing the bug as if it already occurred. What did users or
the team observe? Be specific — name the symptom.>

#### The change that caused it

<Describe the edit a future developer made. Make it sound reasonable — this
should be a change that would pass code review. Include a plausible motivation
for the change (new feature, refactoring, performance improvement, dependency
upgrade, etc.)>

#### Why it broke

<Explain the hidden assumption or fragility that the change violated. Point to
the specific lines or patterns in the current code that create this fragility.
Reference actual function names, variable names, and file paths.>

#### How it was caught

<How would this bug surface? Would tests catch it? Would it fail silently?
Would it corrupt data? Would it only manifest under specific conditions or
at scale? Be honest — if no test would catch it, say so.>

#### Hardening suggestions

<1-3 concrete, actionable suggestions for making the code more resilient
against this kind of change. These might include: adding assertions or
validation, introducing types that enforce invariants, writing a specific test,
adding a comment that explains the non-obvious constraint, refactoring to make
the dependency explicit. Don't suggest vague improvements — be specific enough
that someone could implement your suggestion directly.>
```

## Calibration

Quality over quantity. Aim for 3-7 post-mortems per module, depending on its
complexity. Each one should describe a genuinely plausible scenario — a bug that
a competent developer could introduce during a reasonable edit.

**Avoid:**

- **Current bugs.** You're not looking for things that are broken today. If you
  find an actual bug, mention it to the user separately — don't write a
  fictional post-mortem about it.
- **Adversarial scenarios.** Don't imagine a developer deliberately sabotaging
  the code. The imagined changes should be things a well-intentioned developer
  would do.
- **Extremely unlikely changes.** "If someone rewrote the function in a
  completely different way, it might break" is not useful. The imagined change
  should be a small, local edit — a refactoring, a feature addition, a
  performance tweak.
- **Generic advice.** "This function has no tests" is an observation, not a
  post-mortem. Every post-mortem must describe a **specific** future change and
  a **specific** resulting failure.
- **Excessive severity.** Not everything is Critical. Use severity levels
  honestly. A bug that silently corrupts data is Critical. A bug that causes a
  clear error in an uncommon code path is Low.

**Aim for:**

- Scenarios where the **cause and effect are non-obvious** — the change is in
  one place and the breakage manifests somewhere else, or the breakage only
  appears under specific conditions.
- Fragilities that are **endemic to the design**, not surface-level issues. A
  missing null check is less interesting than an architectural assumption that
  permeates multiple files.
- Post-mortems that would make a reader say "oh, I wouldn't have thought of
  that" — not "well, obviously."

## Output File Structure

```markdown
# Pre-Mortem Report

**Scope:** <files/modules analysed>
**Date:** <today's date>

## Summary

<A short paragraph summarizing the overall fragility posture. How many
post-mortems? What are the dominant themes? Are there systemic patterns, or are
the fragilities mostly independent?>

## Post-Mortems

### 1. <title>
...

### 2. <title>
...

## Themes and Recommendations

<After all post-mortems, step back and identify cross-cutting themes. If
several post-mortems point to the same underlying architectural issue, call it
out here. Suggest structural changes that would address multiple fragilities at
once, not just point fixes.>
```

## Critical Rules

- **Read before writing.** Never write post-mortems for code you haven't read
  thoroughly. You must understand how the code actually works, not just what it
  looks like.
- **Be specific.** Every post-mortem must reference actual functions, variables,
  and file paths in the current codebase. No hand-waving.
- **Be plausible.** The imagined changes must be things a reasonable developer
  might do. If you can't articulate a plausible motivation for the change, the
  scenario isn't realistic enough.
- **Don't fix the code.** Your job is to write the report, not to refactor the
  codebase. The hardening suggestions should describe what to do, but you
  shouldn't implement them unless the user asks.
- **Separate actual bugs.** If you discover a real, current bug while reading,
  flag it to the user immediately via text output — don't bury it in a
  fictional post-mortem.
- **Ask when uncertain.** If you're unsure whether a pattern is truly fragile
  or just unfamiliar to you, use `AskUserQuestion` to discuss it with the user
  before including it in the report.
