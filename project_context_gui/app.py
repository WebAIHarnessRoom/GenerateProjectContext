"""QApplication 启动。"""
from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from project_context_gui.main_window import MainWindow


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv

    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(argv)
    app.setApplicationName("project_context GUI")
    app.setOrganizationName("project_context")

    win = MainWindow()
    win.show()
    return app.exec()