"""配置加载说明对话框。"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QDesktopServices, QFont
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFrame,
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
    ) -> None:
        super().__init__(parent)
        self._result = introspection
        self.setWindowTitle("配置加载说明")
        self.setMinimumSize(680, 640)
        self._build_ui()

    def _build_ui(self) -> None:
        v = QVBoxLayout(self)
        v.setSpacing(10)

        # 标题
        title = QLabel("配置加载顺序")
        f = title.font()
        f.setPointSize(14)
        f.setBold(True)
        title.setFont(f)
        v.addWidget(title)

        intro = QLabel(
            "本工具会把三层排除规则依次叠加使用，越靠下的优先级越高、"
            "越先被检查。最终生效的规则是三层合并的结果。"
        )
        intro.setWordWrap(True)
        intro.setStyleSheet("color:#555;")
        v.addWidget(intro)

        # 滚动区
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        content = QWidget()
        cv = QVBoxLayout(content)
        cv.setContentsMargins(0, 0, 8, 0)
        cv.setSpacing(6)

        # 三层卡片
        layers = self._result.all_layers()
        for i, layer in enumerate(layers):
            cv.addWidget(self._make_layer_card(layer))
            arrow = QLabel("↓  追加")
            arrow.setStyleSheet(
                "color:#888; margin-left: 20px; font-size: 11px;"
            )
            cv.addWidget(arrow)

        # 最终生效
        cv.addWidget(self._make_final_card())

        # 常见问题
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

        # 文件列表（折叠）
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
                btn.setText(
                    ("▾ " if checked else "▸ ")
                    + btn.text().split(" ", 1)[-1]
                )

            toggle.toggled.connect(_on_toggle)
            v.addWidget(toggle)
            v.addWidget(file_box)

        # 备注
        if layer.note:
            note = QLabel(f"ℹ {layer.note}")
            note.setStyleSheet("color:#b07a00; font-size: 11px;")
            note.setWordWrap(True)
            v.addWidget(note)

        if not layer.available and not layer.note:
            na = QLabel("（此层当前不可用）")
            na.setStyleSheet("color:#999; font-size: 11px;")
            v.addWidget(na)

        return card

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
            "① + ② + ③ 合并的结果。若勾选了“忽略项目配置”，② 会被跳过。"
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
            ("为什么项目里的规则没生效？",
             "① 检查项目根下是否存在 .project_context/；\n"
             "② 确认该规则所在的文件已被加载（展开上一层卡片查看）；\n"
             "③ 若规则存在但目录还在，注意区分：\n"
             "    - ignore_dirs 精确匹配目录名\n"
             "    - ignore_dir_globs 支持通配符"),
            ("切换项目后 GUI 里的规则还在吗？",
             "“本次追加”的规则是全局的，不随项目切换。\n"
             "如需每条规则只对特定项目生效，请写进项目的 "
             ".project_context/。"),
            ("怎样让规则永久生效？",
             "① 打开“配置文件”Tab；\n"
             "② 编辑 common.toml 或对应语言的 toml；\n"
             "③ 保存后写回项目，下一次运行自动加载。"),
            ("Python 模式与 EXE 模式的内置规则一样吗？",
             "取决于分发包是否同步更新。\n"
             "本对话框顶部“① 工具内置规则”显示的路径就是当前实际来源。\n"
             "两个分发方式若版本一致，内置规则也一致。"),
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
            toggle.setSizePolicy(
                toggle.sizePolicy().horizontalPolicy(),
                toggle.sizePolicy().verticalPolicy(),
            )

            ans = QLabel(a)
            ans.setStyleSheet(
                "color:#444; font-size: 11px; "
                "padding: 4px 4px 4px 20px;"
            )
            ans.setWordWrap(True)
            ans.setVisible(False)

            def _on(checked, label=ans, btn=toggle):
                label.setVisible(checked)
                prefix = "▾ " if checked else "▸ "
                btn.setText(prefix + btn.text().split(" ", 1)[-1])

            toggle.toggled.connect(_on)
            v.addWidget(toggle)
            v.addWidget(ans)

        return box

    # ------------------------------------------------------------------

    def _on_copy(self) -> None:
        QApplication.clipboard().setText(self._to_text())
        self.setWindowTitle("配置加载说明（已复制到剪贴板）")

    def _to_text(self) -> str:
        lines = ["配置加载说明", "=" * 40, ""]
        for layer in self._result.all_layers():
            lines.append(f"{layer.marker} {layer.name}")
            lines.append(f"  {layer.description}")
            for p in layer.paths:
                lines.append(f"  路径：{p}")
            for f in layer.files:
                lines.append(f"  文件：{f.name}")
            if layer.note:
                lines.append(f"  备注：{layer.note}")
            lines.append("")

        total = sum(l.rules_count for l in self._result.all_layers())
        lines.append(f"最终生效规则：约 {total} 条")
        lines.append("")
        lines.append("常见问题：")
        lines.append("  见 GUI「查看配置加载说明」对话框")
        return "\n".join(lines)

    def _on_open_doc(self) -> None:
        # 尝试打开项目根的 docs/gui.md；找不到则退回打开 README
        candidates = [
            Path(__file__).resolve().parents[2] / "docs" / "gui.md",
            Path(__file__).resolve().parents[2] / "README.md",
        ]
        for p in candidates:
            if p.is_file():
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(p)))
                return