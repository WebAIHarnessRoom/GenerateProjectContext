"""U-DMP-* dump-config 输出。"""
from pathlib import Path

from project_context.config.dumper import dump_config_text
from project_context.config.loader import parse_toml
from project_context.config.models import ContextConfig, FilterConfig


def _ctx(**over):
    base = dict(
        root=Path("/x"),
        filters=FilterConfig(
            ignore_dirs={".git", ".venv"},
            ignore_dir_globs=["*.egg-info"],
            ignore_suffixes={".pyc"},
            ignore_file_globs=["*.tmp"],
            exclude_globs=["a/*"],
        ),
        max_file_size_kb=300,
        max_git_commits=20,
        max_files_per_commit=5,
        include_git=False,
        include_ast=True,
        include_content=True,
        no_timestamp=True,
        active_languages=["python", "node"],
        config_sources=["/builtin/common.toml", "/proj/.project_context/common.toml"],
    )
    base.update(over)
    return ContextConfig(**base)


def test_dump_parsable_toml():
    text = dump_config_text(_ctx())
    # 去掉顶部注释后应能被 TOML 解析
    stripped = "\n".join(
        line for line in text.splitlines() if not line.lstrip().startswith("#")
    )
    data = parse_toml_text(stripped)
    assert data["limits"]["max_file_size_kb"] == 300
    assert data["features"]["include_git"] is False
    assert "python" in data["languages"]["active"]


def test_dump_contains_all_filter_fields():
    text = dump_config_text(_ctx())
    for key in (
        "ignore_dirs", "ignore_dir_globs", "ignore_suffixes",
        "ignore_file_globs", "exclude_globs",
    ):
        assert key in text


def test_dump_lists_sources():
    text = dump_config_text(_ctx())
    assert "config_sources" not in text  # 不出现在 [xxx] 段
    assert "/builtin/common.toml" in text
    assert "/proj/.project_context/common.toml" in text


def test_dump_languages_line():
    text = dump_config_text(_ctx())
    assert "['python', 'node']" in text or '"python"' in text


def parse_toml_text(text: str):
    """从字符串解析 TOML，无需落盘。"""
    try:
        import tomllib
        return tomllib.loads(text)
    except ImportError:
        import tomli
        return tomli.loads(text)