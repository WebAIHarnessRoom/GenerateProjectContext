"""TOML 文本编辑器：行号 + 语法高亮 + 错误行高亮。"""
from __future__ import annotations

import re

from PySide6.QtCore import QRect, QSize, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QPainter,
    QSyntaxHighlighter,
    QTextCharFormat,
    QTextCursor,
    QTextFormat,
)
from PySide6.QtWidgets import QPlainTextEdit, QTextEdit, QWidget


# ---------------------------------------------------------------------------
# 语法高亮
# ---------------------------------------------------------------------------

class TomlHighlighter(QSyntaxHighlighter):
    """极简 TOML 高亮：注释、表头、键、字符串、数字、布尔。"""

    def __init__(self, doc) -> None:
        super().__init__(doc)

        self._comment_fmt = QTextCharFormat()
        self._comment_fmt.setForeground(QColor("#6a737d"))
        self._comment_fmt.setFontItalic(True)

        self._section_fmt = QTextCharFormat()
        self._section_fmt.setForeground(QColor("#005cc5"))
        self._section_fmt.setFontWeight(QFont.Bold)

        self._key_fmt = QTextCharFormat()
        self._key_fmt.setForeground(QColor("#d73a49"))

        self._str_fmt = QTextCharFormat()
        self._str_fmt.setForeground(QColor("#032f62"))

        self._num_fmt = QTextCharFormat()
        self._num_fmt.setForeground(QColor("#005cc5"))

        self._bool_fmt = QTextCharFormat()
        self._bool_fmt.setForeground(QColor("#e36209"))

        self._re_comment = re.compile(r"#[^\n]*")
        self._re_section = re.compile(r"^\s*\[\[?[^\]]+\]\]?\s*$")
        self._re_key = re.compile(r"^\s*([A-Za-z0-9_\-\.\"']+)\s*=")
        self._re_str = re.compile(r'"[^"\\]*(?:\\.[^"\\]*)*"|\'[^\']*\'')
        self._re_num = re.compile(r"\b-?\d+(?:\.\d+)?\b")
        self._re_bool = re.compile(r"\b(?:true|false)\b")

    def highlightBlock(self, text: str) -> None:
        comment_spans: list[tuple[int, int]] = []
        for m in self._re_comment.finditer(text):
            self.setFormat(
                m.start(), m.end() - m.start(), self._comment_fmt
            )
            comment_spans.append((m.start(), m.end()))

        def _in_comment(pos: int) -> bool:
            return any(s <= pos < e for s, e in comment_spans)

        if self._re_section.match(text):
            self.setFormat(0, len(text), self._section_fmt)
            return

        m = self._re_key.match(text)
        if m:
            self.setFormat(
                m.start(1), m.end(1) - m.start(1), self._key_fmt
            )

        for pat, fmt in (
            (self._re_str, self._str_fmt),
            (self._re_num, self._num_fmt),
            (self._re_bool, self._bool_fmt),
        ):
            for m in pat.finditer(text):
                if _in_comment(m.start()):
                    continue
                if fmt is not self._str_fmt and _inside_string(
                    text, m.start()
                ):
                    continue
                self.setFormat(m.start(), m.end() - m.start(), fmt)


def _inside_string(text: str, pos: int) -> bool:
    in_s = in_d = False
    for i, ch in enumerate(text):
        if i >= pos:
            break
        if ch == "'" and not in_d:
            in_s = not in_s
        elif ch == '"' and not in_s:
            in_d = not in_d
    return in_s or in_d


# ---------------------------------------------------------------------------
# 行号
# ---------------------------------------------------------------------------

class _LineNumberArea(QWidget):
    def __init__(self, editor: "TomlEditor") -> None:
        super().__init__(editor)
        self._editor = editor

    def sizeHint(self) -> QSize:
        return QSize(self._editor.line_number_area_width(), 0)

    def paintEvent(self, event) -> None:
        self._editor.line_number_area_paint_event(event)


# ---------------------------------------------------------------------------
# 编辑器
# ---------------------------------------------------------------------------

