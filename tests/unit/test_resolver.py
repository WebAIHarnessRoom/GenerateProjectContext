"""U-RES-* 语言识别与激活。"""
import pytest

from project_context.config.resolver import (
    detect_languages,
    list_available_languages,
    resolve_active_languages,
)
from project_context.config.models import FilterConfig
from project_context.errors import LanguageNotFoundError


def test_list_available_languages_builtin():
    langs = list_available_languages([])
    for name in ("python", "node", "go", "rust"):
        assert name in langs


def test_resolve_explicit_list(py_only):
    r = resolve_active_languages(
        ["python", "go"], py_only, [], {},
        FilterConfig(ignore_dirs={".git"}), detect_min_files=1,
    )
    assert r == ["python", "go"]


def test_resolve_explicit_missing_raises(py_only):
    with pytest.raises(LanguageNotFoundError):
        resolve_active_languages(
            ["no_such_lang_xyz"], py_only, [], {},
            FilterConfig(), detect_min_files=1,
        )


def test_resolve_all(py_only):
    r = resolve_active_languages(
        "all", py_only, [], {},
        FilterConfig(), detect_min_files=1,
    )
    assert "python" in r and "node" in r


def test_detect_py_only(py_only):
    r = detect_languages(
        py_only, [], {},
        FilterConfig(ignore_dirs={".git", "__pycache__"}),
        detect_min_files=1,
    )
    assert "python" in r
    assert "go" not in r


def test_detect_py_node(py_node):
    r = detect_languages(
        py_node, [], {},
        FilterConfig(),
        detect_min_files=1,
    )
    assert "python" in r
    assert "node" in r


def test_detect_threshold(py_node):
    """阈值 100 时，什么都检测不到。"""
    r = detect_languages(
        py_node, [], {},
        FilterConfig(),
        detect_min_files=100,
    )
    assert r == []


def test_detect_ignores_noise_dir(with_noise):
    """with_noise 里 .venv/lib/foo.py 应被忽略，但 src/main.py 仍触发 python。"""
    r = detect_languages(
        with_noise, [], {},
        FilterConfig(
            ignore_dirs={".git", "__pycache__", ".venv", "node_modules", "build"}
        ),
        detect_min_files=1,
    )
    assert "python" in r


def test_detect_empty(empty_project):
    r = detect_languages(
        empty_project, [], {},
        FilterConfig(), detect_min_files=1,
    )
    assert r == []