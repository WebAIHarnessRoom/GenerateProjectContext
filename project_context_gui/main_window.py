"""主窗口：空状态页 + 顶栏 + 三 Tab + 状态栏 + 状态机。"""
from __future__ import annotations

import sys
from enum import Enum
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor, QKeySequence, QPalette, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QStackedWidget,
    QStatusBar,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QCheckBox,
)

from project_context_gui.dialogs.settings_dialog import SettingsDialog
from project_context_gui.services.cli_runner import CliRunner
from project_context_gui.services.opener import open_folder
from project_context_gui.services.project_service import scan_project
from project_context_gui.services.runner_resolver import RunnerResolver
from project_context_gui.services.settings_service import SettingsService
from project_context_gui.state import RunState, build_cli_args
from project_context_gui.tabs.config_tab import ConfigTab
from project_context_gui.tabs.log_tab import LogTab
from project_context_gui.tabs.run_tab import RunTab
from project_context_gui.services.runner_resolver import (
    ERR_NO_ENGINE,
    ERR_NO_EXE,
    ERR_NO_PYTHON_INTERP,
    ERR_PY_MODULE_MISSING,
    ERR_PY_MODULE_PATH_INVALID,
    ERR_PY_POINTED_TO_PKG,
    RunnerResolver,
)

class AppState(Enum):
    EMPTY = "empty"
    READY = "ready"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ---------------------------------------------------------------------------
# 空状态页
# ---------------------------------------------------------------------------

class _EmptyPage(QWidget):
    openRequested = Signal()
    recentRequested = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        v = QVBoxLayout(self)
        v.setAlignment(Qt.AlignCenter)
        v.setSpacing(12)
        v.setContentsMargins(40, 40, 40, 40)

        title = QLabel("还没有打开项目")
        f = title.font()
        f.setPointSize(18)
        f.setBold(True)
        title.setFont(f)
        title.setAlignment(Qt.AlignCenter)
        v.addWidget(title)

        hint = QLabel(
            "点击下方按钮选择项目文件夹，或把文件夹拖到窗口任意位置"
        )
        hint.setStyleSheet("color:#666;")
        hint.setAlignment(Qt.AlignCenter)
        v.addWidget(hint)

        open_btn = QPushButton("📁 打开项目文件夹")
        open_btn.setFixedWidth(240)
        open_btn.setStyleSheet(
            "QPushButton { padding: 10px; font-size: 14px; "
            "background:#2d8f4e; color:white; border-radius: 4px; }"
            "QPushButton:hover { background:#257a42; }"
        )
        open_btn.clicked.connect(self.openRequested.emit)
        v.addWidget(open_btn, 0, Qt.AlignHCenter)

        self._recent_label = QLabel("最近打开")
        self._recent_label.setStyleSheet("color:#666; margin-top: 16px;")
        self._recent_label.setAlignment(Qt.AlignCenter)
        v.addWidget(self._recent_label)

        self._recent_list = QListWidget()
        self._recent_list.setMaximumWidth(560)
        self._recent_list.setMaximumHeight(180)
        self._recent_list.itemDoubleClicked.connect(self._on_recent_click)
        v.addWidget(self._recent_list, 0, Qt.AlignHCenter)

    def set_recent(self, paths: list[str]) -> None:
        self._recent_list.clear()
        for p in paths:
            item = QListWidgetItem(p)
            item.setToolTip(p)
            self._recent_list.addItem(item)
        has = bool(paths)
        self._recent_list.setVisible(has)
        self._recent_label.setVisible(has)

    def _on_recent_click(self, item: QListWidgetItem) -> None:
        self.recentRequested.emit(item.text())


# ---------------------------------------------------------------------------
# 主题 / 字体
# ---------------------------------------------------------------------------

