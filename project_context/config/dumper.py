"""--dump-config 输出。"""
from __future__ import annotations

from typing import List

from .models import ContextConfig


def dump_config_text(ctx: ContextConfig) -> str:
    lines: List[str] = []
    lines.append("# 合并后的最终配置（只读展示，可用于 --config 参考）")
    lines.append(f"# root = {ctx.root}")
    lines.append("")

    lines.append("[limits]")
    lines.append(f"max_file_size_kb     = {ctx.max_file_size_kb}")
    lines.append(f"max_git_commits      = {ctx.max_git_commits}")
    lines.append(f"max_files_per_commit = {ctx.max_files_per_commit}")
    lines.append("")

    lines.append("[features]")
    lines.append(f"include_content = {str(ctx.include_content).lower()}")
    lines.append(f"include_ast     = {str(ctx.include_ast).lower()}")
    lines.append(f"include_git     = {str(ctx.include_git).lower()}")
    lines.append(f"no_timestamp    = {str(ctx.no_timestamp).lower()}")
    lines.append("")

    lines.append("[languages]")
    lines.append(f"active = {ctx.active_languages!r}")
    lines.append("")

    lines.append("[filter]")
    lines.append("ignore_dirs = [")
    for d in sorted(ctx.filters.ignore_dirs):
        lines.append(f"  {d!r},")
    lines.append("]")
    lines.append("ignore_dir_globs = [")
    for d in ctx.filters.ignore_dir_globs:
        lines.append(f"  {d!r},")
    lines.append("]")
    lines.append("ignore_suffixes = [")
    for d in sorted(ctx.filters.ignore_suffixes):
        lines.append(f"  {d!r},")
    lines.append("]")
    lines.append("ignore_file_globs = [")
    for d in ctx.filters.ignore_file_globs:
        lines.append(f"  {d!r},")
    lines.append("]")
    lines.append("exclude_globs = [")
    for d in ctx.filters.exclude_globs:
        lines.append(f"  {d!r},")
    lines.append("]")
    lines.append("")

    lines.append("# 配置来源（按加载顺序）")
    for s in ctx.config_sources:
        lines.append(f"# - {s}")

    return "\n".join(lines)