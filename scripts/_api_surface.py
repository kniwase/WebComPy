"""Shared public API AST resolution and docstring extraction utilities."""

from __future__ import annotations

import ast
import inspect
import re
import textwrap
import tokenize
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, cast

ROOT = Path(__file__).resolve().parent.parent
PACKAGE_ROOTS = [
    ROOT / "packages/webcompy/src/webcompy",
    ROOT / "packages/webcompy-server/src/webcompy_server",
    ROOT / "packages/webcompy-cli/src/webcompy_cli",
    ROOT / "packages/webcompy-testing/src/webcompy_testing",
]
IMPORTANT_INTERNALS = [
    "webcompy.components._generator:ComponentStore",
    "webcompy.elements.types._element:ElementBase",
    "webcompy.signal._graph:SignalNode",
]

Gap = tuple[Path, int, str]

_GOOGLE_SECTION_RE = re.compile(r"^(Args|Attributes|Returns|Yields|Raises|Note|Notes|Example|Examples):$")
_RST_ROLE_RE = re.compile(r":(?:class|func|meth|attr|exc|mod|data|const|obj):`~?([^`]+)`")
_RST_CODE_RE = re.compile(r"``([^`]+)``")


@dataclass(frozen=True)
class DocstringSections:
    """Parsed summary and structured sections from a Google-style docstring."""

    summary: str
    description: str
    sections: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class ResolvedMember:
    """A resolved public method, property, or nested class of a public class."""

    qualname: str
    name: str
    kind: Literal["method", "async_method", "property", "class"]
    signature: str
    docstring: str
    parsed_docstring: DocstringSections
    nested_members: tuple[ResolvedMember, ...] = ()


@dataclass(frozen=True)
class ResolvedSymbol:
    """Canonical public symbol resolved from package re-exports or allowlists."""

    key: str
    name: str
    def_module: str
    def_path: Path
    lineno: int
    kind: Literal["function", "async_function", "class", "constant", "type_alias"]
    signature: str
    docstring: str
    parsed_docstring: DocstringSections
    exports: tuple[tuple[str, str], ...]
    members: tuple[ResolvedMember, ...] = ()
    is_internal: bool = False


def docstring_expr(node: ast.AST) -> ast.Expr | None:
    """Return the leading docstring AST node for a module, class, or function.

    Args:
        node: AST node whose body is inspected.

    Returns:
        The leading constant string expression node when non-empty, else ``None``.

    """
    body = getattr(node, "body", None)
    if not body:
        return None
    first = body[0]
    if (
        isinstance(first, ast.Expr)
        and isinstance(first.value, ast.Constant)
        and isinstance(first.value.value, str)
        and first.value.value.strip()
    ):
        return first
    return None


def trailing_docstring_expr(body: list[ast.stmt], node: ast.AST) -> ast.Expr | None:
    """Return the PEP 224 attribute docstring immediately following an assignment.

    Args:
        body: Statement list containing the assignment node.
        node: Assignment AST node to inspect.

    Returns:
        The immediately following string literal expression node, or ``None``.

    """
    position = body.index(cast("ast.stmt", node))
    following = body[position + 1] if position + 1 < len(body) else None
    if (
        following is not None
        and isinstance(following, ast.Expr)
        and isinstance(following.value, ast.Constant)
        and isinstance(following.value.value, str)
        and following.value.value.strip()
    ):
        return following
    return None


def decorator_leaf_name(node: ast.AST) -> str | None:
    """Extract the terminal identifier name of a decorator expression.

    Args:
        node: Decorator AST expression node.

    Returns:
        The decorator leaf name when resolvable, else ``None``.

    """
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Call):
        return decorator_leaf_name(node.func)
    return None


def is_exempt_method(node: ast.AST) -> bool:
    """Return whether a function carries a docstring-exempt decorator.

    Args:
        node: Function or async function AST node.

    Returns:
        ``True`` for ``overload``, ``setter``, and ``deleter`` decorators.

    """
    for decorator in getattr(node, "decorator_list", []):
        leaf = decorator_leaf_name(decorator)
        if leaf in ("overload", "setter", "deleter"):
            return True
    return False


def assigned_name(node: ast.AST) -> str:
    """Return the assigned identifier name from an ``Assign`` or ``AnnAssign`` node.

    Args:
        node: Simple assignment or annotated assignment node.

    Returns:
        The target variable name.

    """
    if isinstance(node, ast.Assign):
        return cast("ast.Name", node.targets[0]).id
    return cast("ast.Name", cast("ast.AnnAssign", node).target).id


