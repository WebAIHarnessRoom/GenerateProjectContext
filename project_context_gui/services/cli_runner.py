"""QProcess 封装：执行 project_context CLI，实时读 stdout/stderr。"""
from __future__ import annotations

from PySide6.QtCore import QObject, QProcess, QProcessEnvironment, Signal


class CliRunner(QObject):
    """在独立子进程中执行 CLI。信号驱动，UI 友好。"""

    started = Signal()
    output_line = Signal(str)          # 每一行输出（stdout + stderr 已合并）
    finished = Signal(int)             # 退出码
    failed = Signal(str)               # QProcess 级错误（启动失败等）
    cancelled = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._proc = QProcess(self)
        self._proc.setProcessChannelMode(QProcess.MergedChannels)
        self._proc.readyReadStandardOutput.connect(self._on_ready_read)
        self._proc.finished.connect(self._on_finished)
        self._proc.errorOccurred.connect(self._on_error)

        self._cancelled = False
        self._buffer = ""

        # 强制 UTF-8（原 CLI 在 Windows 上会做兼容；这里再兜一层）
        env = QProcessEnvironment.systemEnvironment()
        env.insert("PYTHONIOENCODING", "utf-8")
        env.insert("PYTHONUNBUFFERED", "1")
        self._proc.setProcessEnvironment(env)

    # -- public API ------------------------------------------------------

    def is_running(self) -> bool:
        return self._proc.state() != QProcess.NotRunning

    def run(self, program: str, args: list[str], cwd: str | None = None) -> None:
        if self.is_running():
            return
        self._cancelled = False
        self._buffer = ""
        self._proc.setProgram(program)
        self._proc.setArguments(args)
        if cwd:
            self._proc.setWorkingDirectory(cwd)
        self._proc.start()
        if self._proc.waitForStarted(3000):
            self.started.emit()
        else:
            self.failed.emit("无法启动子进程，请检查 Python 解释器路径。")

    def cancel(self) -> None:
        if not self.is_running():
            return
        self._cancelled = True
        self._proc.terminate()
        if not self._proc.waitForFinished(3000):
            self._proc.kill()
            self._proc.waitForFinished(2000)

    # -- internals -------------------------------------------------------

    def _on_ready_read(self) -> None:
        raw = bytes(self._proc.readAllStandardOutput())
        text = self._buffer + raw.decode("utf-8", errors="replace")
        lines = text.split("\n")
        # 最后一段可能不完整，留到下次
        self._buffer = lines.pop() if lines else ""
        for line in lines:
            self.output_line.emit(line.rstrip("\r"))

    def _flush_buffer(self) -> None:
        if self._buffer:
            self.output_line.emit(self._buffer.rstrip("\r"))
            self._buffer = ""

    def _on_finished(self, code: int, _status) -> None:
        self._on_ready_read()      # 读掉残余
        self._flush_buffer()
        if self._cancelled:
            self.cancelled.emit()
        else:
            self.finished.emit(code)

    def _on_error(self, err) -> None:
        if err == QProcess.FailedToStart:
            self.failed.emit("子进程启动失败。")
        # 其它错误忽略（cancel 会触发 FailedToStart? 不会）