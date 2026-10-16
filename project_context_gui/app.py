"""QApplication 启动。"""
from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from project_context_gui.main_window import MainWindow
from project_context_gui.services.resource_path import find_resource


def _load_app_icon() -> QIcon | None:
    """加载应用图标。找不到返回 None。"""
    candidates = [
        "resources/app.ico",
        "resources/app.png",
        "resources/icon.ico",
        "resources/icon.png",
        # Nuitka 打包后若保持目录结构
        "app.ico",
        "app.png",
    ]
    path = find_resource(*candidates)
    if path is None:
        return None
    icon = QIcon(str(path))
    if icon.isNull():
        return None
    return icon


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv

    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(argv)
    app.setApplicationName("project_context GUI")
    app.setOrganizationName("project_context")

    # 设置应用图标（窗口标题栏 + 任务栏）
    icon = _load_app_icon()
    if icon is not None:
        app.setWindowIcon(icon)
    else:
        print(
            "[warn] 未找到应用图标，使用默认图标。",
            file=sys.stderr,
        )

    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())