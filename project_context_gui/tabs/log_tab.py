"""运行日志 Tab。"""
from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class LogTab(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._level_filter = "全部"
        self._lines: list[tuple[str, str]] = []  # (level, text)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 12, 12, 12)

        # 工具条
        bar = QHBoxLayout()
        bar.addWidget(QLabel("级别："))
        self._level_combo = QComboBox()
        self._level_combo.addItems(["全部", "INFO", "WARN", "ERROR"])
        self._level_combo.currentTextChanged.connect(self._on_level_changed)
        bar.addWidget(self._level_combo)

        bar.addWidget(QLabel("搜索："))
        self._search = QLineEdit()
        self._search.setPlaceholderText("关键字过滤")
        self._search.textChanged.connect(lambda _t: self._render())
        bar.addWidget(self._search, 1)

        self._auto_scroll = QCheckBox("自动滚动")
        self._auto_scroll.setChecked(True)
        bar.addWidget(self._auto_scroll)

        clear_btn = QPushButton("清空")
        clear_btn.clicked.connect(self.clear)
        bar.addWidget(clear_btn)

        export_btn = QPushButton("导出日志…")
        export_btn.clicked.connect(self._export)
        bar.addWidget(export_btn)

        lay.addLayout(bar)

        self._view = QPlainTextEdit()
        self._view.setReadOnly(True)
        font = self._view.font()
        font.setFamily("Consolas, Menlo, monospace")
        self._view.setFont(font)
        lay.addWidget(self._view, 1)

    # -- API -------------------------------------------------------------

    def clear(self) -> None:
        self._lines.clear()
        self._view.clear()

    def append(self, text: str, level: str | None = None) -> None:
        if level is None:
            level = _infer_level(text)
        stamp = datetime.now().strftime("%H:%M:%S")
        display = f"{stamp}  {level:<5} {text}"
        self._lines.append((level, display))
        if self._match(level, text):
            self._append_colored(display, level)
            if self._auto_scroll.isChecked():
                self._view.verticalScrollBar().setValue(
                    self._view.verticalScrollBar().maximum()
                )

    # -- internals -------------------------------------------------------

    def _on_level_changed(self, value: str) -> None:
        self._level_filter = value
        self._render()

    def _match(self, level: str, text: str) -> bool:
        if self._level_filter != "全部" and level != self._level_filter:
            return False
        kw = self._search.text().strip().lower()
        if kw and kw not in text.lower():
            return False
        return True

    def _render(self) -> None:
        self._view.clear()
        for level, display in self._lines:
            if self._match(level, display):
                self._append_colored(display, level)
        if self._auto_scroll.isChecked():
            self._view.verticalScrollBar().setValue(
                self._view.verticalScrollBar().maximum()
            )

    def _append_colored(self, text: str, level: str) -> None:
        fmt = QTextCharFormat()
        if level == "ERROR":
            fmt.setForeground(QColor("#c0392b"))
        elif level == "WARN":
            fmt.setForeground(QColor("#b07a00"))
        cursor = self._view.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(text + "\n", fmt)

    def _export(self) -> None:
        if not self._lines:
            QMessageBox.information(self, "导出日志", "当前没有日志。")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "导出日志", "project_context.log",
            "日志 (*.log);;文本 (*.txt);;所有文件 (*)",
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                for _lvl, line in self._lines:
                    f.write(line + "\n")
            QMessageBox.information(self, "导出日志", f"已保存到：\n{path}")
        except OSError as e:
            QMessageBox.critical(self, "导出失败", str(e))


def _infer_level(text: str) -> str:
    up = text.upper()
    if "ERROR" in up or "TRACEBACK" in up or "EXCEPTION" in up:
        return "ERROR"
    if "WARN" in up:
        return "WARN"
    return "INFO"