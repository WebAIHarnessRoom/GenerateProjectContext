"""异常层次。"""
from __future__ import annotations

from typing import Iterable


class ProjectContextError(Exception):
    """所有异常的基类。"""


class ConfigError(ProjectContextError):
    """配置相关错误。"""


class LanguageNotFoundError(ConfigError):
    def __init__(self, name: str, available: Iterable[str]):
        self.name = name
        self.available = sorted(set(available))
        msg = (
            f"未找到语言配置: {name!r}\n"
            f"  可用语言: {', '.join(self.available) or '(无)'}\n"
            f"  提示: 自定义语言请放到 <root>/.project_context/languages/{name}.toml，"
            f"或用 --language-dir 指定目录。"
        )
        super().__init__(msg)


class UnknownFieldError(ConfigError):
    def __init__(self, source: str, path: str, field: str, allowed: Iterable[str]):
        allowed_s = ", ".join(sorted(allowed)) or "(无)"
        super().__init__(
            f"[{source}] 未知字段: {path}.{field}\n"
            f"  可用字段: {allowed_s}"
        )


class ValidationError(ConfigError):
    pass


class FileReadError(ProjectContextError):
    pass