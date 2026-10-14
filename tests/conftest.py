"""全局 fixtures —— 动态生成临时项目，避免污染真实仓库。"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest


# 保证可以 import project_context
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


# ---------------------------------------------------------------------------
# 通用工具
# ---------------------------------------------------------------------------

def _make_project(base: Path, structure: dict) -> Path:
    """按 {相对路径: 内容或 None} 生成项目目录树。None 表示目录。"""
    base.mkdir(parents=True, exist_ok=True)
    for rel, content in structure.items():
        p = base / rel
        if content is None:
            p.mkdir(parents=True, exist_ok=True)
        else:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
    return base


def _run(args, cwd):
    subprocess.run(args, cwd=str(cwd), check=True, capture_output=True)


# ---------------------------------------------------------------------------
# 项目 fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def empty_project(tmp_path):
    base = tmp_path / "empty"
    base.mkdir()
    return base


@pytest.fixture
def py_only(tmp_path):
    """纯 Python 项目。"""
    return _make_project(tmp_path / "py_only", {
        "app.py": (
            '"""App module."""\n'
            '\n'
            'def main(a: int = 0, *args, **kwargs) -> None:\n'
            '    """Run app."""\n'
            '    pass\n'
        ),
        "models.py": (
            '"""Data models."""\n'
            '\n'
            'class User:\n'
            '    """User entity."""\n'
            '\n'
            '    def __init__(self, uid: int, name: str = ""):\n'
            '        self.uid = uid\n'
            '        self.name = name\n'
            '\n'
            '    async def fetch(self) -> "User":\n'
            '        return self\n'
        ),
        "pyproject.toml": "[project]\nname = 'demo'\n",
        "README.md": "# demo\n",
    })


@pytest.fixture
def py_node(tmp_path):
    """Python + Node 混合。"""
    return _make_project(tmp_path / "py_node", {
        "backend/app.py": "def x():\n    pass\n",
        "frontend/index.ts": "export const x = 1;\n",
        "frontend/package.json": '{"name":"x"}\n',
        "README.md": "# X\n",
    })


@pytest.fixture
def with_noise(tmp_path):
    """含各种需忽略的目录/文件。"""
    return _make_project(tmp_path / "with_noise", {
        "src/main.py": "print('hi')\n",
        ".venv/lib/foo.py": "print('venv')\n",
        "__pycache__/main.cpython-311.pyc": "fake binary\n",
        "node_modules/x.js": "console.log(1);\n",
        "build/out.txt": "out\n",
        ".git/config": "[core]\n",
    })


@pytest.fixture
def weird_encoding(tmp_path):
    """GBK 文件 + 二进制文件。"""
    base = tmp_path / "weird_encoding"
    base.mkdir()
    (base / "gbk_file.py").write_bytes(
        "# 中文注释\nprint('你好')\n".encode("gbk")
    )
    (base / "binary.bin").write_bytes(b"\x00\x01\x02\x03" * 200)
    return base


@pytest.fixture
def broken_python(tmp_path):
    """含语法错误的 .py。"""
    return _make_project(tmp_path / "broken_python", {
        "bad_syntax.py": "def broken(:\n    pass\n",
        "good.py": "def ok():\n    pass\n",
    })


@pytest.fixture
def custom_lang(tmp_path):
    """自定义语言 mydsl + 项目本地配置。"""
    return _make_project(tmp_path / "custom_lang", {
        "src/hello.mydsl": "hello world\n",
        "src/helper.mydsl": "helper\n",
        ".project_context/languages/mydsl.toml": (
            'schema_version = 1\n'
            'name = "mydsl"\n'
            'inherit_defaults = false\n'
            '\n'
            '[detect]\n'
            'suffixes = [".mydsl"]\n'
            '\n'
            '[filter]\n'
            'ignore_dirs = ["mydsl_cache"]\n'
            '\n'
            '[code_langs]\n'
            '".mydsl" = "plaintext"\n'
            '\n'
            '[ast]\n'
            'parser = "none"\n'
        ),
    })


@pytest.fixture
def with_project_config(tmp_path):
    """项目本地 common.toml 忽略 third_party。"""
    return _make_project(tmp_path / "with_project_config", {
        "src/app.py": "print('hi')\n",
        "third_party/lib.py": "print('vendor')\n",
        ".project_context/common.toml": (
            'inherit_defaults = true\n'
            '\n'
            '[filter]\n'
            'ignore_dirs = ["third_party"]\n'
        ),
    })


@pytest.fixture
def git_repo(tmp_path):
    """已初始化并有 1 条提交的 git 仓库。"""
    if shutil.which("git") is None:
        pytest.skip("git 不可用")
    base = _make_project(tmp_path / "git_repo", {
        "app.py": "print('hi')\n",
        "README.md": "# git demo\n",
    })
    _run(["git", "init", "-q"], cwd=base)
    _run(["git", "config", "user.email", "t@t"], cwd=base)
    _run(["git", "config", "user.name", "T"], cwd=base)
    _run(["git", "add", "."], cwd=base)
    _run(["git", "commit", "-q", "-m", "init"], cwd=base)
    return base


# ---------------------------------------------------------------------------
# 公共辅助：获取"内置语言目录"
# ---------------------------------------------------------------------------

@pytest.fixture
def builtin_langs_dir():
    from project_context.config.loader import builtin_config_dir
    return builtin_config_dir() / "languages"