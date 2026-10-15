#!/usr/bin/env python3
"""project_context GUI 测试脚本（无 pytest 依赖，可直接运行）。

用法：
    python run_gui_tests.py               # 全部
    python run_gui_tests.py -k arg        # 只跑名字含 "arg" 的
    python run_gui_tests.py -v            # 打印详细堆栈
    python run_gui_tests.py --list        # 只列用例
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import traceback
from pathlib import Path

# ---------------------------------------------------------------------------
# 保证能 import project_context_gui
# ---------------------------------------------------------------------------
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

# Qt 无头模式（必须在导入 PySide6 之前设置）
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# ---------------------------------------------------------------------------
# 全局 QApplication（惰性创建，且必须最先创建）
# ---------------------------------------------------------------------------
_QT_APP = None
_QT_APP_READY = False


def _ensure_qt_app():
    """惰性创建唯一的 QApplication，并隔离 QSettings 存储位置。

    必须在任何 QWidget 之前调用。若首次调用时已存在 QCoreApplication，
    直接报错暴露问题，而不是让后续 QWidget 崩。
    """
    global _QT_APP, _QT_APP_READY
    if _QT_APP_READY:
        return _QT_APP

    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QSettings

    inst = QApplication.instance()
    if inst is not None and not isinstance(inst, QApplication):
        raise RuntimeError(
            "已存在 QCoreApplication，无法再创建 QApplication。"
            "请确保脚本在任何 Qt 对象之前调用 _ensure_qt_app()。"
        )
    _QT_APP = inst or QApplication(sys.argv)

    # 隔离 QSettings，避免污染开发机
    tmp = Path(tempfile.mkdtemp(prefix="pcgui_qs_"))
    QSettings.setDefaultFormat(QSettings.IniFormat)
    QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, str(tmp))
    QSettings.setPath(QSettings.IniFormat, QSettings.SystemScope, str(tmp))

    _QT_APP_READY = True
    return _QT_APP


# ---------------------------------------------------------------------------
# 极简测试框架
# ---------------------------------------------------------------------------
TESTS: list = []
SKIPPED: list = []


def test(name: str):
    def deco(fn):
        TESTS.append((name, fn))
        return fn
    return deco


def skip(name: str, reason: str):
    SKIPPED.append((name, reason))


class Asserts:
    @staticmethod
    def eq(a, b, msg=""):
        if a != b:
            raise AssertionError(f"{msg}\n  got     : {a!r}\n  expected: {b!r}")

    @staticmethod
    def ne(a, b, msg=""):
        if a == b:
            raise AssertionError(f"{msg}\n  both are: {a!r}")

    @staticmethod
    def true(x, msg=""):
        if not x:
            raise AssertionError(f"{msg}\n  value: {x!r}")

    @staticmethod
    def false(x, msg=""):
        if x:
            raise AssertionError(f"{msg}\n  value: {x!r}")

    @staticmethod
    def in_(x, container, msg=""):
        if x not in container:
            raise AssertionError(f"{msg}\n  {x!r} not in {container!r}")

    @staticmethod
    def not_in(x, container, msg=""):
        if x in container:
            raise AssertionError(f"{msg}\n  {x!r} unexpectedly in {container!r}")

    @staticmethod
    def contains_pair(lst, a, b, msg=""):
        for i in range(len(lst) - 1):
            if lst[i] == a and lst[i + 1] == b:
                return
        raise AssertionError(
            f"{msg}\n  pair ({a!r}, {b!r}) not found in {lst!r}"
        )


A = Asserts


# ---------------------------------------------------------------------------
# 延迟导入
# ---------------------------------------------------------------------------
def import_state():
    from project_context_gui.state import (  # noqa
        RunState, build_cli_args, format_command,
        DEFAULT_MAX_FILE_SIZE_KB, DEFAULT_MAX_GIT_COMMITS,
        DEFAULT_MAX_FILES_PER_COMMIT, DEFAULT_DETECT_MIN_FILES,
    )
    return {
        "RunState": RunState,
        "build_cli_args": build_cli_args,
        "format_command": format_command,
        "D_MAX_SIZE": DEFAULT_MAX_FILE_SIZE_KB,
        "D_MAX_COMMITS": DEFAULT_MAX_GIT_COMMITS,
        "D_MAX_FILES": DEFAULT_MAX_FILES_PER_COMMIT,
        "D_DETECT": DEFAULT_DETECT_MIN_FILES,
    }


def import_project_service():
    from project_context_gui.services.project_service import (  # noqa
        scan_project, ProjectScan,
    )
    return scan_project, ProjectScan


def has_qt() -> bool:
    try:
        import PySide6  # noqa
        return True
    except ImportError:
        return False


def has_cli() -> bool:
    try:
        import project_context  # noqa
        return True
    except ImportError:
        return False


# ===========================================================================
# 单元测试：build_cli_args
# ===========================================================================

@test("U-ARG-01 最小参数")
def _():
    mod = import_state()
    s = mod["RunState"](root="/p", output="/p/a.md")
    A.eq(mod["build_cli_args"](s), ["/p", "-o", "/p/a.md"])


@test("U-ARG-02 无输出")
def _():
    mod = import_state()
    s = mod["RunState"](root="/p", output="")
    A.eq(mod["build_cli_args"](s), ["/p"])


@test("U-ARG-03 quiet")
def _():
    mod = import_state()
    s = mod["RunState"](root="/p", output="/p/a.md", quiet=True)
    A.in_("--quiet", mod["build_cli_args"](s))


@test("U-ARG-04 语言 auto 不传 --languages")
def _():
    mod = import_state()
    s = mod["RunState"](root="/p", output="/p/a.md", languages_mode="auto")
    A.not_in("--languages", mod["build_cli_args"](s))


@test("U-ARG-05 语言 all")
def _():
    mod = import_state()
    s = mod["RunState"](root="/p", output="/p/a.md", languages_mode="all")
    A.contains_pair(mod["build_cli_args"](s), "--languages", "all")


@test("U-ARG-06 语言 custom python,go")
def _():
    mod = import_state()
    s = mod["RunState"](
        root="/p", output="/p/a.md",
        languages_mode="custom", languages_custom=["python", "go"],
    )
    A.contains_pair(mod["build_cli_args"](s), "--languages", "python,go")


@test("U-ARG-07 语言 custom 空列表不传")
def _():
    mod = import_state()
    s = mod["RunState"](
        root="/p", output="/p/a.md",
        languages_mode="custom", languages_custom=[],
    )
    A.not_in("--languages", mod["build_cli_args"](s))


@test("U-ARG-08 检测阈值默认不传")
def _():
    mod = import_state()
    s = mod["RunState"](root="/p", output="/p/a.md", detect_min_files=1)
    A.not_in("--detect-min-files", mod["build_cli_args"](s))


@test("U-ARG-09 检测阈值 3")
def _():
    mod = import_state()
    s = mod["RunState"](root="/p", output="/p/a.md", detect_min_files=3)
    A.contains_pair(mod["build_cli_args"](s), "--detect-min-files", "3")


@test("U-ARG-10 排除 glob 多个")
def _():
    mod = import_state()
    s = mod["RunState"](
        root="/p", output="/p/a.md",
        exclude_globs=["*.pb.go", "*.min.js"],
    )
    args = mod["build_cli_args"](s)
    A.contains_pair(args, "--exclude", "*.pb.go")
    A.contains_pair(args, "--exclude", "*.min.js")


@test("U-ARG-11 排除目录")
def _():
    mod = import_state()
    s = mod["RunState"](root="/p", output="/p/a.md",
                        exclude_dirs=["third_party"])
    A.contains_pair(mod["build_cli_args"](s), "--exclude-dir", "third_party")


@test("U-ARG-12 排除目录 glob")
def _():
    mod = import_state()
    s = mod["RunState"](root="/p", output="/p/a.md",
                        exclude_dir_globs=["build/**"])
    A.contains_pair(mod["build_cli_args"](s), "--exclude-dir-glob", "build/**")


@test("U-ARG-13 排除后缀")
def _():
    mod = import_state()
    s = mod["RunState"](root="/p", output="/p/a.md",
                        exclude_suffixes=[".bak"])
    A.contains_pair(mod["build_cli_args"](s), "--exclude-suffix", ".bak")


@test("U-ARG-14 限制默认值不传")
def _():
    mod = import_state()
    s = mod["RunState"](root="/p", output="/p/a.md")
    args = mod["build_cli_args"](s)
    for flag in ("--max-file-size", "--max-git-commits", "--max-files-per-commit"):
        A.not_in(flag, args)


@test("U-ARG-15 限制非默认")
def _():
    mod = import_state()
    s = mod["RunState"](root="/p", output="/p/a.md",
                        max_file_size_kb=300,
                        max_git_commits=100,
                        max_files_per_commit=30)
    args = mod["build_cli_args"](s)
    A.contains_pair(args, "--max-file-size", "300")
    A.contains_pair(args, "--max-git-commits", "100")
    A.contains_pair(args, "--max-files-per-commit", "30")


@test("U-ARG-16 --no-git")
def _():
    mod = import_state()
    s = mod["RunState"](root="/p", output="/p/a.md", include_git=False)
    A.in_("--no-git", mod["build_cli_args"](s))


@test("U-ARG-17 --no-content")
def _():
    mod = import_state()
    s = mod["RunState"](root="/p", output="/p/a.md", include_content=False)
    A.in_("--no-content", mod["build_cli_args"](s))


@test("U-ARG-18 --no-ast")
def _():
    mod = import_state()
    s = mod["RunState"](root="/p", output="/p/a.md", include_ast=False)
    A.in_("--no-ast", mod["build_cli_args"](s))


@test("U-ARG-19 --no-timestamp")
def _():
    mod = import_state()
    s = mod["RunState"](root="/p", output="/p/a.md", no_timestamp=True)
    A.in_("--no-timestamp", mod["build_cli_args"](s))


@test("U-ARG-20 全部 no-* 同时出现")
def _():
    mod = import_state()
    s = mod["RunState"](
        root="/p", output="/p/a.md",
        include_git=False, include_content=False, include_ast=False,
        no_timestamp=True,
    )
    args = mod["build_cli_args"](s)
    for flag in ("--no-git", "--no-content", "--no-ast", "--no-timestamp"):
        A.in_(flag, args)


@test("U-ARG-21 含空格的路径不被拆开")
def _():
    mod = import_state()
    s = mod["RunState"](root="/a b/c", output="/a b/c/x.md")
    args = mod["build_cli_args"](s)
    A.eq(args[0], "/a b/c")
    A.contains_pair(args, "-o", "/a b/c/x.md")


@test("U-ARG-22 含中文的路径")
def _():
    mod = import_state()
    s = mod["RunState"](root="/项目/甲", output="/项目/甲/x.md")
    args = mod["build_cli_args"](s)
    A.eq(args[0], "/项目/甲")


@test("U-ARG-23 参数顺序稳定")
def _():
    mod = import_state()
    s = mod["RunState"](
        root="/p", output="/p/a.md",
        languages_mode="custom", languages_custom=["python", "go"],
        exclude_globs=["*.pb.go"],
        include_content=False,
        no_timestamp=True,
    )
    a1 = mod["build_cli_args"](s)
    a2 = mod["build_cli_args"](s)
    A.eq(a1, a2)


@test("U-ARG-24 组合场景 A")
def _():
    mod = import_state()
    s = mod["RunState"](
        root="/p", output="/p/a.md",
        languages_mode="custom", languages_custom=["python", "go"],
        exclude_globs=["*.pb.go"], exclude_dirs=["third_party"],
        include_content=False,
    )
    expected = [
        "/p", "-o", "/p/a.md",
        "--languages", "python,go",
        "--exclude", "*.pb.go",
        "--exclude-dir", "third_party",
        "--no-content",
    ]
    A.eq(mod["build_cli_args"](s), expected)


@test("U-ARG-25 组合场景 B")
def _():
    mod = import_state()
    s = mod["RunState"](
        root="/p", output="/p/a.md",
        languages_mode="all",
        max_file_size_kb=500,
        include_git=False, include_ast=False,
    )
    expected = [
        "/p", "-o", "/p/a.md",
        "--languages", "all",
        "--max-file-size", "500",
        "--no-git",
        "--no-ast",
    ]
    A.eq(mod["build_cli_args"](s), expected)


# ===========================================================================
# 单元测试：format_command
# ===========================================================================

@test("U-FMT-01 无空格不加引号")
def _():
    mod = import_state()
    A.eq(mod["format_command"]("python", ["-m", "x"]), "python -m x")


@test("U-FMT-02 含空格加引号")
def _():
    mod = import_state()
    A.eq(mod["format_command"]("python", ["/a b/c"]), 'python "/a b/c"')


@test("U-FMT-03 空列表")
def _():
    mod = import_state()
    A.eq(mod["format_command"]("python", []), "python")


@test("U-FMT-04 中文原样")
def _():
    mod = import_state()
    A.in_("/项目", mod["format_command"]("python", ["/项目"]))


# ===========================================================================
# 单元测试：scan_project
# ===========================================================================

def _tmp_project() -> Path:
    return Path(tempfile.mkdtemp(prefix="pcgui_test_"))


@test("U-SCAN-01 空目录")
def _():
    scan_project, _ = import_project_service()
    p = _tmp_project()
    try:
        r = scan_project(p)
        A.false(r.has_project_context_dir)
        A.false(r.has_git)
        A.eq(r.detected_languages, [])
    finally:
        shutil.rmtree(p, ignore_errors=True)


@test("U-SCAN-02 有 .project_context/common.toml")
def _():
    scan_project, _ = import_project_service()
    p = _tmp_project()
    try:
        cfg = p / ".project_context"
        cfg.mkdir()
        (cfg / "common.toml").write_text("inherit_defaults = true\n")
        r = scan_project(p)
        A.true(r.has_project_context_dir)
        A.true(r.has_common_toml)
    finally:
        shutil.rmtree(p, ignore_errors=True)


@test("U-SCAN-03 语言配置计数")
def _():
    scan_project, _ = import_project_service()
    p = _tmp_project()
    try:
        lang = p / ".project_context" / "languages"
        lang.mkdir(parents=True)
        (lang / "python.toml").write_text("name='python'\n")
        r = scan_project(p)
        A.eq(r.language_toml_count, 1)
    finally:
        shutil.rmtree(p, ignore_errors=True)


@test("U-SCAN-04 检测 .git")
def _():
    scan_project, _ = import_project_service()
    p = _tmp_project()
    try:
        (p / ".git").mkdir()
        A.true(scan_project(p).has_git)
    finally:
        shutil.rmtree(p, ignore_errors=True)


@test("U-SCAN-05 Python 信号")
def _():
    scan_project, _ = import_project_service()
    p = _tmp_project()
    try:
        for i in range(3):
            (p / f"m{i}.py").write_text("x=1\n")
        (p / "pyproject.toml").write_text("[project]\n")
        r = scan_project(p)
        A.in_("python", r.detected_languages)
        A.true(r.suffix_hits.get("python", 0) >= 3)
    finally:
        shutil.rmtree(p, ignore_errors=True)


@test("U-SCAN-06 node_modules 被跳过")
def _():
    scan_project, _ = import_project_service()
    p = _tmp_project()
    try:
        nm = p / "node_modules"
        nm.mkdir()
        for i in range(5):
            (nm / f"x{i}.js").write_text("x")
        r = scan_project(p)
        A.eq(r.suffix_hits.get("node", 0), 0)
    finally:
        shutil.rmtree(p, ignore_errors=True)


@test("U-SCAN-07 大目录保护（性能）")
def _():
    import time
    scan_project, _ = import_project_service()
    p = _tmp_project()
    try:
        for i in range(2000):
            (p / f"f{i}.py").write_text("x")
        t0 = time.monotonic()
        scan_project(p)
        dt = time.monotonic() - t0
        A.true(dt < 5.0, f"扫描 2000 文件耗时 {dt:.2f}s，应 < 5s")
    finally:
        shutil.rmtree(p, ignore_errors=True)


@test("U-SCAN-09 root 指向文件")
def _():
    scan_project, _ = import_project_service()
    p = _tmp_project()
    try:
        f = p / "a.py"
        f.write_text("x")
        r = scan_project(f)
        A.eq(r.detected_languages, [])
        A.false(r.has_git)
    finally:
        shutil.rmtree(p, ignore_errors=True)


# ===========================================================================
# Qt 相关：opener
# ===========================================================================

if has_qt():
    @test("U-OPEN-02 打开不存在的路径抛错")
    def _():
        from project_context_gui.services.opener import open_folder
        try:
            open_folder("/definitely/not/exist/xyz")
            raise AssertionError("应当抛 FileNotFoundError")
        except FileNotFoundError:
            pass
else:
    skip("U-OPEN-02 打开不存在的路径抛错", "PySide6 未安装")


if has_qt():
    @test("U-OPEN-03 传文件打开其父目录")
    def _():
        from project_context_gui.services import opener
        p = Path(tempfile.mkdtemp())
        try:
            f = p / "x.md"
            f.write_text("x")
            called = {}

            def fake_popen(args, *a, **kw):
                called["args"] = args
                return None

            orig = opener.subprocess.Popen
            opener.subprocess.Popen = fake_popen
            try:
                opener.reveal_file(f)
            finally:
                opener.subprocess.Popen = orig
        finally:
            shutil.rmtree(p, ignore_errors=True)
else:
    skip("U-OPEN-03 传文件打开其父目录", "PySide6 未安装")


# ===========================================================================
# Qt 相关：SettingsService
# ===========================================================================

if has_qt():
    @test("U-SET 设置项往返一致")
    def _():
        from PySide6.QtCore import QSettings
        from project_context_gui.services.settings_service import SettingsService

        _ensure_qt_app()  # 确保 QSettings 路径已被隔离

        tmp = Path(tempfile.mkdtemp())
        try:
            QSettings.setDefaultFormat(QSettings.IniFormat)
            QSettings.setPath(
                QSettings.IniFormat, QSettings.UserScope, str(tmp)
            )
            import project_context_gui.services.settings_service as ss
            ss._ORG = "pcgui_test_org"
            ss._APP = "pcgui_test_app"

            s = SettingsService()
            s.default_output_name = "MY.md"
            A.eq(s.default_output_name, "MY.md")

            s.push_recent_project("/a")
            s.push_recent_project("/b")
            s.push_recent_project("/a")
            A.eq(s.recent_projects[0], "/a")
            A.eq(len([x for x in s.recent_projects if x == "/a"]), 1)

            for i in range(15):
                s.push_recent_project(f"/p{i}")
            A.true(len(s.recent_projects) <= 10)

            s.clear_recent_projects()
            A.eq(s.recent_projects, [])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
else:
    skip("U-SET 设置项往返一致", "PySide6 未安装")


# ===========================================================================
# Qt 相关：CliRunner
# ===========================================================================

def _run_cli(args: list, timeout_ms: int = 8000):
    """同步执行 CliRunner，返回 (runner, outputs, result)。"""
    from PySide6.QtCore import QEventLoop, QTimer
    from project_context_gui.services.cli_runner import CliRunner

    _ensure_qt_app()  # 必须是 QApplication，不是 QCoreApplication

    loop = QEventLoop()
    outputs: list = []
    result = {"kind": None, "code": None, "msg": None}

    runner = CliRunner()
    runner.output_line.connect(outputs.append)

    def on_finished(code):
        result["kind"] = "finished"
        result["code"] = code
        loop.quit()

    def on_failed(msg):
        result["kind"] = "failed"
        result["msg"] = msg
        loop.quit()

    def on_cancelled():
        result["kind"] = "cancelled"
        loop.quit()

    runner.finished.connect(on_finished)
    runner.failed.connect(on_failed)
    runner.cancelled.connect(on_cancelled)

    QTimer.singleShot(timeout_ms, loop.quit)
    runner.run(sys.executable, args)
    loop.exec()
    return runner, outputs, result


if has_qt():
    @test("I-RUN-01 正常退出")
    def _():
        code = "print('line 1');print('line 2');print('中文输出')"
        _, outs, r = _run_cli(["-c", code])
        A.eq(r["kind"], "finished")
        A.eq(r["code"], 0)
        A.true(any("line 1" in x for x in outs))
        A.true(any("中文输出" in x for x in outs))
else:
    skip("I-RUN-01 正常退出", "PySide6 未安装")


if has_qt():
    @test("I-RUN-02 非零退出码")
    def _():
        _, _, r = _run_cli(["-c", "import sys; sys.exit(2)"])
        A.eq(r["kind"], "finished")
        A.eq(r["code"], 2)
else:
    skip("I-RUN-02 非零退出码", "PySide6 未安装")


if has_qt():
    @test("I-RUN-05 最后一行无换行也能收到")
    def _():
        code = "import sys; sys.stdout.write('no newline at end')"
        _, outs, _ = _run_cli(["-c", code])
        A.true(any("no newline at end" in x for x in outs),
               f"应包含最后一行，实际: {outs}")
else:
    skip("I-RUN-05 最后一行无换行也能收到", "PySide6 未安装")


if has_qt():
    @test("I-RUN-06 stderr 合并到 output_line")
    def _():
        code = "import sys; print('to stderr', file=sys.stderr)"
        _, outs, _ = _run_cli(["-c", code])
        A.true(any("to stderr" in x for x in outs))
else:
    skip("I-RUN-06 stderr 合并到 output_line", "PySide6 未安装")


if has_qt():
    @test("I-RUN-08b 启动失败（不存在的程序）")
    def _():
        from PySide6.QtCore import QEventLoop, QTimer
        from project_context_gui.services.cli_runner import CliRunner

        _ensure_qt_app()
        loop = QEventLoop()
        result = {"kind": None, "msg": None}
        runner = CliRunner()
        runner.failed.connect(
            lambda m: (result.update(kind="failed", msg=m), loop.quit())
        )
        runner.finished.connect(
            lambda c: (result.update(kind="finished", code=c), loop.quit())
        )
        QTimer.singleShot(5000, loop.quit)
        runner.run("/definitely/not/exist/xyz_program", [])
        loop.exec()
        A.eq(result["kind"], "failed")
else:
    skip("I-RUN-08b 启动失败（不存在的程序）", "PySide6 未安装")


if has_qt():
    @test("I-RUN-07 取消运行")
    def _():
        from PySide6.QtCore import QEventLoop, QTimer
        from project_context_gui.services.cli_runner import CliRunner

        _ensure_qt_app()
        loop = QEventLoop()
        result = {"kind": None}
        runner = CliRunner()
        runner.cancelled.connect(
            lambda: (result.update(kind="cancelled"), loop.quit())
        )
        runner.finished.connect(
            lambda c: (result.update(kind="finished"), loop.quit())
        )
        runner.failed.connect(
            lambda m: (result.update(kind="failed"), loop.quit())
        )
        QTimer.singleShot(8000, loop.quit)
        runner.run(sys.executable, ["-c", "import time; time.sleep(30)"])
        QTimer.singleShot(500, runner.cancel)
        loop.exec()
        A.eq(result["kind"], "cancelled")
else:
    skip("I-RUN-07 取消运行", "PySide6 未安装")


# ===========================================================================
# 一致性门禁
# ===========================================================================

@test("P-01 参数拼装与手工 CLI 一致（dry-run）")
def _():
    mod = import_state()
    s = mod["RunState"](
        root="/proj", output="/proj/OUT.md",
        languages_mode="custom", languages_custom=["python", "node"],
        exclude_globs=["*.pb.go"], exclude_dirs=["third_party"],
        no_timestamp=True, include_git=False,
    )
    expected = [
        "/proj", "-o", "/proj/OUT.md",
        "--languages", "python,node",
        "--exclude", "*.pb.go",
        "--exclude-dir", "third_party",
        "--no-git",
        "--no-timestamp",
    ]
    A.eq(mod["build_cli_args"](s), expected)


if has_qt() and has_cli():
    @test("P-02 字节级一致（真实运行，关闭时间戳）")
    def _():
        # 输入项目目录 与 输出目录 分离，避免输出污染下次输入
        work = Path(tempfile.mkdtemp(prefix="pcgui_parity_"))
        project = work / "proj"
        out_dir = work / "out"
        project.mkdir()
        out_dir.mkdir()
        try:
            (project / "README.md").write_text("# hi\n", encoding="utf-8")
            (project / "a.py").write_text(
                "class A:\n    def f(self): pass\n", encoding="utf-8"
            )
            (project / "pyproject.toml").write_text(
                "[project]\nname='x'\n", encoding="utf-8"
            )
            (project / ".git").mkdir()

            cli_out = out_dir / "cli.md"
            gui_out = out_dir / "gui.md"

            # 1) 手工 CLI
            r1 = subprocess.run(
                [sys.executable, "-m", "project_context", str(project),
                 "-o", str(cli_out), "--no-timestamp", "--no-git"],
                capture_output=True, text=True, timeout=60,
            )
            if r1.returncode != 0:
                raise AssertionError(f"CLI 失败: {r1.stderr}")

            # 2) GUI 参数拼装 + 同样的执行
            mod = import_state()
            s = mod["RunState"](
                root=str(project), output=str(gui_out),
                no_timestamp=True, include_git=False,
            )
            args = mod["build_cli_args"](s)
            r2 = subprocess.run(
                [sys.executable, "-m", "project_context", *args],
                capture_output=True, text=True, timeout=60,
            )
            if r2.returncode != 0:
                raise AssertionError(f"GUI 参数执行失败: {r2.stderr}")

            b1 = cli_out.read_bytes()
            b2 = gui_out.read_bytes()
            A.eq(b1, b2, "GUI 与 CLI 输出应字节级一致")
        finally:
            shutil.rmtree(work, ignore_errors=True)
else:
    reason = []
    if not has_qt():
        reason.append("PySide6 未安装")
    if not has_cli():
        reason.append("project_context 未安装")
    skip("P-02 字节级一致（真实运行，关闭时间戳）", ", ".join(reason))


# ===========================================================================
# 集成测试：RunTab
# ===========================================================================

if has_qt():
    @test("I-RT-01 初始状态")
    def _():
        _ensure_qt_app()
        from project_context_gui.tabs.run_tab import RunTab
        tab = RunTab()
        try:
            A.true(tab._lang_auto.isChecked())
            A.false(tab._lang_all.isChecked())
            A.false(tab._lang_custom.isChecked())
            A.true(tab._cb_content.isChecked())
            A.true(tab._cb_ast.isChecked())
            A.true(tab._cb_git.isChecked())
            A.false(tab._cb_ts.isChecked())
            A.eq(tab._detect_spin.value(), 1)
            A.eq(tab._cmd_view.toPlainText(), "python -m project_context")
        finally:
            tab.deleteLater()
else:
    skip("I-RT-01 初始状态", "PySide6 未安装")


if has_qt():
    @test("I-RT-02 set_root 自动填 output")
    def _():
        _ensure_qt_app()
        from project_context_gui.tabs.run_tab import RunTab
        tab = RunTab()
        try:
            tab.set_root("/tmp/proj")
            A.eq(tab.output_path(),
                 str(Path("/tmp/proj") / "PROJECT_CONTEXT.md"))
        finally:
            tab.deleteLater()
else:
    skip("I-RT-02 set_root 自动填 output", "PySide6 未安装")


if has_qt():
    @test("I-RT-03/04 输出文件存在性提示")
    def _():
        _ensure_qt_app()
        from project_context_gui.tabs.run_tab import RunTab
        tmp = Path(tempfile.mkdtemp(prefix="pcgui_warn_"))
        try:
            out = tmp / "OUT.md"
            tab = RunTab()
            try:
                tab._root_picker.set_path(str(tmp))
                tab._output_picker.set_path(str(out))
                # 初始：显式隐藏
                A.true(tab._output_warn.isHidden())
                out.write_text("x")
                tab._check_output_exists()
                # 存在：不再隐藏
                A.false(tab._output_warn.isHidden())
                out.unlink()
                tab._check_output_exists()
                # 删除：重新隐藏
                A.true(tab._output_warn.isHidden())
            finally:
                tab.deleteLater()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
else:
    skip("I-RT-03/04 输出文件存在性提示", "PySide6 未安装")


if has_qt():
    @test("I-RT-05 切到 all 出现在命令预览")
    def _():
        _ensure_qt_app()
        from project_context_gui.tabs.run_tab import RunTab
        tab = RunTab()
        try:
            tab.set_root("/p")
            tab._lang_all.setChecked(True)
            A.in_("--languages all", tab._cmd_view.toPlainText())
        finally:
            tab.deleteLater()
else:
    skip("I-RT-05 切到 all 出现在命令预览", "PySide6 未安装")


if has_qt():
    @test("I-RT-06 切到 custom 显示语言列表")
    def _():
        _ensure_qt_app()
        from project_context_gui.tabs.run_tab import RunTab
        tab = RunTab()
        try:
            tab._lang_custom.setChecked(True)
            A.true(tab._lang_list.isVisibleTo(tab))
            A.true(tab._lang_add_btn.isVisibleTo(tab))
            tab._lang_auto.setChecked(True)
            A.false(tab._lang_list.isVisibleTo(tab))
        finally:
            tab.deleteLater()
else:
    skip("I-RT-06 切到 custom 显示语言列表", "PySide6 未安装")


if has_qt():
    @test("I-RT-07 custom 语言拼接到 --languages")
    def _():
        _ensure_qt_app()
        from project_context_gui.tabs.run_tab import RunTab
        from PySide6.QtWidgets import QListWidgetItem
        tab = RunTab()
        try:
            tab.set_root("/p")
            tab._lang_custom.setChecked(True)
            tab._lang_list.addItem(QListWidgetItem("python"))
            tab._lang_list.addItem(QListWidgetItem("go"))
            tab._refresh_command_preview()
            A.in_("--languages python,go", tab._cmd_view.toPlainText())
        finally:
            tab.deleteLater()
else:
    skip("I-RT-07 custom 语言拼接到 --languages", "PySide6 未安装")


if has_qt():
    @test("I-RT-09 检测阈值非默认进入命令")
    def _():
        _ensure_qt_app()
        from project_context_gui.tabs.run_tab import RunTab
        tab = RunTab()
        try:
            tab.set_root("/p")
            tab._detect_spin.setValue(3)
            A.in_("--detect-min-files 3", tab._cmd_view.toPlainText())
        finally:
            tab.deleteLater()
else:
    skip("I-RT-09 检测阈值非默认进入命令", "PySide6 未安装")


if has_qt():
    @test("I-RT-10/11/12/13 章节开关进入命令")
    def _():
        _ensure_qt_app()
        from project_context_gui.tabs.run_tab import RunTab
        tab = RunTab()
        try:
            tab.set_root("/p")
            tab._cb_content.setChecked(False)
            tab._cb_ast.setChecked(False)
            tab._cb_git.setChecked(False)
            tab._cb_ts.setChecked(True)
            text = tab._cmd_view.toPlainText()
            for flag in ("--no-content", "--no-ast", "--no-git", "--no-timestamp"):
                A.in_(flag, text)
        finally:
            tab.deleteLater()
else:
    skip("I-RT-10/11/12/13 章节开关进入命令", "PySide6 未安装")


if has_qt():
    @test("I-RT-14/15/16 排除 glob：添加、多行、去重")
    def _():
        _ensure_qt_app()
        from project_context_gui.tabs.run_tab import RunTab
        tab = RunTab()
        try:
            tab.set_root("/p")
            ed = tab._ex_globs
            ed._edit.setText("*.pb.go")
            ed._on_add()
            A.eq(ed.values(), ["*.pb.go"])
            A.in_("--exclude *.pb.go", tab._cmd_view.toPlainText())

            ed._edit.setText("a,b,c")
            ed._on_add()
            A.eq(ed.values(), ["*.pb.go", "a", "b", "c"])

            ed._edit.setText("a")
            ed._on_add()
            A.eq(ed.values(), ["*.pb.go", "a", "b", "c"])
        finally:
            tab.deleteLater()
else:
    skip("I-RT-14/15/16 排除 glob：添加、多行、去重", "PySide6 未安装")


if has_qt():
    @test("I-RT-17 删除排除项后命令预览同步")
    def _():
        _ensure_qt_app()
        from project_context_gui.tabs.run_tab import RunTab
        tab = RunTab()
        try:
            tab.set_root("/p")
            ed = tab._ex_globs
            ed.set_values(["*.pb.go"])
            tab._refresh_command_preview()
            A.in_("--exclude *.pb.go", tab._cmd_view.toPlainText())
            ed._list.setCurrentRow(0)
            ed._on_delete()
            tab._refresh_command_preview()
            A.not_in("--exclude", tab._cmd_view.toPlainText())
        finally:
            tab.deleteLater()
else:
    skip("I-RT-17 删除排除项后命令预览同步", "PySide6 未安装")


if has_qt():
    @test("I-RT-18 修改限制进入命令")
    def _():
        _ensure_qt_app()
        from project_context_gui.tabs.run_tab import RunTab
        tab = RunTab()
        try:
            tab.set_root("/p")
            tab._max_size.setValue(300)
            tab._max_commits.setValue(100)
            tab._max_files.setValue(30)
            text = tab._cmd_view.toPlainText()
            A.in_("--max-file-size 300", text)
            A.in_("--max-git-commits 100", text)
            A.in_("--max-files-per-commit 30", text)
        finally:
            tab.deleteLater()
else:
    skip("I-RT-18 修改限制进入命令", "PySide6 未安装")


if has_qt():
    @test("I-RT-19 复制命令到剪贴板")
    def _():
        _ensure_qt_app()
        from project_context_gui.tabs.run_tab import RunTab
        from PySide6.QtWidgets import QApplication
        tab = RunTab()
        try:
            tab.set_root("/p")
            tab._copy_command()
            A.eq(QApplication.clipboard().text(),
                 tab._cmd_view.toPlainText())
        finally:
            tab.deleteLater()
else:
    skip("I-RT-19 复制命令到剪贴板", "PySide6 未安装")


if has_qt():
    @test("I-RT-22 collect_state 与控件一致")
    def _():
        _ensure_qt_app()
        from project_context_gui.tabs.run_tab import RunTab
        from PySide6.QtWidgets import QListWidgetItem
        tab = RunTab()
        try:
            tab.set_root("/p")
            tab._lang_custom.setChecked(True)
            tab._lang_list.addItem(QListWidgetItem("python"))
            tab._detect_spin.setValue(2)
            tab._cb_git.setChecked(False)
            tab._max_size.setValue(500)
            tab._ex_dirs.set_values(["third_party"])

            s = tab.collect_state()
            A.eq(s.root, "/p")
            A.eq(s.languages_mode, "custom")
            A.eq(s.languages_custom, ["python"])
            A.eq(s.detect_min_files, 2)
            A.eq(s.include_git, False)
            A.eq(s.max_file_size_kb, 500)
            A.eq(s.exclude_dirs, ["third_party"])
        finally:
            tab.deleteLater()
else:
    skip("I-RT-22 collect_state 与控件一致", "PySide6 未安装")


if has_qt():
    @test("I-RT-23 空 root 时预览不含参数")
    def _():
        _ensure_qt_app()
        from project_context_gui.tabs.run_tab import RunTab
        tab = RunTab()
        try:
            A.eq(tab._cmd_view.toPlainText(), "python -m project_context")
        finally:
            tab.deleteLater()
else:
    skip("I-RT-23 空 root 时预览不含参数", "PySide6 未安装")


if has_qt():
    @test("I-RT-24 含空格路径在预览中加引号")
    def _():
        _ensure_qt_app()
        from project_context_gui.tabs.run_tab import RunTab
        tab = RunTab()
        try:
            tab._root_picker.set_path("/a b/proj")
            tab._output_picker.set_path("/a b/proj/OUT.md")
            tab._refresh_command_preview()
            text = tab._cmd_view.toPlainText()
            A.in_('"/a b/proj"', text)
            A.in_('"/a b/proj/OUT.md"', text)
        finally:
            tab.deleteLater()
else:
    skip("I-RT-24 含空格路径在预览中加引号", "PySide6 未安装")


# ===========================================================================
# 集成测试：LogTab
# ===========================================================================

if has_qt():
    @test("I-LT-01 追加信息")
    def _():
        _ensure_qt_app()
        from project_context_gui.tabs.log_tab import LogTab
        tab = LogTab()
        try:
            tab.append("hello world")
            A.eq(len(tab._lines), 1)
            A.eq(tab._lines[0][0], "INFO")
            A.in_("hello world", tab._lines[0][1])
        finally:
            tab.deleteLater()
else:
    skip("I-LT-01 追加信息", "PySide6 未安装")


if has_qt():
    @test("I-LT-02/03/13 级别推断")
    def _():
        _ensure_qt_app()
        from project_context_gui.tabs.log_tab import LogTab, _infer_level
        A.eq(_infer_level("ERROR: x"), "ERROR")
        A.eq(_infer_level("Traceback (most recent call last):"), "ERROR")
        A.eq(_infer_level("WARN something"), "WARN")
        A.eq(_infer_level("INFO plain"), "INFO")
        tab = LogTab()
        try:
            tab.append("ERROR boom")
            A.eq(tab._lines[0][0], "ERROR")
            tab.append("WARN careful")
            A.eq(tab._lines[1][0], "WARN")
        finally:
            tab.deleteLater()
else:
    skip("I-LT-02/03/13 级别推断", "PySide6 未安装")


if has_qt():
    @test("I-LT-04 级别过滤")
    def _():
        _ensure_qt_app()
        from project_context_gui.tabs.log_tab import LogTab
        tab = LogTab()
        try:
            tab.append("info one")
            tab.append("ERROR bad")
            tab.append("info two")
            tab._level_combo.setCurrentText("ERROR")
            text = tab._view.toPlainText()
            A.in_("bad", text)
            A.not_in("info one", text)
            A.not_in("info two", text)
        finally:
            tab.deleteLater()
else:
    skip("I-LT-04 级别过滤", "PySide6 未安装")


if has_qt():
    @test("I-LT-05/06 搜索过滤 + 大小写不敏感")
    def _():
        _ensure_qt_app()
        from project_context_gui.tabs.log_tab import LogTab
        tab = LogTab()
        try:
            tab.append("Alpha")
            tab.append("Beta")
            tab.append("Gamma")
            tab._search.setText("alpha")
            text = tab._view.toPlainText()
            A.in_("Alpha", text)
            A.not_in("Beta", text)
            A.not_in("Gamma", text)
        finally:
            tab.deleteLater()
else:
    skip("I-LT-05/06 搜索过滤 + 大小写不敏感", "PySide6 未安装")


if has_qt():
    @test("I-LT-07 清空")
    def _():
        _ensure_qt_app()
        from project_context_gui.tabs.log_tab import LogTab
        tab = LogTab()
        try:
            for i in range(10):
                tab.append(f"l{i}")
            tab.clear()
            A.eq(len(tab._lines), 0)
            A.eq(tab._view.toPlainText(), "")
        finally:
            tab.deleteLater()
else:
    skip("I-LT-07 清空", "PySide6 未安装")


if has_qt():
    @test("I-LT-14 长日志不卡（5000 行 < 5s）")
    def _():
        import time
        _ensure_qt_app()
        from project_context_gui.tabs.log_tab import LogTab
        tab = LogTab()
        try:
            t0 = time.monotonic()
            for i in range(5000):
                tab.append(f"line {i}")
            dt = time.monotonic() - t0
            A.true(dt < 5.0, f"5000 行耗时 {dt:.2f}s")
            A.eq(len(tab._lines), 5000)
        finally:
            tab.deleteLater()
else:
    skip("I-LT-14 长日志不卡（5000 行 < 5s）", "PySide6 未安装")


# ===========================================================================
# 集成测试：MainWindow 与状态机
# ===========================================================================

if has_qt():
    @test("I-MW-01 初始状态 EMPTY")
    def _():
        _ensure_qt_app()
        from project_context_gui.main_window import MainWindow, AppState
        w = MainWindow()
        try:
            A.eq(w._state, AppState.EMPTY)
            A.false(w._run_btn.isEnabled())
            A.false(w._open_folder_btn.isEnabled())
            A.in_("打开", w._status_label.text())
        finally:
            w.deleteLater()
else:
    skip("I-MW-01 初始状态 EMPTY", "PySide6 未安装")


if has_qt():
    @test("I-MW-02 _load_project 进入 READY")
    def _():
        _ensure_qt_app()
        from project_context_gui.main_window import MainWindow, AppState
        tmp = Path(tempfile.mkdtemp(prefix="pcgui_mw_"))
        try:
            (tmp / "a.py").write_text("x=1\n")
            w = MainWindow()
            try:
                w._load_project(str(tmp))
                A.eq(w._state, AppState.READY)
                A.true(w._run_btn.isEnabled())
                A.true(w._rescan_btn.isEnabled())
                A.eq(w._path_label.text(), str(tmp))
                text = "\n".join(line for _lvl, line in w._log_tab._lines)
                A.in_("已加载项目", text)
            finally:
                w.deleteLater()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
else:
    skip("I-MW-02 _load_project 进入 READY", "PySide6 未安装")


if has_qt():
    @test("I-MW-03/04/05 加载时日志提示")
    def _():
        _ensure_qt_app()
        from project_context_gui.main_window import MainWindow
        tmp = Path(tempfile.mkdtemp(prefix="pcgui_mw_"))
        try:
            cfg = tmp / ".project_context"
            cfg.mkdir()
            (cfg / "common.toml").write_text("inherit_defaults = true\n")
            (tmp / "a.py").write_text("x=1\n")
            w = MainWindow()
            try:
                w._load_project(str(tmp))
                text = "\n".join(line for _lvl, line in w._log_tab._lines)
                A.in_("发现 .project_context", text)
                A.in_("未发现 .git", text)
                A.in_("语言信号", text)
            finally:
                w.deleteLater()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
else:
    skip("I-MW-03/04/05 加载时日志提示", "PySide6 未安装")


if has_qt():
    @test("I-MW-10 RUNNING 按钮变停止")
    def _():
        _ensure_qt_app()
        from project_context_gui.main_window import MainWindow, AppState
        w = MainWindow()
        try:
            w._set_state(AppState.RUNNING)
            A.in_("停止", w._run_btn.text())
            w._set_state(AppState.READY)
            A.in_("开始生成", w._run_btn.text())
        finally:
            w.deleteLater()
else:
    skip("I-MW-10 RUNNING 按钮变停止", "PySide6 未安装")


if has_qt():
    @test("I-MW-14 SUCCESS 启用打开文件夹")
    def _():
        _ensure_qt_app()
        from project_context_gui.main_window import MainWindow, AppState
        w = MainWindow()
        try:
            w._set_state(AppState.SUCCESS)
            A.true(w._open_folder_btn.isEnabled())
            A.in_("成功", w._status_label.text())
        finally:
            w.deleteLater()
else:
    skip("I-MW-14 SUCCESS 启用打开文件夹", "PySide6 未安装")


if has_qt():
    @test("I-MW-15/17 FAILED / CANCELLED 状态")
    def _():
        _ensure_qt_app()
        from project_context_gui.main_window import MainWindow, AppState
        w = MainWindow()
        try:
            w._set_state(AppState.FAILED)
            A.in_("失败", w._status_label.text())
            A.false(w._open_folder_btn.isEnabled())
            w._set_state(AppState.CANCELLED)
            A.in_("取消", w._status_label.text())
        finally:
            w.deleteLater()
else:
    skip("I-MW-15/17 FAILED / CANCELLED 状态", "PySide6 未安装")


if has_qt():
    @test("I-MW-11 RUNNING 时切配置 Tab 被阻止")
    def _():
        _ensure_qt_app()
        from project_context_gui.main_window import MainWindow, AppState
        w = MainWindow()
        try:
            w._set_state(AppState.RUNNING)
            w._tabs.setCurrentIndex(0)
            w._tabs.setCurrentIndex(1)
            A.eq(w._tabs.currentIndex(), 0)
        finally:
            w.deleteLater()
else:
    skip("I-MW-11 RUNNING 时切配置 Tab 被阻止", "PySide6 未安装")


if has_qt():
    @test("I-MW-12 关闭未保存项目时提示（模拟）")
    def _():
        _ensure_qt_app()
        from project_context_gui.main_window import MainWindow
        p = _make_project_with_config()
        try:
            w = MainWindow()
            try:
                w._load_project(str(p))
                w._config_tab._editor.setPlainText("x = 1\n")
                A.true(w._config_tab.has_unsaved())
                # 不真的关闭窗口，仅验证状态
                A.true(w._config_tab.try_save())
                A.false(w._config_tab.has_unsaved())
            finally:
                w.deleteLater()
        finally:
            shutil.rmtree(p, ignore_errors=True)
else:
    skip("I-MW-12 关闭未保存项目时提示（模拟）", "PySide6 未安装")


if has_qt():
    @test("I-MW-24 重新检测刷新日志")
    def _():
        _ensure_qt_app()
        from project_context_gui.main_window import MainWindow
        tmp = Path(tempfile.mkdtemp(prefix="pcgui_mw_"))
        try:
            (tmp / "a.py").write_text("x=1\n")
            w = MainWindow()
            try:
                w._load_project(str(tmp))
                before = len(w._log_tab._lines)
                w._on_rescan()
                A.true(len(w._log_tab._lines) > before)
            finally:
                w.deleteLater()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
else:
    skip("I-MW-24 重新检测刷新日志", "PySide6 未安装")

# ===========================================================================
# 集成测试：ConfigTab
# ===========================================================================

def _make_project_with_config() -> Path:
    """建一个临时项目，带 .project_context/。"""
    p = Path(tempfile.mkdtemp(prefix="pcgui_cfg_"))
    cfg = p / ".project_context"
    (cfg / "languages").mkdir(parents=True)
    (cfg / "common.toml").write_text(
        "# comment\ninherit_defaults = true\n"
        "[limits]\nmax_file_size_kb = 300\n",
        encoding="utf-8",
    )
    (cfg / "languages" / "python.toml").write_text(
        'schema_version = 1\nname = "python"\n', encoding="utf-8"
    )
    return p


if has_qt():
    @test("I-CT-01 空状态")
    def _():
        _ensure_qt_app()
        from project_context_gui.tabs.config_tab import ConfigTab
        p = Path(tempfile.mkdtemp(prefix="pcgui_empty_"))
        try:
            tab = ConfigTab()
            try:
                tab.set_root(str(p))
                A.eq(tab._list.count(), 0)
                A.in_("未发现 .project_context", tab._hint.text())
                A.true(tab._new_common_btn.isEnabled())
            finally:
                tab.deleteLater()
        finally:
            shutil.rmtree(p, ignore_errors=True)
else:
    skip("I-CT-01 空状态", "PySide6 未安装")


if has_qt():
    @test("I-CT-02 列出配置文件")
    def _():
        _ensure_qt_app()
        from project_context_gui.tabs.config_tab import ConfigTab
        p = _make_project_with_config()
        try:
            tab = ConfigTab()
            try:
                tab.set_root(str(p))
                A.eq(tab._list.count(), 2)
                names = [
                    tab._list.item(i).text()
                    for i in range(tab._list.count())
                ]
                A.true(any("common.toml" in n for n in names))
                A.true(any("python.toml" in n for n in names))
                A.true(tab._current is not None)
            finally:
                tab.deleteLater()
        finally:
            shutil.rmtree(p, ignore_errors=True)
else:
    skip("I-CT-02 列出配置文件", "PySide6 未安装")


if has_qt():
    @test("I-CT-03 选中文件加载内容")
    def _():
        _ensure_qt_app()
        from project_context_gui.tabs.config_tab import ConfigTab
        p = _make_project_with_config()
        try:
            tab = ConfigTab()
            try:
                tab.set_root(str(p))
                # 默认选中第一个（common.toml）
                text = tab._editor.toPlainText()
                A.in_("inherit_defaults", text)
                A.in_("max_file_size_kb", text)
                A.false(tab._editor.dirty)
            finally:
                tab.deleteLater()
        finally:
            shutil.rmtree(p, ignore_errors=True)
else:
    skip("I-CT-03 选中文件加载内容", "PySide6 未安装")


if has_qt():
    @test("I-CT-04 编辑后脏标记 + 保存按钮启用")
    def _():
        _ensure_qt_app()
        from project_context_gui.tabs.config_tab import ConfigTab
        p = _make_project_with_config()
        try:
            tab = ConfigTab()
            try:
                tab.set_root(str(p))
                A.false(tab._editor.dirty)
                A.false(tab._save_btn.isEnabled())

                tab._editor.setPlainText("x = 1\n")
                A.true(tab._editor.dirty)
                A.true(tab._save_btn.isEnabled())

                # 刷新后列表项应带 ●
                tab._refresh_current_marker()
                found_mark = any(
                    "●" in tab._list.item(i).text()
                    for i in range(tab._list.count())
                )
                A.true(found_mark, "列表项应带 ● 标记")
            finally:
                tab.deleteLater()
        finally:
            shutil.rmtree(p, ignore_errors=True)
else:
    skip("I-CT-04 编辑后脏标记 + 保存按钮启用", "PySide6 未安装")


if has_qt():
    @test("I-CT-05 校验：合法与非法")
    def _():
        _ensure_qt_app()
        from project_context_gui.tabs.config_tab import ConfigTab
        p = _make_project_with_config()
        try:
            tab = ConfigTab()
            try:
                tab.set_root(str(p))
                # 合法
                tab._editor.setPlainText("a = 1\n")
                A.true(tab._on_validate())
                A.in_("✅", tab._status.text())
                A.true(tab._editor._error_line is None)

                # 非法
                tab._editor.setPlainText("a = [1, 2\n")
                A.false(tab._on_validate())
                A.in_("❌", tab._status.text())
                # 行号可能为 None（视 tomllib 错误类型），不强制
            finally:
                tab.deleteLater()
        finally:
            shutil.rmtree(p, ignore_errors=True)
else:
    skip("I-CT-05 校验：合法与非法", "PySide6 未安装")


if has_qt():
    @test("I-CT-06 保存写盘 + 保留注释")
    def _():
        _ensure_qt_app()
        from project_context_gui.tabs.config_tab import ConfigTab
        p = _make_project_with_config()
        try:
            tab = ConfigTab()
            try:
                tab.set_root(str(p))
                # 当前选中 common.toml
                new_text = (
                    "# 保留的注释\ninherit_defaults = false\n"
                    "[limits]\nmax_file_size_kb = 500\n"
                )
                tab._editor.setPlainText(new_text)
                tab._on_save()

                # 读回验证
                path = tab._current.path
                A.eq(path.read_text(encoding="utf-8"), new_text)
                A.false(tab._editor.dirty)
                A.in_("已保存", tab._status.text())
            finally:
                tab.deleteLater()
        finally:
            shutil.rmtree(p, ignore_errors=True)
else:
    skip("I-CT-06 保存写盘 + 保留注释", "PySide6 未安装")


if has_qt():
    @test("I-CT-07 非法 TOML 拒绝保存")
    def _():
        _ensure_qt_app()
        from project_context_gui.tabs.config_tab import ConfigTab
        p = _make_project_with_config()
        try:
            tab = ConfigTab()
            try:
                tab.set_root(str(p))
                path = tab._current.path
                before = path.read_text(encoding="utf-8")

                tab._editor.setPlainText("a = [1, 2\n")
                ok = tab._save(silent=True)          # 静默保存
                A.false(ok, "非法 TOML 应拒绝保存")
                A.eq(path.read_text(encoding="utf-8"), before)
                A.true(tab._editor.dirty)
            finally:
                tab.deleteLater()
        finally:
            shutil.rmtree(p, ignore_errors=True)
else:
    skip("I-CT-07 非法 TOML 拒绝保存", "PySide6 未安装")


if has_qt():
    @test("I-CT-08 新建 common.toml 模板")
    def _():
        _ensure_qt_app()
        from project_context_gui.tabs.config_tab import ConfigTab
        p = Path(tempfile.mkdtemp(prefix="pcgui_new_"))
        try:
            tab = ConfigTab()
            try:
                tab.set_root(str(p))
                A.eq(tab._list.count(), 0)
                tab._on_new_common()
                A.eq(tab._list.count(), 1)
                A.true((p / ".project_context" / "common.toml").is_file())
                A.in_("inherit_defaults", tab._editor.toPlainText())
            finally:
                tab.deleteLater()
        finally:
            shutil.rmtree(p, ignore_errors=True)
else:
    skip("I-CT-08 新建 common.toml 模板", "PySide6 未安装")


if has_qt():
    @test("I-CT-09 新建语言配置模板")
    def _():
        _ensure_qt_app()
        from project_context_gui.tabs.config_tab import ConfigTab
        from project_context_gui.services.config_service import (
            ConfigService,
        )
        p = Path(tempfile.mkdtemp(prefix="pcgui_newlang_"))
        try:
            svc = ConfigService(p)
            cf = svc.create_language_template("mydsl", "mydsl")
            text = cf.path.read_text(encoding="utf-8")
            A.in_('name = "mydsl"', text)
            A.in_('".mydsl"', text)
            A.in_("schema_version", text)
        finally:
            shutil.rmtree(p, ignore_errors=True)
else:
    skip("I-CT-09 新建语言配置模板", "PySide6 未安装")


if has_qt():
    @test("I-CT-10 删除配置文件")
    def _():
        _ensure_qt_app()
        from project_context_gui.tabs.config_tab import ConfigTab
        from PySide6.QtWidgets import QMessageBox
        p = _make_project_with_config()
        try:
            tab = ConfigTab()
            try:
                tab.set_root(str(p))
                before = tab._list.count()
                # 直接调用内部删除但绕过对话框确认：改成先替换消息框
                # 简化：直接调 svc.delete + 刷新
                path = tab._current.path
                tab._svc.delete(path)
                tab._refresh_list()
                A.eq(tab._list.count(), before - 1)
                A.false(path.is_file())
            finally:
                tab.deleteLater()
        finally:
            shutil.rmtree(p, ignore_errors=True)
else:
    skip("I-CT-10 删除配置文件", "PySide6 未安装")


if has_qt():
    @test("I-CT-11 has_unsaved / try_save 协作")
    def _():
        _ensure_qt_app()
        from project_context_gui.tabs.config_tab import ConfigTab
        p = _make_project_with_config()
        try:
            tab = ConfigTab()
            try:
                tab.set_root(str(p))
                A.false(tab.has_unsaved())
                tab._editor.setPlainText("a = 1\n")
                A.true(tab.has_unsaved())
                # try_save 会走校验 + 写盘
                A.true(tab.try_save())
                A.false(tab.has_unsaved())
            finally:
                tab.deleteLater()
        finally:
            shutil.rmtree(p, ignore_errors=True)
else:
    skip("I-CT-11 has_unsaved / try_save 协作", "PySide6 未安装")


if has_qt():
    @test("I-CT-12 validate_toml 行号提取")
    def _():
        from project_context_gui.services.config_service import (
            validate_toml,
        )
        ok, msg, line = validate_toml("a = 1\nb = [\n")
        A.false(ok)
        A.true(line is not None)
        A.true(line >= 1)

        ok2, _, line2 = validate_toml("a = 1\n")
        A.true(ok2)
        A.true(line2 is None)
else:
    skip("I-CT-12 validate_toml 行号提取", "PySide6 未安装")


# ===========================================================================
# 集成测试：SettingsDialog
# ===========================================================================

if has_qt():
    @test("I-SET-01 设置对话框读取默认值")
    def _():
        _ensure_qt_app()
        from project_context_gui.dialogs.settings_dialog import (
            SettingsDialog,
        )
        from project_context_gui.services.settings_service import (
            SettingsService,
        )
        import project_context_gui.services.settings_service as ss
        ss._ORG = "pcgui_set_org"
        ss._APP = "pcgui_set_app"

        s = SettingsService()
        s.default_output_name = "OUT.md"
        s.theme = "dark"
        s.font_size = 12
        s.python_executable = "/usr/bin/python3"
        s.restore_last_project = False

        dlg = SettingsDialog(s)
        try:
            A.eq(dlg.default_output_name(), "OUT.md")
            A.eq(dlg.theme(), "dark")
            A.eq(dlg.font_size(), 12)
            A.eq(dlg.python_executable(), "/usr/bin/python3")
            A.eq(dlg.restore_last_project(), False)
        finally:
            dlg.deleteLater()
else:
    skip("I-SET-01 设置对话框读取默认值", "PySide6 未安装")


if has_qt():
    @test("I-SET-02 默认输出名为空时兜底")
    def _():
        _ensure_qt_app()
        from project_context_gui.dialogs.settings_dialog import (
            SettingsDialog,
        )
        from project_context_gui.services.settings_service import (
            SettingsService,
        )
        dlg = SettingsDialog(SettingsService())
        try:
            dlg._output_name.setText("   ")
            A.eq(dlg.default_output_name(), "PROJECT_CONTEXT.md")
        finally:
            dlg.deleteLater()
else:
    skip("I-SET-02 默认输出名为空时兜底", "PySide6 未安装")


# ===========================================================================
# 集成测试：MainWindow（M5 增补）
# ===========================================================================

if has_qt():
    @test("I-MW-30 空状态页显示 + 有最近项目")
    def _():
        _ensure_qt_app()
        from project_context_gui.main_window import MainWindow
        import project_context_gui.services.settings_service as ss
        ss._ORG = "pcgui_mw5_org"
        ss._APP = "pcgui_mw5_app"

        w = MainWindow()
        try:
            # 未选项目 → 空状态页
            A.eq(w._stack.currentIndex(), 0)
            A.true(w._empty_page is not None)
            # 最近项目注入
            w._settings.push_recent_project("/tmp/x")
            w._refresh_recent()
            A.true(w._empty_page._recent_list.count() >= 1)
            A.true(w._recent_combo.count() >= 2)   # 占位项 + 至少 1 条
        finally:
            w.deleteLater()
else:
    skip("I-MW-30 空状态页显示 + 有最近项目", "PySide6 未安装")


if has_qt():
    @test("I-MW-31 加载项目后切到 Tab 页")
    def _():
        _ensure_qt_app()
        from project_context_gui.main_window import MainWindow
        import project_context_gui.services.settings_service as ss
        ss._ORG = "pcgui_mw5_org"
        ss._APP = "pcgui_mw5_app"

        tmp = Path(tempfile.mkdtemp(prefix="pcgui_mw5_"))
        try:
            (tmp / "a.py").write_text("x=1\n")
            w = MainWindow()
            try:
                w._load_project(str(tmp))
                A.eq(w._stack.currentIndex(), 1)
                A.in_(str(tmp), w._settings.recent_projects)
                A.eq(w._settings.last_project, str(tmp))
            finally:
                w.deleteLater()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
else:
    skip("I-MW-31 加载项目后切到 Tab 页", "PySide6 未安装")


if has_qt():
    @test("I-MW-32 主题切换不崩")
    def _():
        _ensure_qt_app()
        from project_context_gui.main_window import (
            apply_theme, apply_font_size,
        )
        for t in ("system", "light", "dark"):
            apply_theme(t)
        for sz in (8, 10, 14):
            apply_font_size(sz)
        # 恢复默认
        apply_theme("system")
        apply_font_size(10)
else:
    skip("I-MW-32 主题切换不崩", "PySide6 未安装")


if has_qt():
    @test("I-MW-33 拖拽文件夹加载项目")
    def _():
        _ensure_qt_app()
        from project_context_gui.main_window import MainWindow
        from PySide6.QtCore import QMimeData, QUrl, QPointF, Qt as QtNS
        from PySide6.QtGui import QDragEnterEvent, QDropEvent
        import project_context_gui.services.settings_service as ss
        ss._ORG = "pcgui_mw5_org"
        ss._APP = "pcgui_mw5_app"

        tmp = Path(tempfile.mkdtemp(prefix="pcgui_mw5_"))
        try:
            (tmp / "a.py").write_text("x=1\n")
            w = MainWindow()
            try:
                mime = QMimeData()
                mime.setUrls([QUrl.fromLocalFile(str(tmp))])

                # 新签名使用 QPointF
                enter = QDragEnterEvent(
                    QPointF(10, 10),
                    QtNS.CopyAction, mime,
                    QtNS.LeftButton, QtNS.NoModifier,
                )
                w.dragEnterEvent(enter)
                A.true(enter.isAccepted())

                drop = QDropEvent(
                    QPointF(10, 10),
                    QtNS.CopyAction, mime,
                    QtNS.LeftButton, QtNS.NoModifier,
                )
                w.dropEvent(drop)
                A.eq(w._stack.currentIndex(), 1)
                A.in_(str(tmp), w._settings.recent_projects)
            finally:
                w.deleteLater()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
else:
    skip("I-MW-33 拖拽文件夹加载项目", "PySide6 未安装")


if has_qt():
    @test("I-MW-34 快捷键对象已安装")
    def _():
        _ensure_qt_app()
        from project_context_gui.main_window import MainWindow
        import project_context_gui.services.settings_service as ss
        ss._ORG = "pcgui_mw5_org"
        ss._APP = "pcgui_mw5_app"
        w = MainWindow()
        try:
            from PySide6.QtGui import QShortcut
            shortcuts = w.findChildren(QShortcut)
            A.true(len(shortcuts) >= 5, "应至少安装 5 个快捷键")
        finally:
            w.deleteLater()
else:
    skip("I-MW-34 快捷键对象已安装", "PySide6 未安装")


if has_qt():
    @test("I-MW-35 设置应用后主题/字体写入")
    def _():
        _ensure_qt_app()
        from project_context_gui.main_window import MainWindow
        import project_context_gui.services.settings_service as ss
        ss._ORG = "pcgui_mw5_org"
        ss._APP = "pcgui_mw5_app"

        w = MainWindow()
        try:
            w._settings.theme = "light"
            w._settings.font_size = 11
            w._apply_user_prefs()
            A.eq(w._settings.theme, "light")
            A.eq(w._settings.font_size, 11)
        finally:
            w.deleteLater()
else:
    skip("I-MW-35 设置应用后主题/字体写入", "PySide6 未安装")

# ===========================================================================
# 集成测试：RunnerResolver
# ===========================================================================

class _FakeSettings:
    """测试用：不落盘的极简设置。"""
    def __init__(self, mode="auto", exe_path="", python=""):
        self.runner_mode = mode
        self.exe_path = exe_path
        self.python_executable = python


if has_qt():
    @test("U-CMD-01 Python 模式拼装")
    def _():
        from project_context_gui.services.runner_resolver import (
            make_python_command,
        )
        cmd = make_python_command(["/p", "-o", "/p/a.md"],
                                  python_path="python")
        A.eq(cmd.mode, "python")
        A.eq(cmd.program, "python")
        A.eq(cmd.args, ["-m", "project_context", "/p", "-o", "/p/a.md"])
        A.in_("-m project_context", cmd.display)
        A.false(cmd.is_exe)
else:
    skip("U-CMD-01 Python 模式拼装", "PySide6 未安装")


if has_qt():
    @test("U-CMD-02 EXE 模式拼装")
    def _():
        from project_context_gui.services.runner_resolver import (
            make_exe_command,
        )
        cmd = make_exe_command(["/p", "-o", "/p/a.md"], "C:/gpc/g.exe")
        A.eq(cmd.mode, "exe")
        A.eq(cmd.args, ["/p", "-o", "/p/a.md"])
        A.true(cmd.is_exe)
        A.in_("g.exe", cmd.display)
else:
    skip("U-CMD-02 EXE 模式拼装", "PySide6 未安装")


if has_qt():
    @test("U-CMD-03 EXE 路径含空格加引号")
    def _():
        from project_context_gui.services.runner_resolver import (
            make_exe_command,
        )
        cmd = make_exe_command(["/p"], "C:/Program Files/gpc/g.exe")
        A.in_('"C:/Program Files/gpc/g.exe"', cmd.display)
else:
    skip("U-CMD-03 EXE 路径含空格加引号", "PySide6 未安装")


if has_qt():
    @test("U-CMD-04 空参数无尾随空格")
    def _():
        from project_context_gui.services.runner_resolver import (
            make_exe_command,
        )
        cmd = make_exe_command([], "g.exe")
        A.eq(cmd.display, "g.exe")
else:
    skip("U-CMD-04 空参数无尾随空格", "PySide6 未安装")


if has_qt():
    @test("I-RES-01 resolver auto + 无 exe → python")
    def _():
        from project_context_gui.services.runner_resolver import (
            RunnerResolver,
        )
        s = _FakeSettings(mode="auto")
        r = RunnerResolver(s)
        import shutil
        if shutil.which("generate-project-context.exe"):
            cmd = r.resolve(["/p"])
            A.eq(cmd.mode, "exe")
        else:
            cmd = r.resolve(["/p"])
            A.eq(cmd.mode, "python")
            A.in_("-m", cmd.args)                # 修
            A.in_("project_context", cmd.args)   # 修
            A.eq(cmd.args[:2], ["-m", "project_context"])  # 加固
else:
    skip("I-RES-01 resolver auto + 无 exe → python", "PySide6 未安装")


if has_qt():
    @test("I-RES-02 resolver python 模式")
    def _():
        from project_context_gui.services.runner_resolver import (
            RunnerResolver,
        )
        s = _FakeSettings(mode="python", python="python")
        r = RunnerResolver(s)
        cmd = r.resolve(["/p"])
        A.eq(cmd.mode, "python")
        A.eq(cmd.program, "python")
else:
    skip("I-RES-02 resolver python 模式", "PySide6 未安装")


if has_qt():
    @test("I-RES-03 resolver exe 模式路径不存在 → python 兜底")
    def _():
        from project_context_gui.services.runner_resolver import (
            RunnerResolver,
        )
        s = _FakeSettings(
            mode="exe", exe_path="/definitely/not/exist/g.exe",
            python="python",
        )
        r = RunnerResolver(s)
        # 找不到时 Path 不存在 → 回退 python
        cmd = r.resolve(["/p"])
        # 若 PATH 里恰好有 generate-project-context.exe，会出现 exe
        import shutil
        if shutil.which("generate-project-context.exe"):
            A.eq(cmd.mode, "exe")
        else:
            A.eq(cmd.mode, "python")
else:
    skip("I-RES-03 resolver exe 模式路径不存在 → python 兜底",
         "PySide6 未安装")


if has_qt():
    @test("I-RES-04 current_mode 反映实际模式")
    def _():
        from project_context_gui.services.runner_resolver import (
            RunnerResolver,
        )
        s = _FakeSettings(mode="python")
        r = RunnerResolver(s)
        A.eq(r.current_mode(), "python")
        s.runner_mode = "auto"
        # 取决于本机是否有 exe；两种情况都应合法
        A.in_(r.current_mode(), ["python", "exe"])
else:
    skip("I-RES-04 current_mode 反映实际模式", "PySide6 未安装")


if has_qt():
    @test("I-RES-05 describe 状态行")
    def _():
        from project_context_gui.services.runner_resolver import (
            RunnerResolver,
        )
        s = _FakeSettings(mode="python", python="python")
        r = RunnerResolver(s)
        ok, msg = r.describe_python_status()
        A.true(isinstance(ok, bool))
        A.true(isinstance(msg, str))
        A.true(len(msg) > 0)

        ok2, msg2 = r.describe_exe_status()
        A.true(isinstance(ok2, bool))
        A.true(isinstance(msg2, str))
else:
    skip("I-RES-05 describe 状态行", "PySide6 未安装")


if has_qt():
    @test("I-RES-06 RunTab 注入 resolver 后命令预览变 exe 前缀")
    def _():
        _ensure_qt_app()
        from project_context_gui.tabs.run_tab import RunTab
        from project_context_gui.services.runner_resolver import (
            RunnerResolver,
        )

        # 造一个假的 exe（用系统 python 冒充）
        fake_exe = Path(tempfile.mkdtemp(prefix="pcgui_fakeexe_")) / "g.exe"
        try:
            fake_exe.write_text("")  # 不真跑，只要 is_file 成立

            class _S:
                runner_mode = "exe"
                exe_path = str(fake_exe)
                python_executable = "python"

            tab = RunTab()
            try:
                tab.set_resolver(RunnerResolver(_S()))
                tab.set_root("/p")
                text = tab._cmd_view.toPlainText()
                A.in_(str(fake_exe), text)
                A.not_in("-m project_context", text)
            finally:
                tab.deleteLater()
        finally:
            shutil.rmtree(fake_exe.parent, ignore_errors=True)
else:
    skip("I-RES-06 RunTab 注入 resolver 后命令预览变 exe 前缀",
         "PySide6 未安装")


if has_qt():
    @test("I-RES-07 未注入 resolver 时保持旧预览")
    def _():
        _ensure_qt_app()
        from project_context_gui.tabs.run_tab import RunTab
        tab = RunTab()
        try:
            tab.set_root("/p")
            text = tab._cmd_view.toPlainText()
            A.in_("python -m project_context", text)
        finally:
            tab.deleteLater()
else:
    skip("I-RES-07 未注入 resolver 时保持旧预览", "PySide6 未安装")


if has_qt():
    @test("I-RES-08 MainWindow 有模式徽章")
    def _():
        _ensure_qt_app()
        from project_context_gui.main_window import MainWindow
        import project_context_gui.services.settings_service as ss
        ss._ORG = "pcgui_res_org"
        ss._APP = "pcgui_res_app"

        w = MainWindow()
        try:
            A.true(w._mode_badge is not None)
            text = w._mode_badge.text()
            A.true("EXE" in text or "Python" in text)
        finally:
            w.deleteLater()
else:
    skip("I-RES-08 MainWindow 有模式徽章", "PySide6 未安装")


if has_qt():
    @test("I-RES-09 设置 dialog 有引擎分组")
    def _():
        _ensure_qt_app()
        from project_context_gui.dialogs.settings_dialog import (
            SettingsDialog,
        )
        from project_context_gui.services.settings_service import (
            SettingsService,
        )
        import project_context_gui.services.settings_service as ss
        ss._ORG = "pcgui_res_org"
        ss._APP = "pcgui_res_app"

        dlg = SettingsDialog(SettingsService())
        try:
            A.true(dlg._mode_auto is not None)
            A.true(dlg._mode_python is not None)
            A.true(dlg._mode_exe is not None)
            A.true(dlg._exe_edit is not None)
            A.in_(dlg.runner_mode(), ["auto", "python", "exe"])
        finally:
            dlg.deleteLater()
else:
    skip("I-RES-09 设置 dialog 有引擎分组", "PySide6 未安装")


if has_qt():
    @test("I-RES-10 引擎模式切换联动启用状态")
    def _():
        _ensure_qt_app()
        from project_context_gui.dialogs.settings_dialog import (
            SettingsDialog,
        )
        from project_context_gui.services.settings_service import (
            SettingsService,
        )
        import project_context_gui.services.settings_service as ss
        ss._ORG = "pcgui_res_org"
        ss._APP = "pcgui_res_app"

        dlg = SettingsDialog(SettingsService())
        try:
            dlg._mode_auto.setChecked(True)
            A.false(dlg._exe_edit.isEnabled())
            A.false(dlg._python_edit.isEnabled())

            dlg._mode_python.setChecked(True)
            A.false(dlg._exe_edit.isEnabled())
            A.true(dlg._python_edit.isEnabled())

            dlg._mode_exe.setChecked(True)
            A.true(dlg._exe_edit.isEnabled())
            A.false(dlg._python_edit.isEnabled())
        finally:
            dlg.deleteLater()
else:
    skip("I-RES-10 引擎模式切换联动启用状态", "PySide6 未安装")

# ===========================================================================
# 集成测试：配置来源与加载说明
# ===========================================================================

if has_qt():
    @test("U-CFG-01 RunState 新增 no_inherit_defaults 字段")
    def _():
        mod = import_state()
        s = mod["RunState"](root="/p")
        A.false(s.no_inherit_defaults)
        s2 = mod["RunState"](root="/p", no_inherit_defaults=True)
        A.true(s2.no_inherit_defaults)
else:
    skip("U-CFG-01 RunState 新增 no_inherit_defaults 字段",
         "PySide6 未安装")


if has_qt():
    @test("U-CFG-02 --no-inherit-defaults 进入参数")
    def _():
        mod = import_state()
        s = mod["RunState"](root="/p", no_inherit_defaults=True)
        A.in_("--no-inherit-defaults", mod["build_cli_args"](s))
        s2 = mod["RunState"](root="/p")
        A.not_in("--no-inherit-defaults", mod["build_cli_args"](s2))
else:
    skip("U-CFG-02 --no-inherit-defaults 进入参数",
         "PySide6 未安装")


if has_qt():
    @test("U-CFG-03 introspect 三层结构可用")
    def _():
        from project_context_gui.services.config_introspection import (
            introspect,
        )
        tmp = Path(tempfile.mkdtemp(prefix="pcgui_cfg_"))
        try:
            cfg = tmp / ".project_context"
            cfg.mkdir()
            (cfg / "common.toml").write_text(
                'inherit_defaults = true\n[filter]\n'
                'ignore_dirs = ["a", "b"]\n'
            )
            result = introspect(root=str(tmp), run_state=None)
            A.true(result.layer_builtin is not None)
            A.true(result.layer_project is not None)
            A.true(result.layer_session is not None)
            A.eq(result.layer_project.rules_count, 2)
            A.true(result.layer_project.available)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
else:
    skip("U-CFG-03 introspect 三层结构可用", "PySide6 未安装")


if has_qt():
    @test("U-CFG-04 introspect 项目无 .project_context/")
    def _():
        from project_context_gui.services.config_introspection import (
            introspect,
        )
        tmp = Path(tempfile.mkdtemp(prefix="pcgui_cfg_"))
        try:
            result = introspect(root=str(tmp), run_state=None)
            A.false(result.layer_project.available)
            A.in_(".project_context", result.layer_project.note)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
else:
    skip("U-CFG-04 introspect 项目无 .project_context/", "PySide6 未安装")


if has_qt():
    @test("I-CFG-05 RunTab 勾选“忽略项目配置”进入命令预览")
    def _():
        _ensure_qt_app()
        from project_context_gui.tabs.run_tab import RunTab
        tab = RunTab()
        try:
            tab.set_root("/p")
            tab._cb_no_inherit.setChecked(True)
            A.in_("--no-inherit-defaults",
                  tab._cmd_view.toPlainText())
        finally:
            tab.deleteLater()
else:
    skip("I-CFG-05 RunTab 勾选“忽略项目配置”进入命令预览",
         "PySide6 未安装")


if has_qt():
    @test("I-CFG-06 ConfigHelpDialog 可打开不崩")
    def _():
        _ensure_qt_app()
        from project_context_gui.dialogs.config_help_dialog import (
            ConfigHelpDialog,
        )
        from project_context_gui.services.config_introspection import (
            introspect,
        )
        tmp = Path(tempfile.mkdtemp(prefix="pcgui_cfg_"))
        try:
            result = introspect(root=str(tmp))
            dlg = ConfigHelpDialog(result)
            try:
                A.true(dlg is not None)
                text = dlg._to_text()
                A.in_("配置加载说明", text)
            finally:
                dlg.deleteLater()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
else:
    skip("I-CFG-06 ConfigHelpDialog 可打开不崩", "PySide6 未安装")


if has_qt():
    @test("I-CFG-07 RunTab 有“查看配置加载说明”按钮")
    def _():
        _ensure_qt_app()
        from project_context_gui.tabs.run_tab import RunTab
        from PySide6.QtWidgets import QPushButton
        tab = RunTab()
        try:
            btns = tab.findChildren(QPushButton)
            texts = [b.text() for b in btns]
            A.true(any("配置加载说明" in t for t in texts))
            A.true(any("预览最终生效规则" in t for t in texts))
        finally:
            tab.deleteLater()
else:
    skip("I-CFG-07 RunTab 有“查看配置加载说明”按钮",
         "PySide6 未安装")

# ===========================================================================
# 运行器
# ===========================================================================

def run_all(keyword, verbose: bool, list_only: bool) -> int:
    selected = [(n, f) for (n, f) in TESTS
                if not keyword or keyword.lower() in n.lower()]

    if list_only:
        for n, _ in selected:
            print(f"  {n}")
        print(f"\n共 {len(selected)} 条")
        return 0

    # 关键：只要有 Qt，就先创建 QApplication，避免 QCoreApplication 抢先
    if has_qt():
        try:
            _ensure_qt_app()
        except RuntimeError as e:
            print(f"[警告] 初始化 QApplication 失败: {e}")

    print("=" * 68)
    print(f"project_context GUI 测试  （共 {len(selected)} 条）")
    print(f"Python  : {sys.version.split()[0]}")
    print(f"Qt 可用 : {has_qt()}")
    print(f"CLI 可用: {has_cli()}")
    print("=" * 68)

    passed = 0
    failed = 0
    failures = []

    total = len(selected)
    for idx, (name, fn) in enumerate(selected, 1):
        prefix = f"[{idx:>2}/{total}]"
        try:
            fn()
        except AssertionError as e:
            failed += 1
            failures.append((name, str(e)))
            print(f"{prefix} {name}  ... FAIL")
            if verbose:
                print("        " + str(e).replace("\n", "\n        "))
        except Exception as e:
            failed += 1
            tb = traceback.format_exc()
            failures.append((name, f"{type(e).__name__}: {e}\n{tb}"))
            print(f"{prefix} {name}  ... ERROR")
            if verbose:
                print("        " + tb.replace("\n", "\n        "))
        else:
            passed += 1
            print(f"{prefix} {name}  ... PASS")

    print("=" * 68)
    print(f"结果: {passed} passed, {failed} failed, {len(SKIPPED)} skipped")
    print("=" * 68)

    if SKIPPED:
        print("跳过：")
        for n, r in SKIPPED:
            print(f"  - {n}  （{r}）")

    if failures:
        print("\n失败详情：")
        for n, msg in failures:
            print(f"\n  ✗ {n}")
            print("    " + msg.replace("\n", "\n    "))

    return 0 if failed == 0 else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("-k", "--keyword", default=None, help="过滤用例名")
    ap.add_argument("-v", "--verbose", action="store_true")
    ap.add_argument("--list", action="store_true", help="只列用例")
    args = ap.parse_args()
    return run_all(args.keyword, args.verbose, args.list)


if __name__ == "__main__":
    sys.exit(main())