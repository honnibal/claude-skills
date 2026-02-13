---
name: stub-package
description: Generate a condensed structural overview of a Python package or module — signatures, imports, class attributes, and docstrings only, with bodies replaced by ellipsis.
argument-hint: "[path to .py file or package directory, and optional flags]"
disable-model-invocation: true
---

# Stub Package: Structural Overview Generator

You are now in stub-generation mode. Your job is to run `stub_package.py` on the
target path and present the condensed structural overview to the user.

## Scope

$ARGUMENTS

- If the user provides a path to a `.py` file or directory, use that directly.
- If no argument is given, use `AskUserQuestion` to ask which file or package
  directory to stub. Suggest the current project's source root if one is obvious.

## Workflow

1. **Run the stub generator.** Execute the script:

   ```
   python ~/.claude/commands/stub_package.py <path> [flags]
   ```

   Available flags:
   - `--no-docstrings` — omit docstrings (much more compact)
   - `--no-private` — skip `_private` names (keeps `__dunder__` methods)
   - `--output FILE` — write to a file instead of stdout

   Choose flags based on the user's request. If they ask for a "compact" or
   "brief" overview, add `--no-docstrings`. If they want only the public API,
   add `--no-private`.

2. **Present the output.** Show the stubbed output directly. If it's very long
   (more than ~200 lines), write it to a file and tell the user where it is.

3. **Answer questions.** If the user asks follow-up questions about the
   structure, use the stub output as context. You can re-read specific source
   files for more detail when needed.

## What the output shows

The stub generator parses Python source with `ast` and emits:

- Module docstrings
- Import statements (verbatim)
- Module-level assignments (`__all__`, constants, type aliases)
- Class definitions with bases, decorators, class-level attributes, and method
  signatures (bodies replaced with `...`)
- Function/async function signatures with decorators (bodies replaced with `...`)
- Source location comments (`# file:line-line`) before each definition

For packages (directories), files are grouped under `# === path/file.py ===`
headers, with `__init__.py` listed first in each directory.

## Critical rules

- Always use the script at `~/.claude/commands/stub_package.py`. Do not
  attempt to replicate its logic manually.
- The script requires Python 3.9+ (uses `ast.unparse`).
- If the target path doesn't exist, report the error clearly.
- If the output is intended as context for another task (e.g. "stub this
  package so I can understand the API"), present it and then ask how to proceed.
