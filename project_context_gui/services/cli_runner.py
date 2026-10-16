"""QProcess 封装：执行 project_context CLI，实时读 stdout/stderr。"""
from __future__ import annotations

import logging

from PySide6.QtCore import QObject, QProcess, QProcessEnvironment, Signal

logger = logging.getLogger(__name__)


class CliRunner(QObject):
    """在独立子进程中执行 CLI。信号驱动，UI 友好。"""

    started = Signal()
    output_line = Signal(str)
    finished = Signal(int)
    failed = Signal(str)
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

    # -- public API ------------------------------------------------------

    def is_running(self) -> bool:
        return self._proc.state() != QProcess.NotRunning

    def run(
        self,
        program: str,
        args: list,
        cwd: str | None = None,
        extra_env: dict | None = None,
    ) -> None:
        logger.debug(
            ">>> CliRunner.run program=%s cwd=%s extra_env=%s",
            program, cwd, extra_env,
        )
        if self.is_running():
            logger.debug("CliRunner 已在运行，忽略本次请求")
            return
        self._cancelled = False
        self._buffer = ""

        env = QProcessEnvironment.systemEnvironment()
        env.insert("PYTHONIOENCODING", "utf-8")
        env.insert("PYTHONUNBUFFERED", "1")
        if extra_env:
            for k, v in extra_env.items():
                env.insert(str(k), str(v))
        self._proc.setProcessEnvironment(env)

        self._proc.setProgram(program)
        self._proc.setArguments(args)
        if cwd:
            self._proc.setWorkingDirectory(cwd)
        self._proc.start()
        if self._proc.waitForStarted(3000):
            logger.debug("CliRunner 子进程已启动")
            self.started.emit()
        else:
            logger.error("CliRunner 启动子进程失败")
            self.failed.emit("无法启动子进程，请检查解释器路径。")

    def cancel(self) -> None:
        logger.debug(">>> CliRunner.cancel is_running=%s", self.is_running())
        if not self.is_running():
            return
        self._cancelled = True
        self._proc.terminate()
        if not self._proc.waitForFinished(3000):
            logger.warning("terminate 超时，改用 kill")
            self._proc.kill()
            self._proc.waitForFinished(2000)

    # -- internals -------------------------------------------------------

    def _on_ready_read(self) -> None:
        raw = bytes(self._proc.readAllStandardOutput())
        text = self._buffer + raw.decode("utf-8", errors="replace")
        lines = text.split("\n")
        self._buffer = lines.pop() if lines else ""
        for line in lines:
            self.output_line.emit(line.rstrip("\r"))

    def _flush_buffer(self) -> None:
        if self._buffer:
            self.output_line.emit(self._buffer.rstrip("\r"))
            self._buffer = ""

    def _on_finished(self, code: int, _status) -> None:
        logger.debug(
            "CliRunner 子进程结束 code=%s cancelled=%s",
            code, self._cancelled,
        )
        self._on_ready_read()
        self._flush_buffer()
        if self._cancelled:
            self.cancelled.emit()
        else:
            self.finished.emit(code)

    def _on_error(self, err) -> None:
        if err == QProcess.FailedToStart:
            logger.error("CliRunner 子进程启动失败")
            self.failed.emit("子进程启动失败。")