def assignment_target(stmt: ast.stmt, name: str) -> str | None:
    """Return ``name`` if ``stmt`` assigns to that simple identifier.

    Args:
        stmt: Top-level statement node.
        name: Expected identifier name.

    Returns:
        ``name`` when matched, else ``None``.

    """
    if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
        return stmt.targets[0].id if stmt.targets[0].id == name else None
    if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
        return stmt.target.id if stmt.target.id == name else None
    return None


def is_type_checking_test(node: ast.AST) -> bool:
    """Return whether an ``If`` condition tests ``TYPE_CHECKING``.

    Args:
        node: Conditional test expression AST node.

    Returns:
        ``True`` when checking ``TYPE_CHECKING`` directly or via attribute access.

    """
    if isinstance(node, ast.Name):
        return node.id == "TYPE_CHECKING"
    if isinstance(node, ast.Attribute):
        return node.attr == "TYPE_CHECKING"
    return False


def top_level_statements(tree: ast.Module) -> list[ast.stmt]:
    """Return module top-level statements plus ``TYPE_CHECKING`` import guards.

    Args:
        tree: Parsed module AST.

    Returns:
        Ordered list of module statements including ``TYPE_CHECKING`` branches.

    """
    statements = list(tree.body)
    for stmt in tree.body:
        if isinstance(stmt, ast.If) and is_type_checking_test(stmt.test):
            statements.extend(stmt.body)
    return statements


def import_target(importer: str, importer_is_package: bool, node: ast.ImportFrom) -> str | None:
    """Resolve an ``ImportFrom`` statement's absolute dotted module path.

    Args:
        importer: Dotted module path performing the import.
        importer_is_package: Whether ``importer`` is an ``__init__.py`` package.
        node: ``ImportFrom`` AST node.

    Returns:
        Resolved dotted module path, or ``None`` for invalid relative imports.

    """
    if node.module is None:
        return None
    if node.level == 0:
        return node.module
    package = importer if importer_is_package else ".".join(importer.split(".")[:-1])
    parts = package.split(".")
    cut = node.level - 1
    if cut > len(parts):
        return None
    base = parts[: len(parts) - cut] if cut else parts
    return ".".join([*base, node.module])


def display_path(path: Path, roots: list[Path]) -> str:
    """Format a source file path relative to the workspace or package root.

    Args:
        path: File path to display.
        roots: Fallback package root paths.

    Returns:
        Human-readable relative path string.

    """
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        pass
    for root in roots:
        try:
            return str(path.relative_to(root))
        except ValueError:
            pass
    return str(path)


def clean_rst_markup(text: str) -> str:
    """Convert reStructuredText inline code and role syntax into CommonMark.

    Args:
        text: Raw cleaned docstring text.

    Returns:
        Text with ``:role:`...` `` and `` ``...`` `` normalized for Markdown.

    """
    cleaned = _RST_ROLE_RE.sub(lambda m: f"`{m.group(1)}`", text)
    return _RST_CODE_RE.sub(lambda m: f"`{m.group(1)}`", cleaned)


def parse_google_docstring(raw: str) -> DocstringSections:
    """Parse a Google-style docstring into summary, description, and sections.

    Args:
        raw: Cleaned docstring text.

    Returns:
        Structured ``DocstringSections`` instance.

    """
    if not raw.strip():
        return DocstringSections(summary="", description="", sections=())

    lines = raw.splitlines()
    blocks: list[tuple[str | None, list[str]]] = []
    current_header: str | None = None
    current_lines: list[str] = []

    for line in lines:
        match = _GOOGLE_SECTION_RE.match(line.strip()) if not line.startswith((" ", "\t")) else None
        if match is not None:
            blocks.append((current_header, current_lines))
            current_header = match.group(1)
            current_lines = []
        else:
            current_lines.append(line)
    blocks.append((current_header, current_lines))

    intro_text = "\n".join(blocks[0][1]).strip("\n")
    paragraphs = [p.strip("\n") for p in re.split(r"\n[ \t]*\n", intro_text) if p.strip()]
    summary = clean_rst_markup(" ".join(line.strip() for line in paragraphs[0].splitlines())) if paragraphs else ""
    desc_blocks: list[str] = []
    for para in paragraphs[1:]:
        if para.startswith((" ", "\t")):
            if desc_blocks and desc_blocks[-1].endswith("::") and not desc_blocks[-1].endswith("`::`"):
                desc_blocks[-1] = desc_blocks[-1][:-1]
            elif summary.endswith("::") and not desc_blocks:
                summary = summary[:-1]
            code = textwrap.dedent(para).strip("\n")
            desc_blocks.append(f"```python\n{code}\n```")
        elif para.lstrip().startswith(("- ", "* ")):
            desc_blocks.append(clean_rst_markup(para))
        else:
            desc_blocks.append(clean_rst_markup(" ".join(line.strip() for line in para.splitlines() if line.strip())))
    description = "\n\n".join(desc_blocks)

    parsed_sections: list[tuple[str, str]] = []
    for header, sec_lines in blocks[1:]:
        if header is None:
            continue
        content = inspect.cleandoc("\n".join(sec_lines)).strip()
        if content:
            parsed_sections.append((header, content))

    return DocstringSections(
        summary=summary,
        description=description,
        sections=tuple(parsed_sections),
    )


