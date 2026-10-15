"""解析实际执行命令：python -m project_context 或 generate-project-context.exe。"""
from __future__ import annotations

import shutil
import sys
from dataclasses import dataclass
from pathlib import Path


EXE_NAME = "generate-project-context.exe"


# ---------------------------------------------------------------------------
# 命令模型
# ---------------------------------------------------------------------------

@dataclass
class ResolvedCommand:
    """一次运行的完整命令。"""
    program: str          # 完整程序路径
    args: list[str]       # 完整参数列表
    mode: str             # "python" | "exe"
    display: str          # 用于命令预览的可读字符串

    @property
    def is_exe(self) -> bool:
        return self.mode == "exe"


# ---------------------------------------------------------------------------
# 拼装工具
# ---------------------------------------------------------------------------

def _quote_join(items: list[str]) -> str:
    return " ".join(f'"{a}"' if " " in a else a for a in items)


def make_python_command(cli_args: list[str],
                        python_path: str | None = None) -> ResolvedCommand:
    """python -m project_context <cli_args>"""
    python = python_path or sys.executable
    args = ["-m", "project_context", *cli_args]
    display_parts = [python] + [
        f'"{a}"' if " " in a else a for a in args if a
    ]
    return ResolvedCommand(
        program=python,
        args=args,
        mode="python",
        display=" ".join(display_parts),
    )


def make_exe_command(cli_args: list[str],
                     exe_path: str) -> ResolvedCommand:
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
# 解析器
# ---------------------------------------------------------------------------

class RunnerResolver:
    """根据用户设置与可用性，把 cli_args 解析为完整命令。

    不负责执行，只负责"选哪一种方式 + 拼好命令行"。
    """

    def __init__(self, settings) -> None:
        self._settings = settings

    # -- 对外 -----------------------------------------------------------

    def resolve(self, cli_args: list[str]) -> ResolvedCommand:
        """核心方法：返回一个 ResolvedCommand。"""
        mode = self._settings.runner_mode
        if mode == "auto":
            mode = self._auto_detect_mode()

        if mode == "exe":
            exe = self._find_exe()
            if exe is not None:
                return make_exe_command(cli_args, str(exe))
            # exe 找不到：静默回退 Python，由调用者视需要提示
            return self._make_python(cli_args, fallback_from="exe")

        return self._make_python(cli_args)

    # -- 探测 -----------------------------------------------------------

    def _auto_detect_mode(self) -> str:
        if self._find_exe() is not None:
            return "exe"
        return "python"

    def _find_exe(self) -> Path | None:
        # 1. 用户显式设置
        custom = self._settings.exe_path
        if custom:
            p = Path(custom)
            if p.is_file():
                return p

        # 2. GUI 可执行文件同目录（frozen 时）
        if getattr(sys, "frozen", False):
            beside = Path(sys.executable).parent / EXE_NAME
            if beside.is_file():
                return beside

        # 3. PATH
        found = shutil.which(EXE_NAME)
        if found:
            return Path(found)

        return None

    # -- 内部拼装 --------------------------------------------------------

    def _make_python(self, cli_args: list[str],
                     fallback_from: str | None = None) -> ResolvedCommand:
        python = self._settings.python_executable or sys.executable
        cmd = make_python_command(cli_args, python_path=python)
        return cmd

    # -- 状态检查（供 UI 使用） -------------------------------------------

    def current_mode(self) -> str:
        """返回 UI 应展示的模式名：实际使用的，不是设置值。"""
        mode = self._settings.runner_mode
        if mode == "auto":
            return self._auto_detect_mode()
        return mode

    def describe_exe_status(self) -> tuple[bool, str]:
        """返回 (是否可用, 描述)。供设置对话框状态行使用。"""
        exe = self._find_exe()
        if exe is None:
            return False, "⚠ 未找到 generate-project-context.exe"
        return True, f"✅ 已找到：{exe}"

    def describe_python_status(self) -> tuple[bool, str]:
        python = self._settings.python_executable or sys.executable
        if not python:
            return False, "⚠ 未指定解释器"
        if not Path(python).is_file():
            return False, f"⚠ 路径不存在：{python}"
        return True, f"✅ 可用：{python}"