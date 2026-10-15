"""设置对话框。所有字段只在按"确定"后被主窗口读取。"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
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
        self.setMinimumWidth(500)
        self._build_ui()
        self._load()

    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        v = QVBoxLayout(self)
        v.setSpacing(12)

        # 通用
        general = QGroupBox("通用")
        gf = QFormLayout(general)

        self._output_name = QLineEdit()
        gf.addRow("默认输出文件名", self._output_name)

        py_row = QHBoxLayout()
        self._python_edit = QLineEdit()
        self._python_edit.setPlaceholderText(
            "留空使用当前 GUI 的 Python 解释器"
        )
        self._python_edit.setReadOnly(True)
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
        gf.addRow("Python 解释器", py_wrap)

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

    def _load(self) -> None:
        s = self._settings
        self._output_name.setText(s.default_output_name)
        self._python_edit.setText(s.python_executable)

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

    # ---- 取值 ----

    def default_output_name(self) -> str:
        v = self._output_name.text().strip()
        return v or "PROJECT_CONTEXT.md"

    def python_executable(self) -> str:
        return self._python_edit.text().strip()

    def theme(self) -> str:
        return self._theme.currentData()

    def font_size(self) -> int:
        return self._font_size.value()

    def restore_last_project(self) -> bool:
        return self._restore_last.isChecked()