def _format_arguments(args: ast.arguments) -> list[str]:
    parts: list[str] = []
    positional = list(args.posonlyargs) + list(args.args)
    defaults: list[ast.expr | None] = [None] * (len(positional) - len(args.defaults)) + list(args.defaults)
    posonly_count = len(args.posonlyargs)

    for idx, (arg, default) in enumerate(zip(positional, defaults, strict=True)):
        text = arg.arg
        if arg.annotation is not None:
            text += f": {ast.unparse(arg.annotation)}"
        if default is not None:
            text += f" = {ast.unparse(default)}"
        parts.append(text)
        if posonly_count > 0 and idx + 1 == posonly_count:
            parts.append("/")

    if args.vararg is not None:
        vtext = f"*{args.vararg.arg}"
        if args.vararg.annotation is not None:
            vtext += f": {ast.unparse(args.vararg.annotation)}"
        parts.append(vtext)
    elif args.kwonlyargs:
        parts.append("*")

    for kwarg, kwdefault in zip(args.kwonlyargs, args.kw_defaults, strict=True):
        text = kwarg.arg
        if kwarg.annotation is not None:
            text += f": {ast.unparse(kwarg.annotation)}"
        if kwdefault is not None:
            text += f" = {ast.unparse(kwdefault)}"
        parts.append(text)

    if args.kwarg is not None:
        ktext = f"**{args.kwarg.arg}"
        if args.kwarg.annotation is not None:
            ktext += f": {ast.unparse(args.kwarg.annotation)}"
        parts.append(ktext)

    return parts


def format_function_signature(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    *,
    strip_first_self: bool = False,
    include_decorators: bool = False,
) -> str:
    """Format a Python function or method AST signature concisely.

    Args:
        node: Function or async function definition node.
        strip_first_self: Reserved flag; retained parameters include ``self`` or ``cls`` explicitly if omitted.
        include_decorators: Whether to prepend ``property``/``classmethod``/``staticmethod`` decorators.

    Returns:
        Formatted signature string without function body.

    """
    del strip_first_self
    prefix_lines: list[str] = []
    if include_decorators:
        for dec in node.decorator_list:
            leaf = decorator_leaf_name(dec)
            if leaf in {"property", "classmethod", "staticmethod"}:
                prefix_lines.append(f"@{leaf}")

    keyword = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
    params = _format_arguments(node.args)
    ret = f" -> {ast.unparse(node.returns)}" if node.returns is not None else ""
    single = f"{keyword} {node.name}({', '.join(params)}){ret}"
    if len(single) <= 92:
        sig = single
    else:
        body_params = ",\n    ".join(params)
        sig = f"{keyword} {node.name}(\n    {body_params},\n){ret}"

    if prefix_lines:
        return "\n".join([*prefix_lines, sig])
    return sig


