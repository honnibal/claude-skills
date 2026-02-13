# claude-skills

Reusable [Claude Code](https://docs.anthropic.com/en/docs/claude-code) slash
command skills. To install a skill, copy it to `~/.claude/commands/` (rename
from `.md.txt` to `.md`).

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

### `tighten-types.md.txt`

Prompts Claude to systematically review Python source files and tighten type
annotations. The skill works through a prioritised checklist:

1. **Missing class attribute annotations** --- adds type annotations to class
   bodies based on `__init__` assignments and `__slots__`.
2. **Third-party library types** --- replaces `Any` or vague annotations with
   concrete types exported by the relevant library (e.g. spaCy's `Language`,
   `Doc`, PyTorch's `Tensor`).
3. **Structured dicts to models** --- identifies dictionaries with assumed key
   structure and promotes them to Pydantic `BaseModel` or `TypedDict`, with
   guidance on choosing between the two.
4. **`@overload` for narrowable unions** --- adds overload signatures when a
   function's return type (or argument type) can be narrowed from another
   argument, such as a boolean flag, `Literal` string, or input type.
5. **Redundant in-body annotations** --- treats type annotations inside function
   bodies as a code smell indicating that types are too loose upstream, and
   fixes the root cause.
6. **Style modernisation** --- `Optional[X]` to `X | None`, `typing.List` to
   `list`, `Self`, `collections.abc` types, etc. Applied opportunistically when
   already editing a file.

Usage:

```
/tighten-types                          # whole project
/tighten-types src/mypackage/core.py    # specific file
/tighten-types src/mypackage/           # specific directory
```

## License

MIT
