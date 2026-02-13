"""Generate condensed Python stubs showing only signatures and structure."""

import argparse
import ast
import sys
from pathlib import Path


def format_arguments(node: ast.arguments) -> str:
    """Reconstruct a full argument signature from an ast.arguments node."""
    parts = []

    # Positional-only and regular args
    num_posonly = len(node.posonlyargs)
    all_pos = node.posonlyargs + node.args
    # Defaults align to the end of all_pos
    num_defaults = len(node.defaults)
    num_pos = len(all_pos)

    for i, arg in enumerate(all_pos):
        s = arg.arg
        if arg.annotation:
            s += ": " + ast.unparse(arg.annotation)
        # Check if this arg has a default
        default_idx = i - (num_pos - num_defaults)
        if default_idx >= 0:
            s += " = " + ast.unparse(node.defaults[default_idx])
        parts.append(s)
        if i == num_posonly - 1 and num_posonly > 0:
            parts.append("/")

    if node.vararg:
        s = "*" + node.vararg.arg
        if node.vararg.annotation:
            s += ": " + ast.unparse(node.vararg.annotation)
        parts.append(s)
    elif node.kwonlyargs:
        parts.append("*")

    for i, arg in enumerate(node.kwonlyargs):
        s = arg.arg
        if arg.annotation:
            s += ": " + ast.unparse(arg.annotation)
        default = node.kw_defaults[i]
        if default is not None:
            s += " = " + ast.unparse(default)
        parts.append(s)

    if node.kwarg:
        s = "**" + node.kwarg.arg
        if node.kwarg.annotation:
            s += ": " + ast.unparse(node.kwarg.annotation)
        parts.append(s)

    return ", ".join(parts)


def get_docstring(body: list) -> str | None:
    """Extract docstring from a function/class body."""
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        return body[0].value.value
    return None


def _format_docstring(doc: str, indent: str) -> str:
    """Format a docstring with proper indentation."""
    lines = doc.split("\n")
    if len(lines) == 1:
        return f'{indent}"""{doc}"""\n'
    # Multi-line: indent all lines
    result = f'{indent}"""{lines[0]}\n'
    for line in lines[1:]:
        if line.strip():
            result += f"{indent}{line}\n"
        else:
            result += "\n"
    # Ensure closing quotes are on their own line if not already
    if not result.rstrip().endswith('"""'):
        result += f'{indent}"""\n'
    return result


def stub_function(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    source_file: str,
    indent: str,
    *,
    include_docstrings: bool = True,
) -> str:
    """Format a FunctionDef/AsyncFunctionDef as a stub."""
    lines = []

    # Location comment
    lines.append(f"{indent}# {source_file}:{node.lineno}-{node.end_lineno}")

    # Decorators
    for dec in node.decorator_list:
        lines.append(f"{indent}@{ast.unparse(dec)}")

    # Signature
    async_prefix = "async " if isinstance(node, ast.AsyncFunctionDef) else ""
    sig = format_arguments(node.args)
    ret = ""
    if node.returns:
        ret = " -> " + ast.unparse(node.returns)
    lines.append(f"{indent}{async_prefix}def {node.name}({sig}){ret}:")

    # Docstring
    body_indent = indent + "    "
    doc = get_docstring(node.body) if include_docstrings else None
    if doc:
        lines.append(_format_docstring(doc, body_indent).rstrip())

    lines.append(f"{body_indent}...")
    return "\n".join(lines)


def stub_class(
    node: ast.ClassDef,
    source: str,
    source_file: str,
    indent: str,
    *,
    include_docstrings: bool = True,
    include_private: bool = True,
) -> str:
    """Format a ClassDef as a stub."""
    lines = []

    # Location comment
    lines.append(f"{indent}# {source_file}:{node.lineno}-{node.end_lineno}")

    # Decorators
    for dec in node.decorator_list:
        lines.append(f"{indent}@{ast.unparse(dec)}")

    # Class line
    bases = []
    for base in node.bases:
        bases.append(ast.unparse(base))
    for kw in node.keywords:
        if kw.arg:
            bases.append(f"{kw.arg}={ast.unparse(kw.value)}")
        else:
            bases.append(f"**{ast.unparse(kw.value)}")
    base_str = f"({', '.join(bases)})" if bases else ""
    lines.append(f"{indent}class {node.name}{base_str}:")

    body_indent = indent + "    "
    has_content = False

    # Docstring
    doc = get_docstring(node.body) if include_docstrings else None
    if doc:
        lines.append(_format_docstring(doc, body_indent).rstrip())
        has_content = True

    for child in node.body:
        # Skip docstring node (already handled)
        if (
            isinstance(child, ast.Expr)
            and isinstance(child.value, ast.Constant)
            and isinstance(child.value.value, str)
            and child is node.body[0]
        ):
            continue

        if isinstance(child, ast.AnnAssign):
            segment = ast.get_source_segment(source, child)
            if segment:
                lines.append(f"{body_indent}{segment}")
            else:
                lines.append(f"{body_indent}{ast.unparse(child)}")
            has_content = True

        elif isinstance(child, ast.Assign):
            segment = ast.get_source_segment(source, child)
            if segment:
                lines.append(f"{body_indent}{segment}")
            else:
                lines.append(f"{body_indent}{ast.unparse(child)}")
            has_content = True

        elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not include_private and _is_private(child.name):
                continue
            lines.append("")
            lines.append(
                stub_function(
                    child,
                    source_file,
                    body_indent,
                    include_docstrings=include_docstrings,
                )
            )
            has_content = True

        elif isinstance(child, ast.ClassDef):
            if not include_private and _is_private(child.name):
                continue
            lines.append("")
            lines.append(
                stub_class(
                    child,
                    source,
                    source_file,
                    body_indent,
                    include_docstrings=include_docstrings,
                    include_private=include_private,
                )
            )
            has_content = True

    if not has_content:
        lines.append(f"{body_indent}...")

    return "\n".join(lines)


