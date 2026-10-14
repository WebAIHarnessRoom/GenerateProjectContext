"""参数映射表：唯一事实来源。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional


@dataclass
class ParamSpec:
    cli: str
    dest: str
    config_path: tuple
    kind: str                   # scalar | append | csv | pair | flag
    transform: Optional[Callable] = None
    default: Any = None
    help: str = ""


PARAM_MAP: List[ParamSpec] = [
    ParamSpec("--config", "config", ("common_file",), "scalar",
              help="通用配置文件路径"),
    ParamSpec("--inherit-defaults", "inherit_defaults", ("inherit_defaults",), "flag",
              transform=lambda v: True, default=None,
              help="继承内置配置"),
    ParamSpec("--no-inherit-defaults", "inherit_defaults", ("inherit_defaults",), "flag",
              transform=lambda v: False, default=None,
              help="不继承内置配置"),

    ParamSpec("--languages", "languages", ("languages", "active"), "csv",
              default=None,
              help="显式激活语言: python,go | auto | all"),
    ParamSpec("--detect-min-files", "detect_min_files",
              ("languages", "detect_min_files"), "scalar",
              transform=int, default=None,
              help="自动检测阈值"),

    ParamSpec("--language-dir", "language_dirs", ("language_dirs",), "append",
              default=None, help="额外语言配置目录（可重复）"),
    ParamSpec("--language-config", "language_configs", ("language_configs",), "pair",
              default=None, help="NAME=PATH 覆盖某语言配置（可重复）"),

    ParamSpec("--max-file-size", "max_file_size_kb",
              ("limits", "max_file_size_kb"), "scalar",
              transform=int, default=None,
              help="单文件大小上限 KB（默认 200）"),
    ParamSpec("--max-git-commits", "max_git_commits",
              ("limits", "max_git_commits"), "scalar",
              transform=int, default=None,
              help="采集提交数量（默认 50）"),
    ParamSpec("--max-files-per-commit", "max_files_per_commit",
              ("limits", "max_files_per_commit"), "scalar",
              transform=int, default=None,
              help="每条提交列出文件数（默认 20）"),

    ParamSpec("--no-git", "no_git", ("features", "include_git"), "flag",
              transform=lambda v: not v, default=None,
              help="不采集 Git 信息"),
    ParamSpec("--no-content", "no_content", ("features", "include_content"), "flag",
              transform=lambda v: not v, default=None,
              help="不输出源码"),
    ParamSpec("--no-ast", "no_ast", ("features", "include_ast"), "flag",
              transform=lambda v: not v, default=None,
              help="不输出 AST 摘要"),
    ParamSpec("--no-timestamp", "no_timestamp", ("features", "no_timestamp"), "flag",
              transform=lambda v: v, default=None,
              help="关闭时间戳"),

    ParamSpec("--exclude", "exclude", ("filter", "ignore_file_globs"), "append",
              default=None, help="追加文件 glob（可重复）"),
    ParamSpec("--exclude-dir", "exclude_dirs", ("filter", "ignore_dirs"), "append",
              default=None, help="追加忽略目录名（可重复）"),
    ParamSpec("--exclude-dir-glob", "exclude_dir_globs",
              ("filter", "ignore_dir_globs"), "append",
              default=None, help="追加忽略目录 glob（可重复）"),
    ParamSpec("--exclude-suffix", "exclude_suffixes",
              ("filter", "ignore_suffixes"), "append",
              default=None, help="追加忽略后缀（可重复）"),
]


def build_argparser():
    import argparse
    parser = argparse.ArgumentParser(
        description="读取项目结构、源码与 Git 日志，生成 Markdown 上下文文档。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("root", nargs="?", default=".", help="项目根目录，默认当前目录")
    parser.add_argument("-o", "--output", default=None,
                        help="输出路径，默认 <root>/PROJECT_CONTEXT.md")
    parser.add_argument("--list-languages", action="store_true",
                        help="列出可用语言并退出")
    parser.add_argument("--dump-config", action="store_true",
                        help="打印合并后的最终配置并退出")
    parser.add_argument("--quiet", action="store_true", help="静默模式")

    seen = set()
    for spec in PARAM_MAP:
        if spec.cli in seen:
            continue
        seen.add(spec.cli)

        if spec.kind == "flag":
            parser.add_argument(
                spec.cli, dest=spec.dest, action="store_const",
                const=True,
                default=argparse.SUPPRESS,
                help=spec.help,
            )
        elif spec.kind == "append":
            parser.add_argument(spec.cli, dest=spec.dest, action="append",
                                default=argparse.SUPPRESS, help=spec.help)
        elif spec.kind == "csv":
            parser.add_argument(spec.cli, dest=spec.dest, type=str,
                                default=argparse.SUPPRESS, help=spec.help)
        elif spec.kind == "pair":
            parser.add_argument(spec.cli, dest=spec.dest, action="append",
                                default=argparse.SUPPRESS, help=spec.help)
        else:  # scalar
            parser.add_argument(spec.cli, dest=spec.dest, type=str,
                                default=argparse.SUPPRESS, help=spec.help)
    return parser


def cli_to_kwargs(args) -> dict:
    """把 argparse.Namespace 转成 generate_context 的关键字参数。"""
    out: dict = {}

    # 特殊处理 flag 语义：多个 flag 可能写同一 dest，取最后出现的
    for spec in PARAM_MAP:
        if not hasattr(args, spec.dest):
            continue
        raw = getattr(args, spec.dest)
        if raw is None:
            continue

        if spec.dest == "inherit_defaults":
            # 两个 flag 都写同一 dest，随便哪个出现都拿其值
            if spec.cli == "--inherit-defaults" and raw is True:
                out[spec.dest] = True
            elif spec.cli == "--no-inherit-defaults" and raw is True:
                out[spec.dest] = False
            continue

        if spec.kind == "flag":
            # transform 已隐含在 const 里，这里根据出现与否决定
            val = spec.transform(raw) if spec.transform else raw
            out[spec.dest] = val

        elif spec.kind == "append":
            out[spec.dest] = list(raw)

        elif spec.kind == "csv":
            if spec.dest == "languages":
                out[spec.dest] = raw  # "auto" | "all" | "python,go"

        elif spec.kind == "pair":
            d = {}
            for item in raw:
                if "=" not in item:
                    continue
                k, v = item.split("=", 1)
                d[k.strip()] = v.strip()
            out[spec.dest] = d

        else:  # scalar
            val = spec.transform(raw) if spec.transform else raw
            out[spec.dest] = val

    # 统一转换 no_git/no_content/no_ast 到对应 include_*
    if "no_git" in out:
        out["include_git"] = out.pop("no_git")
    if "no_content" in out:
        out["include_content"] = out.pop("no_content")
    if "no_ast" in out:
        out["include_ast"] = out.pop("no_ast")

    return out