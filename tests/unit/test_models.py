"""U-MOD-* 数据模型。"""
from pathlib import Path

import pytest

from project_context.config.models import (
    CommonConfig,
    DetectRule,
    FilterConfig,
    LanguageConfig,
    common_from_dict,
    filter_from_dict,
    language_from_dict,
)
from project_context.errors import UnknownFieldError


# ---------- FilterConfig ----------

def test_filter_config_extend_union():
    a = FilterConfig(ignore_dirs={"x"}, ignore_suffixes={".a"},
                     ignore_file_globs=["*.p"], ignore_dir_globs=["g*"])
    b = FilterConfig(ignore_dirs={"y"}, ignore_suffixes={".b"},
                     ignore_file_globs=["*.q"], ignore_dir_globs=["h*"])
    r = a.extend(b)
    assert r.ignore_dirs == {"x", "y"}
    assert r.ignore_suffixes == {".a", ".b"}
    assert r.ignore_file_globs == ["*.p", "*.q"]
    assert r.ignore_dir_globs == ["g*", "h*"]


def test_filter_config_extend_does_not_mutate_original():
    a = FilterConfig(ignore_dirs={"x"})
    b = FilterConfig(ignore_dirs={"y"})
    _ = a.extend(b)
    assert a.ignore_dirs == {"x"}
    assert b.ignore_dirs == {"y"}


def test_filter_config_is_empty_true():
    assert FilterConfig().is_empty() is True


def test_filter_config_is_empty_false():
    assert FilterConfig(ignore_dirs={"x"}).is_empty() is False


# ---------- DetectRule ----------

def test_detect_rule_extend_dedup():
    a = DetectRule(suffixes=[".a"])
    b = DetectRule(suffixes=[".a", ".b"])
    r = a.extend(b)
    assert r.suffixes == [".a", ".b"]


# ---------- CommonConfig.extend ----------

def test_common_config_extend_scalar_override():
    a = CommonConfig(max_file_size_kb=100)
    b = CommonConfig(max_file_size_kb=200)
    assert a.extend(b).max_file_size_kb == 200


def test_common_config_extend_filter_union():
    a = CommonConfig(filter=FilterConfig(ignore_dirs={"x"}))
    b = CommonConfig(filter=FilterConfig(ignore_dirs={"y"}))
    r = a.extend(b)
    assert r.filter.ignore_dirs == {"x", "y"}


# ---------- LanguageConfig.extend ----------

def test_language_config_extend_dict_merge():
    a = LanguageConfig(code_langs={".py": "python"})
    b = LanguageConfig(code_langs={".py": "python3", ".pyi": "python"})
    r = a.extend(b)
    assert r.code_langs[".py"] == "python3"
    assert r.code_langs[".pyi"] == "python"


def test_language_config_extend_none_parser_does_not_override():
    a = LanguageConfig(ast_parser="python")
    b = LanguageConfig(ast_parser="none")
    assert a.extend(b).ast_parser == "python"


# ---------- from_dict 校验 ----------

def test_common_from_dict_unknown_field():
    with pytest.raises(UnknownFieldError):
        common_from_dict({"xxx": 1})


def test_common_from_dict_defaults():
    cfg = common_from_dict({})
    assert cfg.max_file_size_kb == 200
    assert cfg.include_git is True
    assert cfg.languages_active == "auto"


def test_language_from_dict_unknown_field():
    with pytest.raises(UnknownFieldError):
        language_from_dict({"xxx": 1})


def test_filter_from_dict_unknown_field():
    with pytest.raises(UnknownFieldError):
        filter_from_dict({"bad": []})