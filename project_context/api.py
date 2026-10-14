"""公共 API。"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .config.models import ContextConfig
from .engine.context import build_context_config
from .engine.renderer import render_document


def generate_context(
    root: Union[str, Path] = ".",
    *,
    output: Optional[Union[str, Path]] = None,
    config: Optional[Union[str, Path]] = None,
    inherit_defaults: Optional[bool] = None,
    languages=None,
    detect_min_files: Optional[int] = None,
    language_dirs: Optional[List[Union[str, Path]]] = None,
    language_configs: Optional[Dict[str, Union[str, Path]]] = None,
    exclude: Optional[List[str]] = None,
    exclude_dirs: Optional[List[str]] = None,
    exclude_dir_globs: Optional[List[str]] = None,
    exclude_suffixes: Optional[List[str]] = None,
    max_file_size_kb: Optional[int] = None,
    max_git_commits: Optional[int] = None,
    max_files_per_commit: Optional[int] = None,
    include_git: Optional[bool] = None,
    include_content: Optional[bool] = None,
    include_ast: Optional[bool] = None,
    no_timestamp: Optional[bool] = None,
    dump_config: bool = False,
    verbose: bool = False,
) -> Union[Path, str]:
    root_p = Path(root).expanduser().resolve()
    if not root_p.is_dir():
        raise FileNotFoundError(f"目录不存在: {root_p}")

    out_path: Optional[Path] = None
    if output is not None:
        out_path = Path(output).expanduser().resolve()
    # output=None 时 out_path 保持 None，最终返回 str

    ctx = build_context_config(
        root_p,
        config=Path(config) if config else None,
        inherit_defaults=inherit_defaults,
        languages=languages,
        detect_min_files=detect_min_files,
        language_dirs=[Path(d) for d in (language_dirs or [])],
        language_configs={k: Path(v) for k, v in (language_configs or {}).items()},
        exclude=exclude,
        exclude_dirs=exclude_dirs,
        exclude_dir_globs=exclude_dir_globs,
        exclude_suffixes=exclude_suffixes,
        max_file_size_kb=max_file_size_kb,
        max_git_commits=max_git_commits,
        max_files_per_commit=max_files_per_commit,
        include_git=include_git,
        include_content=include_content,
        include_ast=include_ast,
        no_timestamp=no_timestamp,
    )

    if dump_config:
        from .config.dumper import dump_config_text
        text = dump_config_text(ctx)
        if out_path is not None:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(text, encoding="utf-8")
            return out_path
        return text

    document = render_document(root_p, ctx)

    if out_path is None:
        return document

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(document, encoding="utf-8")
    return out_path