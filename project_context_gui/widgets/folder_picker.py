"""只读路径输入框 + 浏览按钮。支持拖拽。"""
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


class FolderPicker(QWidget):
    pathChanged = Signal(str)

    def __init__(
        self,
        placeholder: str = "选择一个文件夹…",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._edit = QLineEdit()
        self._edit.setPlaceholderText(placeholder)
        self._edit.setReadOnly(True)
        self._edit.setAcceptDrops(True)

        self._btn = QPushButton("浏览…")
        self._btn.setFixedWidth(80)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self._edit, 1)
        lay.addWidget(self._btn)

        self._btn.clicked.connect(self._on_browse)
        self._edit.textChanged.connect(self.pathChanged.emit)

        # 拖拽
        self._edit.dragEnterEvent = self._drag_enter  # type: ignore[assignment]
        self._edit.dropEvent = self._drop            # type: ignore[assignment]

    # -- API -------------------------------------------------------------

    def path(self) -> str:
        return self._edit.text()

    def set_path(self, value: str) -> None:
        self._edit.setText(value or "")

    # -- internals -------------------------------------------------------

    def _on_browse(self) -> None:
        start = self._edit.text() or str(Path.home())
        chosen = QFileDialog.getExistingDirectory(self, "选择项目文件夹", start)
        if chosen:
            self._edit.setText(chosen)

    def _drag_enter(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def _drop(self, event) -> None:
        urls = event.mimeData().urls()
        if not urls:
            return
        p = Path(urls[0].toLocalFile())
        if p.is_dir():
            self._edit.setText(str(p))
            event.acceptProposedAction()