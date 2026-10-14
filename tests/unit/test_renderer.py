"""U-RND-* 渲染。"""
from pathlib import Path

from project_context.config.models import ContextConfig, FilterConfig
from project_context.engine.renderer import (
    build_tree_text,
    code_block,
    guess_lang,
)


def test_code_block_normal():
    s = code_block("a\nb", "python")
    assert s.startswith("```python\n")
    assert s.endswith("\n```\n")


def test_code_block_fence_escape():
    """内容里已有 ``` 时，围栏需要加长。"""
    text = "some ``` inside"
    s = code_block(text, "text")
    assert s.startswith("````text\n")
    assert s.endswith("\n````\n")


def test_guess_lang_by_suffix():
    ctx = ContextConfig(
        root=Path("/x"),
        filters=FilterConfig(),
        code_lang_map={".py": "python", ".ts": "typescript"},
    )
    assert guess_lang(Path("a.py"), ctx) == "python"
    assert guess_lang(Path("a.ts"), ctx) == "typescript"


def test_guess_lang_by_name():
    ctx = ContextConfig(
        root=Path("/x"),
        filters=FilterConfig(),
        code_lang_name_map={"Makefile": "makefile"},
    )
    assert guess_lang(Path("Makefile"), ctx) == "makefile"


def test_guess_lang_unknown():
    ctx = ContextConfig(root=Path("/x"), filters=FilterConfig())
    assert guess_lang(Path("a.xyz"), ctx) == ""


def test_build_tree_single_file(tmp_path):
    f = tmp_path / "a.py"
    f.write_text("x")
    text = build_tree_text(tmp_path, [f])
    assert tmp_path.name + "/" in text
    assert "a.py" in text


def test_build_tree_nested(tmp_path):
    d = tmp_path / "src"
    d.mkdir()
    f = d / "a.py"
    f.write_text("x")
    text = build_tree_text(tmp_path, [f])
    assert "src/" in text
    assert "a.py" in text

# ---------------------------------------------------------------------------
# render_document 端到端渲染
# ---------------------------------------------------------------------------

from project_context.config.models import ContextConfig
from project_context.engine.renderer import render_document


def _make_ctx(root, **over):
    base = dict(
        root=root,
        filters=FilterConfig(ignore_dirs={".git", "__pycache__"}),
        code_lang_map={".py": "python", ".md": "markdown"},
        code_lang_name_map={"Makefile": "makefile"},
        ast_parsers={"python": "python"},
    )
    base.update(over)
    return ContextConfig(**base)


def test_render_document_full(tmp_path):
    (tmp_path / "a.py").write_text(
        'def hello(name: str = "x") -> None:\n    """Say hi."""\n',
        encoding="utf-8",
    )
    (tmp_path / "README.md").write_text("# hi\n", encoding="utf-8")
    ctx = _make_ctx(tmp_path, include_git=False)
    md = render_document(tmp_path, ctx)
    assert "# 项目上下文文档" in md
    assert "## 1. 项目概览" in md
    assert "## 2. 目录结构" in md
    assert "## 3. 代码结构总览" in md
    assert "## 4. 源码与配置文件内容" in md
    assert "## 5. Git 提交历史" not in md          # 无 git
    assert "def hello" in md
    assert "Say hi." in md


def test_render_document_no_ast(tmp_path):
    (tmp_path / "a.py").write_text("def f():\n    pass\n", encoding="utf-8")
    ctx = _make_ctx(tmp_path, include_ast=False, include_git=False)
    md = render_document(tmp_path, ctx)
    assert "## 3. 代码结构总览" not in md


def test_render_document_no_content(tmp_path):
    (tmp_path / "a.py").write_text("def f():\n    pass\n", encoding="utf-8")
    ctx = _make_ctx(tmp_path, include_content=False, include_git=False)
    md = render_document(tmp_path, ctx)
    assert "## 4. 源码与配置文件内容" not in md


def test_render_document_no_timestamp(tmp_path):
    (tmp_path / "a.py").write_text("x = 1\n", encoding="utf-8")
    ctx = _make_ctx(tmp_path, no_timestamp=True, include_git=False)
    md = render_document(tmp_path, ctx)
    assert "生成时间" not in md


def test_render_document_with_git(tmp_path):
    import shutil, subprocess
    if shutil.which("git") is None:
        import pytest
        pytest.skip("git 不可用")
    (tmp_path / "a.py").write_text("x = 1\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "init", "-q"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.email", "t@t"],
                   check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "T"],
                   check=True)
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-q", "-m", "init"],
                   check=True)

    ctx = _make_ctx(tmp_path, include_git=True)
    md = render_document(tmp_path, ctx)
    assert "## 5. Git 提交历史" in md
    assert "### 5.1 提交概览" in md
    assert "### 5.2 提交详情" in md


def test_render_document_syntax_error(tmp_path):
    (tmp_path / "bad.py").write_text("def broken(:\n", encoding="utf-8")
    ctx = _make_ctx(tmp_path, include_git=False)
    md = render_document(tmp_path, ctx)
    assert "语法解析失败" in md


def test_render_document_truncation_warning(tmp_path):
    (tmp_path / "big.py").write_text("x = 1\n" * 10000, encoding="utf-8")
    ctx = _make_ctx(tmp_path, max_file_size_kb=1, include_git=False)
    md = render_document(tmp_path, ctx)
    assert "⚠️" in md or "截断" in md