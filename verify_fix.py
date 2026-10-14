"""快速核验关键修复点。"""
import sys
from pathlib import Path

# 1. 内置配置目录
from project_context.config.loader import builtin_config_dir, find_language_files
d = builtin_config_dir()
assert d.is_dir(), f"configs 目录不存在: {d}"
langs = sorted(find_language_files([]).keys())
assert "python" in langs, f"内置语言缺失: {langs}"
print("[OK] configs 目录:", d)
print("[OK] 内置语言:", langs)

# 2. UnknownFieldError
from project_context.config.models import common_from_dict
from project_context.errors import UnknownFieldError
try:
    common_from_dict({"xxx": 1})
    raise SystemExit("[FAIL] 未知字段未报错")
except UnknownFieldError:
    print("[OK] UnknownFieldError 正常抛出")

# 3. 内置 common 有 .git
from project_context.config.merger import load_common
cfg, _ = load_common(Path("/tmp"), None, None)
assert ".git" in cfg.filter.ignore_dirs
print("[OK] 内置 common 生效, .git 已忽略")

# 4. AST 空格
from project_context.engine.ast.python import summarize_python
out = summarize_python("def f(*, x: int = 1):\n    pass\n")
line = next(l for l in out if "def" in l)
assert "x: int = 1" in line, f"AST 输出错误: {line}"
print("[OK] AST 签名:", line)

# 5. output=None 返回 str
from project_context import generate_context
import tempfile
with tempfile.TemporaryDirectory() as td:
    p = Path(td) / "p"; p.mkdir()
    (p / "a.py").write_text("x = 1\n", encoding="utf-8")
    md = generate_context(root=p, output=None, no_timestamp=True)
    assert isinstance(md, str), f"output=None 应返回 str，实际: {type(md)}"
    print("[OK] API output=None 返回 str, 长度:", len(md))

print("\n全部核验通过")