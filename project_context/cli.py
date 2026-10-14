"""CLI 入口。"""
from __future__ import annotations

import sys
from pathlib import Path

from .api import generate_context
from .config.loader import find_language_files
from .errors import ConfigError, ProjectContextError
from .params import build_argparser, cli_to_kwargs

def main(argv=None) -> int:
    parser = build_argparser()
    args = parser.parse_args(argv)

    kwargs = cli_to_kwargs(args)

    # 特殊模式：list-languages
    if getattr(args, "list_languages", False):
        extra_dirs = [Path(d) for d in (kwargs.get("language_dirs") or [])]
        langs = sorted(find_language_files(extra_dirs).keys())
        print("可用语言：")
        for n in langs:
            print(f"  - {n}")
        return 0

    # 默认输出路径（仅 CLI 层保持旧行为）
    output = args.output
    if output is None and not getattr(args, "dump_config", False):
        output = Path(args.root).expanduser().resolve() / "PROJECT_CONTEXT.md"

    try:
        result = generate_context(
            root=args.root,
            output=output,
            dump_config=getattr(args, "dump_config", False),
            verbose=not getattr(args, "quiet", False),
            **kwargs,
        )
    except ConfigError as e:
        print(f"[config-error] {e}", file=sys.stderr)
        return 2
    except ProjectContextError as e:
        print(f"[error] {e}", file=sys.stderr)
        return 1
    except FileNotFoundError as e:
        print(f"[error] {e}", file=sys.stderr)
        return 1

    if getattr(args, "dump_config", False):
        if isinstance(result, str):
            print(result)
        else:
            print(f"配置已写入: {result}")
        return 0

    if isinstance(result, Path):
        size_kb = result.stat().st_size / 1024
        if not getattr(args, "quiet", False):
            print(f"\n[DONE] {result}  ({size_kb:.1f} KB)")
    return 0