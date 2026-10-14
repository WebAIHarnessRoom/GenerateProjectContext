"""配置数据模型：全部为不可变合并语义（合并时返回新实例）。"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Set, Union

from ..errors import UnknownFieldError


# ---------------------------------------------------------------------------
# FilterConfig
# ---------------------------------------------------------------------------

@dataclass
class FilterConfig:
    ignore_dirs: Set[str] = field(default_factory=set)
    ignore_dir_globs: List[str] = field(default_factory=list)
    ignore_suffixes: Set[str] = field(default_factory=set)
    ignore_file_globs: List[str] = field(default_factory=list)
    exclude_globs: List[str] = field(default_factory=list)

    def extend(self, other: "FilterConfig") -> "FilterConfig":
        """并集语义；不修改原对象。"""
        return FilterConfig(
            ignore_dirs=set(self.ignore_dirs) | set(other.ignore_dirs),
            ignore_dir_globs=list(self.ignore_dir_globs) + list(other.ignore_dir_globs),
            ignore_suffixes=set(self.ignore_suffixes) | set(other.ignore_suffixes),
            ignore_file_globs=list(self.ignore_file_globs) + list(other.ignore_file_globs),
            exclude_globs=list(self.exclude_globs) + list(other.exclude_globs),
        )

    def is_empty(self) -> bool:
        return not (
            self.ignore_dirs
            or self.ignore_dir_globs
            or self.ignore_suffixes
            or self.ignore_file_globs
            or self.exclude_globs
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ignore_dirs": sorted(self.ignore_dirs),
            "ignore_dir_globs": list(self.ignore_dir_globs),
            "ignore_suffixes": sorted(self.ignore_suffixes),
            "ignore_file_globs": list(self.ignore_file_globs),
            "exclude_globs": list(self.exclude_globs),
        }


# ---------------------------------------------------------------------------
# DetectRule
# ---------------------------------------------------------------------------

@dataclass
class DetectRule:
    suffixes: List[str] = field(default_factory=list)
    file_globs: List[str] = field(default_factory=list)
    dir_markers: List[str] = field(default_factory=list)

    def extend(self, other: "DetectRule") -> "DetectRule":
        return DetectRule(
            suffixes=_dedup(self.suffixes + other.suffixes),
            file_globs=_dedup(self.file_globs + other.file_globs),
            dir_markers=_dedup(self.dir_markers + other.dir_markers),
        )


# ---------------------------------------------------------------------------
# CommonConfig
# ---------------------------------------------------------------------------

@dataclass
class CommonConfig:
    schema_version: int = 1
    inherit_defaults: bool = True

    filter: FilterConfig = field(default_factory=FilterConfig)

    max_file_size_kb: int = 200
    max_git_commits: int = 50
    max_files_per_commit: int = 20

    include_content: bool = True
    include_ast: bool = True
    include_git: bool = True
    no_timestamp: bool = False

    languages_active: Union[str, List[str]] = "auto"
    detect_min_files: int = 1

    def extend(self, other: "CommonConfig") -> "CommonConfig":
        """other 覆盖 self；filter 采用并集。"""
        return CommonConfig(
            schema_version=other.schema_version or self.schema_version,
            inherit_defaults=other.inherit_defaults,
            filter=self.filter.extend(other.filter),
            max_file_size_kb=other.max_file_size_kb,
            max_git_commits=other.max_git_commits,
            max_files_per_commit=other.max_files_per_commit,
            include_content=other.include_content,
            include_ast=other.include_ast,
            include_git=other.include_git,
            no_timestamp=other.no_timestamp,
            languages_active=other.languages_active,
            detect_min_files=other.detect_min_files,
        )


# ---------------------------------------------------------------------------
# LanguageConfig
# ---------------------------------------------------------------------------

@dataclass
class LanguageConfig:
    schema_version: int = 1
    name: str = ""
    inherit_defaults: bool = True
    active: bool = True

    detect: DetectRule = field(default_factory=DetectRule)
    filter: FilterConfig = field(default_factory=FilterConfig)

    code_langs: Dict[str, str] = field(default_factory=dict)
    code_lang_names: Dict[str, str] = field(default_factory=dict)

    ast_parser: str = "none"

    def extend(self, other: "LanguageConfig") -> "LanguageConfig":
        """other 覆盖 self；列表/dict 有明确语义。"""
        merged_code = dict(self.code_langs)
        merged_code.update(other.code_langs)
        merged_names = dict(self.code_lang_names)
        merged_names.update(other.code_lang_names)

        return LanguageConfig(
            schema_version=other.schema_version or self.schema_version,
            name=other.name or self.name,
            inherit_defaults=other.inherit_defaults,
            active=other.active,
            detect=self.detect.extend(other.detect),
            filter=self.filter.extend(other.filter),
            code_langs=merged_code,
            code_lang_names=merged_names,
            ast_parser=other.ast_parser if other.ast_parser != "none" else self.ast_parser,
        )


# ---------------------------------------------------------------------------
# ContextConfig（引擎输入）
# ---------------------------------------------------------------------------

@dataclass
class ContextConfig:
    root: Path

    filters: FilterConfig

    max_file_size_kb: int = 200
    max_git_commits: int = 50
    max_files_per_commit: int = 20

    include_content: bool = True
    include_ast: bool = True
    include_git: bool = True
    no_timestamp: bool = False

    active_languages: List[str] = field(default_factory=list)
    code_lang_map: Dict[str, str] = field(default_factory=dict)
    code_lang_name_map: Dict[str, str] = field(default_factory=dict)
    ast_parsers: Dict[str, str] = field(default_factory=dict)  # 语言名 -> parser

    config_sources: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _dedup(items: List[str]) -> List[str]:
    seen: Set[str] = set()
    out: List[str] = []
    for x in items:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


# ---------------------------------------------------------------------------
# dict -> dataclass 转换
# ---------------------------------------------------------------------------

_FILTER_KEYS = {
    "ignore_dirs", "ignore_dir_globs", "ignore_suffixes",
    "ignore_file_globs", "exclude_globs",
}

_COMMON_TOP_KEYS = {
    "schema_version", "inherit_defaults",
    "filter", "limits", "features", "languages",
}

_LANG_TOP_KEYS = {
    "schema_version", "name", "inherit_defaults", "active",
    "detect", "filter", "code_langs", "code_lang_names", "ast",
}


def filter_from_dict(d: Dict[str, Any]) -> FilterConfig:
    unknown = set(d) - _FILTER_KEYS
    if unknown:
        raise UnknownFieldError("config", "filter", sorted(unknown)[0], _FILTER_KEYS)
    return FilterConfig(
        ignore_dirs=set(d.get("ignore_dirs", [])),
        ignore_dir_globs=list(d.get("ignore_dir_globs", [])),
        ignore_suffixes=set(d.get("ignore_suffixes", [])),
        ignore_file_globs=list(d.get("ignore_file_globs", [])),
        exclude_globs=list(d.get("exclude_globs", [])),
    )


def common_from_dict(d: Dict[str, Any]) -> CommonConfig:
    unknown = set(d) - _COMMON_TOP_KEYS
    if unknown:
        raise UnknownFieldError("config", "common", sorted(unknown)[0], _COMMON_TOP_KEYS)

    limits = d.get("limits", {}) or {}
    features = d.get("features", {}) or {}
    langs = d.get("languages", {}) or {}

    return CommonConfig(
        schema_version=int(d.get("schema_version", 1)),
        inherit_defaults=bool(d.get("inherit_defaults", True)),
        filter=filter_from_dict(d.get("filter", {}) or {}),
        max_file_size_kb=int(limits.get("max_file_size_kb", 200)),
        max_git_commits=int(limits.get("max_git_commits", 50)),
        max_files_per_commit=int(limits.get("max_files_per_commit", 20)),
        include_content=bool(features.get("include_content", True)),
        include_ast=bool(features.get("include_ast", True)),
        include_git=bool(features.get("include_git", True)),
        no_timestamp=bool(features.get("no_timestamp", False)),
        languages_active=langs.get("active", "auto"),
        detect_min_files=int(langs.get("detect_min_files", 1)),
    )


def language_from_dict(d: Dict[str, Any]) -> LanguageConfig:
    unknown = set(d) - _LANG_TOP_KEYS
    if unknown:
        raise UnknownFieldError("config", "language", sorted(unknown)[0], _LANG_TOP_KEYS)

    detect_d = d.get("detect", {}) or {}
    ast_d = d.get("ast", {}) or {}

    return LanguageConfig(
        schema_version=int(d.get("schema_version", 1)),
        name=str(d.get("name", "")),
        inherit_defaults=bool(d.get("inherit_defaults", True)),
        active=bool(d.get("active", True)),
        detect=DetectRule(
            suffixes=list(detect_d.get("suffixes", [])),
            file_globs=list(detect_d.get("file_globs", [])),
            dir_markers=list(detect_d.get("dir_markers", [])),
        ),
        filter=filter_from_dict(d.get("filter", {}) or {}),
        code_langs=dict(d.get("code_langs", {})),
        code_lang_names=dict(d.get("code_lang_names", {})),
        ast_parser=str(ast_d.get("parser", "none")),
    )