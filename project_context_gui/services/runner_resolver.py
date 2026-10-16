"""解析实际执行命令：python -m project_context 或 generate-project-context.exe。"""
from __future__ import annotations

import os
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path


EXE_NAME = "generate-project-context.exe"


# ---------------------------------------------------------------------------
# 命令模型
# ---------------------------------------------------------------------------

@dataclass
class ResolvedCommand:
    """一次运行的完整命令。"""
    program: str
    args: list
    mode: str
    display: str
    warning: str = ""            # 非致命提示（记日志）
    error_kind: str = ""         # 致命错误分类："" 表示无错
    error_message: str = ""      # 致命错误消息（用于对话框）
    env: dict = field(default_factory=dict)

    @property
    def is_exe(self) -> bool:
        return self.mode == "exe"

    @property
    def has_error(self) -> bool:
        return bool(self.error_kind)


# 错误分类常量
ERR_NO_ENGINE = "no_engine"
ERR_NO_PYTHON_INTERP = "no_python_interp"
ERR_PY_MODULE_MISSING = "py_module_missing"
ERR_PY_MODULE_PATH_INVALID = "py_module_path_invalid"
ERR_PY_POINTED_TO_PKG = "py_pointed_to_pkg"
ERR_NO_EXE = "no_exe"


# ---------------------------------------------------------------------------
# 拼装工具
# ---------------------------------------------------------------------------

def _quote_join(items: list) -> str:
    return " ".join(f'"{a}"' if " " in a else a for a in items)


def make_python_command(
    cli_args: list,
    python_path: str | None = None,
    module_root: str | None = None,
) -> ResolvedCommand:
    """python -m project_context <cli_args>

    module_root 是 project_context 的父目录，注入子进程 PYTHONPATH。
    """
    python = python_path or sys.executable
    args = ["-m", "project_context", *cli_args]
    display_parts = [python] + [
        f'"{a}"' if " " in a else a for a in args if a
    ]

    env: dict = {}
    if module_root:
        existing = os.environ.get("PYTHONPATH", "")
        env["PYTHONPATH"] = (
            module_root if not existing
            else (module_root + os.pathsep + existing)
        )

    return ResolvedCommand(
        program=python,
        args=args,
        mode="python",
        display=" ".join(display_parts),
        env=env,
    )


def make_exe_command(cli_args: list, exe_path: str) -> ResolvedCommand:
    """<exe_path> <cli_args>"""
    exe_str = str(exe_path)
    prefix = f'"{exe_str}"' if " " in exe_str else exe_str
    rest = _quote_join([a for a in cli_args if a])
    display = prefix if not rest else f"{prefix} {rest}"
    return ResolvedCommand(
        program=exe_str,
        args=list(cli_args),
        mode="exe",
        display=display,
    )


# ---------------------------------------------------------------------------
# 打包环境探测
# ---------------------------------------------------------------------------

def is_frozen() -> bool:
    if getattr(sys, "frozen", False):
        return True
    try:
        import __compiled__  # type: ignore  # noqa: F401
        return True
    except ImportError:
        return False


def program_dir() -> Path:
    """返回当前运行的程序目录。

    - PyInstaller：EXE 所在目录（不是 _internal）
    - Nuitka：__compiled__.containing_dir
    - 源码运行：项目根
    """
    try:
        import __compiled__  # type: ignore
        return Path(__compiled__.containing_dir)
    except ImportError:
        pass

    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent

    # 源码运行：project_context_gui/services/runner_resolver.py → 项目根
    return Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# Python 模块路径探测
# ---------------------------------------------------------------------------

def find_python_module_root(settings) -> tuple:
    """探测 project_context 的父目录。

    返回 (root_or_None, status_code, message)
    status_code:
        "ok_user"              用户指定，有效
        "ok_program"           程序目录，有效
        "user_pointed_to_pkg"  用户填的是包目录本身
        "user_path_invalid"    用户路径下没有 project_context/
        "not_found"            未找到
    """
    # ① 用户指定
    user_path = (getattr(settings, "python_module_path", "") or "").strip()
    if user_path:
        p = Path(user_path)
        if not p.is_absolute():
            return None, "user_path_invalid", (
                f"指定的路径不是绝对路径：{p}\n\n"
                "请填写 project_context 的父目录的绝对路径。"
            )
        if (p / "project_context" / "__init__.py").is_file():
            return str(p), "ok_user", f"✅ 已找到：{p}（用户指定）"
        # 用户填了包目录本身？
        if p.name == "project_context" and (p / "__init__.py").is_file():
            return None, "user_pointed_to_pkg", (
                f"你指定的是 project_context 包目录本身：\n  {p}\n\n"
                f"请改填它的父目录：\n  {p.parent}\n\n"
                "判定方法：打开该目录，应能看到 project_context/ 子目录，"
                "而不是直接看到 __init__.py。"
            )
        return None, "user_path_invalid", (
            f"指定的路径下未找到 project_context 模块：\n  {p}\n\n"
            f"该目录下应包含：\n  {p / 'project_context' / '__init__.py'}"
        )

    # ② 程序目录
    d = program_dir()
    if (d / "project_context" / "__init__.py").is_file():
        return str(d), "ok_program", f"✅ 已找到：{d}（程序目录）"

    # ③ 未找到
    return None, "not_found", (
        "未找到 project_context 模块，Python 模式不可用。"
    )


