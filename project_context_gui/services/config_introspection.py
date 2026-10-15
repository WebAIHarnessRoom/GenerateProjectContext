"""配置加载内省：定位三层配置的实际路径与内容。"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore


@dataclass
class LayerInfo:
    """一层配置的实况。"""
    name: str                    # "内置" / "项目配置" / "本次追加"
    marker: str                  # "①" / "②" / "③"
    description: str             # 一句话说明
    paths: list[Path] = field(default_factory=list)
    files: list[Path] = field(default_factory=list)
    rules_count: int = 0
    available: bool = True
    note: str = ""


@dataclass
class IntrospectionResult:
    """三层配置的总览。"""
    layer_builtin: LayerInfo
    layer_project: LayerInfo
    layer_session: LayerInfo

    def all_layers(self) -> list[LayerInfo]:
        return [self.layer_builtin, self.layer_project, self.layer_session]


def locate_builtin_config_dir(
    mode: str = "python",
    exe_path: str = "",
    python_path: str = "",
) -> Path | None:
    """定位工具内置配置目录。

    优先顺序：
      - exe 模式：exe 同目录下的 project_context/configs/
      - python 模式：site-packages/project_context/configs/
    """
    if mode == "exe" and exe_path:
        exe_dir = Path(exe_path).parent
        for candidate in (
            exe_dir / "project_context" / "configs",
            exe_dir / "_internal" / "project_context" / "configs",
        ):
            if candidate.is_dir():
                return candidate

    # Python：从 project_context 包的位置推
    try:
        import project_context
        pkg_dir = Path(project_context.__file__).parent
        cfg = pkg_dir / "configs"
        if cfg.is_dir():
            return cfg
    except ImportError:
        pass

    return None


def inspect_builtin(
    mode: str = "python",
    exe_path: str = "",
    python_path: str = "",
) -> LayerInfo:
    info = LayerInfo(
        name="工具内置规则",
        marker="①",
        description="工具自带，随分发包提供，不可修改",
    )

    cfg_dir = locate_builtin_config_dir(mode, exe_path, python_path)
    if cfg_dir is None:
        info.available = False
        info.note = "未找到内置配置目录（可能已被裁剪）"
        return info

    info.paths = [cfg_dir]
    common = cfg_dir / "common.toml"
    if common.is_file():
        info.files.append(common)
    lang_dir = cfg_dir / "languages"
    if lang_dir.is_dir():
        info.files.extend(sorted(lang_dir.glob("*.toml")))

    info.rules_count = _count_rules(info.files)
    return info


def inspect_project(root: str | Path | None) -> LayerInfo:
    info = LayerInfo(
        name="项目配置",
        marker="②",
        description="项目根下的 .project_context/ 目录",
    )
    if not root:
        info.available = False
        info.note = "尚未选择项目"
        return info

    root_path = Path(root)
    if not root_path.is_dir():
        info.available = False
        info.note = f"项目路径不存在：{root_path}"
        return info

    cfg_dir = root_path / ".project_context"
    if not cfg_dir.is_dir():
        info.available = False
        info.note = "项目未提供 .project_context/，将只用内置规则"
        return info

    info.paths = [cfg_dir]
    common = cfg_dir / "common.toml"
    if common.is_file():
        info.files.append(common)
    lang_dir = cfg_dir / "languages"
    if lang_dir.is_dir():
        info.files.extend(sorted(lang_dir.glob("*.toml")))

    if not info.files:
        info.available = False
        info.note = ".project_context/ 目录存在但没有 .toml 文件"
    else:
        info.rules_count = _count_rules(info.files)

    return info


def inspect_session(run_state) -> LayerInfo:
    info = LayerInfo(
        name="本次追加",
        marker="③",
        description="在“运行配置”Tab 的过滤面板里输入，仅本次运行生效",
    )
    if run_state is None:
        info.available = False
        info.note = "尚未配置"
        return info

    count = (
        len(run_state.exclude_globs)
        + len(run_state.exclude_dirs)
        + len(run_state.exclude_dir_globs)
        + len(run_state.exclude_suffixes)
    )
    info.rules_count = count
    if run_state.no_inherit_defaults:
        info.note = "已勾选“忽略项目配置”，项目配置层将被跳过"
    return info


def introspect(
    root: str | Path | None,
    run_state=None,
    mode: str = "python",
    exe_path: str = "",
    python_path: str = "",
) -> IntrospectionResult:
    """一次性生成三层配置实况。"""
    return IntrospectionResult(
        layer_builtin=inspect_builtin(mode, exe_path, python_path),
        layer_project=inspect_project(root),
        layer_session=inspect_session(run_state),
    )


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------

def _count_rules(files: list[Path]) -> int:
    """统计一组 TOML 里的排除规则条数。"""
    total = 0
    for f in files:
        try:
            data = tomllib.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        total += _count_in_dict(data)
    return total


def _count_in_dict(data: dict) -> int:
    total = 0
    filter_section = data.get("filter")
    if isinstance(filter_section, dict):
        for key in (
            "ignore_dirs", "ignore_dir_globs", "ignore_suffixes",
            "ignore_file_globs", "exclude_globs",
        ):
            v = filter_section.get(key)
            if isinstance(v, list):
                total += len(v)
    return total