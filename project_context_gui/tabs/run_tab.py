"""运行配置 Tab —— 项目、输出、语言、内容开关、过滤、限制、命令预览。"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
    QApplication,
)

from project_context_gui.state import (
    DEFAULT_MAX_FILES_PER_COMMIT,
    DEFAULT_MAX_FILE_SIZE_KB,
    DEFAULT_MAX_GIT_COMMITS,
    DEFAULT_DETECT_MIN_FILES,
    RunState,
    build_cli_args,
    format_command,
)
from project_context_gui.widgets.collapsible import Collapsible
from project_context_gui.widgets.file_picker import FilePicker
from project_context_gui.widgets.folder_picker import FolderPicker
from project_context_gui.widgets.list_editor import ListEditor
from project_context_gui.services.runner_resolver import (
    ResolvedCommand,
    make_python_command,
)

from PySide6.QtWidgets import QFileDialog, QMessageBox

_BUILTIN_LANGUAGES = [
    "python", "node", "go", "rust", "java",
    "cpp", "php", "ruby", "dotnet",
]


class RunTab(QWidget):
    """核心配置页。向主窗口发信号。"""

    requestRun = Signal()
    requestStop = Signal()
    stateChanged = Signal()          # 参数变化，用于刷新预览

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._resolver = None
        self._build_ui()
        self._connect()
        self._refresh_command_preview()

    # -- 构造 -------------------------------------------------------------

    def _build_ui(self) -> None:
        from PySide6.QtWidgets import QFrame, QScrollArea

        # 外层：仅放一个 QScrollArea
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)                       # 内容随宽度自适应
        scroll.setFrameShape(QFrame.NoFrame)                  # 去掉边框
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        # 内容容器：原来所有区块都放这里
        content = QWidget()
        inner = QVBoxLayout(content)
        inner.setContentsMargins(12, 12, 12, 12)
        inner.setSpacing(10)

        # 区块一：项目与输出
        inner.addWidget(self._build_project_group())

        # 区块二：语言
        inner.addWidget(self._build_language_group())

        # 区块三：输出内容
        inner.addWidget(self._build_content_group())

        # 区块四：过滤（折叠，默认收起）
        self._filter_block = Collapsible("过滤降噪（高级）", expanded=False)
        self._build_filter_into(self._filter_block.content_layout())
        inner.addWidget(self._filter_block)

        # 区块五：限制（折叠）
        self._limits_block = Collapsible("限制（高级）", expanded=False)
        self._build_limits_into(self._limits_block.content_layout())
        inner.addWidget(self._limits_block)

        # 区块六：命令预览（折叠）
        self._cmd_block = Collapsible("命令预览（高级）", expanded=False)
        self._build_command_into(self._cmd_block.content_layout())
        inner.addWidget(self._cmd_block)

        inner.addStretch(1)

        scroll.setWidget(content)
        outer.addWidget(scroll)

    def _build_project_group(self) -> QGroupBox:
        box = QGroupBox("项目与输出")
        form = QFormLayout(box)
        form.setLabelAlignment(Qt.AlignRight)

        self._root_picker = FolderPicker("选择项目根目录…")
        self._output_picker = FilePicker(
            mode="save",
            filter_="Markdown (*.md);;所有文件 (*)",
            placeholder="默认 <项目>/PROJECT_CONTEXT.md",
        )
        self._quiet_cb = QCheckBox("安静模式（不打印进度）")

        form.addRow("项目文件夹", self._root_picker)
        form.addRow("输出文件", self._output_picker)
        form.addRow("", self._quiet_cb)

        self._output_warn = QLabel("⚠ 输出文件已存在，运行时会被覆盖")
        self._output_warn.setStyleSheet("color: #b07a00;")
        self._output_warn.setVisible(False)
        form.addRow("", self._output_warn)

        return box

    def _build_language_group(self) -> QGroupBox:
        box = QGroupBox("语言")
        lay = QVBoxLayout(box)

        # 三个 radio
        radio_row = QHBoxLayout()
        self._lang_auto = QRadioButton("自动检测")
        self._lang_all = QRadioButton("全部语言")
        self._lang_custom = QRadioButton("手动选择")
        self._lang_auto.setChecked(True)
        self._lang_group = QButtonGroup(self)
        self._lang_group.addButton(self._lang_auto)
        self._lang_group.addButton(self._lang_all)
        self._lang_group.addButton(self._lang_custom)
        radio_row.addWidget(self._lang_auto)
        radio_row.addWidget(self._lang_all)
        radio_row.addWidget(self._lang_custom)
        radio_row.addStretch(1)
        lay.addLayout(radio_row)

        # 自定义语言：列表 + 添加按钮
        self._lang_list = QListWidget()
        self._lang_list.setFixedHeight(72)
        self._lang_list.setVisible(False)

        self._lang_add_btn = QPushButton("+ 添加语言")
        self._lang_add_btn.setVisible(False)
        self._lang_add_btn.setFixedWidth(120)

        custom_row = QHBoxLayout()
        custom_row.addWidget(self._lang_list, 1)
        custom_row.addWidget(self._lang_add_btn, 0, Qt.AlignTop)
        lay.addLayout(custom_row)

        # 检测阈值
        thresh_row = QHBoxLayout()
        thresh_row.addWidget(QLabel("检测阈值："))
        self._detect_spin = QSpinBox()
        self._detect_spin.setRange(1, 1000)
        self._detect_spin.setValue(DEFAULT_DETECT_MIN_FILES)
        self._detect_spin.setFixedWidth(80)
        thresh_row.addWidget(self._detect_spin)
        thresh_row.addWidget(QLabel("个文件（自动检测时生效）"))
        thresh_row.addStretch(1)
        lay.addLayout(thresh_row)

        return box

    def _build_content_group(self) -> QGroupBox:
        box = QGroupBox("输出内容（章节开关）")
        grid = QGridLayout(box)

        self._cb_content = QCheckBox("包含源码内容")
        self._cb_ast = QCheckBox("包含 AST 摘要")
        self._cb_git = QCheckBox("包含 Git 历史")
        self._cb_ts = QCheckBox("关闭时间戳（用于快照对比）")

        self._cb_content.setChecked(True)
        self._cb_ast.setChecked(True)
        self._cb_git.setChecked(True)
        self._cb_ts.setChecked(False)

        grid.addWidget(self._cb_content, 0, 0)
        grid.addWidget(self._cb_ast, 0, 1)
        grid.addWidget(self._cb_git, 0, 2)
        grid.addWidget(self._cb_ts, 1, 0, 1, 3)
        return box

    def _build_filter_into(self, lay: QVBoxLayout) -> None:
        self._ex_globs = ListEditor(
            "排除文件 glob",
            placeholder="例如 *.pb.go",
            hint="按通配符排除文件，支持 * 与 ?",
        )
        self._ex_dirs = ListEditor(
            "排除目录名",
            placeholder="例如 third_party",
            hint="精确匹配目录名，或点右侧从文件夹选择",
        )
        self._ex_dir_globs = ListEditor(
            "排除目录 glob",
            placeholder="例如 build/**",
            hint="按通配符排除目录路径",
        )
        self._ex_suffixes = ListEditor(
            "排除后缀",
            placeholder="例如 .bak",
            hint="按文件后缀排除，例如 .bak",
        )

        # 给"排除目录名"追加文件夹选择按钮
        self._ex_dirs.add_tool_button(
            "从文件夹选择…", self._on_pick_exclude_dir
        )

        lay.addWidget(self._ex_globs)
        lay.addWidget(self._ex_dirs)
        lay.addWidget(self._ex_dir_globs)
        lay.addWidget(self._ex_suffixes)

    def _build_limits_into(self, lay: QVBoxLayout) -> None:
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)

        self._max_size = QSpinBox()
        self._max_size.setRange(1, 100_000)
        self._max_size.setValue(DEFAULT_MAX_FILE_SIZE_KB)
        self._max_size.setSuffix(" KB")
        self._max_size.setFixedWidth(120)          # ← 缩短

        self._max_commits = QSpinBox()
        self._max_commits.setRange(0, 100_000)
        self._max_commits.setValue(DEFAULT_MAX_GIT_COMMITS)
        self._max_commits.setFixedWidth(120)       # ← 缩短

        self._max_files = QSpinBox()
        self._max_files.setRange(0, 10_000)
        self._max_files.setValue(DEFAULT_MAX_FILES_PER_COMMIT)
        self._max_files.setFixedWidth(120)         # ← 缩短

        form.addRow("单文件大小上限", self._max_size)
        form.addRow("最大 Git 提交数", self._max_commits)
        form.addRow("每提交文件数", self._max_files)
        lay.addLayout(form)

    def _build_command_into(self, lay: QVBoxLayout) -> None:
        self._cmd_view = QPlainTextEdit()
        self._cmd_view.setReadOnly(True)
        self._cmd_view.setFixedHeight(80)
        font = self._cmd_view.font()
        font.setFamily("Consolas, Menlo, monospace")
        self._cmd_view.setFont(font)

        copy_btn = QPushButton("复制命令")
        copy_btn.setFixedWidth(100)
        copy_btn.clicked.connect(self._copy_command)

        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(copy_btn)

        lay.addWidget(self._cmd_view)
        lay.addLayout(row)

    # -- 信号连接 ---------------------------------------------------------

    def _connect(self) -> None:
        # 项目/输出
        self._root_picker.pathChanged.connect(self._on_root_changed)
        self._output_picker.pathChanged.connect(self._on_output_changed)
        self._quiet_cb.toggled.connect(self._emit_changed)

        # 语言
        self._lang_group.buttonToggled.connect(self._on_lang_mode_changed)
        self._lang_add_btn.clicked.connect(self._on_add_languages)
        self._detect_spin.valueChanged.connect(self._emit_changed)

        # 内容
        for cb in (self._cb_content, self._cb_ast, self._cb_git, self._cb_ts):
            cb.toggled.connect(self._emit_changed)

        # 过滤
        for editor in (self._ex_globs, self._ex_dirs,
                       self._ex_dir_globs, self._ex_suffixes):
            editor.changed.connect(self._emit_changed)

        # 限制
        self._max_size.valueChanged.connect(self._emit_changed)
        self._max_commits.valueChanged.connect(self._emit_changed)
        self._max_files.valueChanged.connect(self._emit_changed)

    # -- 联动 -------------------------------------------------------------

    def _on_root_changed(self, path: str) -> None:
        if path and not self._output_picker.path():
            name = "PROJECT_CONTEXT.md"
            self._output_picker.set_path(str(Path(path) / name))
        self._check_output_exists()
        self._emit_changed()

    def _on_output_changed(self, _path: str) -> None:
        self._check_output_exists()
        self._emit_changed()

    def _check_output_exists(self) -> None:
        p = self._output_picker.path()
        self._output_warn.setVisible(bool(p) and Path(p).exists())

    def _on_lang_mode_changed(self, *_args) -> None:
        custom = self._lang_custom.isChecked()
        self._lang_list.setVisible(custom)
        self._lang_add_btn.setVisible(custom)
        self._emit_changed()

    def _on_add_languages(self) -> None:
        dlg = _LanguageDialog(self)
        if dlg.exec() == QDialog.Accepted:
            current = self._custom_languages()
            for lang in dlg.selected():
                if lang not in current:
                    self._lang_list.addItem(QListWidgetItem(lang))
            self._emit_changed()

    def _on_pick_exclude_dir(self) -> None:
        """从项目根目录打开文件夹选择器，把选中目录加入排除列表。"""
        root = self._root_picker.path()
        start = root if root and Path(root).is_dir() else str(Path.home())

        chosen = QFileDialog.getExistingDirectory(
            self, "选择要排除的目录", start
        )
        if not chosen:
            return

        chosen_path = Path(chosen)
        value = self._normalize_exclude_dir(chosen_path, root)
        if not value:
            return

        if not self._ex_dirs.add_value(value):
            QMessageBox.information(
                self, "已存在",
                f"“{value}”已在排除列表中。",
            )
            return
        self._emit_changed()


    def _normalize_exclude_dir(self, chosen: Path, root: str) -> str:
        """把选中的绝对路径转成适合放进排除列表的值。

        - 项目根的直接子目录 → 目录名（例如 third_party）
        - 更深的目录         → 相对路径（例如 src/generated）
        - 不在项目根下       → 绝对路径
        """
        if not root:
            return str(chosen)
        try:
            rel = chosen.relative_to(Path(root))
        except ValueError:
            return str(chosen)
        parts = rel.parts
        if not parts:
            return ""
        if len(parts) == 1:
            return parts[0]
        return str(rel).replace("\\", "/")

    def _custom_languages(self) -> list[str]:
        return [
            self._lang_list.item(i).text()
            for i in range(self._lang_list.count())
        ]

    def _emit_changed(self, *_args) -> None:
        self._refresh_command_preview()
        self.stateChanged.emit()

    def _copy_command(self) -> None:
        QApplication.clipboard().setText(self._cmd_view.toPlainText())

    def _refresh_command_preview(self) -> None:
        state = self.collect_state()
        if self._resolver is not None:
            cli_args = build_cli_args(state)
            cmd = self._resolver.resolve(cli_args)
            self._cmd_view.setPlainText(cmd.display)
            return

        # 未注入 resolver 时保持旧行为（兼容既有测试）
        program = "python -m project_context"
        args = build_cli_args(state)
        self._cmd_view.setPlainText(format_command(program, args))

    # -- 对外 -------------------------------------------------------------

    def collect_state(self) -> RunState:
        if self._lang_auto.isChecked():
            mode = "auto"
        elif self._lang_all.isChecked():
            mode = "all"
        else:
            mode = "custom"

        return RunState(
            root=self._root_picker.path(),
            output=self._output_picker.path(),
            quiet=self._quiet_cb.isChecked(),
            languages_mode=mode,
            languages_custom=self._custom_languages(),
            detect_min_files=self._detect_spin.value(),
            exclude_globs=self._ex_globs.values(),
            exclude_dirs=self._ex_dirs.values(),
            exclude_dir_globs=self._ex_dir_globs.values(),
            exclude_suffixes=self._ex_suffixes.values(),
            include_content=self._cb_content.isChecked(),
            include_ast=self._cb_ast.isChecked(),
            include_git=self._cb_git.isChecked(),
            no_timestamp=self._cb_ts.isChecked(),
            max_file_size_kb=self._max_size.value(),
            max_git_commits=self._max_commits.value(),
            max_files_per_commit=self._max_files.value(),
        )

    def set_root(self, path: str) -> None:
        self._root_picker.set_path(path)
        # 强制重新推导输出
        self._output_picker.set_path("")
        self._on_root_changed(path)

    def set_resolver(self, resolver) -> None:
        """由 MainWindow 注入 RunnerResolver。"""
        self._resolver = resolver
        self._refresh_command_preview()

    def apply_settings(self, default_output_name: str) -> None:
        """由主窗口把用户偏好注入。"""
        self._default_output_name = default_output_name

    def set_enabled_for_running(self, running: bool) -> None:
        """运行中禁用配置控件。"""
        for w in self.findChildren(QWidget):
            if w is self._cmd_view:
                continue
            # 仅禁用输入类控件；按钮/标签无需处理
            if isinstance(w, (QPushButton,)):
                continue
            w.setEnabled(not running)
        # 命令预览始终可复制
        self._cmd_view.setEnabled(True)

    def output_path(self) -> str:
        return self._output_picker.path()


class _LanguageDialog(QDialog):
    """勾选内置语言。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("选择语言")
        self.setMinimumWidth(280)

        lay = QVBoxLayout(self)
        self._checks: dict[str, QCheckBox] = {}
        for lang in _BUILTIN_LANGUAGES:
            cb = QCheckBox(lang)
            self._checks[lang] = cb
            lay.addWidget(cb)

        bb = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    def selected(self) -> list[str]:
        return [k for k, cb in self._checks.items() if cb.isChecked()]