def _is_private(name: str) -> bool:
    """Check if a name is private (starts with _ but isn't a dunder)."""
    return name.startswith("_") and not (name.startswith("__") and name.endswith("__"))


def stub_module(source: str, source_file: str, *, include_docstrings: bool = True, include_private: bool = True) -> str:
    """Parse and stub a single module."""
    tree = ast.parse(source)
    parts = []

    for node in ast.iter_child_nodes(tree):
        # Module docstring
        if (
            isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
            and node is next(ast.iter_child_nodes(tree))
        ):
            if include_docstrings:
                segment = ast.get_source_segment(source, node)
                if segment:
                    parts.append(segment)
                else:
                    parts.append(f'"""{node.value.value}"""')
            continue

        # Imports
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            segment = ast.get_source_segment(source, node)
            if segment:
                parts.append(segment)
            else:
                parts.append(ast.unparse(node))
            continue

        # Module-level assignments
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            segment = ast.get_source_segment(source, node)
            if segment:
                parts.append(segment)
            else:
                parts.append(ast.unparse(node))
            continue

        # Functions
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not include_private and _is_private(node.name):
                continue
            parts.append(
                stub_function(
                    node,
                    source_file,
                    "",
                    include_docstrings=include_docstrings,
                )
            )
            continue

        # Classes
        if isinstance(node, ast.ClassDef):
            if not include_private and _is_private(node.name):
                continue
            parts.append(
                stub_class(
                    node,
                    source,
                    source_file,
                    "",
                    include_docstrings=include_docstrings,
                    include_private=include_private,
                )
            )
            continue

    return "\n\n".join(parts)


def _sort_key(path: Path, root: Path) -> tuple:
    """Sort key: __init__.py first within each directory, then alphabetical."""
    rel = path.relative_to(root)
    parts = list(rel.parts)
    # Replace filename for sorting: __init__.py sorts first
    if parts[-1] == "__init__.py":
        parts[-1] = "\x00"  # sorts before any real filename
    return tuple(parts)


def stub_package(path: Path, *, include_docstrings: bool = True, include_private: bool = True) -> str:
    """Stub a file or package directory."""
    if path.is_file():
        source = path.read_text()
        return stub_module(
            source,
            path.name,
            include_docstrings=include_docstrings,
            include_private=include_private,
        )

    # Directory: find all .py files
    py_files = sorted(path.rglob("*.py"), key=lambda p: _sort_key(p, path))
    sections = []

    for py_file in py_files:
        rel = py_file.relative_to(path.parent)
        source = py_file.read_text()
        if not source.strip():
            continue
        header = f"# === {rel} ==="
        body = stub_module(
            source,
            str(rel),
            include_docstrings=include_docstrings,
            include_private=include_private,
        )
        if body.strip():
            sections.append(f"{header}\n\n{body}")

    return "\n\n".join(sections)


def main():
    parser = argparse.ArgumentParser(
        description="Generate condensed Python stubs showing only signatures and structure."
    )
    parser.add_argument("path", type=Path, help="Path to a .py file or package directory")
    parser.add_argument("--output", "-o", type=Path, help="Write output to file instead of stdout")
    parser.add_argument("--no-docstrings", action="store_true", help="Omit docstrings from stubs")
    parser.add_argument("--no-private", action="store_true", help="Skip _private functions/classes (keep __dunder__)")

    args = parser.parse_args()

    if not args.path.exists():
        print(f"Error: {args.path} does not exist", file=sys.stderr)
        sys.exit(1)

    result = stub_package(
        args.path,
        include_docstrings=not args.no_docstrings,
        include_private=not args.no_private,
    )

    if args.output:
        args.output.write_text(result + "\n")
        print(f"Wrote stubs to {args.output}", file=sys.stderr)
    else:
        print(result)


if __name__ == "__main__":
    main()
