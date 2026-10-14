"""Python AST 摘要。"""
from __future__ import annotations

import ast
from typing import List


def _unparse(node) -> str:
    if node is None:
        return ""
    fn = getattr(ast, "unparse", None)
    if fn is None:
        return "..."
    try:
        return fn(node)
    except Exception:
        return "..."


def _first_line_doc(node) -> str:
    doc = ast.get_docstring(node, clean=True)
    if not doc:
        return ""
    line = doc.strip().splitlines()[0].strip()
    if len(line) > 100:
        line = line[:97] + "..."
    return line

def format_arguments(a: ast.arguments) -> str:
    parts: List[str] = []
    posonly = list(getattr(a, "posonlyargs", []))
    normal = list(a.args)
    all_pos = posonly + normal
    defaults = list(a.defaults)
    offset = len(all_pos) - len(defaults)

    for i, arg in enumerate(all_pos):
        s = arg.arg
        if arg.annotation is not None:
            s += ": " + _unparse(arg.annotation)
        di = i - offset
        if di >= 0:
            s += " = " + _unparse(defaults[di])     # ← 加空格
        parts.append(s)
        if posonly and i == len(posonly) - 1:
            parts.append("/")

    if a.vararg is not None:
        s = "*" + a.vararg.arg
        if a.vararg.annotation is not None:
            s += ": " + _unparse(a.vararg.annotation)
        parts.append(s)
    elif a.kwonlyargs:
        parts.append("*")

    for arg, default in zip(a.kwonlyargs, a.kw_defaults):
        s = arg.arg
        if arg.annotation is not None:
            s += ": " + _unparse(arg.annotation)
        if default is not None:
            s += " = " + _unparse(default)          # ← 加空格
        parts.append(s)

    if a.kwarg is not None:
        s = "**" + a.kwarg.arg
        if a.kwarg.annotation is not None:
            s += ": " + _unparse(a.kwarg.annotation)
        parts.append(s)

    return "(" + ", ".join(parts) + ")"

def summarize_python(source: str) -> List[str]:
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return [f"- ⚠️ 语法解析失败：{exc}"]

    out: List[str] = []

    def render(body, level: int) -> None:
        pad = "  " * level
        for node in body:
            if isinstance(node, ast.ClassDef):
                bases = ", ".join(_unparse(b) for b in node.bases)
                if node.keywords:
                    bases += (", " if bases else "") + ", ".join(
                        f"{k.arg}={_unparse(k.value)}" for k in node.keywords
                    )
                head = f"{pad}- **class** `{node.name}`"
                if bases:
                    head += f"({bases})"
                doc = _first_line_doc(node)
                if doc:
                    head += f"  — {doc}"
                out.append(head)
                render(node.body, level + 1)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                kw = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
                sig = f"{node.name}{format_arguments(node.args)}"
                if node.returns is not None:
                    sig += " -> " + _unparse(node.returns)
                head = f"{pad}- **{kw}** `{sig}`"
                if node.decorator_list:
                    decos = ", ".join("@" + _unparse(d) for d in node.decorator_list)
                    head += f"  `[{decos}]`"
                doc = _first_line_doc(node)
                if doc:
                    head += f"  — {doc}"
                out.append(head)

    render(tree.body, 0)
    return out