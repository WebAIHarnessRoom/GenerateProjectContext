"""project_context —— 项目上下文文档生成器。"""
from .api import generate_context
from .config.models import ContextConfig
from .config.resolver import list_available_languages
from .errors import (
    ConfigError,
    FileReadError,
    LanguageNotFoundError,
    ProjectContextError,
    UnknownFieldError,
    ValidationError,
)

__version__ = "0.1.0"

__all__ = [
    "generate_context",
    "ContextConfig",
    "list_available_languages",
    "ProjectContextError",
    "ConfigError",
    "LanguageNotFoundError",
    "UnknownFieldError",
    "ValidationError",
    "FileReadError",
]