"""U-LOAD-* 配置加载。"""
from pathlib import Path

import pytest

from project_context.config.loader import (
    builtin_config_dir,
    find_language_by_name,
    find_language_files,
    parse_toml,
)
from project_context.errors import ConfigError


def test_parse_toml_ok(tmp_path):
    p = tmp_path / "x.toml"
    p.write_text("[a]\nb = 1\n", encoding="utf-8")
    assert parse_toml(p) == {"a": {"b": 1}}


def test_parse_toml_missing(tmp_path):
    with pytest.raises(ConfigError):
        parse_toml(tmp_path / "nope.toml")


def test_parse_toml_syntax_error(tmp_path):
    p = tmp_path / "bad.toml"
    p.write_text("this is not = = toml", encoding="utf-8")
    with pytest.raises(ConfigError) as ei:
        parse_toml(p)
    assert "bad.toml" in str(ei.value)


def test_parse_toml_directory(tmp_path):
    d = tmp_path / "dir"
    d.mkdir()
    with pytest.raises(ConfigError):
        parse_toml(d)


def test_builtin_config_dir_exists():
    d = builtin_config_dir()
    assert d.is_dir()
    assert (d / "common.toml").is_file()


def test_find_language_files_includes_builtins():
    langs = find_language_files([])
    for name in ("python", "node", "go", "rust", "java", "cpp"):
        assert name in langs


def test_find_language_files_extra_overrides(tmp_path):
    extra = tmp_path / "extra"
    extra.mkdir()
    (extra / "python.toml").write_text('name = "python"\n', encoding="utf-8")
    langs = find_language_files([extra])
    assert langs["python"] == extra / "python.toml"


def test_find_language_by_name_hit():
    assert find_language_by_name("python", []) is not None


def test_find_language_by_name_miss():
    assert find_language_by_name("no_such_lang_xyz", []) is None