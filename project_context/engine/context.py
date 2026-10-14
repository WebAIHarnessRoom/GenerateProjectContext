"""ContextConfig 组装。"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from ..config.loader import builtin_config_dir, parse_toml
from ..config.merger import load_common, load_language
from ..config.models import ContextConfig, FilterConfig
from ..config.resolver import detect_languages, resolve_active_languages


GENERIC_CODE_LANGS: Dict[str, str] = {
    ".toml": "toml", ".cfg": "ini", ".ini": "ini", ".conf": "ini",
    ".json": "json", ".json5": "json",
    ".yaml": "yaml", ".yml": "yaml",
    ".md": "markdown", ".rst": "rst", ".txt": "text",
    ".sh": "bash", ".bash": "bash", ".zsh": "bash", ".fish": "fish",
    ".bat": "bat", ".ps1": "powershell",
    ".sql": "sql", ".graphql": "graphql", ".proto": "protobuf",
    ".html": "html", ".htm": "html", ".css": "css", ".scss": "scss",
    ".xml": "xml", ".svg": "xml",
    ".dockerfile": "dockerfile", ".mk": "makefile", ".cmake": "cmake",
}

GENERIC_NAME_LANGS: Dict[str, str] = {
    "Makefile": "makefile", "makefile": "makefile", "GNUmakefile": "makefile",
    "Dockerfile": "dockerfile", "dockerfile": "dockerfile",
    "Jenkinsfile": "groovy", "Vagrantfile": "ruby", "Procfile": "text",
}


def build_context_config(
    root: Path,
    *,
    config: Optional[Path] = None,
    inherit_defaults: Optional[bool] = None,
    languages=None,
    detect_min_files: Optional[int] = None,
    language_dirs: Optional[List[Path]] = None,
    language_configs: Optional[Dict[str, Path]] = None,
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
) -> ContextConfig:
    extra_dirs = [Path(d).expanduser().resolve() for d in (language_dirs or []) if d]
    lang_overrides = {
        k: Path(v).expanduser().resolve() for k, v in (language_configs or {}).items()
    }

    common, common_sources = load_common(root, config, inherit_defaults)
    sources = list(common_sources)

    # 决定 active languages
    if languages is not None:
        active = resolve_active_languages(
            languages, root, extra_dirs, lang_overrides,
            common.filter, common.detect_min_files,
        )
    else:
        active = resolve_active_languages(
            common.languages_active, root, extra_dirs, lang_overrides,
            common.filter, common.detect_min_files,
        )

    # 合并每个激活语言的 filter / code_langs / ast
    filters = common.filter
    code_map = dict(GENERIC_CODE_LANGS)
    code_name_map = dict(GENERIC_NAME_LANGS)
    ast_parsers: Dict[str, str] = {}

    for name in active:
        lcfg, lang_sources = load_language(name, root, lang_overrides.get(name), extra_dirs)
        sources.extend(lang_sources)
        if not lcfg.active:
            continue
        filters = filters.extend(lcfg.filter)
        code_map.update(lcfg.code_langs)
        code_name_map.update(lcfg.code_lang_names)
        ast_parsers[name] = lcfg.ast_parser

    # CLI/API 覆盖
    cli_filter = FilterConfig(
        ignore_dirs=set(exclude_dirs or []),
        ignore_dir_globs=list(exclude_dir_globs or []),
        ignore_suffixes=set(exclude_suffixes or []),
        ignore_file_globs=list(exclude or []),
    )
    filters = filters.extend(cli_filter)

    # 值覆盖
    ctx = ContextConfig(
        root=root,
        filters=filters,
        max_file_size_kb=max_file_size_kb or common.max_file_size_kb,
        max_git_commits=max_git_commits or common.max_git_commits,
        max_files_per_commit=max_files_per_commit or common.max_files_per_commit,
        include_content=include_content if include_content is not None else common.include_content,
        include_ast=include_ast if include_ast is not None else common.include_ast,
        include_git=include_git if include_git is not None else common.include_git,
        no_timestamp=no_timestamp if no_timestamp is not None else common.no_timestamp,
        active_languages=active,
        code_lang_map=code_map,
        code_lang_name_map=code_name_map,
        ast_parsers=ast_parsers,
        config_sources=_dedup(sources),
    )
    return ctx


def _dedup(items):
    seen = []
    for x in items:
        if x not in seen:
            seen.append(x)
    return seen