def has_configs_dir(module_root: str) -> bool:
    """检查 project_context/configs/common.toml 是否存在。"""
    p = Path(module_root) / "project_context" / "configs" / "common.toml"
    return p.is_file()


# ---------------------------------------------------------------------------
# 解析器
# ---------------------------------------------------------------------------

class RunnerResolver:
    """根据用户设置与可用性，把 cli_args 解析为完整命令。"""

    def __init__(self, settings) -> None:
        self._settings = settings

    # -- 对外 -----------------------------------------------------------

    def resolve(self, cli_args: list, force_mode: str | None = None) -> ResolvedCommand:
        """核心方法。force_mode 用于"仅本次运行"覆盖。"""
        mode = force_mode or self._settings.runner_mode
        if mode == "auto":
            return self._resolve_auto(cli_args)
        if mode == "python":
            return self._resolve_python(cli_args)
        return self._resolve_exe(cli_args)

    # -- 各模式解析 -----------------------------------------------------

    def _resolve_auto(self, cli_args: list) -> ResolvedCommand:
        """auto：优先本机默认方式，另一方式作为回退。"""
        if is_frozen():
            # 打包环境：优先后端 EXE
            exe = self._find_exe()
            if exe is not None:
                return make_exe_command(cli_args, str(exe))
            # 回退 Python
            return self._try_python(cli_args, fallback_reason="EXE 不可用")
        else:
            # 源码环境：优先 Python
            if self._python_usable():
                return self._make_python(cli_args)
            exe = self._find_exe()
            if exe is not None:
                cmd = make_exe_command(cli_args, str(exe))
                cmd.warning = "Python 模式不可用，已回退到 EXE 模式。"
                return cmd
            return self._error(
                cli_args, ERR_NO_ENGINE,
                "无可用执行引擎。\n\n"
                "请打开设置配置 EXE 路径或 Python 环境。"
            )

    def _resolve_python(self, cli_args: list) -> ResolvedCommand:
        """显式 Python 模式：不可用时报错，不静默回退。"""
        interp_err = self._check_python_interp()
        if interp_err:
            return interp_err(cli_args)

        root, code, msg = find_python_module_root(self._settings)
        if root is None:
            err_kind = {
                "user_pointed_to_pkg": ERR_PY_POINTED_TO_PKG,
                "user_path_invalid": ERR_PY_MODULE_PATH_INVALID,
                "not_found": ERR_PY_MODULE_MISSING,
            }.get(code, ERR_PY_MODULE_MISSING)

            # 组装完整的错误消息
            extra = ""
            if code == "not_found":
                tried = []
                up = (getattr(self._settings, "python_module_path", "") or "").strip()
                if up:
                    tried.append(f"• 设置中指定的路径：{up}")
                else:
                    tried.append("• 设置中指定的路径：（未指定）")
                tried.append(f"• 程序目录：{program_dir()}")
                extra = "已尝试以下位置：\n" + "\n".join(tried) + "\n\n"
                extra += (
                    "解决方法（任选其一）：\n"
                    f"  1. 把整个 project_context/ 目录复制到\n"
                    f"     {program_dir()}\n"
                    "  2. 或在本设置中指定 project_context 的父目录\n"
                    "  3. 或改用 EXE 模式（无需 Python 环境）"
                )

            return self._error(
                cli_args, err_kind, extra or msg
            )

        # 找到模块，注入 PYTHONPATH
        cmd = self._make_python(cli_args, module_root=root)

        # configs/ 缺失时给警告，不阻断
        if not has_configs_dir(root):
            cmd.warning = (
                "检测到 project_context 模块，但缺少 configs/ 目录。"
                "内置排除规则可能不完整。"
            )
        return cmd

    def _resolve_exe(self, cli_args: list) -> ResolvedCommand:
        """显式 EXE 模式。"""
        exe = self._find_exe()
        if exe is not None:
            return make_exe_command(cli_args, str(exe))

        # 回退 Python
        if self._python_usable():
            cmd = self._make_python(cli_args)
            cmd.warning = "未找到 generate-project-context.exe，已回退到 Python 模式。"
            return cmd

        return self._error(
            cli_args, ERR_NO_EXE,
            f"未找到 generate-project-context.exe。\n\n"
            f"请在设置中指定路径，或配置 Python 环境。"
        )

    # -- 内部工具 -------------------------------------------------------

    def _try_python(self, cli_args: list, fallback_reason: str = "") -> ResolvedCommand:
        """auto 模式下尝试 Python 作为回退。"""
        interp_err = self._check_python_interp()
        if interp_err:
            return interp_err(cli_args)

        root, code, msg = find_python_module_root(self._settings)
        if root is None:
            err_kind = {
                "user_pointed_to_pkg": ERR_PY_POINTED_TO_PKG,
                "user_path_invalid": ERR_PY_MODULE_PATH_INVALID,
                "not_found": ERR_PY_MODULE_MISSING,
            }.get(code, ERR_PY_MODULE_MISSING)
            return self._error(cli_args, err_kind, msg)

        cmd = self._make_python(cli_args, module_root=root)
        if fallback_reason:
            cmd.warning = f"已使用 Python 模式（{fallback_reason}）。"
        if not has_configs_dir(root):
            cmd.warning = (cmd.warning + " " if cmd.warning else "") + \
                "project_context 缺少 configs/ 目录，内置规则可能不完整。"
        return cmd

    def _check_python_interp(self):
        """返回 None（OK）或一个"制造错误命令"的工厂。"""
        if not is_frozen():
            return None
        custom = (getattr(self._settings, "python_executable", "") or "").strip()
        if not custom:
            def _err(cli_args):
                return self._error(
                    cli_args, ERR_NO_PYTHON_INTERP,
                    "打包运行的 GUI 不含 Python 解释器。\n\n"
                    "请在设置中指定一个可用的 Python 解释器，"
                    "或改用 EXE 模式。"
                )
            return _err
        if not Path(custom).is_file():
            def _err(cli_args):
                return self._error(
                    cli_args, ERR_NO_PYTHON_INTERP,
                    f"指定的 Python 解释器不存在：\n  {custom}\n\n"
                    "请在设置中重新指定。"
                )
            return _err
        return None

    def _python_usable(self) -> bool:
        """Python 模式是否整体可用（解释器 + 模块）。"""
        if self._check_python_interp():
            return False
        root, _code, _msg = find_python_module_root(self._settings)
        return root is not None

    def _find_exe(self) -> Path | None:
        custom = (getattr(self._settings, "exe_path", "") or "").strip()
        if custom:
            p = Path(custom)
            if p.is_file():
                return p

        exe_dir = program_dir()
        beside = exe_dir / EXE_NAME
        if beside.is_file():
            return beside

        found = shutil.which(EXE_NAME)
        if found:
            return Path(found)

        return None

    def _make_python(self, cli_args: list, module_root: str | None = None) -> ResolvedCommand:
        python = (getattr(self._settings, "python_executable", "") or "").strip()
        if not python:
            python = sys.executable
        if module_root is None:
            root, _code, _msg = find_python_module_root(self._settings)
            module_root = root
        return make_python_command(
            cli_args, python_path=python, module_root=module_root,
        )

    def _error(self, cli_args: list, kind: str, message: str) -> ResolvedCommand:
        return ResolvedCommand(
            program="",
            args=list(cli_args),
            mode="",
            display="（无可用执行引擎）",
            error_kind=kind,
            error_message=message,
        )

    # -- 状态查询（供 UI） ----------------------------------------------

    def current_mode(self) -> str:
        """返回 UI 展示的实际模式名。"""
        mode = self._settings.runner_mode
        if mode == "auto":
            return "exe" if is_frozen() and self._find_exe() else "python"
        if mode == "python" and not self._python_usable():
            if self._find_exe() is not None:
                return "exe"
        if mode == "exe" and self._find_exe() is None:
            if self._python_usable():
                return "python"
        return mode

    def describe_exe_status(self) -> tuple:
        exe = self._find_exe()
        if exe is None:
            return False, "⚠ 未找到 generate-project-context.exe"
        return True, f"✅ 已找到：{exe}"

    def describe_python_status(self) -> tuple:
        if is_frozen():
            custom = (getattr(self._settings, "python_executable", "") or "").strip()
            if not custom:
                return False, (
                    "⚠ 打包运行时必须显式指定 Python 解释器，"
                    "否则 Python 模式不可用"
                )
            if not Path(custom).is_file():
                return False, f"⚠ 路径不存在：{custom}"
            return True, f"✅ 可用：{custom}"

        python = (getattr(self._settings, "python_executable", "") or "").strip()
        if not python:
            python = sys.executable
        if not Path(python).is_file():
            return False, f"⚠ 路径不存在：{python}"
        return True, f"✅ 可用：{python}"

    def describe_module_status(self) -> tuple:
        """返回 (是否可用, 描述)。供设置里 Python 模块路径状态行使用。"""
        root, code, msg = find_python_module_root(self._settings)
        if root is not None:
            return True, msg
        return False, msg