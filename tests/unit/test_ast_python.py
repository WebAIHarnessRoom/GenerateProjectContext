"""U-AST-* Python AST 摘要。"""
from project_context.engine.ast.python import summarize_python


def test_function_signature():
    src = "def f(a: int, b: str = 'x') -> bool:\n    pass\n"
    out = summarize_python(src)
    assert any("def" in line and "f(" in line for line in out)
    assert any("a: int" in line for line in out)
    assert any("b: str = 'x'" in line for line in out)
    assert any("-> bool" in line for line in out)


def test_class_and_methods():
    src = (
        "class User:\n"
        "    def __init__(self, uid: int):\n"
        "        self.uid = uid\n"
        "    async def fetch(self):\n"
        "        return self\n"
    )
    out = summarize_python(src)
    assert any("class" in l and "User" in l for l in out)
    assert any("def" in l and "__init__" in l for l in out)
    assert any("async def" in l and "fetch" in l for l in out)


def test_decorator_shown():
    src = (
        "@staticmethod\n"
        "def f():\n"
        "    pass\n"
    )
    out = summarize_python(src)
    assert any("@staticmethod" in l for l in out)


def test_docstring_first_line():
    src = (
        "def f():\n"
        '    """This is doc."""\n'
        "    pass\n"
    )
    out = summarize_python(src)
    assert any("This is doc." in l for l in out)


def test_docstring_long_truncated():
    long_doc = "A" * 200
    src = f'def f():\n    """{long_doc}"""\n    pass\n'
    out = summarize_python(src)
    line = next(l for l in out if "def" in l)
    assert line.endswith("...")


def test_varargs_kwargs():
    src = "def f(*args, **kwargs):\n    pass\n"
    out = summarize_python(src)
    line = next(l for l in out if "def" in l)
    assert "*args" in line
    assert "**kwargs" in line


def test_kwonly():
    src = "def f(*, x: int = 1):\n    pass\n"
    out = summarize_python(src)
    line = next(l for l in out if "def" in l)
    assert "*" in line
    assert "x: int = 1" in line


def test_syntax_error_returns_warning():
    out = summarize_python("def broken(:\n")
    assert len(out) == 1
    assert "语法解析失败" in out[0]


def test_empty_file():
    assert summarize_python("") == []


def test_nested_class():
    src = (
        "class Outer:\n"
        "    class Inner:\n"
        "        pass\n"
    )
    out = summarize_python(src)
    # 应包含 Outer 与 Inner，且 Inner 缩进一级
    assert any("Outer" in l for l in out)
    inner_line = next(l for l in out if "Inner" in l)
    assert inner_line.startswith("  ")