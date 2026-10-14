"""Markdown 组装。"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

from ..config.models import ContextConfig
from .ast import get_parser
from .collector import collect_files
from .git_info import gather_git_info
from .reader import read_all


def code_block(text: str, lang: str = "") -> str:
    fence = "```"
    while fence in text:
        fence += "`"
    body = text.rstrip("\n")
    return f"{fence}{lang}\n{body}\n{fence}\n"


def guess_lang(path: Path, ctx: ContextConfig) -> str:
    if path.name in ctx.code_lang_name_map:
        return ctx.code_lang_name_map[path.name]
    return ctx.code_lang_map.get(path.suffix.lower(), "")


def build_tree_text(root: Path, files: List[Path]) -> str:
    tree: Dict[str, dict] = {}
    for f in files:
        rel = f.relative_to(root)
        node = tree
        for part in rel.parts[:-1]:
            node = node.setdefault(part, {})
        node[rel.parts[-1]] = None

    lines: List[str] = [root.name + "/"]

    def render(node, prefix):
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


def render_document(root: Path, ctx: ContextConfig) -> str:
    files = collect_files(root, ctx.filters)
    contents = {}
    if ctx.include_content or ctx.include_ast:
        contents = read_all(files, root, ctx.max_file_size_kb, only_py=not ctx.include_content)

    git_info = gather_git_info(root, ctx.max_git_commits, enabled=ctx.include_git)

    now = "" if ctx.no_timestamp else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    project_name = root.name

    total_lines = sum(t.count("\n") + 1 for t, _ in contents.values())
    py_files = [f for f in files if f.suffix == ".py"]

    md: List[str] = []
    md.append(f"# 项目上下文文档：{project_name}\n")
    if now:
        md.append(f"> 生成时间：{now}  ")
    md.append(f"> 项目根目录：`{root}`  ")
    md.append(f"> 生成脚本：`generate_project_context.py`\n")
    md.append("> 本文档由脚本自动生成，包含项目目录结构、源码内容、代码结构摘要"
              "与 Git 提交历史，用于人工理解项目以及为 AI 提供工程上下文。\n")

    # 目录
    md.append("## 目录\n")
    md.append("1. [项目概览](#1-项目概览)")
    md.append("2. [目录结构](#2-目录结构)")
    if ctx.include_ast:
        md.append("3. [代码结构总览](#3-代码结构总览)")
    if ctx.include_content:
        md.append("4. [源码与配置文件内容](#4-源码与配置文件内容)")
    if git_info.get("is_repo"):
        md.append("5. [Git 提交历史](#5-git-提交历史)")
    md.append("\n---\n")

    # 1. 概览
    md.append("## 1. 项目概览\n")
    md.append(f"- 项目名称：`{project_name}`")
    md.append(f"- 项目根目录：`{root}`")
    md.append(f"- 纳入统计的文件数：**{len(files)}**")
    md.append(f"- Python 文件数：**{len(py_files)}**")
    md.append(f"- 纳入文档的代码/文本总行数：**{total_lines}**")
    if ctx.active_languages:
        md.append(f"- 激活语言：{', '.join(f'`{n}`' for n in ctx.active_languages)}")
    if git_info.get("is_repo"):
        md.append(f"- Git 当前分支：`{git_info['branch']}`")
        if git_info.get("head"):
            md.append(f"- 最新提交：`{git_info['head']}`")
    else:
        md.append("- Git 仓库：未检测到（或已禁用）")
    if ctx.config_sources:
        md.append("- 配置来源：")
        for s in ctx.config_sources:
            md.append(f"  - `{s}`")
    md.append("")

    suffix_count: Dict[str, int] = {}
    for f in files:
        key = f.suffix.lower() or "(无后缀)"
        suffix_count[key] = suffix_count.get(key, 0) + 1
    top = sorted(suffix_count.items(), key=lambda kv: -kv[1])[:15]
    if top:
        md.append("**文件类型分布（Top 15）**\n")
        md.append("| 后缀 | 数量 |")
        md.append("| --- | --- |")
        for s, c in top:
            md.append(f"| `{s}` | {c} |")
        md.append("")
    md.append("---\n")

    # 2. 目录结构
    md.append("## 2. 目录结构\n")
    md.append("> 已忽略版本控制、虚拟环境、缓存、构建产物等与编码无关的目录与文件。\n")
    md.append(code_block(build_tree_text(root, files), "text"))
    md.append("\n---\n")

    # 3. AST
    if ctx.include_ast:
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
            # 根据语言选择 parser
            parser = get_parser(ctx.ast_parsers.get("python", "python"))
            if parser is None:
                continue
            summary = parser(text)
            if not summary:
                continue
            md.append(f"### `{rel}`\n")
            md.append("\n".join(summary))
            md.append("")
        md.append("---\n")

    # 4. 源码内容
    if ctx.include_content:
        md.append("## 4. 源码与配置文件内容\n")
        if not contents:
            md.append("_没有可读取的文本文件。_\n")
        for f in files:
            rel = f.relative_to(root).as_posix()
            entry = contents.get(rel)
            if entry is None:
                continue
            text, truncated = entry
            lang = guess_lang(f, ctx)
            line_count = text.count("\n") + 1
            md.append(f"### `{rel}`\n")
            md.append(f"_{line_count} 行_\n")
            if truncated:
                md.append(f"> ⚠️ 文件超过大小限制，已截断显示前 {ctx.max_file_size_kb} KB。\n")
            md.append(code_block(text, lang))
            md.append("")
        md.append("---\n")

    # 5. Git
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
                subj = c["subject"].replace("|", "\\|")
                md.append(f"| `{c['sha']}` | {c['date']} | {c['author']} | {subj} |")
            md.append("")
            md.append("### 5.2 提交详情\n")
            for c in commits:
                md.append(f"#### `{c['sha']}` · {c['date']} · {c['author']}\n")
                md.append(f"- **提交信息**：{c['subject']}")
                md.append(f"- **变更规模**：{len(c['files'])} 个文件，+{c['added']} / -{c['deleted']}")
                if c["files"]:
                    shown = c["files"][: ctx.max_files_per_commit]
                    md.append("- **变更文件**：")
                    for path, a, d in shown:
                        if a.isdigit() and d.isdigit():
                            md.append(f"  - `{path}` (+{a} / -{d})")
                        else:
                            md.append(f"  - `{path}` (二进制)")
                    if len(c["files"]) > len(shown):
                        md.append(f"  - _……其余 {len(c['files']) - len(shown)} 个文件已省略_")
                md.append("")
        else:
            md.append("_未获取到提交记录。_\n")

    return "\n".join(md)