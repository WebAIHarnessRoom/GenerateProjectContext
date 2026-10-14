"""U-PRM-* 参数映射。"""
import pytest

from project_context.params import PARAM_MAP, build_argparser, cli_to_kwargs


def _parse(argv):
    return build_argparser().parse_args(argv)


def test_build_argparser_contains_all():
    p = build_argparser()
    # 抽查关键参数
    ns = p.parse_args(["root", "--max-file-size", "300"])
    assert ns.max_file_size_kb == "300"


def test_cli_scalar_conversion():
    args = _parse(["root", "--max-file-size", "300", "--max-git-commits", "10"])
    kw = cli_to_kwargs(args)
    assert kw["max_file_size_kb"] == 300
    assert kw["max_git_commits"] == 10


def test_cli_append():
    args = _parse(["root", "--exclude", "*.a", "--exclude", "*.b"])
    kw = cli_to_kwargs(args)
    assert kw["exclude"] == ["*.a", "*.b"]


def test_cli_no_git():
    args = _parse(["root", "--no-git"])
    kw = cli_to_kwargs(args)
    assert kw.get("include_git") is False


def test_cli_no_content():
    args = _parse(["root", "--no-content"])
    kw = cli_to_kwargs(args)
    assert kw.get("include_content") is False


def test_cli_no_ast():
    args = _parse(["root", "--no-ast"])
    kw = cli_to_kwargs(args)
    assert kw.get("include_ast") is False


def test_cli_pair():
    args = _parse([
        "root",
        "--language-config", "python=/tmp/py.toml",
        "--language-config", "go=/tmp/go.toml",
    ])
    kw = cli_to_kwargs(args)
    assert "python" in kw["language_configs"]
    assert "go" in kw["language_configs"]


def test_cli_pair_bad_format_ignored():
    args = _parse(["root", "--language-config", "python"])
    kw = cli_to_kwargs(args)
    assert kw.get("language_configs") == {}


def test_cli_empty_kwargs():
    args = _parse(["root"])
    kw = cli_to_kwargs(args)
    assert kw == {}


def test_cli_csv_languages():
    args = _parse(["root", "--languages", "python,go"])
    kw = cli_to_kwargs(args)
    assert kw["languages"] == "python,go"


def test_param_map_unique_dest():
    """除已知的双 flag 情形外，dest 不应重复。"""
    d = {}
    for s in PARAM_MAP:
        d.setdefault(s.dest, []).append(s.cli)
    for dest, clis in d.items():
        if len(clis) > 1:
            # 只允许 inherit_defaults
            assert dest == "inherit_defaults", f"dest 冲突: {dest} {clis}"