def format_class_signature(node: ast.ClassDef) -> str:
    """Format a class header along with its ``__init__`` or dataclass signature.

    Args:
        node: Class definition AST node.

    Returns:
        Formatted class signature string.

    """
    bases = [ast.unparse(base) for base in node.bases]
    kw_bases = [f"{kw.arg}={ast.unparse(kw.value)}" for kw in node.keywords if kw.arg]
    all_bases = [*bases, *kw_bases]
    header = f"class {node.name}({', '.join(all_bases)})" if all_bases else f"class {node.name}"

    init_node = next(
        (
            stmt
            for stmt in node.body
            if isinstance(stmt, ast.FunctionDef) and stmt.name == "__init__" and not is_exempt_method(stmt)
        ),
        None,
    )
    if init_node is not None:
        init_sig = format_function_signature(init_node)
        indented = "\n".join(f"    {line}" for line in init_sig.splitlines())
        return f"{header}:\n{indented}"

    is_dataclass = any(decorator_leaf_name(dec) == "dataclass" for dec in node.decorator_list)
    if is_dataclass:
        fields: list[str] = []
        for stmt in node.body:
            if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                fname = stmt.target.id
                if fname.startswith("_"):
                    continue
                ann = ast.unparse(stmt.annotation)
                if "ClassVar" in ann:
                    continue
                entry = f"    {fname}: {ann}"
                if stmt.value is not None:
                    entry += f" = {ast.unparse(stmt.value)}"
                fields.append(entry)
        if fields:
            return f"{header}:\n" + "\n".join(fields)

    return header


def format_assignment_signature(node: ast.Assign | ast.AnnAssign) -> tuple[Literal["constant", "type_alias"], str]:
    """Classify and format a module-level assignment or type alias node.

    Args:
        node: Assignment or annotated assignment AST node.

    Returns:
        Pair of ``(kind, signature)``.

    """
    raw = " ".join(line.strip() for line in ast.unparse(node).splitlines())
    kind: Literal["constant", "type_alias"] = "constant"
    if isinstance(node, ast.AnnAssign):
        ann = ast.unparse(node.annotation)
        if ann == "TypeAlias":
            kind = "type_alias"
    if len(raw) > 100 and "=" in raw:
        lhs, rhs = raw.split("=", 1)
        lhs = lhs.strip()
        rhs = rhs.strip()
        if len(rhs) > 68:
            raw = f"{lhs} = ..."
    return kind, raw


class SourceIndex:
    """Lazy cache mapping source file paths to text and parsed AST modules."""

    def __init__(self) -> None:
        """Initialize empty text and AST caches."""
        self.sources: dict[Path, str] = {}
        self.trees: dict[Path, ast.Module] = {}

    def source(self, path: Path) -> str:
        """Read and cache UTF-8/declared-encoding source text for ``path``.

        Args:
            path: Python source file path.

        Returns:
            Decoded source text.

        """
        if path not in self.sources:
            with tokenize.open(path) as handle:
                self.sources[path] = handle.read()
        return self.sources[path]

    def tree(self, path: Path) -> ast.Module:
        """Parse and cache the AST for ``path``.

        Args:
            path: Python source file path.

        Returns:
            Parsed ``ast.Module``.

        """
        if path not in self.trees:
            self.trees[path] = ast.parse(self.source(path), filename=str(path))
        return self.trees[path]


class Registry:
    """Discovery index mapping package roots to modules and source files."""

    def __init__(self, roots: list[Path], index: SourceIndex) -> None:
        """Initialize the registry for the given package root directories.

        Args:
            roots: Package root directories to scan.
            index: Shared ``SourceIndex`` cache.

        """
        self.roots = roots
        self.index = index
        self._module_of: dict[Path, str] = {}

    def py_files(self) -> list[tuple[Path, str]]:
        """Enumerate all non-stub ``*.py`` files and their dotted module names.

        Returns:
            Sorted list of ``(path, module_name)`` tuples.

        """
        files: list[tuple[Path, str]] = []
        for root in self.roots:
            for path in sorted(root.rglob("*.py")):
                if path.name.endswith(".pyi"):
                    continue
                relative = path.relative_to(root)
                parts = list(relative.with_suffix("").parts)
                if parts[-1] == "__init__":
                    parts.pop()
                module = ".".join([root.name, *parts])
                self._module_of[path] = module
                files.append((path, module))
        files.sort(key=lambda pair: str(pair[0]))
        return files

    def locate(self, module: str) -> Path | None:
        """Locate the source file implementing ``module``.

        Args:
            module: Dotted module name.

        Returns:
            Source ``Path`` if found under configured roots, else ``None``.

        """
        parts = module.split(".")
        for root in self.roots:
            if root.name != parts[0]:
                continue
            if len(parts) == 1:
                package_init = root / "__init__.py"
                return package_init if package_init.exists() else None
            sub = root.joinpath(*parts[1:])
            package_init = sub / "__init__.py"
            if package_init.exists():
                return package_init
            module_file = sub.with_suffix(".py")
            if module_file.exists():
                return module_file
        return None

    def module_of(self, path: Path) -> str:
        """Return the cached dotted module name for ``path``.

        Args:
            path: Previously discovered file path.

        Returns:
            Dotted module name.

        """
        return self._module_of[path]


