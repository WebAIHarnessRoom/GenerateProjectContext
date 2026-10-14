"""U-MRG-* 配置合并。"""
from pathlib import Path

import pytest

from project_context.config.merger import load_common, load_language


# ---------- load_common ----------

def test_load_common_builtin_only(tmp_path):
    cfg, sources = load_common(tmp_path, None, None)
    assert ".git" in cfg.filter.ignore_dirs
    assert ".idea" in cfg.filter.ignore_dirs
    assert any("common.toml" in s for s in sources)


def test_load_common_project_override(tmp_path):
    proj = tmp_path / ".project_context"
    proj.mkdir()
    (proj / "common.toml").write_text(
        'inherit_defaults = true\n\n'
        '[filter]\n'
        'ignore_dirs = ["third_party"]\n',
        encoding="utf-8",
    )
    cfg, sources = load_common(tmp_path, None, None)
    assert "third_party" in cfg.filter.ignore_dirs
    assert ".git" in cfg.filter.ignore_dirs           # 并集
    assert any(".project_context" in s for s in sources)


def test_load_common_explicit_config(tmp_path):
    explicit = tmp_path / "explicit.toml"
    explicit.write_text(
        '[filter]\nignore_dirs = ["custom_x"]\n',
        encoding="utf-8",
    )
    cfg, sources = load_common(tmp_path, explicit, None)
    assert "custom_x" in cfg.filter.ignore_dirs
    assert any("explicit.toml" in s for s in sources)


def test_load_common_no_inherit_global(tmp_path):
    proj = tmp_path / ".project_context"
    proj.mkdir()
    (proj / "common.toml").write_text(
        '[filter]\nignore_dirs = ["xxx"]\n',
        encoding="utf-8",
    )
    cfg, _ = load_common(tmp_path, None, inherit_defaults=False)
    assert "xxx" in cfg.filter.ignore_dirs
    assert ".git" not in cfg.filter.ignore_dirs       # 减掉内置


def test_load_common_project_no_inherit_in_file(tmp_path):
    proj = tmp_path / ".project_context"
    proj.mkdir()
    (proj / "common.toml").write_text(
        'inherit_defaults = false\n'
        '[filter]\nignore_dirs = ["only_me"]\n',
        encoding="utf-8",
    )
    cfg, _ = load_common(tmp_path, None, None)
    assert "only_me" in cfg.filter.ignore_dirs
    assert ".git" not in cfg.filter.ignore_dirs


# ---------- load_language ----------

def test_load_language_builtin(tmp_path):
    cfg, sources = load_language("python", tmp_path, None, [])
    assert ".venv" in cfg.filter.ignore_dirs
    assert cfg.ast_parser == "python"
    assert cfg.code_langs.get(".py") == "python"


def test_load_language_project_override(tmp_path):
    proj = tmp_path / ".project_context" / "languages"
    proj.mkdir(parents=True)
    (proj / "python.toml").write_text(
        'inherit_defaults = true\n'
        '[filter]\nignore_dirs = ["local_venv"]\n',
        encoding="utf-8",
    )
    cfg, sources = load_language("python", tmp_path, None, [])
    assert "local_venv" in cfg.filter.ignore_dirs
    assert ".venv" in cfg.filter.ignore_dirs           # 并集
    assert any(".project_context" in s for s in sources)


def test_load_language_extra_dir(tmp_path):
    extra = tmp_path / "extra_langs"
    extra.mkdir()
    (extra / "python.toml").write_text(
        '[filter]\nignore_dirs = ["from_extra"]\n',
        encoding="utf-8",
    )
    cfg, sources = load_language("python", tmp_path, None, [extra])
    assert "from_extra" in cfg.filter.ignore_dirs
    assert any(str(extra) in s for s in sources)


def test_load_language_explicit_override(tmp_path):
    explicit = tmp_path / "my_python.toml"
    explicit.write_text(
        '[filter]\nignore_dirs = ["explicit_venv"]\n',
        encoding="utf-8",
    )
    cfg, sources = load_language("python", tmp_path, explicit, [])
    assert "explicit_venv" in cfg.filter.ignore_dirs


def test_load_language_new_custom_lang(tmp_path):
    proj = tmp_path / ".project_context" / "languages"
    proj.mkdir(parents=True)
    (proj / "mydsl.toml").write_text(
        'name = "mydsl"\ninherit_defaults = false\n'
        '[detect]\nsuffixes = [".mydsl"]\n'
        '[code_langs]\n".mydsl" = "plaintext"\n',
        encoding="utf-8",
    )
    cfg, _ = load_language("mydsl", tmp_path, None, [])
    assert cfg.name == "mydsl"
    assert ".mydsl" in cfg.detect.suffixes
    assert cfg.code_langs[".mydsl"] == "plaintext"