"""分层合并。"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .models import (
    CommonConfig,
    LanguageConfig,
    common_from_dict,
    language_from_dict,
)
from .loader import (
    builtin_config_dir,
    find_language_by_name,
    parse_toml,
)


class MergeTrace:
    """记录每个字段最终来源，便于 --dump-config。"""
    def __init__(self) -> None:
        self.entries: Dict[str, List[Tuple[str, object]]] = {}

    def record(self, key: str, source: str, value: object) -> None:
        self.entries.setdefault(key, []).append((source, value))

    def sources(self) -> List[str]:
        seen = []
        for lst in self.entries.values():
            for src, _ in lst:
                if src not in seen:
                    seen.append(src)
        return seen


def load_common(
    root: Path,
    explicit: Optional[Path],
    inherit_defaults: Optional[bool],
) -> Tuple[CommonConfig, List[str]]:
    sources: List[str] = []

    # 1. 内置
    builtin_path = builtin_config_dir() / "common.toml"
    if builtin_path.is_file():
        base = common_from_dict(parse_toml(builtin_path))
        sources.append(str(builtin_path))
    else:
        base = CommonConfig()

    merged = base

    # 2. 项目本地
    project_path = root / ".project_context" / "common.toml"
    if project_path.is_file():
        override = common_from_dict(parse_toml(project_path))
        if not override.inherit_defaults:
            merged = override
        else:
            merged = merged.extend(override)
        sources.append(str(project_path))

    # 3. 显式
    if explicit is not None:
        exp_path = Path(explicit).expanduser().resolve()
        override = common_from_dict(parse_toml(exp_path))
        if not override.inherit_defaults:
            merged = override
        else:
            merged = merged.extend(override)
        sources.append(str(exp_path))

    # 全局开关：--no-inherit-defaults
    if inherit_defaults is False:
        # 关闭继承：丢弃内置带来的 filter 部分
        merged = CommonConfig(
            schema_version=merged.schema_version,
            inherit_defaults=False,
            filter=_subtract(merged.filter, base.filter),
            max_file_size_kb=merged.max_file_size_kb,
            max_git_commits=merged.max_git_commits,
            max_files_per_commit=merged.max_files_per_commit,
            include_content=merged.include_content,
            include_ast=merged.include_ast,
            include_git=merged.include_git,
            no_timestamp=merged.no_timestamp,
            languages_active=merged.languages_active,
            detect_min_files=merged.detect_min_files,
        )

    return merged, sources


def _subtract(a, b):
    """a - b：用于 --no-inherit-defaults 场景。"""
    from .models import FilterConfig
    return FilterConfig(
        ignore_dirs=set(a.ignore_dirs) - set(b.ignore_dirs),
        ignore_dir_globs=[x for x in a.ignore_dir_globs if x not in b.ignore_dir_globs],
        ignore_suffixes=set(a.ignore_suffixes) - set(b.ignore_suffixes),
        ignore_file_globs=[x for x in a.ignore_file_globs if x not in b.ignore_file_globs],
        exclude_globs=list(a.exclude_globs),
    )


def load_language(
    name: str,
    root: Path,
    explicit: Optional[Path],
    extra_dirs: List[Path],
) -> Tuple[LanguageConfig, List[str]]:
    sources: List[str] = []

    # 1. 内置
    builtin_path = builtin_config_dir() / "languages" / f"{name}.toml"
    if builtin_path.is_file():
        base = language_from_dict(parse_toml(builtin_path))
        base.name = base.name or name
        sources.append(str(builtin_path))
    else:
        base = LanguageConfig(name=name)

    merged = base

    # 2. --language-dir
    for d in extra_dirs:
        p = Path(d) / f"{name}.toml"
        if p.is_file():
            override = language_from_dict(parse_toml(p))
            override.name = override.name or name
            merged = merged.extend(override) if override.inherit_defaults else override
            sources.append(str(p))

    # 3. 项目本地
    project_path = root / ".project_context" / "languages" / f"{name}.toml"
    if project_path.is_file():
        override = language_from_dict(parse_toml(project_path))
        override.name = override.name or name
        merged = merged.extend(override) if override.inherit_defaults else override
        sources.append(str(project_path))

    # 4. 显式
    if explicit is not None:
        exp = Path(explicit).expanduser().resolve()
        override = language_from_dict(parse_toml(exp))
        override.name = override.name or name
        merged = merged.extend(override) if override.inherit_defaults else override
        sources.append(str(exp))

    return merged, sources