def resolve_symbol(
    registry: Registry,
    index: SourceIndex,
    module: str,
    name: str,
    visited: frozenset[tuple[str, str]],
) -> tuple[Path, str, ast.AST] | None:
    """Resolve ``module:name`` through re-export and alias chains to its definition node.

    Args:
        registry: Module discovery registry.
        index: Parsed AST index.
        module: Starting dotted module name.
        name: Symbol name to resolve.
        visited: Cycle detection set of ``(module, name)`` pairs.

    Returns:
        ``(definition_path, definition_module, ast_node)`` or ``None`` if external/missing.

    """
    marker = (module, name)
    if marker in visited:
        return None
    visited = visited | {marker}
    path = registry.locate(module)
    if path is None:
        return None
    tree = index.tree(path)
    winner: tuple[str, ast.AST | str, str | None] | None = None
    for stmt in tree.body:
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and stmt.name == name:
            winner = ("definition", stmt, None)
        elif isinstance(stmt, ast.ImportFrom):
            for alias in stmt.names:
                if (alias.asname or alias.name) == name:
                    winner = ("importfrom", stmt, alias.name)
                    break
        elif isinstance(stmt, (ast.Assign, ast.AnnAssign)) and assignment_target(stmt, name) == name:
            winner = ("alias", stmt.value.id, None) if isinstance(stmt.value, ast.Name) else ("definition", stmt, None)
    if winner is None:
        for stmt in tree.body:
            if isinstance(stmt, ast.If) and is_type_checking_test(stmt.test):
                for inner in stmt.body:
                    if isinstance(inner, ast.ImportFrom):
                        for alias in inner.names:
                            if (alias.asname or alias.name) == name:
                                winner = ("importfrom", inner, alias.name)
    if winner is None:
        return None
    kind, payload, import_name = winner
    if kind == "alias":
        return resolve_symbol(registry, index, module, cast("str", payload), visited)
    if kind == "importfrom":
        node = cast("ast.ImportFrom", payload)
        target = import_target(module, path.name == "__init__.py", node)
        if target is None:
            return None
        return resolve_symbol(registry, index, target, cast("str", import_name), visited)
    return (path, module, cast("ast.AST", payload))


def _clean_docstring_expr(doc_node: ast.Expr | None) -> str:
    if doc_node is not None and isinstance(doc_node.value, ast.Constant) and isinstance(doc_node.value.value, str):
        return inspect.cleandoc(doc_node.value.value)
    return ""


def _extract_class_members(qualname: str, node: ast.ClassDef) -> tuple[ResolvedMember, ...]:
    members: list[ResolvedMember] = []
    for child in node.body:
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if "." in child.name or child.name.startswith("_") or is_exempt_method(child):
                continue
            is_prop = any(decorator_leaf_name(d) == "property" for d in child.decorator_list)
            kind: Literal["method", "async_method", "property", "class"]
            if is_prop:
                kind = "property"
            elif isinstance(child, ast.AsyncFunctionDef):
                kind = "async_method"
            else:
                kind = "method"
            doc_node = docstring_expr(child)
            raw_doc = _clean_docstring_expr(doc_node)
            members.append(
                ResolvedMember(
                    qualname=f"{qualname}.{child.name}",
                    name=child.name,
                    kind=kind,
                    signature=format_function_signature(child, include_decorators=True),
                    docstring=raw_doc,
                    parsed_docstring=parse_google_docstring(raw_doc),
                )
            )
        elif isinstance(child, ast.ClassDef):
            if child.name.startswith("_"):
                continue
            doc_node = docstring_expr(child)
            raw_doc = _clean_docstring_expr(doc_node)
            nested = _extract_class_members(f"{qualname}.{child.name}", child)
            members.append(
                ResolvedMember(
                    qualname=f"{qualname}.{child.name}",
                    name=child.name,
                    kind="class",
                    signature=format_class_signature(child),
                    docstring=raw_doc,
                    parsed_docstring=parse_google_docstring(raw_doc),
                    nested_members=nested,
                )
            )
    members.sort(key=lambda m: (m.kind == "class", m.name.lower(), m.name))
    return tuple(members)


