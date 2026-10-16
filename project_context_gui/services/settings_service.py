"""基于 QSettings 的用户偏好。"""
from __future__ import annotations

from PySide6.QtCore import QSettings

_ORG = "project_context"
_APP = "gui"

_DEFAULT_OUTPUT_NAME = "PROJECT_CONTEXT.md"
_DEFAULT_THEME = "system"
_DEFAULT_FONT_SIZE = 10


class SettingsService:
    def __init__(self) -> None:
        self._s = QSettings(_ORG, _APP)

    # ---- 输出 ----

    @property
    def default_output_name(self) -> str:
        return self._s.value("output/name", _DEFAULT_OUTPUT_NAME, type=str)

    @default_output_name.setter
    def default_output_name(self, v: str) -> None:
        self._s.setValue("output/name", v)

    # ---- 执行引擎 ----

    @property
    def runner_mode(self) -> str:
        """auto / python / exe"""
        return self._s.value("runtime/mode", "auto", type=str)

    @runner_mode.setter
    def runner_mode(self, v: str) -> None:
        self._s.setValue("runtime/mode", v)

    @property
    def exe_path(self) -> str:
        return self._s.value("runtime/exe_path", "", type=str)

    @exe_path.setter
    def exe_path(self, v: str) -> None:
        self._s.setValue("runtime/exe_path", v)

    @property
    def python_executable(self) -> str:
        return self._s.value("runtime/python", "", type=str)

    @python_executable.setter
    def python_executable(self, v: str) -> None:
        self._s.setValue("runtime/python", v)

    @property
    def python_module_path(self) -> str:
        """project_context 的父目录。留空表示自动探测程序目录。"""
        return self._s.value("runtime/python_module_path", "", type=str)

    @python_module_path.setter
    def python_module_path(self, v: str) -> None:
        self._s.setValue("runtime/python_module_path", v)

    # ---- 外观 ----

    @property
    def theme(self) -> str:
        return self._s.value("ui/theme", _DEFAULT_THEME, type=str)

    @theme.setter
    def theme(self, v: str) -> None:
        self._s.setValue("ui/theme", v)

    @property
    def font_size(self) -> int:
        return self._s.value("ui/font_size", _DEFAULT_FONT_SIZE, type=int)

    @font_size.setter
    def font_size(self, v: int) -> None:
        self._s.setValue("ui/font_size", int(v))

    # ---- 行为 ----

    @property
    def restore_last_project(self) -> bool:
        return self._s.value("behavior/restore_last", True, type=bool)

    @restore_last_project.setter
    def restore_last_project(self, v: bool) -> None:
        self._s.setValue("behavior/restore_last", bool(v))

    @property
    def last_project(self) -> str:
        return self._s.value("behavior/last_project", "", type=str)

    @last_project.setter
    def last_project(self, v: str) -> None:
        self._s.setValue("behavior/last_project", v)

    # ---- 最近项目 ----

    @property
    def recent_projects(self) -> list:
        v = self._s.value("recent/projects", [], type=list)
        return [str(x) for x in v] if v else []

    def push_recent_project(self, path: str, limit: int = 10) -> None:
        items = [p for p in self.recent_projects if p != path]
        items.insert(0, path)
        self._s.setValue("recent/projects", items[:limit])

    def clear_recent_projects(self) -> None:
        self._s.setValue("recent/projects", [])

    # ---- 窗口几何 ----

    @property
    def window_geometry(self):
        return self._s.value("ui/geometry", None)

    @window_geometry.setter
    def window_geometry(self, v) -> None:
        self._s.setValue("ui/geometry", v)

    @property
    def window_state(self):
        return self._s.value("ui/window_state", None)

    @window_state.setter
    def window_state(self, v) -> None:
        self._s.setValue("ui/window_state", v)