def apply_theme(theme: str) -> None:
    app = QApplication.instance()
    if app is None:
        return
    if theme == "light":
        app.setStyle("Fusion")
        pal = QPalette()
        pal.setColor(QPalette.Window, QColor(0xF5, 0xF5, 0xF5))
        pal.setColor(QPalette.WindowText, QColor(0x22, 0x22, 0x22))
        pal.setColor(QPalette.Base, QColor(0xFF, 0xFF, 0xFF))
        pal.setColor(QPalette.AlternateBase, QColor(0xF0, 0xF0, 0xF0))
        pal.setColor(QPalette.Text, QColor(0x22, 0x22, 0x22))
        pal.setColor(QPalette.Button, QColor(0xE8, 0xE8, 0xE8))
        pal.setColor(QPalette.ButtonText, QColor(0x22, 0x22, 0x22))
        pal.setColor(QPalette.Highlight, QColor(0x2D, 0x8F, 0x4E))
        pal.setColor(QPalette.HighlightedText, QColor(0xFF, 0xFF, 0xFF))
        app.setPalette(pal)
    elif theme == "dark":
        app.setStyle("Fusion")
        pal = QPalette()
        pal.setColor(QPalette.Window, QColor(0x2B, 0x2B, 0x2B))
        pal.setColor(QPalette.WindowText, QColor(0xE0, 0xE0, 0xE0))
        pal.setColor(QPalette.Base, QColor(0x1E, 0x1E, 0x1E))
        pal.setColor(QPalette.AlternateBase, QColor(0x30, 0x30, 0x30))
        pal.setColor(QPalette.Text, QColor(0xE0, 0xE0, 0xE0))
        pal.setColor(QPalette.Button, QColor(0x3A, 0x3A, 0x3A))
        pal.setColor(QPalette.ButtonText, QColor(0xE0, 0xE0, 0xE0))
        pal.setColor(QPalette.Highlight, QColor(0x2D, 0x8F, 0x4E))
        pal.setColor(QPalette.HighlightedText, QColor(0xFF, 0xFF, 0xFF))
        app.setPalette(pal)
    # "system": 保持默认，不处理


def apply_font_size(size: int) -> None:
    app = QApplication.instance()
    if app is None:
        return
    font = app.font()
    font.setPointSize(size)
    app.setFont(font)


# ---------------------------------------------------------------------------
# 主窗口
# ---------------------------------------------------------------------------

