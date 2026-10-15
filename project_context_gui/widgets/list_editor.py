"""可重复字符串参数编辑器：输入框 + 添加 + 列表 + 删除。"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class ListEditor(QWidget):
    """一行输入 + 一个列表，用于 --exclude/--exclude-dir 等。"""

    changed = Signal()

    def __init__(
        self,
        title: str,
        placeholder: str = "",
        hint: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._title = title

        # 标题行：标题 + 可选灰字提示
        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        self._label = QLabel(title)
        title_row.addWidget(self._label)
        if hint:
            h = QLabel(hint)
            h.setStyleSheet("color:#888; font-size: 11px;")
            title_row.addWidget(h)
        title_row.addStretch(1)

        self._edit = QLineEdit()
        self._edit.setPlaceholderText(placeholder or f"输入 {title} 后回车")
        self._add_btn = QPushButton("添加")
        self._add_btn.setFixedWidth(70)

        top = QHBoxLayout()
        top.addWidget(self._edit, 1)
        top.addWidget(self._add_btn)
        self._top_layout = top

        self._list = QListWidget()
        self._list.setSelectionMode(QListWidget.SingleSelection)
        self._list.setFixedHeight(90)
        self._list.setAlternatingRowColors(True)

        self._del_btn = QPushButton("删除选中")
        self._del_btn.setFixedWidth(90)
        self._empty_hint = QLabel("暂无规则")
        self._empty_hint.setStyleSheet("color:#888;")

        bottom = QHBoxLayout()
        bottom.addWidget(self._empty_hint, 1)
        bottom.addWidget(self._del_btn)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addLayout(title_row)
        lay.addLayout(top)
        lay.addWidget(self._list)
        lay.addLayout(bottom)

        self._edit.returnPressed.connect(self._on_add)
        self._add_btn.clicked.connect(self._on_add)
        self._del_btn.clicked.connect(self._on_delete)
        self._list.itemSelectionChanged.connect(self._update_empty_hint)

        self._update_empty_hint()

    # -- API -------------------------------------------------------------

    def values(self) -> list[str]:
        return [self._list.item(i).text() for i in range(self._list.count())]

    def set_values(self, items: list[str]) -> None:
        self._list.clear()
        for it in items:
            self._list.addItem(QListWidgetItem(it))
        self._update_empty_hint()

    def add_value(self, value: str) -> bool:
        """添加一个值。已存在或空则返回 False。"""
        value = value.strip()
        if not value:
            return False
        if value in set(self.values()):
            return False
        self._list.addItem(QListWidgetItem(value))
        self._update_empty_hint()
        self.changed.emit()
        return True

    def add_tool_button(self, text: str, callback) -> QPushButton:
        """在输入行右侧追加一个按钮，返回按钮对象。"""
        btn = QPushButton(text)
        btn.setFixedWidth(130)
        btn.clicked.connect(callback)
        self._top_layout.addWidget(btn)
        return btn

    # -- internals -------------------------------------------------------

    def _on_add(self) -> None:
        text = self._edit.text().strip()
        if not text:
            return
        parts = [p.strip() for p in text.replace(",", "\n").splitlines()]
        existing = set(self.values())
        added = False
        for p in parts:
            if p and p not in existing:
                self._list.addItem(QListWidgetItem(p))
                existing.add(p)
                added = True
        self._edit.clear()
        self._update_empty_hint()
        if added:
            self.changed.emit()

    def _on_delete(self) -> None:
        for item in self._list.selectedItems():
            self._list.takeItem(self._list.row(item))
        self._update_empty_hint()
        self.changed.emit()

    def _update_empty_hint(self) -> None:
        empty = self._list.count() == 0
        self._empty_hint.setVisible(empty)
        self._del_btn.setEnabled(not empty)

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key_Delete and self._list.hasFocus():
            self._on_delete()
        else:
            super().keyPressEvent(event)