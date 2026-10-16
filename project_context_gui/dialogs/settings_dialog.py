"""设置对话框。所有字段只在按"确定"后被主窗口读取。"""
from __future__ import annotations

from pathlib import Path

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

from project_context_gui.services.runner_resolver import is_frozen
from project_context_gui.services.settings_service import SettingsService


class SettingsDialog(QDialog):
    """设置对话框。"""

    def __init__(
        self,
        settings: SettingsService,
        parent: QWidget | None = None,
        focus_module_path: bool = False,
    ) -> None:
        super().__init__(parent)
        self._settings = settings
        self.setWindowTitle("设置")
        self.setMinimumWidth(620)
        self._build_ui()
        self._load()
        self._refresh_engine_states()

        if focus_module_path:
            # 焦点放到 Python 模块路径输入框
            self._module_edit.setFocus()

    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        v = QVBoxLayout(self)
        v.setSpacing(12)

        v.addWidget(self._build_engine_group())

        general = QGroupBox("通用")
        gf = QFormLayout(general)
        self._output_name = QLineEdit()
        gf.addRow("默认输出文件名", self._output_name)
        v.addWidget(general)

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

        if is_frozen():
            hint_frozen = QLabel(
                "ℹ 当前 GUI 以打包方式运行（不含 Python 解释器）。\n"
                "Python 模式需要同时指定外部 Python 解释器与 "
                "project_context 模块路径；否则该模式不可用。"
            )
            hint_frozen.setWordWrap(True)
            hint_frozen.setStyleSheet(
                "color:#b07a00; background:#fff8e6; "
                "padding: 6px; border-radius: 4px; font-size: 11px;"
            )
            lay.addWidget(hint_frozen)

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
        self._exe_status.setWordWrap(True)
        exe_form.addRow("", self._exe_status)

        # Python 解释器
        py_row = QHBoxLayout()
        self._python_edit = QLineEdit()
        if is_frozen():
            self._python_edit.setPlaceholderText(
                "打包运行时必填；源码运行时留空用当前解释器"
            )
        else:
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
        exe_form.addRow("Python 解释器", py_wrap)

        self._python_status = QLabel("")
        self._python_status.setStyleSheet("color:#666; font-size: 11px;")
        self._python_status.setWordWrap(True)
        exe_form.addRow("", self._python_status)

        # Python 模块路径
        mod_row = QHBoxLayout()
        self._module_edit = QLineEdit()
        self._module_edit.setPlaceholderText(
            "留空时自动查找程序目录；也可手动指定父目录"
        )
        self._module_edit.textChanged.connect(self._refresh_engine_states)
        mod_row.addWidget(self._module_edit, 1)

        mod_pick = QPushButton("浏览…")
        mod_pick.setFixedWidth(80)
        mod_pick.clicked.connect(self._on_pick_module)
        mod_row.addWidget(mod_pick)

        mod_clear = QPushButton("清空")
        mod_clear.setFixedWidth(60)
        mod_clear.clicked.connect(lambda: self._module_edit.setText(""))
        mod_row.addWidget(mod_clear)

        mod_wrap = QWidget()
        mod_wrap.setLayout(mod_row)

        # 字段标题带副标题
        mod_label = QLabel("Python 模块路径\n(project_context 的父目录)")
        mod_label.setStyleSheet("font-size: 11px;")
        exe_form.addRow(mod_label, mod_wrap)

        self._module_status = QLabel("")
        self._module_status.setStyleSheet("color:#666; font-size: 11px;")
        self._module_status.setWordWrap(True)
        exe_form.addRow("", self._module_status)

        lay.addLayout(exe_form)

        if is_frozen():
            hint_text = (
                "ℹ 自动模式：打包运行时优先 EXE，找不到时回退 Python。"
            )
        else:
            hint_text = (
                "ℹ 自动模式：源码运行时优先 Python，找不到时回退 EXE。"
            )
        hint = QLabel(hint_text)
        hint.setStyleSheet("color:#666; font-size: 11px;")
        hint.setWordWrap(True)
        lay.addWidget(hint)

        for rb in (self._mode_auto, self._mode_python, self._mode_exe):
            rb.toggled.connect(self._refresh_engine_states)

        return box

    def _refresh_engine_states(self) -> None:
        mode = self._current_mode()

        # 启用状态
        if mode == "auto":
            self._exe_edit.setEnabled(False)
            self._python_edit.setEnabled(False)
            self._module_edit.setEnabled(False)
        elif mode == "python":
            self._exe_edit.setEnabled(False)
            self._python_edit.setEnabled(True)
            self._module_edit.setEnabled(True)
        else:  # exe
            self._exe_edit.setEnabled(True)
            self._python_edit.setEnabled(False)
            self._module_edit.setEnabled(False)

        # 用临时 probe 探测
        from project_context_gui.services.runner_resolver import (
            RunnerResolver,
        )

        class _Probe:
            def __init__(self, mode, exe, py, mod):
                self.runner_mode = mode
                self.exe_path = exe
                self.python_executable = py
                self.python_module_path = mod

        probe = _Probe(
            mode,
            self._exe_edit.text().strip(),
            self._python_edit.text().strip(),
            self._module_edit.text().strip(),
        )
        resolver = RunnerResolver(probe)

        ok_exe, msg_exe = resolver.describe_exe_status()
        self._set_status(self._exe_status, ok_exe, msg_exe)

        ok_py, msg_py = resolver.describe_python_status()
        self._set_status(self._python_status, ok_py, msg_py)

        ok_mod, msg_mod = resolver.describe_module_status()
        self._set_status(self._module_status, ok_mod, msg_mod)

    def _set_status(self, label: QLabel, ok: bool, msg: str) -> None:
        label.setText(msg)
        label.setStyleSheet(
            "color:#2d8f4e; font-size: 11px;" if ok
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

        mode = s.runner_mode
        if mode == "python":
            self._mode_python.setChecked(True)
        elif mode == "exe":
            self._mode_exe.setChecked(True)
        else:
            self._mode_auto.setChecked(True)
        self._exe_edit.setText(s.exe_path)
        self._python_edit.setText(s.python_executable)
        self._module_edit.setText(s.python_module_path)

        self._output_name.setText(s.default_output_name)

        idx = self._theme.findData(s.theme)
        if idx < 0:
            idx = 0
        self._theme.setCurrentIndex(idx)
        self._font_size.setValue(s.font_size)

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

    def _on_pick_module(self) -> None:
        start = self._module_edit.text() or str(Path.home())
        path = QFileDialog.getExistingDirectory(
            self, "选择 project_context 的父目录", start
        )
        if path:
            self._module_edit.setText(path)

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

    def python_module_path(self) -> str:
        return self._module_edit.text().strip()

    def theme(self) -> str:
        return self._theme.currentData()

    def font_size(self) -> int:
        return self._font_size.value()

    def restore_last_project(self) -> bool:
        return self._restore_last.isChecked()