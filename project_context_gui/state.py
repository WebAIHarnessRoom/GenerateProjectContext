"""GUI 运行状态模型 + CLI 参数拼装。

命令预览与真实执行共用 build_cli_args，保证"所见即所跑"。
"""
from __future__ import annotations

from dataclasses import dataclass, field


# 与原 CLI 默认值保持一致（README 中有列出）
DEFAULT_MAX_FILE_SIZE_KB = 200
DEFAULT_MAX_GIT_COMMITS = 50
DEFAULT_MAX_FILES_PER_COMMIT = 20
DEFAULT_DETECT_MIN_FILES = 1


@dataclass
class RunState:
    """UI 状态与 CLI 参数的唯一映射。"""

    # 基础
    root: str = ""
    output: str = ""
    quiet: bool = False

    # 语言
    languages_mode: str = "auto"          # "auto" | "all" | "custom"
    languages_custom: list[str] = field(default_factory=list)
    detect_min_files: int = DEFAULT_DETECT_MIN_FILES

    # 过滤
    exclude_globs: list[str] = field(default_factory=list)
    exclude_dirs: list[str] = field(default_factory=list)
    exclude_dir_globs: list[str] = field(default_factory=list)
    exclude_suffixes: list[str] = field(default_factory=list)

    # 内容开关
    include_content: bool = True
    include_ast: bool = True
    include_git: bool = True
    no_timestamp: bool = False

    # 限制
    max_file_size_kb: int = DEFAULT_MAX_FILE_SIZE_KB
    max_git_commits: int = DEFAULT_MAX_GIT_COMMITS
    max_files_per_commit: int = DEFAULT_MAX_FILES_PER_COMMIT


def build_cli_args(state: RunState) -> list[str]:
    """把 RunState 转成 project_context CLI 参数列表（不含程序名）。"""
    args: list[str] = [state.root]

    if state.output:
        args += ["-o", state.output]

    if state.quiet:
        args.append("--quiet")

    # 语言
    if state.languages_mode == "all":
        args += ["--languages", "all"]
    elif state.languages_mode == "custom" and state.languages_custom:
        args += ["--languages", ",".join(state.languages_custom)]
    # auto 是默认，不传即可

    if state.detect_min_files != DEFAULT_DETECT_MIN_FILES:
        args += ["--detect-min-files", str(state.detect_min_files)]

    # 过滤
    for g in state.exclude_globs:
        args += ["--exclude", g]
    for d in state.exclude_dirs:
        args += ["--exclude-dir", d]
    for g in state.exclude_dir_globs:
        args += ["--exclude-dir-glob", g]
    for s in state.exclude_suffixes:
        args += ["--exclude-suffix", s]

    # 限制
    if state.max_file_size_kb != DEFAULT_MAX_FILE_SIZE_KB:
        args += ["--max-file-size", str(state.max_file_size_kb)]
    if state.max_git_commits != DEFAULT_MAX_GIT_COMMITS:
        args += ["--max-git-commits", str(state.max_git_commits)]
    if state.max_files_per_commit != DEFAULT_MAX_FILES_PER_COMMIT:
        args += ["--max-files-per-commit", str(state.max_files_per_commit)]

    # 章节开关
    if not state.include_git:
        args.append("--no-git")
    if not state.include_content:
        args.append("--no-content")
    if not state.include_ast:
        args.append("--no-ast")
    if state.no_timestamp:
        args.append("--no-timestamp")

    return args

def format_command(program: str, args: list[str]) -> str:
    """给命令预览用的可读字符串（仅用于展示，不用于执行）。"""
    parts = [program] + [
        f'"{a}"' if " " in a else a
        for a in args
        if a          # ← 跳过空参数（例如未选择项目时的 root）
    ]
    return " ".join(parts)