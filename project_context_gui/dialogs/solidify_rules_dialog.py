"""把 L3（本次追加）规则固化到 L2（项目配置）。"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore

try:
    import tomlkit
    HAS_TOMLKIT = True
except ImportError:
    HAS_TOMLKIT = False


class SolidifyRulesDialog(QDialog):
    """把本次追加的规则写入项目配置文件。"""

    def __init__(
        self,
        run_state,
        project_root: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._state = run_state
        self._root = project_root
        self._written: Path | None = None
        self._lang_paths: list = []
        self.setWindowTitle("固化到项目配置")
        self.setMinimumWidth(560)
        self._build_ui()
        self._refresh_preview()

    def written_path(self) -> Path | None:
        return self._written

    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        v = QVBoxLayout(self)
        v.setSpacing(10)

        v.addWidget(QLabel(
            "将把当前“本次追加”的规则写入项目配置文件。\n"
            "同名规则会跳过，不覆盖已有值。"
        ))

        # 目标文件
        v.addWidget(QLabel("<b>写入目标</b>"))

        self._target_group = QButtonGroup(self)
        common_dir = Path(self._root) / ".project_context"

        rb_common = QRadioButton("common.toml（通用，所有语言）")
        rb_common.setChecked(True)
        self._target_group.addButton(rb_common, 0)
        v.addWidget(rb_common)

        lang_dir = common_dir / "languages"
        if lang_dir.is_dir():
            for i, f in enumerate(sorted(lang_dir.glob("*.toml"))):
                rb = QRadioButton(f"languages/{f.name}")
                self._target_group.addButton(rb, i + 1)
                self._lang_paths.append(f)
                v.addWidget(rb)

        self._target_group.idToggled.connect(
            lambda _id, _on: self._refresh_preview()
        )

        # 规则摘要
        v.addWidget(QLabel("<b>将要写入的规则</b>"))
        self._summary = QLabel("")
        self._summary.setStyleSheet(
            "background:#f7f7f7; padding:6px; border-radius:4px;"
        )
        self._summary.setWordWrap(True)
        v.addWidget(self._summary)

        # 清空选项
        self._clear_after = QCheckBox(
            "写入后清空本次追加（避免重复）"
        )
        self._clear_after.setChecked(True)
        v.addWidget(self._clear_after)

        # 预览
        v.addWidget(QLabel("<b>预览（# + 表示新增行）</b>"))
        self._preview = QPlainTextEdit()
        self._preview.setReadOnly(True)
        self._preview.setFixedHeight(160)
        f = QFont("Consolas")
        f.setStyleHint(QFont.Monospace)
        self._preview.setFont(f)
        v.addWidget(self._preview)

        bb = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        bb.accepted.connect(self._on_accept)
        bb.rejected.connect(self.reject)
        v.addWidget(bb)

    # ------------------------------------------------------------------

    def _target_path(self) -> Path | None:
        tid = self._target_group.checkedId()
        base = Path(self._root) / ".project_context"
        if tid == 0:
            return base / "common.toml"
        if 0 < tid <= len(self._lang_paths):
            return self._lang_paths[tid - 1]
        return None

    def _refresh_preview(self) -> None:
        target = self._target_path()
        if target is None:
            return

        # 规则摘要
        lines = []
        if self._state.exclude_globs:
            lines.append(
                "排除文件 glob   " + ", ".join(self._state.exclude_globs)
            )
        if self._state.exclude_dirs:
            lines.append(
                "排除目录名      " + ", ".join(self._state.exclude_dirs)
            )
        if self._state.exclude_dir_globs:
            lines.append(
                "排除目录 glob   "
                + ", ".join(self._state.exclude_dir_globs)
            )
        if self._state.exclude_suffixes:
            lines.append(
                "排除后缀        " + ", ".join(self._state.exclude_suffixes)
            )
        self._summary.setText(
            "\n".join(lines) if lines else "（无规则可固化）"
        )

        self._preview.setPlainText(self._make_preview(target))

    def _make_preview(self, target: Path) -> str:
        existing: dict = {}
        if target.is_file():
            try:
                existing = tomllib.loads(
                    target.read_text(encoding="utf-8")
                )
            except Exception:
                existing = {}

        filter_sec = existing.get("filter", {}) or {}

        def merged(key: str, incoming: list):
            old = filter_sec.get(key, []) or []
            old_set = set(old)
            new = [x for x in incoming if x not in old_set]
            return list(old), new

        out = [f"# 目标文件：{target}", ""]
        out.append("[filter]")
        for key, incoming in (
            ("ignore_dirs", self._state.exclude_dirs),
            ("ignore_dir_globs", self._state.exclude_dir_globs),
            ("ignore_suffixes", self._state.exclude_suffixes),
            ("exclude_globs", self._state.exclude_globs),
        ):
            if not incoming:
                continue
            old, new = merged(key, incoming)
            allv = old + new
            line = (
                f"{key} = ["
                + ", ".join(f'"{x}"' for x in allv)
                + "]"
            )
            out.append(line)
            for n in new:
                out.append(f"#   + {n}")

        if len(out) == 3:
            out.append("# （无新增规则）")
        return "\n".join(out)

    # ------------------------------------------------------------------

    def _on_accept(self, silent: bool = False) -> None:
        target = self._target_path()
        if target is None:
            if not silent:
                QMessageBox.warning(
                    self, "目标无效", "未选择目标文件。"
                )
            return

        try:
            self._write(target)
        except Exception as e:
            if not silent:
                QMessageBox.critical(self, "写入失败", str(e))
            return

        self._written = target
        if self._clear_after.isChecked():
            self._state.exclude_dirs.clear()
            self._state.exclude_dir_globs.clear()
            self._state.exclude_suffixes.clear()
            self._state.exclude_globs.clear()
        self.accept()

    def try_accept(self) -> bool:
        """静默路径：给测试与程序化调用。返回是否成功。"""
        self._on_accept(silent=True)
        return self._written is not None

    def _write(self, target: Path) -> None:
        if not HAS_TOMLKIT:
            raise RuntimeError(
                "未安装 tomlkit，无法安全写入（会破坏注释与格式）。\n"
                "请执行：pip install tomlkit"
            )

        if target.is_file():
            text = target.read_text(encoding="utf-8")
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            text = "inherit_defaults = true\n\n[filter]\n"

        doc = tomlkit.parse(text)
        if "filter" not in doc:
            doc["filter"] = tomlkit.table()
        sec = doc["filter"]
        self._merge_into(sec, tomlkit.array)
        target.write_text(tomlkit.dumps(doc), encoding="utf-8")

    def _merge_into(self, sec, ArrayType) -> None:
        def ensure_array(key: str):
            if key not in sec:
                sec[key] = ArrayType()
                return sec[key]
            return sec[key]

        for key, incoming in (
            ("ignore_dirs", self._state.exclude_dirs),
            ("ignore_dir_globs", self._state.exclude_dir_globs),
            ("ignore_suffixes", self._state.exclude_suffixes),
            ("exclude_globs", self._state.exclude_globs),
        ):
            if not incoming:
                continue
            arr = ensure_array(key)
            existing = set(arr)
            for x in incoming:
                if x not in existing:
                    arr.append(x)