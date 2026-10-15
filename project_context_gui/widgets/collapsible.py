"""可折叠区块（高级项）。"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QToolButton,
    QVBoxLayout,
    QWidget,
)


class Collapsible(QWidget):
    def __init__(
        self,
        title: str,
        expanded: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._toggle = QToolButton()
        self._toggle.setText(title)
        self._toggle.setCheckable(True)
        self._toggle.setChecked(expanded)
        self._toggle.setStyleSheet(
            "QToolButton { border: none; font-weight: bold; padding: 4px; }"
        )
        self._toggle.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self._toggle.setArrowType(
            Qt.DownArrow if expanded else Qt.RightArrow
        )

        self._content = QFrame()
        self._content.setFrameShape(QFrame.NoFrame)
        self._content.setVisible(expanded)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(self._toggle)
        lay.addWidget(self._content)

        self._toggle.toggled.connect(self._on_toggle)

    def content_layout(self) -> QVBoxLayout:
        if self._content.layout() is None:
            inner = QVBoxLayout(self._content)
            inner.setContentsMargins(12, 4, 4, 8)
            return inner
        return self._content.layout()  # type: ignore[return-value]

    def _on_toggle(self, checked: bool) -> None:
        self._content.setVisible(checked)
        self._toggle.setArrowType(Qt.DownArrow if checked else Qt.RightArrow)