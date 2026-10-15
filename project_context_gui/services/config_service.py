"""读写 .project_context/ 下的 TOML 配置文件。"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

try:
    import tomllib  # Python 3.11+
except ImportError:  # pragma: no cover
    import tomli as tomllib  # type: ignore

try:
    import tomlkit  # 可选：保留注释与格式
    HAS_TOMLKIT = True
except ImportError:  # pragma: no cover
    HAS_TOMLKIT = False


DEFAULT_COMMON_TEMPLATE = '''\
# project_context 通用配置
# 参考：README.md「配置系统」章节

inherit_defaults = true

[filter]
# 追加忽略目录（精确匹配目录名）
# ignore_dirs = ["third_party"]
# 追加忽略后缀
# ignore_suffixes = [".bak"]
# 追加忽略文件 glob
# exclude_globs = ["tests/fixtures/*"]

[limits]
# 单文件大小上限（KB）
# max_file_size_kb = 300
# 采集的提交数量
# max_git_commits = 100
# 每条提交列出的文件数
# max_files_per_commit = 30

[features]
# 是否输出源码内容
# include_content = true
# 是否输出 AST 摘要
# include_ast = true
# 是否采集 Git 信息
# include_git = true

[languages]
# 激活语言：auto / all / ["python", "go"]
active = "auto"
# 自动检测阈值
# detect_min_files = 1
'''

LANGUAGE_TEMPLATE = '''\
schema_version = 1
name = "{name}"
inherit_defaults = false

[detect]
suffixes = [".{suffix}"]

[filter]
ignore_dirs = []

[code_langs]
".{suffix}" = "plaintext"

[ast]
parser = "none"
'''


@dataclass
class ConfigFile:
    """一个配置文件的元信息。"""
    path: Path
    rel_path: str          # 相对 .project_context/ 的路径
    kind: str              # "common" | "language"


class ConfigService:
    """管理项目根的 .project_context/ 目录。"""

    def __init__(self, root: str | Path | None = None) -> None:
        self._root: Path | None = None
        if root:
            self.set_root(root)

    def set_root(self, root: str | Path | None) -> None:
        self._root = Path(root) if root else None

    @property
    def root(self) -> Path | None:
        return self._root

    @property
    def config_dir(self) -> Path | None:
        return self._root / ".project_context" if self._root else None

    def exists(self) -> bool:
        d = self.config_dir
        return bool(d and d.is_dir())

    def list_files(self) -> list[ConfigFile]:
        """列出 .project_context/ 下所有已知 TOML。"""
        d = self.config_dir
        if not d or not d.is_dir():
            return []

        files: list[ConfigFile] = []
        common = d / "common.toml"
        if common.is_file():
            files.append(ConfigFile(common, "common.toml", "common"))

        lang_dir = d / "languages"
        if lang_dir.is_dir():
            for p in sorted(lang_dir.glob("*.toml")):
                files.append(
                    ConfigFile(p, f"languages/{p.name}", "language")
                )
        return files

    def read(self, path: Path) -> str:
        return path.read_text(encoding="utf-8")

    def write(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def delete(self, path: Path) -> None:
        if path.is_file():
            path.unlink()

    # -- 模板 -----------------------------------------------------------

    def create_common_template(self) -> ConfigFile:
        d = self.config_dir
        assert d is not None
        p = d / "common.toml"
        self.write(p, DEFAULT_COMMON_TEMPLATE)
        return ConfigFile(p, "common.toml", "common")

    def create_language_template(
        self, name: str, suffix: str | None = None
    ) -> ConfigFile:
        d = self.config_dir
        assert d is not None
        suffix = suffix or name.lower()
        p = d / "languages" / f"{name}.toml"
        self.write(p, LANGUAGE_TEMPLATE.format(name=name, suffix=suffix))
        return ConfigFile(p, f"languages/{p.name}", "language")


# -- 校验 -------------------------------------------------------------------

def validate_toml(text: str) -> tuple[bool, str, int | None]:
    """校验 TOML 文本。

    返回 (是否合法, 错误信息, 错误行号从 1 起)。

    说明：
        tomli / tomllib 对“文档末尾出错”类的错误（如 Unclosed array）
        只给出 "at end of document"，不含行号。此时兜底返回最后一行的
        行号，便于 UI 高亮一个合理位置。
    """
    try:
        tomllib.loads(text)
        return True, "", None
    except Exception as e:  # TOMLDecodeError
        msg = str(e)
        line = _extract_line(msg)
        if line is None:
            line = max(1, text.count("\n") + 1)
        return False, msg, line

def _extract_line(msg: str) -> int | None:
    """从 tomllib / tomli 错误信息里抓行号。

    兼容多种格式：
      - 'Invalid statement (at line 4, column 1)'
      - 'Unclosed array (at line 2, column 5)'
      - '... at row 4'
    若消息为 'at end of document' 之类，返回 None。
    """
    for pat in (
        r"at\s+line\s+(\d+)",
        r"\(line\s+(\d+)",
        r"line\s+(\d+)",
        r"row\s+(\d+)",
    ):
        m = re.search(pat, msg, re.IGNORECASE)
        if m:
            try:
                return int(m.group(1))
            except ValueError:
                continue
    return None


def format_toml(text: str) -> str:
    """用 tomlkit 重新格式化（保留注释）。失败或缺失返回原文。"""
    if not HAS_TOMLKIT:
        return text
    try:
        doc = tomlkit.parse(text)
        return tomlkit.dumps(doc)
    except Exception:
        return text