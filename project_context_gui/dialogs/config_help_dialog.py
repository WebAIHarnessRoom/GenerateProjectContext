"""配置加载说明对话框。"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from project_context_gui.services.config_introspection import (
    IntrospectionResult,
    LayerInfo,
)


class ConfigHelpDialog(QDialog):
    """展示配置加载顺序、来源与常见问题。"""

    def __init__(
        self,
        introspection: IntrospectionResult,
        parent: QWidget | None = None,
        *,
        project_root: str = "",
        run_state=None,
    ) -> None:
        super().__init__(parent)
        self._result = introspection
        self._project_root = project_root
        self._run_state = run_state
        self._jump_target: str = ""
        self._solidified: bool = False
        self.setWindowTitle("配置加载说明")
        self.setMinimumSize(680, 680)
        self._build_ui()

    # -- 对外 -----------------------------------------------------------

    @property
    def jump_target(self) -> str:
        """如果用户点了“去编辑”，返回目标 Tab；否则空字符串。"""
        return self._jump_target

    @property
    def solidified(self) -> bool:
        """是否执行过“固化到项目配置”。"""
        return self._solidified

    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        v = QVBoxLayout(self)
        v.setSpacing(10)

        title = QLabel("配置加载顺序")
        f = title.font()
        f.setPointSize(14)
        f.setBold(True)
        title.setFont(f)
        v.addWidget(title)

        intro = QLabel(
            "本工具会把三层排除规则依次叠加使用。最终生效的规则是三层"
            "合并的结果。每一层都有对应的编辑入口，见卡片右侧按钮。"
        )
        intro.setWordWrap(True)
        intro.setStyleSheet("color:#555;")
        v.addWidget(intro)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        from PySide6.QtWidgets import QFrame
        scroll.setFrameShape(QFrame.NoFrame)

        content = QWidget()
        cv = QVBoxLayout(content)
        cv.setContentsMargins(0, 0, 8, 0)
        cv.setSpacing(6)

        layers = self._result.all_layers()
        for i, layer in enumerate(layers):
            cv.addWidget(self._make_layer_card(layer))
            arrow = QLabel("↓  追加")
            arrow.setStyleSheet(
                "color:#888; margin-left: 20px; font-size: 11px;"
            )
            cv.addWidget(arrow)

        cv.addWidget(self._make_final_card())
        cv.addWidget(self._make_faq_card())
        cv.addStretch(1)

        scroll.setWidget(content)
        v.addWidget(scroll, 1)

        # 底部按钮
        row = QHBoxLayout()
        copy_btn = QPushButton("复制说明")
        copy_btn.clicked.connect(self._on_copy)
        row.addWidget(copy_btn)

        doc_btn = QPushButton("打开文档")
        doc_btn.clicked.connect(self._on_open_doc)
        row.addWidget(doc_btn)

        row.addStretch(1)
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        row.addWidget(close_btn)

        v.addLayout(row)

    # ------------------------------------------------------------------
    # 单层卡片
    # ------------------------------------------------------------------

    def _make_layer_card(self, layer: LayerInfo) -> QWidget:
        card = QGroupBox()
        card.setStyleSheet(
            "QGroupBox { border: 1px solid #d8d8d8; border-radius: 6px; "
            "background: #fafafa; margin-top: 4px; padding: 8px; }"
        )
        v = QVBoxLayout(card)
        v.setSpacing(4)

        # 标题行
        head = QHBoxLayout()
        title = QLabel(f"{layer.marker}  {layer.name}")
        f = title.font()
        f.setBold(True)
        title.setFont(f)
        head.addWidget(title)
        head.addStretch(1)

        if layer.rules_count > 0:
            cnt = QLabel(f"{layer.rules_count} 条规则")
            cnt.setStyleSheet("color:#2d8f4e; font-size: 11px;")
            head.addWidget(cnt)
        v.addLayout(head)

        # 说明
        desc = QLabel(layer.description)
        desc.setStyleSheet("color:#666; font-size: 11px;")
        desc.setWordWrap(True)
        v.addWidget(desc)

        # 路径
        if layer.paths:
            for p in layer.paths:
                pl = QLabel(f"📂 {p}")
                pl.setStyleSheet("color:#444; font-size: 11px;")
                pl.setTextInteractionFlags(Qt.TextSelectableByMouse)
                v.addWidget(pl)

        # 文件列表
        if layer.files:
            toggle = QToolButton()
            toggle.setText(f"▸ 已加载 {len(layer.files)} 个配置文件")
            toggle.setCheckable(True)
            toggle.setStyleSheet(
                "QToolButton { border: none; color: #005cc5; "
                "font-size: 11px; padding: 2px; }"
            )
            toggle.setToolButtonStyle(Qt.ToolButtonTextOnly)

            file_box = QWidget()
            fv = QVBoxLayout(file_box)
            fv.setContentsMargins(16, 0, 0, 0)
            fv.setSpacing(2)
            for fpath in layer.files:
                fl = QLabel(f"• {fpath.name}  —  {fpath}")
                fl.setStyleSheet("color:#666; font-size: 10px;")
                fl.setTextInteractionFlags(Qt.TextSelectableByMouse)
                fv.addWidget(fl)
            file_box.setVisible(False)

            def _on_toggle(checked, box=file_box, btn=toggle):
                box.setVisible(checked)
                label = btn.text().split(" ", 1)[-1]
                btn.setText(("▾ " if checked else "▸ ") + label)

            toggle.toggled.connect(_on_toggle)
            v.addWidget(toggle)
            v.addWidget(file_box)

        # 备注
        if layer.note:
            note = QLabel(f"ℹ {layer.note}")
            note.setStyleSheet("color:#b07a00; font-size: 11px;")
            note.setWordWrap(True)
            v.addWidget(note)

        if not layer.available and not layer.note and not layer.files:
            na = QLabel("（此层当前不可用）")
            na.setStyleSheet("color:#999; font-size: 11px;")
            v.addWidget(na)

        # 编辑入口
        if layer.edit_hint:
            edit_row = QHBoxLayout()
            hint = QLabel(f"✎ {layer.edit_hint}")
            hint.setStyleSheet("color:#005cc5; font-size: 11px;")
            edit_row.addWidget(hint, 1)

            if layer.edit_target:
                btn = QPushButton("去编辑 →")
                btn.setFixedWidth(100)
                btn.clicked.connect(
                    lambda _=False, t=layer.edit_target:
                    self._on_jump_to(t)
                )
                edit_row.addWidget(btn)

            v.addLayout(edit_row)

        # L3 层额外加"固化到项目配置"
        if layer.marker == "③" and layer.rules_count > 0:
            sol_row = QHBoxLayout()
            sh = QLabel("⇪ 想永久生效？")
            sh.setStyleSheet("color:#666; font-size: 11px;")
            sol_row.addWidget(sh, 1)

            sbtn = QPushButton("固化到项目配置")
            sbtn.setFixedWidth(150)
            sbtn.clicked.connect(self._on_solidify)
            sol_row.addWidget(sbtn)

            v.addLayout(sol_row)

        return card

    # ------------------------------------------------------------------

    def _make_final_card(self) -> QWidget:
        card = QGroupBox()
        card.setStyleSheet(
            "QGroupBox { border: 1px solid #2d8f4e; border-radius: 6px; "
            "background: #eef6ee; margin-top: 4px; padding: 8px; }"
        )
        v = QVBoxLayout(card)

        head = QHBoxLayout()
        title = QLabel("✓  最终生效规则")
        f = title.font()
        f.setBold(True)
        title.setFont(f)
        head.addWidget(title)
        head.addStretch(1)

        total = sum(
            layer.rules_count for layer in self._result.all_layers()
        )
        cnt = QLabel(f"约 {total} 条")
        cnt.setStyleSheet("color:#2d8f4e; font-size: 11px;")
        head.addWidget(cnt)
        v.addLayout(head)

        desc = QLabel(
            "① + ② + ③ 合并的结果。"
            "若勾选了“忽略项目配置”，② 会被跳过。"
        )
        desc.setStyleSheet("color:#555; font-size: 11px;")
        desc.setWordWrap(True)
        v.addWidget(desc)

        return card

    def _make_faq_card(self) -> QWidget:
        box = QGroupBox("常见问题")
        v = QVBoxLayout(box)
        v.setSpacing(2)

        qa_list = [
            ("我在 GUI 加的规则和项目里的配置冲突怎么办？",
             "不冲突，会叠加：\n"
             "  • 项目里 ignore_dirs = [\"third_party\"]\n"
             "  • GUI 加 --exclude-dir build\n"
             "  最终两者都生效。"),
            ("为什么项目里的规则没生效？",
             "① 展开上方“② 项目配置”卡片，看是否已加载文件；\n"
             "② 若显示“未发现 .project_context/”，"
             "点“去编辑 →”到「配置文件」Tab 新建；\n"
             "③ 若规则存在但目录还在，注意区分：\n"
             "    - ignore_dirs 精确匹配目录名\n"
             "    - ignore_dir_globs 支持通配符"),
            ("切换项目后 GUI 里的规则还在吗？",
             "“本次追加”（③ 层）的规则是全局的，不随项目切换。\n"
             "如需每条规则只对特定项目生效，点“固化到项目配置”"
             "写入项目的 .project_context/。"),
            ("怎样让规则永久生效？",
             "两条路：\n"
             "  • 在“③ 本次追加”卡片里点“固化到项目配置”\n"
             "  • 或到「配置文件」Tab 手动编辑 common.toml"),
            ("Python 模式与 EXE 模式的内置规则一样吗？",
             "取决于分发包是否同步更新。\n"
             "本对话框顶部“① 工具内置规则”显示的路径就是当前来源。"),
        ]

        for q, a in qa_list:
            toggle = QToolButton()
            toggle.setText(f"▸ {q}")
            toggle.setCheckable(True)
            toggle.setStyleSheet(
                "QToolButton { border: none; color: #005cc5; "
                "font-size: 11px; padding: 2px; text-align: left; }"
            )
            toggle.setToolButtonStyle(Qt.ToolButtonTextOnly)

            ans = QLabel(a)
            ans.setStyleSheet(
                "color:#444; font-size: 11px; "
                "padding: 4px 4px 4px 20px;"
            )
            ans.setWordWrap(True)
            ans.setVisible(False)

            def _on(checked, label=ans, btn=toggle):
                label.setVisible(checked)
                label_text = btn.text().split(" ", 1)[-1]
                btn.setText(("▾ " if checked else "▸ ") + label_text)

            toggle.toggled.connect(_on)
            v.addWidget(toggle)
            v.addWidget(ans)

        return box

    # ------------------------------------------------------------------
    # 槽
    # ------------------------------------------------------------------

    def _on_jump_to(self, target: str) -> None:
        self._jump_target = target
        self.accept()

    def _on_solidify(self) -> None:
        from project_context_gui.dialogs.solidify_rules_dialog import (
            SolidifyRulesDialog,
        )
        from PySide6.QtWidgets import QMessageBox

        if self._run_state is None or not self._project_root:
            QMessageBox.information(
                self, "固化", "没有可固化的规则或未选择项目。"
            )
            return

        dlg = SolidifyRulesDialog(
            self._run_state, self._project_root, self
        )
        if dlg.exec() == QDialog.Accepted:
            written = dlg.written_path()
            QMessageBox.information(
                self, "固化完成",
                f"已写入：\n{written}"
            )
            self._solidified = True
            self.accept()

    def _on_copy(self) -> None:
        QApplication.clipboard().setText(self._to_text())
        self.setWindowTitle("配置加载说明（已复制到剪贴板）")

    def _to_text(self) -> str:
        lines = ["配置加载说明", "=" * 40, ""]
        for layer in self._result.all_layers():
            lines.append(f"{layer.marker} {layer.name}")
            lines.append(f"  {layer.description}")
            if layer.edit_hint:
                lines.append(f"  编辑入口：{layer.edit_hint}")
            for p in layer.paths:
                lines.append(f"  路径：{p}")
            for f in layer.files:
                lines.append(f"  文件：{f.name}")
            if layer.note:
                lines.append(f"  备注：{layer.note}")
            lines.append("")

        total = sum(l.rules_count for l in self._result.all_layers())
        lines.append(f"最终生效规则：约 {total} 条")
        return "\n".join(lines)

    def _on_open_doc(self) -> None:
        candidates = [
            Path(__file__).resolve().parents[2] / "docs" / "gui.md",
            Path(__file__).resolve().parents[2] / "README.md",
        ]
        for p in candidates:
            if p.is_file():
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(p)))
                return