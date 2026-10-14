#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_project_context.py

读取 Python 项目结构、源码内容与 Git 提交日志，整理为一份 Markdown 文档，
用于人工快速理解项目，也用于给 AI 提供工程上下文。

用法：
    python generate_project_context.py                     # 分析当前目录
    python generate_project_context.py /path/to/project -o context.md
    python generate_project_context.py . --max-git-commits 100 --max-file-size 300
    python generate_project_context.py . --no-content      # 只输出结构，不输出源码
    python generate_project_context.py . --exclude "*.pb.go" --exclude "tests/fixtures/*"

依赖：Python 3.9+（使用了 ast.unparse）；Git 可选。
"""

from __future__ import annotations

import argparse
import ast
import fnmatch
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

# ---------------------------------------------------------------------------
# 默认忽略规则
# ---------------------------------------------------------------------------

# 与“编码”无关的目录：版本控制、IDE、缓存、虚拟环境、构建产物等
DEFAULT_IGNORE_DIRS = {
    ".git", ".hg", ".svn", ".bzr",
    ".idea", ".vscode", ".vs", ".settings", ".fleet", ".history",
    "__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache",
    ".tox", ".nox", ".eggs", ".hypothesis", ".pytype", ".pyre",
    "build", "dist", "target", "node_modules",
    "venv", ".venv", "env", ".env", "virtualenv", "site-packages",
    "htmlcov", ".coverage", ".cache", ".ipynb_checkpoints",
    ".terraform", ".serverless", ".gradle", "coverage",
}

DEFAULT_IGNORE_DIR_GLOBS = [
    "*.egg-info", "*.dist-info", "*.egg", ".git*", "docs/_build",
]

# 与“编码”无关的文件后缀：二进制、媒体、模型权重、压缩包、锁文件等
DEFAULT_IGNORE_SUFFIXES = {
    # 编译产物 / 二进制
    ".pyc", ".pyo", ".pyd", ".so", ".dll", ".dylib", ".a", ".o", ".obj",
    ".class", ".jar", ".exe", ".bin", ".wasm", ".lib", ".exp",
    # 数据 / 序列化
    ".db", ".sqlite", ".sqlite3", ".dat", ".pkl", ".pickle",
    ".npy", ".npz", ".parquet", ".h5", ".hdf5", ".pt", ".pth",
    ".onnx", ".ckpt", ".safetensors", ".gguf", ".vocab",
    # 图片 / 音视频 / 字体
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".svg", ".webp",
    ".tiff", ".psd", ".ai", ".eps",
    ".mp3", ".mp4", ".avi", ".mov", ".wav", ".flac", ".ogg", ".mkv",
    ".ttf", ".otf", ".woff", ".woff2", ".eot",
    # 压缩包
    ".zip", ".tar", ".gz", ".bz2", ".xz", ".7z", ".rar", ".whl", ".egg",
    # 锁文件 / 日志 / 临时文件
    ".lock", ".log", ".tmp", ".temp", ".bak", ".orig", ".swp", ".swo", ".rej",
    # 文档 / 表格 / 演示（与代码无关的二进制格式）
    ".ipynb", ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    # 其他
    ".map", ".min.js", ".min.css", ".DS_Store", ".pyc.orig",
}

DEFAULT_IGNORE_FILE_GLOBS = [
    ".DS_Store", "Thumbs.db", "desktop.ini", "*.pyc", "*.pyo",
]

# 代码块语言映射
LANG_BY_SUFFIX = {
    ".py": "python", ".pyi": "python", ".pyx": "cython", ".pxd": "cython",
    ".toml": "toml", ".cfg": "ini", ".ini": "ini", ".conf": "ini",
    ".json": "json", ".json5": "json", ".yaml": "yaml", ".yml": "yaml",
    ".md": "markdown", ".rst": "rst", ".txt": "text",
    ".sh": "bash", ".bash": "bash", ".zsh": "bash", ".fish": "fish",
    ".bat": "bat", ".ps1": "powershell",
    ".sql": "sql", ".graphql": "graphql", ".proto": "protobuf",
    ".js": "javascript", ".mjs": "javascript", ".cjs": "javascript",
    ".ts": "typescript", ".tsx": "tsx", ".jsx": "jsx",
    ".html": "html", ".htm": "html", ".css": "css", ".scss": "scss",
    ".xml": "xml", ".svg": "xml",
    ".c": "c", ".h": "c", ".cpp": "cpp", ".hpp": "cpp", ".cc": "cpp",
    ".java": "java", ".kt": "kotlin", ".go": "go", ".rs": "rust",
    ".rb": "ruby", ".php": "php", ".cs": "csharp", ".swift": "swift",
    ".dockerfile": "dockerfile", ".mk": "makefile", ".cmake": "cmake",
    ".env": "bash", ".gitignore": "gitignore",
}

LANG_BY_NAME = {
    "Makefile": "makefile", "makefile": "makefile", "GNUmakefile": "makefile",
    "Dockerfile": "dockerfile", "dockerfile": "dockerfile",
    "Jenkinsfile": "groovy", "Vagrantfile": "ruby", "Procfile": "text",
}


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------

def should_ignore_dir(name: str, ignore_dirs: Iterable[str],
                      ignore_globs: Iterable[str]) -> bool:
    if name in ignore_dirs:
        return True
    return any(fnmatch.fnmatch(name, pat) for pat in ignore_globs)


def should_ignore_file(name: str, rel_posix: str, ignore_suffixes: Iterable[str],
                       ignore_globs: Iterable[str]) -> bool:
    suffix = Path(name).suffix.lower()
    if suffix in ignore_suffixes:
        return True
    if name in DEFAULT_IGNORE_FILE_GLOBS:
        return True
    for pat in ignore_globs:
        if fnmatch.fnmatch(name, pat) or fnmatch.fnmatch(rel_posix, pat):
            return True
    return False


def guess_lang(path: Path) -> str:
    if path.name in LANG_BY_NAME:
        return LANG_BY_NAME[path.name]
    return LANG_BY_SUFFIX.get(path.suffix.lower(), "")


def code_block(text: str, lang: str = "") -> str:
    """生成不会与内容冲突的围栏代码块。"""
    fence = "```"
    while fence in text:
        fence += "`"
    body = text.rstrip("\n")
    return f"{fence}{lang}\n{body}\n{fence}\n"


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


# ---------------------------------------------------------------------------
# 文件收集与读取
# ---------------------------------------------------------------------------

def collect_source_files(root: Path,
                         output_path: Optional[Path],
                         ignore_dirs: Iterable[str],
                         ignore_dir_globs: Iterable[str],
                         ignore_suffixes: Iterable[str],
                         ignore_file_globs: List[str]) -> List[Path]:
    """遍历项目，返回需要纳入文档的文件绝对路径列表。"""
    files: List[Path] = []
    out_resolved = output_path.resolve() if output_path else None

    for dirpath, dirnames, filenames in os.walk(root):
        # 原地裁剪，跳过忽略目录与符号链接目录
        dirnames[:] = sorted(
            d for d in dirnames
            if not should_ignore_dir(d, ignore_dirs, ignore_dir_globs)
            and not os.path.islink(os.path.join(dirpath, d))
        )
        for fn in sorted(filenames):
            p = Path(dirpath) / fn
            if os.path.islink(p):
                continue
            try:
                rel_posix = p.relative_to(root).as_posix()
            except ValueError:
                rel_posix = p.name
            if should_ignore_file(fn, rel_posix, ignore_suffixes, ignore_file_globs):
                continue
            if out_resolved and p.resolve() == out_resolved:
                continue
            files.append(p)

    files.sort(key=lambda x: x.relative_to(root).as_posix().lower())
    return files


def read_text_file(path: Path, max_bytes: int) -> Optional[Tuple[str, bool]]:
    """读取文本文件。返回 (内容, 是否被截断)；二进制或不可读返回 None。"""
    try:
        data = path.read_bytes()
    except OSError:
        return None

    truncated = False
    if len(data) > max_bytes:
        data = data[:max_bytes]
        truncated = True

    # 简单二进制检测
    if b"\x00" in data[:8192]:
        return None

    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        try:
            text = data.decode("gbk")
        except UnicodeDecodeError:
            text = data.decode("utf-8", errors="replace")

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text, truncated


# ---------------------------------------------------------------------------
# 目录树
# ---------------------------------------------------------------------------

def build_tree_text(root: Path, files: List[Path]) -> str:
    """根据纳入的文件列表构建目录树文本。"""
    tree: Dict[str, dict] = {}
    for f in files:
        rel = f.relative_to(root)
        node = tree
        for part in rel.parts[:-1]:
            node = node.setdefault(part, {})
        node[rel.parts[-1]] = None  # None 表示文件

    lines: List[str] = [root.name + "/"]

    def render(node: Dict[str, dict], prefix: str) -> None:
        # 目录优先，其次文件，各自按名称排序
        entries = sorted(node.items(), key=lambda kv: (kv[1] is None, kv[0].lower()))
        for i, (name, child) in enumerate(entries):
            last = i == len(entries) - 1
            connector = "└── " if last else "├── "
            if child is None:
                lines.append(prefix + connector + name)
            else:
                lines.append(prefix + connector + name + "/")
                render(child, prefix + ("    " if last else "│   "))

    render(tree, "")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Python AST 结构摘要
# ---------------------------------------------------------------------------

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
            s += "=" + _unparse(defaults[di])
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
            s += "=" + _unparse(default)
        parts.append(s)

    if a.kwarg is not None:
        s = "**" + a.kwarg.arg
        if a.kwarg.annotation is not None:
            s += ": " + _unparse(a.kwarg.annotation)
        parts.append(s)

    return "(" + ", ".join(parts) + ")"


def _first_line_doc(node) -> str:
    doc = ast.get_docstring(node, clean=True)
    if not doc:
        return ""
    line = doc.strip().splitlines()[0].strip()
    if len(line) > 100:
        line = line[:97] + "..."
    return line


def summarize_python(source: str) -> List[str]:
    """返回某个 Python 文件的类/函数结构摘要（Markdown 列表行）。"""
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


# ---------------------------------------------------------------------------
# Git
# ---------------------------------------------------------------------------

def run_git(root: Path, args: List[str]) -> Optional[str]:
    try:
        proc = subprocess.run(
            ["git", "-C", str(root)] + args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except (FileNotFoundError, OSError):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout


def parse_git_log(root: Path, max_commits: int) -> List[dict]:
    fmt = "%x1e%h%x1f%ad%x1f%an%x1f%s"
    raw = run_git(root, [
        "log",
        f"--max-count={max_commits}",
        "--date=short",
        f"--pretty=format:{fmt}",
        "--numstat",
        "--no-merges",
    ])
    if not raw:
        return []

    commits: List[dict] = []
    for chunk in raw.split("\x1e"):
        chunk = chunk.strip("\n")
        if not chunk:
            continue
        lines = chunk.split("\n")
        parts = lines[0].split("\x1f")
        if len(parts) < 4:
            continue
        sha, date, author = parts[0], parts[1], parts[2]
        subject = "\x1f".join(parts[3:])

        files: List[Tuple[str, str, str]] = []
        added_total = 0
        deleted_total = 0
        for line in lines[1:]:
            if not line.strip():
                continue
            seg = line.split("\t")
            if len(seg) < 3:
                continue
            a, d, path = seg[0], seg[1], "\t".join(seg[2:])
            if a.isdigit():
                added_total += int(a)
            if d.isdigit():
                deleted_total += int(d)
            files.append((path, a, d))

        commits.append({
            "sha": sha,
            "date": date,
            "author": author,
            "subject": subject,
            "files": files,
            "added": added_total,
            "deleted": deleted_total,
        })
    return commits


def gather_git_info(root: Path, max_commits: int, enabled: bool) -> dict:
    info = {"is_repo": False, "branch": "", "head": "", "commits": []}
    if not enabled:
        return info

    branch = run_git(root, ["rev-parse", "--abbrev-ref", "HEAD"])
    if branch is None:
        return info

    info["is_repo"] = True
    info["branch"] = branch.strip()
    head = run_git(root, ["log", "-1", "--date=short",
                          "--pretty=format:%h · %ad · %an · %s"])
    info["head"] = (head or "").strip()
    info["commits"] = parse_git_log(root, max_commits)
    return info


# ---------------------------------------------------------------------------
# 文档组装
# ---------------------------------------------------------------------------

def build_document(root: Path,
                   files: List[Path],
                   contents: Dict[str, Tuple[str, bool]],
                   git_info: dict,
                   args: argparse.Namespace) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    project_name = root.name

    total_lines = sum(text.count("\n") + 1 for text, _ in contents.values())
    py_files = [f for f in files if f.suffix == ".py"]

    md: List[str] = []
    md.append(f"# 项目上下文文档：{project_name}\n")
    md.append(f"> 生成时间：{now}  ")
    md.append(f"> 项目根目录：`{root}`  ")
    md.append(f"> 生成脚本：`generate_project_context.py`\n")
    md.append(
        "> 本文档由脚本自动生成，包含项目目录结构、源码内容、代码结构摘要"
        "与 Git 提交历史，用于人工理解项目以及为 AI 提供工程上下文。\n"
    )

    # ---- 目录 ----
    md.append("## 目录\n")
    md.append("1. [项目概览](#1-项目概览)")
    md.append("2. [目录结构](#2-目录结构)")
    if not args.no_ast:
        md.append("3. [代码结构总览](#3-代码结构总览)")
    if not args.no_content:
        md.append("4. [源码与配置文件内容](#4-源码与配置文件内容)")
    if git_info.get("is_repo"):
        md.append("5. [Git 提交历史](#5-git-提交历史)")
    md.append("\n---\n")

    # ---- 1. 项目概览 ----
    md.append("## 1. 项目概览\n")
    md.append(f"- 项目名称：`{project_name}`")
    md.append(f"- 项目根目录：`{root}`")
    md.append(f"- 纳入统计的文件数：**{len(files)}**")
    md.append(f"- Python 文件数：**{len(py_files)}**")
    md.append(f"- 纳入文档的代码/文本总行数：**{total_lines}**")
    if git_info.get("is_repo"):
        md.append(f"- Git 当前分支：`{git_info['branch']}`")
        if git_info.get("head"):
            md.append(f"- 最新提交：`{git_info['head']}`")
    else:
        md.append("- Git 仓库：未检测到（或已禁用）")
    md.append("")

    # 按后缀统计
    suffix_count: Dict[str, int] = {}
    for f in files:
        key = f.suffix.lower() or "(无后缀)"
        suffix_count[key] = suffix_count.get(key, 0) + 1
    top_suffix = sorted(suffix_count.items(), key=lambda kv: -kv[1])[:15]
    if top_suffix:
        md.append("**文件类型分布（Top 15）**\n")
        md.append("| 后缀 | 数量 |")
        md.append("| --- | --- |")
        for suf, cnt in top_suffix:
            md.append(f"| `{suf}` | {cnt} |")
        md.append("")
    md.append("---\n")

    # ---- 2. 目录结构 ----
    md.append("## 2. 目录结构\n")
    md.append("> 已忽略版本控制、虚拟环境、缓存、构建产物等与编码无关的目录与文件。\n")
    md.append(code_block(build_tree_text(root, files), "text"))
    md.append("\n---\n")

    # ---- 3. 代码结构总览 ----
    if not args.no_ast:
        md.append("## 3. 代码结构总览\n")
        md.append("> 基于 AST 解析出的类 / 函数签名，便于快速把握模块职责。\n")
        if not py_files:
            md.append("_未发现 Python 文件。_\n")
        for f in py_files:
            rel = f.relative_to(root).as_posix()
            entry = contents.get(rel)
            if entry is None:
                continue
            text, _ = entry
            summary = summarize_python(text)
            if not summary:
                continue
            md.append(f"### `{rel}`\n")
            md.append("\n".join(summary))
            md.append("")
        md.append("---\n")

    # ---- 4. 源码内容 ----
    if not args.no_content:
        md.append("## 4. 源码与配置文件内容\n")
        if not contents:
            md.append("_没有可读取的文本文件。_\n")
        for f in files:
            rel = f.relative_to(root).as_posix()
            entry = contents.get(rel)
            if entry is None:
                continue
            text, truncated = entry
            lang = guess_lang(f)
            line_count = text.count("\n") + 1
            md.append(f"### `{rel}`\n")
            md.append(f"_{line_count} 行_\n")
            if truncated:
                md.append(f"> ⚠️ 文件超过大小限制，已截断显示前 {args.max_file_size} KB。\n")
            md.append(code_block(text, lang))
            md.append("")
        md.append("---\n")

    # ---- 5. Git 历史 ----
    if git_info.get("is_repo"):
        commits = git_info["commits"]
        md.append("## 5. Git 提交历史\n")
        md.append(f"- 分支：`{git_info['branch']}`")
        md.append(f"- 采集提交数：**{len(commits)}**")
        md.append("")

        if commits:
            md.append("### 5.1 提交概览\n")
            md.append("| SHA | 日期 | 作者 | 提交信息 |")
            md.append("| --- | --- | --- | --- |")
            for c in commits:
                subject = c["subject"].replace("|", "\\|")
                md.append(f"| `{c['sha']}` | {c['date']} | {c['author']} | {subject} |")
            md.append("")

            md.append("### 5.2 提交详情\n")
            for c in commits:
                md.append(f"#### `{c['sha']}` · {c['date']} · {c['author']}\n")
                md.append(f"- **提交信息**：{c['subject']}")
                md.append(
                    f"- **变更规模**：{len(c['files'])} 个文件，"
                    f"+{c['added']} / -{c['deleted']}"
                )
                if c["files"]:
                    shown = c["files"][: args.max_files_per_commit]
                    md.append("- **变更文件**：")
                    for path, a, d in shown:
                        if a.isdigit() and d.isdigit():
                            md.append(f"  - `{path}` (+{a} / -{d})")
                        else:
                            md.append(f"  - `{path}` (二进制)")
                    if len(c["files"]) > len(shown):
                        md.append(
                            f"  - _……其余 {len(c['files']) - len(shown)} 个文件已省略_"
                        )
                md.append("")
        else:
            md.append("_未获取到提交记录。_\n")

    return "\n".join(md)


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="读取 Python 项目结构、源码与 Git 日志，生成 Markdown 上下文文档。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("root", nargs="?", default=".",
                        help="项目根目录，默认当前目录")
    parser.add_argument("-o", "--output", default=None,
                        help="输出 Markdown 文件路径，默认 <root>/PROJECT_CONTEXT.md")
    parser.add_argument("--max-file-size", type=int, default=200,
                        help="单个文件最大读取大小（KB），超出则截断，默认 200")
    parser.add_argument("--max-git-commits", type=int, default=50,
                        help="采集的 Git 提交数量，默认 50")
    parser.add_argument("--max-files-per-commit", type=int, default=20,
                        help="每条提交最多列出的变更文件数，默认 20")
    parser.add_argument("--no-git", action="store_true",
                        help="不采集 Git 信息")
    parser.add_argument("--no-content", action="store_true",
                        help="不输出源码内容，只输出结构与 Git 历史")
    parser.add_argument("--no-ast", action="store_true",
                        help="不输出 AST 代码结构摘要")
    parser.add_argument("--exclude", action="append", default=[],
                        metavar="GLOB",
                        help="额外忽略的文件 glob（可重复），如 --exclude 'tests/fixtures/*'")
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)

    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        print(f"[错误] 目录不存在：{root}", file=sys.stderr)
        return 1

    if args.output:
        output_path = Path(args.output).expanduser().resolve()
    else:
        output_path = root / "PROJECT_CONTEXT.md"

    max_bytes = max(1, args.max_file_size) * 1024
    ignore_file_globs = list(DEFAULT_IGNORE_FILE_GLOBS) + list(args.exclude)

    print(f"[1/4] 扫描项目结构：{root}")
    files = collect_source_files(
        root=root,
        output_path=output_path,
        ignore_dirs=DEFAULT_IGNORE_DIRS,
        ignore_dir_globs=DEFAULT_IGNORE_DIR_GLOBS,
        ignore_suffixes=DEFAULT_IGNORE_SUFFIXES,
        ignore_file_globs=ignore_file_globs,
    )
    print(f"      纳入文件 {len(files)} 个")

    contents: Dict[str, Tuple[str, bool]] = {}
    if not args.no_content or not args.no_ast:
        print("[2/4] 读取文件内容")
        for f in files:
            rel = f.relative_to(root).as_posix()
            result = read_text_file(f, max_bytes)
            if result is None:
                continue
            # --no-content 时只保留 .py（供 AST 使用）以节省内存
            if args.no_content and f.suffix != ".py":
                continue
            contents[rel] = result
        print(f"      成功读取 {len(contents)} 个文本文件")
    else:
        print("[2/4] 跳过文件内容读取")

    print("[3/4] 采集 Git 信息")
    git_info = gather_git_info(root, args.max_git_commits, enabled=not args.no_git)
    if git_info["is_repo"]:
        print(f"      分支 {git_info['branch']}，采集提交 {len(git_info['commits'])} 条")
    else:
        print("      未检测到 Git 仓库，跳过")

    print("[4/4] 生成 Markdown 文档")
    document = build_document(root, files, contents, git_info, args)

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(document, encoding="utf-8")
    except OSError as exc:
        print(f"[错误] 写入失败：{exc}", file=sys.stderr)
        return 1

    size_kb = output_path.stat().st_size / 1024
    print(f"\n✅ 完成：{output_path}  ({size_kb:.1f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())