@dataclass
class _SymbolAccumulator:
    def_path: Path
    def_module: str
    name: str
    node: ast.AST
    exports: set[tuple[str, str]] = field(default_factory=set)
    is_internal: bool = False


def collect_public_surface(
    roots: list[Path] = PACKAGE_ROOTS,
    important_internals: list[str] = IMPORTANT_INTERNALS,
) -> dict[str, ResolvedSymbol]:
    """Resolve the complete public API surface across the configured packages.

    Walks every ``__init__.py`` to resolve public re-exports and direct public
    definitions, plus entries in ``important_internals``, deduplicating symbols
    by canonical definition key ``module:name``.

    Args:
        roots: Package source root directories to inspect.
        important_internals: Additional ``module:symbol`` allowlist entries.

    Returns:
        Dictionary mapping canonical definition keys to ``ResolvedSymbol`` records.

    """
    index = SourceIndex()
    registry = Registry(roots, index)
    found: dict[str, _SymbolAccumulator] = {}

    def _record(
        export_mod: str,
        export_name: str,
        resolved: tuple[Path, str, ast.AST],
        *,
        is_internal: bool = False,
    ) -> None:
        dpath, dmod, dnode = resolved
        dname = getattr(dnode, "name", None) or assigned_name(dnode)
        key = f"{dmod}:{dname}"
        if key not in found:
            found[key] = _SymbolAccumulator(
                def_path=dpath,
                def_module=dmod,
                name=dname,
                node=dnode,
                is_internal=is_internal,
            )
        elif not is_internal:
            found[key].is_internal = False
        found[key].exports.add((export_mod, export_name))

    for path, module in registry.py_files():
        if path.name != "__init__.py":
            continue
        tree = index.tree(path)
        for stmt in top_level_statements(tree):
            if isinstance(stmt, ast.ImportFrom) and stmt.module is not None:
                target = import_target(module, True, stmt)
                if target is None:
                    continue
                for alias in stmt.names:
                    if alias.name == "*" or alias.name.startswith("_"):
                        continue
                    export_name = alias.asname or alias.name
                    if export_name.startswith("_"):
                        continue
                    resolved = resolve_symbol(registry, index, target, alias.name, frozenset())
                    if resolved is not None:
                        _record(module, export_name, resolved)
            elif (
                isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef))
                and not is_exempt_method(stmt)
                and not stmt.name.startswith("_")
            ) or (isinstance(stmt, ast.ClassDef) and not stmt.name.startswith("_")):
                _record(module, stmt.name, (path, module, stmt))

    for entry in important_internals:
        mod, _, sym = entry.partition(":")
        resolved = resolve_symbol(registry, index, mod, sym, frozenset())
        if resolved is not None:
            _record(mod, sym, resolved, is_internal=True)

    surface: dict[str, ResolvedSymbol] = {}
    for key in sorted(found):
        acc = found[key]
        node = acc.node
        lineno = getattr(node, "lineno", 1)
        members: tuple[ResolvedMember, ...] = ()
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            kind: Literal["function", "async_function", "class", "constant", "type_alias"] = (
                "async_function" if isinstance(node, ast.AsyncFunctionDef) else "function"
            )
            signature = format_function_signature(node)
            doc_node = docstring_expr(node)
            raw_doc = _clean_docstring_expr(doc_node)
        elif isinstance(node, ast.ClassDef):
            kind = "class"
            signature = format_class_signature(node)
            doc_node = docstring_expr(node)
            raw_doc = _clean_docstring_expr(doc_node)
            members = _extract_class_members(acc.name, node)
        else:
            assign_node = cast("ast.Assign | ast.AnnAssign", node)
            kind, signature = format_assignment_signature(assign_node)
            doc_node = trailing_docstring_expr(index.tree(acc.def_path).body, assign_node)
            raw_doc = _clean_docstring_expr(doc_node)

        surface[key] = ResolvedSymbol(
            key=key,
            name=acc.name,
            def_module=acc.def_module,
            def_path=acc.def_path,
            lineno=lineno,
            kind=kind,
            signature=signature,
            docstring=raw_doc,
            parsed_docstring=parse_google_docstring(raw_doc),
            exports=tuple(sorted(acc.exports)),
            members=members,
            is_internal=acc.is_internal,
        )
    return surface
