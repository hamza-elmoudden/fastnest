from __future__ import annotations

import ast
from pathlib import Path


def find_app_module(start_dir: Path, max_levels: int = 3) -> Path | None:
    current = start_dir.resolve()
    for _ in range(max_levels + 1):
        candidate = current / "app_module.py"
        if candidate.is_file():
            return candidate
        if current.parent == current:
            break
        current = current.parent
    return None


def _is_module_decorator(func: ast.expr) -> bool:
    if isinstance(func, ast.Name):
        return func.id == "Module"
    if isinstance(func, ast.Attribute):
        return func.attr == "Module"
    return False


def _find_imports_list(tree: ast.Module) -> ast.List | None:
    best: ast.List | None = None
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        for dec in node.decorator_list:
            if not (isinstance(dec, ast.Call) and _is_module_decorator(dec.func)):
                continue
            for kw in dec.keywords:
                if kw.arg == "imports" and isinstance(kw.value, ast.List):
                    if node.name == "AppModule":
                        return kw.value
                    if best is None:
                        best = kw.value
    return best


def _line_start_offsets(source: str) -> list[int]:
    offsets = [0]
    for line in source.splitlines(keepends=True):
        offsets.append(offsets[-1] + len(line))
    return offsets


def _offset(line_starts: list[int], lineno: int, col: int) -> int:
    return line_starts[lineno - 1] + col


def _find_import_insert_offset(tree: ast.Module, line_starts: list[int]) -> int:
    relative_imports = []
    all_imports = []
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            all_imports.append(node)
            if isinstance(node, ast.ImportFrom) and (node.level or 0) > 0:
                relative_imports.append(node)

    target = relative_imports[-1] if relative_imports else (all_imports[-1] if all_imports else None)
    if target is None:
        return 0
    return line_starts[target.end_lineno]


def _build_new_list_text(list_text: str, module_class_name: str) -> str:
    inner = list_text[1:-1]
    if inner.strip() == "":
        return "[" + module_class_name + "]"

    if "\n" in inner:
        indent = "    "
        for candidate_line in reversed(inner.split("\n")):
            if candidate_line.strip():
                indent = candidate_line[: len(candidate_line) - len(candidate_line.lstrip())]
                break
        stripped = inner.rstrip()
        trailing_ws = inner[len(stripped):]
        if not stripped.endswith(","):
            stripped += ","
        new_inner = f"{stripped}\n{indent}{module_class_name},{trailing_ws}"
    else:
        stripped = inner.rstrip()
        trailing_ws = inner[len(stripped):]
        if stripped and not stripped.endswith(","):
            stripped += ","
        sep = " " if stripped else ""
        new_inner = f"{stripped}{sep}{module_class_name}{trailing_ws}"

    return "[" + new_inner + "]"


def register_module(app_module_path: Path, module_class_name: str, import_line: str) -> None:
    source = app_module_path.read_text()
    tree = ast.parse(source)

    imports_list = _find_imports_list(tree)
    if imports_list is None:
        raise ValueError("Could not find an imports=[...] list inside a @Module(...) decorator")

    line_starts = _line_start_offsets(source)

    list_start = _offset(line_starts, imports_list.lineno, imports_list.col_offset)
    list_end = _offset(line_starts, imports_list.end_lineno, imports_list.end_col_offset)
    list_text = source[list_start:list_end]
    new_list_text = _build_new_list_text(list_text, module_class_name)

    import_offset = _find_import_insert_offset(tree, line_starts)

    edits = sorted(
        [
            (list_start, list_end, new_list_text),
            (import_offset, import_offset, import_line + "\n"),
        ],
        key=lambda edit: edit[0],
        reverse=True,
    )

    result = source
    for start, end, text in edits:
        result = result[:start] + text + result[end:]

    app_module_path.write_text(result)