class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("project_context GUI")
        self.resize(1000, 740)
        self.setAcceptDrops(True)

        self._settings = SettingsService()
        self._runner = CliRunner(self)
        self._resolver = RunnerResolver(self._settings)
        self._state = AppState.EMPTY
        self._started_at: float = 0.0
        self._tick_timer = QTimer(self)
        self._tick_timer.setInterval(500)
        self._tick_timer.timeout.connect(self._update_running_status)

        # 应用用户偏好（主题 / 字体）
        apply_theme(self._settings.theme)
        apply_font_size(self._settings.font_size)

        self._build_ui()
        self._connect_runner()
        self._install_shortcuts()
        self._restore_geometry()

        self._set_state(AppState.EMPTY)
        self._refresh_recent()
        self._update_mode_badge()

        # 恢复上次项目（可选）
        QTimer.singleShot(0, self._maybe_restore_last_project)

    # ------------------------------------------------------------------
    # UI 构建
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QWidget()
        v = QVBoxLayout(root)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)
        v.addWidget(self._build_body())
        self.setCentralWidget(root)

        # 状态栏
        bar = QStatusBar(self)
        self.setStatusBar(bar)
        self._status_label = QLabel("就绪")
        self._progress = QProgressBar()
        self._progress.setRange(0, 0)
        self._progress.setFixedWidth(160)
        self._progress.setVisible(False)
        self._open_folder_btn = QPushButton("打开输出文件夹")
        self._open_folder_btn.setEnabled(False)
        self._open_folder_btn.clicked.connect(self._on_open_output_folder)
        bar.addWidget(self._status_label, 1)
        bar.addPermanentWidget(self._progress)
        bar.addPermanentWidget(self._open_folder_btn)

    def _build_body(self) -> QWidget:
        body = QWidget()
        bv = QVBoxLayout(body)
        bv.setContentsMargins(0, 0, 0, 0)
        bv.setSpacing(0)

        bv.addWidget(self._build_topbar())

        # Tab 页
        self._tabs = QTabWidget()
        self._run_tab = RunTab()
        self._config_tab = ConfigTab()
        self._log_tab = LogTab()

        self._tabs.addTab(self._run_tab, "运行配置")
        self._tabs.addTab(self._config_tab, "配置文件")
        self._tabs.addTab(self._log_tab, "运行日志")

        # Tab 栏右上角：配置加载说明入口
        corner = QWidget()
        corner_lay = QHBoxLayout(corner)
        corner_lay.setContentsMargins(0, 0, 8, 0)
        corner_lay.setSpacing(0)

        self._cfg_help_btn = QToolButton()
        self._cfg_help_btn.setText("?")
        self._cfg_help_btn.setFixedSize(22, 22)
        self._cfg_help_btn.setCursor(Qt.PointingHandCursor)
        self._cfg_help_btn.setStyleSheet(
            "QToolButton {"
            "  border: 1px solid #b8d8b8; border-radius: 11px;"
            "  background: #eef6ee; color: #2d8f4e;"
            "  font-weight: bold;"
            "}"
            "QToolButton:hover { background: #dcefdc; }"
        )
        self._cfg_help_btn.setToolTip("查看配置加载说明")
        self._cfg_help_btn.clicked.connect(self._on_show_config_help)
        corner_lay.addWidget(self._cfg_help_btn)

        self._tabs.setCornerWidget(corner, Qt.TopRightCorner)

        self._tabs.currentChanged.connect(self._on_tab_changed)
        self._run_tab.stateChanged.connect(self._on_run_state_changed)

        # 注入 resolver（命令预览将反映实际执行方式）
        self._run_tab.set_resolver(self._resolver)

        tabs_page = QWidget()
        tpv = QVBoxLayout(tabs_page)
        tpv.setContentsMargins(0, 0, 0, 0)
        tpv.addWidget(self._tabs)

        # 空状态页
        self._empty_page = _EmptyPage()
        self._empty_page.openRequested.connect(self._on_open_project)
        self._empty_page.recentRequested.connect(self._load_project)

        # 堆栈
        self._stack = QStackedWidget()
        self._stack.addWidget(self._empty_page)   # 0
        self._stack.addWidget(tabs_page)          # 1

        bv.addWidget(self._stack, 1)
        return body

    def _build_topbar(self) -> QWidget:
        top = QWidget()
        top_lay = QHBoxLayout(top)
        top_lay.setContentsMargins(12, 10, 12, 10)

        self._open_btn = QPushButton("📁 打开项目")
        self._open_btn.clicked.connect(self._on_open_project)
        top_lay.addWidget(self._open_btn)

        # 最近项目下拉
        self._recent_combo = QComboBox()
        self._recent_combo.setMinimumWidth(160)
        self._recent_combo.setToolTip("最近打开的项目")
        self._recent_combo.activated.connect(self._on_recent_combo)
        top_lay.addWidget(self._recent_combo)

        self._path_label = QLabel("（未选择项目）")
        self._path_label.setStyleSheet("color: #555;")
        top_lay.addWidget(self._path_label, 1)

        # 执行引擎徽章（可点击 → 打开设置）
        self._mode_badge = QPushButton("⚙ 自动")
        self._mode_badge.setObjectName("modeBadge")
        self._mode_badge.setFlat(True)
        self._mode_badge.setCursor(Qt.PointingHandCursor)
        self._mode_badge.setStyleSheet(
            "QPushButton#modeBadge {"
            "  background: #eef6ee; border: 1px solid #b8d8b8;"
            "  border-radius: 10px; padding: 2px 10px;"
            "  color: #2d8f4e; font-size: 11px;"
            "}"
            "QPushButton#modeBadge:hover { background: #dcefdc; }"
        )
        self._mode_badge.setToolTip("点击切换执行引擎")
        self._mode_badge.clicked.connect(self._on_open_settings)
        top_lay.addWidget(self._mode_badge)

        self._rescan_btn = QPushButton("重新检测")
        self._rescan_btn.clicked.connect(self._on_rescan)
        self._rescan_btn.setEnabled(False)
        top_lay.addWidget(self._rescan_btn)

        self._settings_btn = QPushButton("⚙ 设置")
        self._settings_btn.clicked.connect(self._on_open_settings)
        top_lay.addWidget(self._settings_btn)

        self._run_btn = QPushButton("▶ 开始生成")
        self._run_btn.setStyleSheet(
            "QPushButton { background:#2d8f4e; color:white; "
            "font-weight:bold; padding: 6px 16px; border-radius: 4px; }"
            "QPushButton:disabled { background:#aaa; }"
        )
        self._run_btn.clicked.connect(self._on_run_clicked)
        top_lay.addWidget(self._run_btn)

        return top

    def _install_shortcuts(self) -> None:
        QShortcut(QKeySequence.Open, self,
                  activated=self._on_open_project)          # Ctrl+O
        QShortcut(QKeySequence.Save, self,
                  activated=self._on_save_shortcut)          # Ctrl+S
        QShortcut(QKeySequence.Refresh, self,
                  activated=self._on_rescan)                 # F5
        QShortcut(QKeySequence(Qt.Key_Escape), self,
                  activated=self._on_esc_shortcut)           # Esc
        QShortcut(QKeySequence("Ctrl+L"), self,
                  activated=self._log_tab.clear)             # Ctrl+L

    # ------------------------------------------------------------------
    # 信号连接
    # ------------------------------------------------------------------

    def _connect_runner(self) -> None:
        self._runner.started.connect(self._on_runner_started)
        self._runner.output_line.connect(self._on_runner_output)
        self._runner.finished.connect(self._on_runner_finished)
        self._runner.failed.connect(self._on_runner_failed)
        self._runner.cancelled.connect(self._on_runner_cancelled)

    # ------------------------------------------------------------------
    # 顶栏行为
    # ------------------------------------------------------------------

    def _on_open_project(self) -> None:
        start = self._settings.last_project or str(Path.home())
        path = QFileDialog.getExistingDirectory(
            self, "选择项目文件夹", start
        )
        if not path:
            return
        self._load_project(path)

    def _load_project(self, path: str) -> None:
        self._path_label.setText(path)
        self._rescan_btn.setEnabled(True)
        self._run_tab.set_root(path)
        self._settings.push_recent_project(path)
        self._settings.last_project = path
        self._refresh_recent()

        scan = scan_project(path)
        self._log_tab.append(f"已加载项目：{path}")
        self._log_tab.append("配置加载顺序：内置 → 项目 → 本次追加")

        # ① 内置
        try:
            from project_context_gui.services.config_introspection import (
                locate_builtin_config_dir,
            )
            mode = self._resolver.current_mode()
            exe_path = self._settings.exe_path or ""
            builtin_dir = locate_builtin_config_dir(
                mode=mode, exe_path=exe_path,
            )
            self._log_tab.append(
                f"① 内置规则：{builtin_dir or '未找到'}"
            )
        except Exception:
            self._log_tab.append("① 内置规则：未找到")

        # ② 项目
        if scan.has_project_context_dir:
            self._log_tab.append(
                f"② 项目配置：发现 .project_context/，"
                f"共 {len(scan.config_files)} 个文件"
                + (f"（{', '.join(scan.config_files)}）"
                   if scan.config_files else "")
            )
        else:
            self._log_tab.append(
                "② 项目配置：未发现 .project_context/，将只用内置规则"
            )

        # ③ 本次追加
        run_state = self._run_tab.collect_state()
        session_count = (
            len(run_state.exclude_globs)
            + len(run_state.exclude_dirs)
            + len(run_state.exclude_dir_globs)
            + len(run_state.exclude_suffixes)
        )
        self._log_tab.append(f"③ 本次追加：{session_count} 条")
        self._log_tab.append(
            "提示：点“运行配置”Tab 的“查看配置加载说明”可了解详情。"
        )

        if scan.detected_languages:
            self._log_tab.append(
                f"语言信号：{', '.join(scan.detected_languages)}"
            )
        if not scan.has_git:
            self._log_tab.append("未发现 .git，Git 历史章节将被跳过。")

        self._config_tab.set_root(path)
        self._set_state(AppState.READY)
        self._stack.setCurrentIndex(1)

    def _on_recent_combo(self, idx: int) -> None:
        if idx <= 0:
            return
        path = self._recent_combo.itemData(idx)
        if path and Path(path).is_dir():
            self._load_project(path)
        # 复位到占位项
        self._recent_combo.blockSignals(True)
        self._recent_combo.setCurrentIndex(0)
        self._recent_combo.blockSignals(False)

    def _refresh_recent(self) -> None:
        recent = self._settings.recent_projects

        # 下拉
        self._recent_combo.blockSignals(True)
        self._recent_combo.clear()
        self._recent_combo.addItem("最近项目…", None)
        for p in recent:
            self._recent_combo.addItem(Path(p).name or p, p)
        self._recent_combo.blockSignals(False)

        # 空状态页
        self._empty_page.set_recent(recent)

    def _maybe_restore_last_project(self) -> None:
        if not self._settings.restore_last_project:
            return
        last = self._settings.last_project
        if last and Path(last).is_dir():
            self._load_project(last)

    def _on_rescan(self) -> None:
        path = self._run_tab.collect_state().root
        if path:
            self._load_project(path)

    def _on_run_state_changed(self) -> None:
        pass

    def _on_tab_changed(self, idx: int) -> None:
        if self._state == AppState.RUNNING and idx == 1:
            self._tabs.setCurrentIndex(0)
            return

        if idx != 1 and self._config_tab.has_unsaved():
            ret = QMessageBox.question(
                self, "未保存",
                "配置文件有未保存修改，是否保存？",
                QMessageBox.Save | QMessageBox.Discard
                | QMessageBox.Cancel,
                QMessageBox.Save,
            )
            if ret == QMessageBox.Save:
                if not self._config_tab.try_save():
                    self._tabs.setCurrentIndex(1)
            elif ret == QMessageBox.Cancel:
                self._tabs.setCurrentIndex(1)

    # ------------------------------------------------------------------
    # 快捷键槽
    # ------------------------------------------------------------------

    def _on_save_shortcut(self) -> None:
        if self._tabs.currentWidget() is self._config_tab:
            self._config_tab.try_save()

    def _on_esc_shortcut(self) -> None:
        if self._state == AppState.RUNNING:
            self._request_cancel()

    # ------------------------------------------------------------------
    # 设置
    # ------------------------------------------------------------------

    def _on_open_settings(self) -> None:
        dlg = SettingsDialog(self._settings, self)
        if dlg.exec() != QDialog.Accepted:
            return
        self._settings.default_output_name = dlg.default_output_name()
        self._settings.runner_mode = dlg.runner_mode()
        self._settings.exe_path = dlg.exe_path()
        self._settings.python_executable = dlg.python_executable()
        self._settings.python_module_path = dlg.python_module_path()
        self._settings.theme = dlg.theme()
        self._settings.font_size = dlg.font_size()
        self._settings.restore_last_project = dlg.restore_last_project()

        # 重建 resolver，刷新 RunTab 预览与徽章
        self._resolver = RunnerResolver(self._settings)
        self._run_tab.set_resolver(self._resolver)
        self._update_mode_badge()
        self._apply_user_prefs()

    def _on_show_config_help(self) -> None:
        """由 Tab 栏角落按钮触发的配置加载说明。"""
        # 委托给 RunTab，避免逻辑重复
        self._run_tab._on_show_config_help()

    def _on_config_help_jump(self, target: str) -> None:
        """由配置加载说明对话框触发的 Tab 跳转。"""
        if target == "config_tab":
            self._tabs.setCurrentIndex(1)
        elif target == "run_tab_filter":
            self._tabs.setCurrentIndex(0)
            # 展开过滤面板
            try:
                self._run_tab._filter_block._toggle.setChecked(True)
            except Exception:
                pass

    def _apply_user_prefs(self) -> None:
        apply_theme(self._settings.theme)
        apply_font_size(self._settings.font_size)

    def _update_mode_badge(self) -> None:
        """根据 resolver 当前实际模式刷新徽章文案。"""
        try:
            mode = self._resolver.current_mode()
        except Exception:
            mode = "python"
        if mode == "exe":
            self._mode_badge.setText("📦 EXE")
        else:
            self._mode_badge.setText("🐍 Python")

    # ------------------------------------------------------------------
    # 运行/停止
    # ------------------------------------------------------------------

    def _on_run_clicked(self) -> None:
        if self._state == AppState.RUNNING:
            self._request_cancel()
            return
        self._start_run()

    def _start_run(self) -> None:
        state = self._run_tab.collect_state()
        if not state.root or not Path(state.root).is_dir():
            QMessageBox.warning(
                self, "无法运行", "请先选择一个有效的项目文件夹。"
            )
            return
        if not state.output:
            QMessageBox.warning(self, "无法运行", "请设置输出文件路径。")
            return

        if Path(state.output).exists():
            ret = QMessageBox.question(
                self,
                "覆盖确认",
                f"输出文件已存在：\n{state.output}\n\n是否覆盖？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if ret != QMessageBox.Yes:
                return

        cli_args = build_cli_args(state)
        cmd = self._resolver.resolve(cli_args)

        # 致命错误：弹分类对话框
        if cmd.has_error:
            self._show_engine_error(cmd, cli_args)
            return

        # 非致命警告
        if cmd.warning:
            self._log_tab.append(f"⚠ {cmd.warning}")

        self._log_tab.append(f"执行方式：{cmd.mode}")
        self._log_tab.append(f"命令：{cmd.display}")

        self._started_at = _now()
        self._tick_timer.start()
        self._set_state(AppState.RUNNING)
        self._progress.setVisible(True)
        self._tabs.setCurrentWidget(self._log_tab)

        self._runner.run(
            cmd.program, cmd.args,
            cwd=state.root,
            extra_env=cmd.env,
        )

    def _show_engine_error(self, cmd, cli_args) -> None:
        """根据 error_kind 弹不同对话框。"""
        kind = cmd.error_kind
        msg = cmd.error_message

        # EXE 可用性（用于"改用 EXE 模式"按钮）
        exe_available = self._resolver._find_exe() is not None

        if kind in (ERR_PY_MODULE_MISSING,
                    ERR_PY_MODULE_PATH_INVALID,
                    ERR_PY_POINTED_TO_PKG):
            self._show_python_module_error(kind, msg, exe_available, cli_args)
            return

        if kind == ERR_NO_PYTHON_INTERP:
            ret = QMessageBox.warning(
                self, "无法运行",
                msg + "\n\n是否打开设置？",
                QMessageBox.Open | QMessageBox.Cancel,
                QMessageBox.Open,
            )
            if ret == QMessageBox.Open:
                self._open_settings_focus_module()
            return

        if kind == ERR_NO_EXE:
            ret = QMessageBox.warning(
                self, "无法运行",
                msg + "\n\n是否打开设置？",
                QMessageBox.Open | QMessageBox.Cancel,
                QMessageBox.Open,
            )
            if ret == QMessageBox.Open:
                self._on_open_settings()
            return

        # 其它：通用
        QMessageBox.warning(self, "无法运行", msg or "无可用执行引擎。")
        self._on_open_settings()

    def _show_python_module_error(self, kind: str, msg: str,
                                   exe_available: bool, cli_args) -> None:
        """Python 模块相关错误的专用对话框。"""
        dlg = QMessageBox(self)
        dlg.setIcon(QMessageBox.Warning)
        dlg.setWindowTitle("Python 模块不可用")
        dlg.setText("无法使用 Python 模式")

        if kind == ERR_PY_POINTED_TO_PKG:
            dlg.setInformativeText(msg)
        elif kind == ERR_PY_MODULE_PATH_INVALID:
            dlg.setInformativeText(msg)
        else:  # ERR_PY_MODULE_MISSING
            dlg.setInformativeText(msg)

        # 记住选择（仅当 EXE 可用时显示）
        remember_cb = None
        if exe_available:
            remember_cb = QCheckBox("记住此选择（以后自动使用 EXE 模式）")
            dlg.setCheckBox(remember_cb)

        open_settings_btn = dlg.addButton("打开设置", QMessageBox.ActionRole)
        if exe_available:
            switch_btn = dlg.addButton(
                "改用 EXE 模式", QMessageBox.AcceptRole
            )
        else:
            switch_btn = None
        dlg.addButton("取消", QMessageBox.RejectRole)

        dlg.exec()

        clicked = dlg.clickedButton()
        if clicked is open_settings_btn:
            self._open_settings_focus_module()
            return
        if switch_btn is not None and clicked is switch_btn:
            remember = remember_cb is not None and remember_cb.isChecked()
            if remember:
                # 永久切换
                self._settings.runner_mode = "exe"
                self._resolver = RunnerResolver(self._settings)
                self._run_tab.set_resolver(self._resolver)
                self._update_mode_badge()
            else:
                # 仅本次：直接构造 EXE 命令
                cmd = self._resolver.resolve(cli_args, force_mode="exe")
                if not cmd.has_error and cmd.program:
                    self._execute_cmd(cmd, cli_args)
                    return
                QMessageBox.warning(
                    self, "无法运行", "EXE 模式也不可用。"
                )
                return
            # 永久切换后重跑
            self._start_run()

    def _open_settings_focus_module(self) -> None:
        from project_context_gui.dialogs.settings_dialog import (
            SettingsDialog,
        )
        dlg = SettingsDialog(
            self._settings, self, focus_module_path=True,
        )
        if dlg.exec() != QDialog.Accepted:
            return
        self._settings.default_output_name = dlg.default_output_name()
        self._settings.runner_mode = dlg.runner_mode()
        self._settings.exe_path = dlg.exe_path()
        self._settings.python_executable = dlg.python_executable()
        self._settings.python_module_path = dlg.python_module_path()
        self._settings.theme = dlg.theme()
        self._settings.font_size = dlg.font_size()
        self._settings.restore_last_project = dlg.restore_last_project()

        self._resolver = RunnerResolver(self._settings)
        self._run_tab.set_resolver(self._resolver)
        self._update_mode_badge()
        self._apply_user_prefs()

    def _execute_cmd(self, cmd, cli_args) -> None:
        """已知 cmd 无错误时，直接执行。"""
        if cmd.warning:
            self._log_tab.append(f"⚠ {cmd.warning}")
        self._log_tab.append(f"执行方式：{cmd.mode}")
        self._log_tab.append(f"命令：{cmd.display}")

        state = self._run_tab.collect_state()
        self._started_at = _now()
        self._tick_timer.start()
        self._set_state(AppState.RUNNING)
        self._progress.setVisible(True)
        self._tabs.setCurrentWidget(self._log_tab)

        self._runner.run(
            cmd.program, cmd.args,
            cwd=state.root,
            extra_env=cmd.env,
        )

    def _request_cancel(self, confirm: bool = True) -> None:
        if confirm:
            ret = QMessageBox.question(
                self,
                "停止运行",
                "确定要停止当前生成任务吗？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if ret != QMessageBox.Yes:
                return
        self._runner.cancel()

    # ------------------------------------------------------------------
    # Runner 回调
    # ------------------------------------------------------------------

    def _on_runner_started(self) -> None:
        self._log_tab.append("子进程已启动。")

    def _on_runner_output(self, line: str) -> None:
        self._log_tab.append(line)

    def _on_runner_finished(self, code: int) -> None:
        self._tick_timer.stop()
        self._progress.setVisible(False)

        if code == 0:
            self._set_state(AppState.SUCCESS)
            out = self._run_tab.output_path()
            elapsed = _now() - self._started_at
            self._log_tab.append(f"生成成功，耗时 {elapsed:.1f} 秒。")
            QMessageBox.information(
                self, "生成成功",
                f"耗时：{elapsed:.1f} 秒\n输出：\n{out}"
            )
        else:
            self._set_state(AppState.FAILED)
            self._log_tab.append(f"生成失败，退出码 {code}。")
            self._show_failure_dialog(code)
            self._tabs.setCurrentWidget(self._log_tab)

    def _show_failure_dialog(self, code: int) -> None:
        lines = [line for _lvl, line in self._log_tab._lines]
        tail = lines[-20:] if len(lines) > 20 else lines
        tail_text = "\n".join(tail)

        dlg = QMessageBox(self)
        dlg.setIcon(QMessageBox.Critical)
        dlg.setWindowTitle("生成失败")
        dlg.setText(f"子进程返回非零退出码：{code}")
        dlg.setInformativeText("最近日志（最多 20 行）：")
        dlg.setDetailedText(tail_text)
        dlg.setStandardButtons(QMessageBox.Ok)
        dlg.exec()

    def _on_runner_failed(self, msg: str) -> None:
        self._tick_timer.stop()
        self._progress.setVisible(False)
        self._set_state(AppState.FAILED)
        self._log_tab.append(f"[stderr] {msg}")
        # EXE 模式额外提示切换方式
        try:
            if self._resolver.current_mode() == "exe":
                self._log_tab.append(
                    "提示：可在设置中切换执行引擎，或指定其他 EXE 路径。"
                )
        except Exception:
            pass
        QMessageBox.critical(self, "启动失败", msg)

    def _on_runner_cancelled(self) -> None:
        self._tick_timer.stop()
        self._progress.setVisible(False)
        self._set_state(AppState.CANCELLED)
        self._log_tab.append("已取消。")

    # ------------------------------------------------------------------
    # 状态机与状态栏
    # ------------------------------------------------------------------

    def _set_state(self, state: AppState) -> None:
        self._state = state
        running = state == AppState.RUNNING

        if running:
            self._run_btn.setText("■ 停止")
            self._run_btn.setStyleSheet(
                "QPushButton { background:#c0392b; color:white; "
                "font-weight:bold; padding: 6px 16px; border-radius: 4px; }"
            )
        else:
            self._run_btn.setText("▶ 开始生成")
            self._run_btn.setStyleSheet(
                "QPushButton { background:#2d8f4e; color:white; "
                "font-weight:bold; padding: 6px 16px; border-radius: 4px; }"
                "QPushButton:disabled { background:#aaa; }"
            )
        self._run_btn.setEnabled(
            state in (AppState.READY, AppState.SUCCESS,
                      AppState.FAILED, AppState.CANCELLED,
                      AppState.RUNNING)
        )
        self._open_btn.setEnabled(not running)
        self._rescan_btn.setEnabled(
            not running and bool(self._run_tab.collect_state().root)
        )

        self._run_tab.set_enabled_for_running(running)

        if state == AppState.EMPTY:
            self._status_label.setText("就绪 —— 请先打开一个项目文件夹")
        elif state == AppState.READY:
            self._status_label.setText("就绪")
        elif state == AppState.RUNNING:
            self._status_label.setText("正在生成…")
        elif state == AppState.SUCCESS:
            self._status_label.setText("生成成功")
        elif state == AppState.FAILED:
            self._status_label.setText("生成失败，请查看日志")
        elif state == AppState.CANCELLED:
            self._status_label.setText("已取消")

        self._open_folder_btn.setEnabled(state == AppState.SUCCESS)

    def _update_running_status(self) -> None:
        if self._state != AppState.RUNNING:
            return
        elapsed = _now() - self._started_at
        self._status_label.setText(f"正在生成… 已运行 {elapsed:.1f} 秒")

    # ------------------------------------------------------------------
    # 打开输出
    # ------------------------------------------------------------------

    def _on_open_output_folder(self) -> None:
        out = self._run_tab.output_path()
        if not out:
            return
        try:
            open_folder(out)
        except Exception as e:
            QMessageBox.warning(self, "打开失败", str(e))

    # ------------------------------------------------------------------
    # 拖拽
    # ------------------------------------------------------------------

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.isLocalFile() and Path(url.toLocalFile()).is_dir():
                    event.acceptProposedAction()
                    return
        super().dragEnterEvent(event)

    def dropEvent(self, event) -> None:
        for url in event.mimeData().urls():
            if url.isLocalFile():
                p = Path(url.toLocalFile())
                if p.is_dir():
                    self._load_project(str(p))
                    event.acceptProposedAction()
                    return
        super().dropEvent(event)

    # ------------------------------------------------------------------
    # 几何恢复与关闭
    # ------------------------------------------------------------------

    def _restore_geometry(self) -> None:
        geo = self._settings.window_geometry
        if geo is not None:
            try:
                self.restoreGeometry(geo)
            except Exception:
                pass
        state = self._settings.window_state
        if state is not None:
            try:
                self.restoreState(state)
            except Exception:
                pass

    def closeEvent(self, event) -> None:
        # 未保存检查
        if self._config_tab.has_unsaved():
            ret = QMessageBox.question(
                self, "未保存",
                "配置文件有未保存修改，退出前是否保存？",
                QMessageBox.Save | QMessageBox.Discard
                | QMessageBox.Cancel,
                QMessageBox.Save,
            )
            if ret == QMessageBox.Save:
                if not self._config_tab.try_save():
                    event.ignore()
                    return
            elif ret == QMessageBox.Cancel:
                event.ignore()
                return

        # 运行中确认退出
        if self._state == AppState.RUNNING:
            ret = QMessageBox.question(
                self, "退出",
                "当前正在生成，确定退出？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if ret != QMessageBox.Yes:
                event.ignore()
                return
            self._tick_timer.stop()
            self._runner.cancel()
            if self._runner.is_running():
                self._runner.cancel()
            QApplication.processEvents()

        if self._runner.is_running():
            self._runner.cancel()
            QApplication.processEvents()

        # 保存几何
        try:
            self._settings.window_geometry = self.saveGeometry()
            self._settings.window_state = self.saveState()
        except Exception:
            pass

        event.accept()


def _now() -> float:
    import time
    return time.monotonic()