"""配置文件 Tab：查看 / 编辑 / 校验 / 保存 .project_context/ 下的 TOML。"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from project_context_gui.services.config_service import (
    ConfigFile,
    ConfigService,
    format_toml,
    validate_toml,
)
from project_context_gui.widgets.toml_editor import TomlEditor


class ConfigTab(QWidget):
    """配置文件 Tab。"""

    saved = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._svc = ConfigService()
        self._current: ConfigFile | None = None
        self._build_ui()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)
        outer.setSpacing(8)

        # 三层提示（本次新增）
        layer_hint = QLabel(
            "ℹ 这里编辑的是三层配置的「② 项目配置」层，会随项目分发；"
            "想临时追加规则，请到「运行配置」Tab 的过滤面板。"
        )
        layer_hint.setWordWrap(True)
        layer_hint.setStyleSheet(
            "color:#005cc5; background:#f0f7ff; "
            "padding: 6px; border-radius: 4px;"
        )
        outer.addWidget(layer_hint)

        h_row = QHBoxLayout()
        help_btn = QPushButton("查看配置加载说明")
        help_btn.setFixedWidth(160)
        help_btn.clicked.connect(self._on_show_config_help)
        h_row.addWidget(help_btn)
        h_row.addStretch(1)
        outer.addLayout(h_row)

        # 状态提示行（原有）
        self._hint = QLabel("请先选择项目")
        self._hint.setStyleSheet("color:#666;")
        outer.addWidget(self._hint)

        splitter = QSplitter(Qt.Horizontal)

        # 左侧
        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        lv.setSpacing(4)

        lv.addWidget(QLabel("配置文件"))
        self._list = QListWidget()
        self._list.currentItemChanged.connect(self._on_select)
        lv.addWidget(self._list, 1)

        btn_row = QHBoxLayout()
        self._new_common_btn = QPushButton("新建 common.toml")
        self._new_common_btn.clicked.connect(self._on_new_common)
        btn_row.addWidget(self._new_common_btn)

        self._new_lang_btn = QPushButton("新建语言配置…")
        self._new_lang_btn.clicked.connect(self._on_new_language)
        btn_row.addWidget(self._new_lang_btn)
        lv.addLayout(btn_row)

        self._delete_btn = QPushButton("删除选中")
        self._delete_btn.clicked.connect(self._on_delete)
        lv.addWidget(self._delete_btn)

        splitter.addWidget(left)

        # 右侧
        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(0, 0, 0, 0)
        rv.setSpacing(4)

        self._file_label = QLabel("（未选择文件）")
        f = QFont()
        f.setBold(True)
        self._file_label.setFont(f)
        rv.addWidget(self._file_label)

        self._editor = TomlEditor()
        self._editor.setPlaceholderText("选择左侧配置文件开始编辑…")
        self._editor.textChanged.connect(self._on_text_changed)
        rv.addWidget(self._editor, 1)

        tools = QHBoxLayout()
        self._validate_btn = QPushButton("校验")
        self._validate_btn.clicked.connect(self._on_validate)
        tools.addWidget(self._validate_btn)

        self._format_btn = QPushButton("格式化")
        self._format_btn.clicked.connect(self._on_format)
        tools.addWidget(self._format_btn)

        self._save_btn = QPushButton("保存 (Ctrl+S)")
        self._save_btn.clicked.connect(self._on_save)
        tools.addWidget(self._save_btn)

        tools.addStretch(1)

        self._status = QLabel("")
        self._status.setStyleSheet("color:#666;")
        tools.addWidget(self._status)

        rv.addLayout(tools)

        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        splitter.setSizes([240, 720])

        outer.addWidget(splitter, 1)
        self._update_buttons()

    # ------------------------------------------------------------------
    # 对外 API
    # ------------------------------------------------------------------

    def set_root(self, root: str | None) -> None:
        self._svc.set_root(root)
        self._current = None
        self._editor.setPlainText("")
        self._editor.set_dirty(False)
        self._file_label.setText("（未选择文件）")
        self._status.setText("")
        self._refresh_list()
        self._refresh_hint()

    def has_unsaved(self) -> bool:
        return bool(self._current and self._editor.dirty)

    def try_save(self) -> bool:
        if not self._current or not self._editor.dirty:
            return True
        return self._save(silent=True)

    # ------------------------------------------------------------------
    # 配置加载说明
    # ------------------------------------------------------------------

    def _on_show_config_help(self) -> None:
        from project_context_gui.dialogs.config_help_dialog import (
            ConfigHelpDialog,
        )
        from project_context_gui.services.config_introspection import (
            introspect,
        )
        root = str(self._svc.root) if self._svc.root else ""
        result = introspect(root=root, run_state=None)
        dlg = ConfigHelpDialog(result, self, project_root=root)
        dlg.exec()
        # 若用户点了“去编辑”但目标就是本 Tab，无需切换；
        # 若目标是 run_tab_filter，通知主窗口
        if dlg.jump_target == "run_tab_filter":
            w = self.window()
            if hasattr(w, "_on_config_help_jump"):
                w._on_config_help_jump("run_tab_filter")

    # ------------------------------------------------------------------
    # 列表刷新
    # ------------------------------------------------------------------

    def _refresh_list(self) -> None:
        self._list.blockSignals(True)
        self._list.clear()
        files = self._svc.list_files()
        for cf in files:
            item = QListWidgetItem(cf.rel_path)
            item.setData(Qt.UserRole, cf)
            self._list.addItem(item)
        self._list.blockSignals(False)

        if files:
            self._list.setCurrentRow(0)
        else:
            self._current = None
            self._editor.setPlainText("")
            self._editor.set_dirty(False)
            self._file_label.setText("（未选择文件）")
        self._update_buttons()

    def _refresh_hint(self) -> None:
        if not self._svc.root:
            self._hint.setText("请先选择项目")
            return
        if not self._svc.exists():
            self._hint.setText(
                "未发现 .project_context/，可点击"
                "“新建 common.toml”创建。"
                f"  项目：{self._svc.root}"
            )
        else:
            n = len(self._svc.list_files())
            self._hint.setText(
                f".project_context/ 已加载，共 {n} 个配置文件。"
                f"  项目：{self._svc.root}"
            )

    def _is_current(self, cf: ConfigFile) -> bool:
        return bool(self._current and self._current.path == cf.path)

    def _refresh_current_marker(self) -> None:
        for i in range(self._list.count()):
            item = self._list.item(i)
            cf: ConfigFile = item.data(Qt.UserRole)
            if self._is_current(cf):
                mark = " ●" if self._editor.dirty else ""
                item.setText(cf.rel_path + mark)
                break

    # ------------------------------------------------------------------
    # 选择文件
    # ------------------------------------------------------------------

    def _on_select(self, item, _prev) -> None:
        if item is None:
            return
        cf: ConfigFile = item.data(Qt.UserRole)
        if self._current and self._current.path == cf.path:
            return

        if self._editor.dirty:
            ret = QMessageBox.question(
                self, "未保存",
                f"“{self._current.rel_path}”有未保存修改，是否丢弃？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if ret != QMessageBox.Yes:
                self._list.blockSignals(True)
                for i in range(self._list.count()):
                    other = self._list.item(i)
                    data: ConfigFile = other.data(Qt.UserRole)
                    if self._current and data.path == self._current.path:
                        self._list.setCurrentRow(i)
                        break
                self._list.blockSignals(False)
                return

        self._load_file(cf)

    def _load_file(self, cf: ConfigFile) -> None:
        try:
            text = self._svc.read(cf.path)
        except OSError as e:
            QMessageBox.warning(self, "读取失败", str(e))
            return
        self._current = cf
        self._editor.load_text(text)
        self._file_label.setText(cf.rel_path)
        self._status.setText("")
        self._editor.clear_error_line()
        self._update_buttons()

    # ------------------------------------------------------------------
    # 编辑与保存
    # ------------------------------------------------------------------

    def _on_text_changed(self) -> None:
        self._refresh_current_marker()
        self._update_buttons()

    def _update_buttons(self) -> None:
        has_current = self._current is not None
        self._save_btn.setEnabled(has_current and self._editor.dirty)
        self._validate_btn.setEnabled(has_current)
        self._format_btn.setEnabled(has_current)
        self._delete_btn.setEnabled(has_current)
        self._new_common_btn.setEnabled(
            bool(self._svc.root) and not self._common_exists()
        )
        self._new_lang_btn.setEnabled(bool(self._svc.root))

    def _common_exists(self) -> bool:
        d = self._svc.config_dir
        return bool(d and (d / "common.toml").is_file())

    def _on_validate(self) -> bool:
        if not self._current:
            return False
        text = self._editor.toPlainText()
        ok, msg, line = validate_toml(text)
        if ok:
            self._editor.clear_error_line()
            self._status.setText("✅ TOML 语法正确")
            self._status.setStyleSheet("color:#2d8f4e;")
            return True
        self._editor.set_error_line(line)
        self._status.setText(f"❌ {msg}")
        self._status.setStyleSheet("color:#c0392b;")
        if line:
            block = self._editor.document().findBlockByNumber(line - 1)
            if block.isValid():
                cur = self._editor.textCursor()
                cur.setPosition(block.position())
                self._editor.setTextCursor(cur)
                self._editor.centerCursor()
        return False

    def _on_format(self) -> None:
        if not self._current:
            return
        text = self._editor.toPlainText()
        ok, msg, line = validate_toml(text)
        if not ok:
            self._editor.set_error_line(line)
            QMessageBox.warning(
                self, "格式化失败", f"TOML 语法错误：{msg}"
            )
            return
        formatted = format_toml(text)
        if formatted == text:
            self._status.setText("格式化无变化")
            self._status.setStyleSheet("color:#666;")
            return
        self._editor.setPlainText(formatted)
        self._editor.set_dirty(True)
        self._status.setText("已格式化")

    def _on_save(self) -> None:
        self._save(silent=False)

    def _save(self, silent: bool = False) -> bool:
        if not self._current:
            return True

        text = self._editor.toPlainText()
        ok, msg, line = validate_toml(text)
        if not ok:
            self._editor.set_error_line(line)
            self._status.setText(f"❌ {msg}")
            self._status.setStyleSheet("color:#c0392b;")
            if not silent:
                QMessageBox.warning(
                    self, "无法保存", f"TOML 语法错误：\n{msg}"
                )
            return False

        try:
            self._svc.write(self._current.path, text)
        except OSError as e:
            if not silent:
                QMessageBox.critical(self, "保存失败", str(e))
            return False

        self._editor.set_dirty(False)
        self._refresh_current_marker()
        self._status.setText(f"已保存：{self._current.rel_path}")
        self._status.setStyleSheet("color:#2d8f4e;")
        self._update_buttons()
        self.saved.emit()
        return True

    # ------------------------------------------------------------------
    # 新建 / 删除
    # ------------------------------------------------------------------

    def _on_new_common(self) -> None:
        if not self._svc.root:
            return
        try:
            cf = self._svc.create_common_template()
        except OSError as e:
            QMessageBox.critical(self, "创建失败", str(e))
            return
        self._refresh_list()
        self._refresh_hint()
        self._select_by_path(cf.path)

    def _on_new_language(self) -> None:
        if not self._svc.root:
            return
        dlg = _NewLanguageDialog(self)
        if dlg.exec() != QDialog.Accepted:
            return
        try:
            cf = self._svc.create_language_template(
                dlg.name(), dlg.suffix()
            )
        except OSError as e:
            QMessageBox.critical(self, "创建失败", str(e))
            return
        self._refresh_list()
        self._refresh_hint()
        self._select_by_path(cf.path)

    def _on_delete(self) -> None:
        if not self._current:
            return
        ret = QMessageBox.question(
            self, "删除确认",
            f"确定删除 {self._current.rel_path} 吗？\n此操作不可撤销。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if ret != QMessageBox.Yes:
            return
        try:
            self._svc.delete(self._current.path)
        except OSError as e:
            QMessageBox.critical(self, "删除失败", str(e))
            return
        self._current = None
        self._editor.setPlainText("")
        self._editor.set_dirty(False)
        self._file_label.setText("（未选择文件）")
        self._refresh_list()
        self._refresh_hint()

    def _select_by_path(self, path: Path) -> None:
        for i in range(self._list.count()):
            item = self._list.item(i)
            cf: ConfigFile = item.data(Qt.UserRole)
            if cf.path == path:
                self._list.setCurrentRow(i)
                return


# ---------------------------------------------------------------------------
# 新建语言对话框
# ---------------------------------------------------------------------------

class _NewLanguageDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("新建语言配置")
        self.setMinimumWidth(320)

        lay = QVBoxLayout(self)
        form = QFormLayout()

        self._name = QLineEdit()
        self._name.setPlaceholderText("例如 mydsl")
        form.addRow("语言名", self._name)

        self._suffix = QLineEdit()
        self._suffix.setPlaceholderText("例如 mydsl（默认同语言名）")
        form.addRow("后缀", self._suffix)

        lay.addLayout(form)

        bb = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        bb.accepted.connect(self._on_accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    def _on_accept(self) -> None:
        name = self._name.text().strip()
        if not name:
            QMessageBox.warning(self, "参数错误", "语言名不能为空。")
            return
        if not all(c.isalnum() or c in "-_" for c in name):
            QMessageBox.warning(
                self, "参数错误",
                "语言名只能包含字母、数字、连字符、下划线。",
            )
            return
        self.accept()

    def name(self) -> str:
        return self._name.text().strip()

    def suffix(self) -> str:
        s = self._suffix.text().strip()
        return s or self.name().lower()