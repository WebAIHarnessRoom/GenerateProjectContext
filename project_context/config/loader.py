"""TOML 加载 + 校验。"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from ..errors import ConfigError

try:  # Python 3.11+
    import tomllib as _toml
except ImportError:  # 3.9 / 3.10
    try:
        import tomli as _toml  # type: ignore
    except ImportError:  # pragma: no cover
        _toml = None


def parse_toml(path: Path) -> Dict[str, Any]:
    if _toml is None:
        raise ConfigError(
            "读取 TOML 需要 Python 3.11+ 内置 tomllib，或安装 tomli: pip install tomli"
        )
    try:
        return _toml.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ConfigError(f"配置文件不存在: {path}")
    except IsADirectoryError:
        raise ConfigError(f"期望文件，得到目录: {path}")
    except Exception as exc:
        raise ConfigError(f"解析 TOML 失败 {path}: {exc}")


def builtin_config_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "configs"


def find_language_files(extra_dirs: List[Path]) -> Dict[str, Path]:
    """返回 {lang_name: path}，后者覆盖前者（同一 name 时后加入的优先）。"""
    result: Dict[str, Path] = {}

    # 内置
    builtin_lang_dir = builtin_config_dir() / "languages"
    if builtin_lang_dir.is_dir():
        for p in sorted(builtin_lang_dir.glob("*.toml")):
            result[p.stem] = p

    # 额外目录
    for d in extra_dirs:
        if not d or not Path(d).is_dir():
            continue
        for p in sorted(Path(d).glob("*.toml")):
            result[p.stem] = p

    return result


def find_language_by_name(name: str, extra_dirs: List[Path]) -> Optional[Path]:
    for d in reversed(extra_dirs):  # 后加入的优先
        if not d or not Path(d).is_dir():
            continue
        p = Path(d) / f"{name}.toml"
        if p.is_file():
            return p
    p = builtin_config_dir() / "languages" / f"{name}.toml"
    return p if p.is_file() else None