"""设置对话框。所有字段只在按"确定"后被主窗口读取。"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from project_context_gui.services.settings_service import SettingsService


class SettingsDialog(QDialog):
    """设置对话框。"""

    def __init__(
        self,
        settings: SettingsService,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._settings = settings
        self.setWindowTitle("设置")
        self.setMinimumWidth(560)
        self._build_ui()
        self._load()
        self._refresh_engine_states()

    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        v = QVBoxLayout(self)
        v.setSpacing(12)

        # 执行引擎
        v.addWidget(self._build_engine_group())

        # 通用
        general = QGroupBox("通用")
        gf = QFormLayout(general)

        self._output_name = QLineEdit()
        gf.addRow("默认输出文件名", self._output_name)

        v.addWidget(general)

        # 外观
        appearance = QGroupBox("外观")
        af = QFormLayout(appearance)

        self._theme = QComboBox()
        self._theme.addItem("跟随系统", "system")
        self._theme.addItem("浅色", "light")
        self._theme.addItem("深色", "dark")
        af.addRow("主题", self._theme)

        self._font_size = QSpinBox()
        self._font_size.setRange(8, 20)
        self._font_size.setSuffix(" pt")
        af.addRow("字体大小", self._font_size)

        v.addWidget(appearance)

        # 行为
        behavior = QGroupBox("行为")
        bf = QFormLayout(behavior)

        self._restore_last = QCheckBox("启动时恢复上次打开的项目")
        bf.addRow("", self._restore_last)

        v.addWidget(behavior)

        v.addStretch(1)

        bb = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        v.addWidget(bb)

    # ------------------------------------------------------------------
    # 执行引擎分组
    # ------------------------------------------------------------------

    def _build_engine_group(self) -> QGroupBox:
        box = QGroupBox("执行引擎")
        lay = QVBoxLayout(box)

        # 模式选择
        mode_row = QHBoxLayout()
        self._mode_auto = QRadioButton("自动")
        self._mode_python = QRadioButton("Python")
        self._mode_exe = QRadioButton("EXE")
        self._mode_group = QButtonGroup(self)
        for rb in (self._mode_auto, self._mode_python, self._mode_exe):
            self._mode_group.addButton(rb)
            mode_row.addWidget(rb)
        mode_row.addStretch(1)
        lay.addLayout(mode_row)

        # EXE 路径
        exe_form = QFormLayout()
        exe_row = QHBoxLayout()
        self._exe_edit = QLineEdit()
        self._exe_edit.setPlaceholderText(
            "留空时自动查找 PATH 与 GUI 同目录"
        )
        self._exe_edit.textChanged.connect(self._refresh_engine_states)
        exe_row.addWidget(self._exe_edit, 1)
        exe_btn = QPushButton("浏览…")
        exe_btn.setFixedWidth(80)
        exe_btn.clicked.connect(self._on_pick_exe)
        exe_row.addWidget(exe_btn)
        exe_wrap = QWidget()
        exe_wrap.setLayout(exe_row)
        exe_form.addRow("EXE 路径", exe_wrap)

        self._exe_status = QLabel("")
        self._exe_status.setStyleSheet("color:#666; font-size: 11px;")
        exe_form.addRow("", self._exe_status)

        # Python 路径
        py_row = QHBoxLayout()
        self._python_edit = QLineEdit()
        self._python_edit.setPlaceholderText(
            "留空使用当前 GUI 的 Python 解释器"
        )
        self._python_edit.textChanged.connect(self._refresh_engine_states)
        py_row.addWidget(self._python_edit, 1)

        pick_btn = QPushButton("浏览…")
        pick_btn.setFixedWidth(80)
        pick_btn.clicked.connect(self._on_pick_python)
        py_row.addWidget(pick_btn)

        clear_btn = QPushButton("清空")
        clear_btn.setFixedWidth(60)
        clear_btn.clicked.connect(lambda: self._python_edit.setText(""))
        py_row.addWidget(clear_btn)

        py_wrap = QWidget()
        py_wrap.setLayout(py_row)
        exe_form.addRow("Python", py_wrap)

        self._python_status = QLabel("")
        self._python_status.setStyleSheet("color:#666; font-size: 11px;")
        exe_form.addRow("", self._python_status)

        lay.addLayout(exe_form)

        hint = QLabel(
            "ℹ 自动模式优先使用 EXE，找不到时回退到 Python。"
        )
        hint.setStyleSheet("color:#666; font-size: 11px;")
        lay.addWidget(hint)

        # 模式切换时联动启用状态
        for rb in (self._mode_auto, self._mode_python, self._mode_exe):
            rb.toggled.connect(self._refresh_engine_states)

        return box

    def _refresh_engine_states(self) -> None:
        mode = self._current_mode()

        # 启用状态
        if mode == "auto":
            self._exe_edit.setEnabled(False)
            self._python_edit.setEnabled(False)
        elif mode == "python":
            self._exe_edit.setEnabled(False)
            self._python_edit.setEnabled(True)
        else:  # exe
            self._exe_edit.setEnabled(True)
            self._python_edit.setEnabled(False)

        # 状态行
        # 用临时 SettingsService 覆写路径，调用 resolver 探测
        from project_context_gui.services.runner_resolver import (
            RunnerResolver,
        )

        # 构造一个只用于探测的临时 settings（不写盘）
        class _Probe:
            def __init__(self, mode, exe, py):
                self.runner_mode = mode
                self.exe_path = exe
                self.python_executable = py

        probe = _Probe(
            mode,
            self._exe_edit.text().strip(),
            self._python_edit.text().strip(),
        )
        resolver = RunnerResolver(probe)

        ok_exe, msg_exe = resolver.describe_exe_status()
        self._exe_status.setText(msg_exe)
        self._exe_status.setStyleSheet(
            "color:#2d8f4e; font-size: 11px;" if ok_exe
            else "color:#b07a00; font-size: 11px;"
        )

        ok_py, msg_py = resolver.describe_python_status()
        self._python_status.setText(msg_py)
        self._python_status.setStyleSheet(
            "color:#2d8f4e; font-size: 11px;" if ok_py
            else "color:#b07a00; font-size: 11px;"
        )

    def _current_mode(self) -> str:
        if self._mode_auto.isChecked():
            return "auto"
        if self._mode_python.isChecked():
            return "python"
        return "exe"

    # ------------------------------------------------------------------
    # 加载 / 取值
    # ------------------------------------------------------------------

    def _load(self) -> None:
        s = self._settings

        # 执行引擎
        mode = s.runner_mode
        if mode == "python":
            self._mode_python.setChecked(True)
        elif mode == "exe":
            self._mode_exe.setChecked(True)
        else:
            self._mode_auto.setChecked(True)
        self._exe_edit.setText(s.exe_path)
        self._python_edit.setText(s.python_executable)

        # 通用
        self._output_name.setText(s.default_output_name)

        # 外观
        idx = self._theme.findData(s.theme)
        if idx < 0:
            idx = 0
        self._theme.setCurrentIndex(idx)
        self._font_size.setValue(s.font_size)

        # 行为
        self._restore_last.setChecked(s.restore_last_project)

    def _on_pick_python(self) -> None:
        start = self._python_edit.text() or str(Path.home())
        path, _ = QFileDialog.getOpenFileName(
            self, "选择 Python 解释器", start,
            "Python (python*);;所有文件 (*)",
        )
        if path:
            self._python_edit.setText(path)

    def _on_pick_exe(self) -> None:
        start = self._exe_edit.text() or str(Path.home())
        path, _ = QFileDialog.getOpenFileName(
            self, "选择 generate-project-context.exe", start,
            "可执行文件 (*.exe);;所有文件 (*)",
        )
        if path:
            self._exe_edit.setText(path)

    # ---- 取值 ----

    def default_output_name(self) -> str:
        v = self._output_name.text().strip()
        return v or "PROJECT_CONTEXT.md"

    def runner_mode(self) -> str:
        return self._current_mode()

    def exe_path(self) -> str:
        return self._exe_edit.text().strip()

    def python_executable(self) -> str:
        return self._python_edit.text().strip()

    def theme(self) -> str:
        return self._theme.currentData()

    def font_size(self) -> int:
        return self._font_size.value()

    def restore_last_project(self) -> bool:
        return self._restore_last.isChecked()