class TomlEditor(QPlainTextEdit):
    dirtyChanged = Signal(bool)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        font = QFont("Consolas")
        font.setStyleHint(QFont.Monospace)
        font.setPointSize(10)
        self.setFont(font)
        self.setTabStopDistance(
            4 * self.fontMetrics().horizontalAdvance(" ")
        )
        self.setLineWrapMode(QPlainTextEdit.NoWrap)

        self._highlighter = TomlHighlighter(self.document())
        self._line_area = _LineNumberArea(self)
        self._error_line: int | None = None
        self._dirty = False

        self.blockCountChanged.connect(self._update_line_area_width)
        self.updateRequest.connect(self._update_line_area)
        self.cursorPositionChanged.connect(self._highlight_current_line)
        self.textChanged.connect(self._on_text_changed)

        self._update_line_area_width()
        self._highlight_current_line()

    # -- 脏标记 ---------------------------------------------------------

    @property
    def dirty(self) -> bool:
        return self._dirty

    def set_dirty(self, value: bool) -> None:
        if self._dirty != value:
            self._dirty = value
            self.dirtyChanged.emit(value)

    def _on_text_changed(self) -> None:
        if not self._dirty:
            self.set_dirty(True)

    def load_text(self, text: str) -> None:
        self.setPlainText(text)
        self.set_dirty(False)
        self.clear_error_line()

    # -- 错误行 ---------------------------------------------------------

    def set_error_line(self, line: int | None) -> None:
        self._error_line = line
        self._highlight_current_line()

    def clear_error_line(self) -> None:
        self._error_line = None
        self._highlight_current_line()

    # -- 行号区域 -------------------------------------------------------

    def line_number_area_width(self) -> int:
        digits = 1
        max_blocks = max(1, self.blockCount())
        while max_blocks >= 10:
            max_blocks //= 10
            digits += 1
        return 12 + self.fontMetrics().horizontalAdvance("9") * digits

    def _update_line_area_width(self) -> None:
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def _update_line_area(self, rect: QRect, dy: int) -> None:
        if dy:
            self._line_area.scroll(0, dy)
        else:
            self._line_area.update(
                0, rect.y(), self._line_area.width(), rect.height()
            )
        if rect.contains(self.viewport().rect()):
            self._update_line_area_width()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        cr = self.contentsRect()
        self._line_area.setGeometry(
            QRect(
                cr.left(), cr.top(),
                self.line_number_area_width(), cr.height(),
            )
        )

    def line_number_area_paint_event(self, event) -> None:
        painter = QPainter(self._line_area)
        painter.fillRect(event.rect(), QColor("#f5f5f5"))

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = (
            self.blockBoundingGeometry(block)
            .translated(self.contentOffset())
            .top()
        )
        bottom = top + self.blockBoundingRect(block).height()

        height = self.fontMetrics().height()
        cur_line = self.textCursor().blockNumber() + 1

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                num = block_number + 1
                if self._error_line is not None and num == self._error_line:
                    painter.setPen(QColor("#c0392b"))
                elif num == cur_line:
                    painter.setPen(QColor("#24292e"))
                else:
                    painter.setPen(QColor("#999999"))
                painter.drawText(
                    0, int(top),
                    self._line_area.width() - 6, height,
                    Qt.AlignRight, str(num),
                )
            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            block_number += 1

    # -- 当前行与错误行高亮 ---------------------------------------------

    def _highlight_current_line(self) -> None:
        sels: list[QTextEdit.ExtraSelection] = []

        if not self.isReadOnly():
            sel = QTextEdit.ExtraSelection()
            sel.format.setBackground(QColor("#f0f7ff"))
            sel.format.setProperty(
                QTextFormat.FullWidthSelection, True
            )
            sel.cursor = self.textCursor()
            sel.cursor.clearSelection()
            sels.append(sel)

        if self._error_line is not None:
            sel = QTextEdit.ExtraSelection()
            sel.format.setBackground(QColor("#ffe0e0"))
            sel.format.setProperty(
                QTextFormat.FullWidthSelection, True
            )
            block = self.document().findBlockByNumber(
                self._error_line - 1
            )
            if block.isValid():
                cur = QTextCursor(block)
                cur.clearSelection()
                sel.cursor = cur
                sels.append(sel)

        self.setExtraSelections(sels)