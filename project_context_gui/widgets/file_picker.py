"""只读文件路径输入框 + 选择按钮（保存/打开两种模式）。"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QWidget,
)


class FilePicker(QWidget):
    pathChanged = Signal(str)

    def __init__(
        self,
        mode: str = "save",                 # "save" | "open"
        filter_: str = "Markdown (*.md);;所有文件 (*)",
        placeholder: str = "选择文件…",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._mode = mode
        self._filter = filter_

        self._edit = QLineEdit()
        self._edit.setPlaceholderText(placeholder)
        self._edit.setReadOnly(True)

        self._btn = QPushButton("另存为…" if mode == "save" else "浏览…")
        self._btn.setFixedWidth(90)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self._edit, 1)
        lay.addWidget(self._btn)

        self._btn.clicked.connect(self._on_browse)
        self._edit.textChanged.connect(self.pathChanged.emit)

    def path(self) -> str:
        return self._edit.text()

    def set_path(self, value: str) -> None:
        self._edit.setText(value or "")

    def _on_browse(self) -> None:
        start = self._edit.text() or str(Path.home())
        if self._mode == "save":
            chosen, _ = QFileDialog.getSaveFileName(
                self, "选择输出文件", start, self._filter
            )
        else:
            chosen, _ = QFileDialog.getOpenFileName(
                self, "选择文件", start, self._filter
            )
        if chosen:
            self._edit.setText(chosen)