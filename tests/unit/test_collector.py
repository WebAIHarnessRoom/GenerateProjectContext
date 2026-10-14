"""U-COL-* 文件遍历。"""
from project_context.config.models import FilterConfig
from project_context.engine.collector import collect_files


def _rel_paths(root, files):
    return {f.relative_to(root).as_posix() for f in files}


def test_collect_basic(py_only):
    fc = FilterConfig(ignore_dirs={".git", "__pycache__"})
    files = collect_files(py_only, fc)
    rels = _rel_paths(py_only, files)
    assert "app.py" in rels
    assert "models.py" in rels


def test_collect_ignores_dirs(with_noise):
    fc = FilterConfig(
        ignore_dirs={".git", "__pycache__", ".venv", "node_modules", "build"}
    )
    files = collect_files(with_noise, fc)
    rels = _rel_paths(with_noise, files)
    assert not any(".venv" in r for r in rels)
    assert not any("__pycache__" in r for r in rels)
    assert not any("node_modules" in r for r in rels)
    assert "src/main.py" in rels


def test_collect_ignores_suffix(with_noise):
    fc = FilterConfig(ignore_suffixes={".pyc"})
    files = collect_files(with_noise, fc)
    rels = _rel_paths(with_noise, files)
    assert not any(r.endswith(".pyc") for r in rels)


def test_collect_exclude_globs(with_noise):
    fc = FilterConfig(ignore_file_globs=["*.js"])
    files = collect_files(with_noise, fc)
    rels = _rel_paths(with_noise, files)
    assert not any(r.endswith(".js") for r in rels)


def test_collect_exclude_globs_relative(with_noise):
    """相对路径匹配。"""
    fc = FilterConfig(exclude_globs=["build/*"])
    files = collect_files(with_noise, fc)
    rels = _rel_paths(with_noise, files)
    assert not any(r.startswith("build/") for r in rels)


def test_collect_output_self_excluded(tmp_path, py_only):
    out = py_only / "app.py"      # 假装输出就是这个文件
    files = collect_files(py_only, FilterConfig(), output_path=out)
    rels = _rel_paths(py_only, files)
    assert "app.py" not in rels


def test_collect_sorted(py_only):
    files = collect_files(py_only, FilterConfig())
    rels = [f.relative_to(py_only).as_posix().lower() for f in files]
    assert rels == sorted(rels)


def test_collect_empty_dir(empty_project):
    files = collect_files(empty_project, FilterConfig())
    assert files == []