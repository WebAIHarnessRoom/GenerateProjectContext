# 开发指南

适用版本：**0.1.0**

本文面向贡献者，介绍环境准备、目录结构、测试、覆盖率、构建、发布与设计原则。

本文档属于 **GenerateProjectContext** 项目。核心包为 `project_context`，GUI 包为 `project_context_gui`。

仓库地址：https://github.com/WebAIHarnessRoom/GenerateProjectContext

---

## 目录

1. [环境准备](#1-环境准备)
2. [仓库结构](#2-仓库结构)
3. [运行测试](#3-运行测试)
4. [GUI 测试](#4-gui-测试)
5. [覆盖率](#5-覆盖率)
6. [构建与本地安装验证](#6-构建与本地安装验证)
7. [发布流程](#7-发布流程)
8. [设计原则](#8-设计原则)
9. [贡献方式](#9-贡献方式)

---

## 1. 环境准备

```bash
git clone https://github.com/WebAIHarnessRoom/GenerateProjectContext.git
cd GenerateProjectContext

python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

pip install -U pip
pip install -e ".[dev,gui]"
```

若需要 GUI“格式化”功能：

```bash
pip install tomlkit
```

Python 3.9 / 3.10 额外需要：

```bash
pip install tomli
```

---

## 2. 仓库结构

```
GenerateProjectContext/
├── project_context/               核心库
│   ├── __init__.py                公共 API 导出
│   ├── __main__.py                python -m project_context
│   ├── cli.py                     argparse + main
│   ├── api.py                     generate_context
│   ├── params.py                  PARAM_MAP（参数唯一事实来源）
│   ├── errors.py                  异常层次
│   ├── config/
│   │   ├── models.py              数据模型
│   │   ├── loader.py              TOML 加载 + 校验
│   │   ├── merger.py              分层合并
│   │   ├── resolver.py            语言查找 + 自动检测
│   │   └── dumper.py              --dump-config
│   ├── engine/
│   │   ├── context.py             ContextConfig 组装
│   │   ├── collector.py           目录遍历 + 降噪
│   │   ├── reader.py              编码兜底 + 截断
│   │   ├── git_info.py            Git 采集
│   │   ├── renderer.py            Markdown 组装
│   │   └── ast/
│   │       ├── __init__.py        AST_PARSERS 注册表
│   │       └── python.py          Python AST 摘要
│   └── configs/                   内置配置
│       ├── common.toml
│       └── languages/*.toml
│
├── project_context_gui/           GUI
│   ├── __init__.py
│   ├── __main__.py                python -m project_context_gui
│   ├── app.py                     QApplication 启动
│   ├── main_window.py             主窗口 + 状态机
│   ├── state.py                   RunState + CLI 参数拼装
│   ├── dialogs/                   设置、配置说明、固化规则
│   ├── services/                  CLI 子进程、配置读写、引擎解析
│   ├── tabs/                      运行配置、配置文件、运行日志
│   └── widgets/                   折叠面板、文件选择、TOML 编辑器
│
├── tests/                         pytest 用例
│   ├── conftest.py                全局 fixtures
│   ├── unit/                      单元测试
│   ├── regression/                旧 CLI 回归
│   └── e2e/                       CLI/API 一致性门禁
│
├── scripts/dev/                   开发脚本
│   ├── run_tests.py               pytest 封装
│   ├── run_gui_tests.py           GUI 测试 runner
│   ├── run_test_api.py            API 冒烟
│   └── verify_fix.py              关键修复核验
│
├── docs/                          文档
│   ├── cli.md
│   ├── gui.md
│   ├── exe.md
│   ├── api.md
│   ├── configuration.md
│   ├── development.md
│   ├── faq.md
│   └── legacy/v0.0.1/             归档旧版
│
├── .github/
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug_report.yml
│   │   ├── feature_request.yml
│   │   └── config.yml
│   ├── PULL_REQUEST_TEMPLATE.md
│   └── workflows/
│       └── ci.yml
│
├── pyproject.toml                 包元数据
├── pytest.ini                     测试配置
├── .coveragerc                    覆盖率配置
├── README.md
├── CHANGELOG.md
├── SECURITY.md
└── LICENSE
```

---

## 3. 运行测试

```bash
# 全量
pytest -ra

# 只跑门禁
pytest -m gate -ra

# 跳过慢速
pytest -m "not slow" -ra

# 指定目录
pytest tests/unit -ra

# 按名字过滤
pytest -k merger -ra
```

或使用封装脚本：

```bash
python scripts/dev/run_tests.py
python scripts/dev/run_tests.py --gates
python scripts/dev/run_tests.py --cov
python scripts/dev/run_tests.py --quiet
```

`pytest.ini` 定义了：

- `testpaths = tests`
- `addopts = -ra -q --strict-markers`
- marker：`gate`、`slow`、`git`

新增 marker 必须先在 `pytest.ini` 注册，否则 `--strict-markers` 会让测试失败。

---

## 4. GUI 测试

GUI 测试使用独立 runner，不依赖 pytest：

```bash
# Linux/macOS
QT_QPA_PLATFORM=offscreen python scripts/dev/run_gui_tests.py

# Windows PowerShell
$env:QT_QPA_PLATFORM="offscreen"
python scripts/dev/run_gui_tests.py

# 只跑名字含 arg 的用例
python scripts/dev/run_gui_tests.py -k arg

# 只列用例
python scripts/dev/run_gui_tests.py --list
```

该脚本在导入 PySide6 前设置 `QT_QPA_PLATFORM=offscreen`，可在无显示服务器的环境运行。

Linux 上若报缺少 Qt 库，需安装：

```bash
sudo apt-get install -y \
  libegl1 libgl1 libxkbcommon0 libdbus-1-3 libfontconfig1 \
  libxcb-cursor0 libxcb-xinerama0 libxcb-icccm4 libxcb-image0 \
  libxcb-keysyms1 libxcb-randr0 libxcb-render-util0 libxcb-shape0
```

---

## 5. 覆盖率

```bash
pytest --cov=project_context --cov-report=term-missing
```

或：

```bash
python scripts/dev/run_tests.py --cov
```

HTML 报告输出到 `.coverage_html/index.html`。

`.coveragerc` 定义：

- `source = project_context`：只统计核心库
- `branch = True`：统计分支覆盖
- `[paths]`：合并不同机器上的同一源码路径
- `exclude_lines`：排除 `__main__`、`NotImplementedError`、`pragma: no cover`

若要统计 GUI，追加：

```bash
pytest --cov=project_context --cov=project_context_gui
```

---

## 6. 构建与本地安装验证

```bash
python -m build
python -m twine check dist/*
```

在干净虚拟环境中验证 wheel：

```bash
python -m venv /tmp/verify-wheel
# Windows: /tmp/verify-wheel/Scripts/activate
source /tmp/verify-wheel/bin/activate

pip install dist/project_context-0.1.0-py3-none-any.whl

python -c "import project_context; print(project_context.__version__)"
python -c "import project_context.config, project_context.engine.ast"
python -c "from project_context.config.loader import builtin_config_dir; print(builtin_config_dir().is_dir())"
```

最后一条应输出 `True`，表示内置配置被打进 wheel。

再验证 GUI 包可导入：

```bash
pip install "dist/project_context-0.1.0-py3-none-any.whl[gui]"
python -c "import project_context_gui"
```

---

## 7. 发布流程

### 7.1 版本约定

- 语义化版本：`MAJOR.MINOR.PATCH`
- Git tag：`v0.1.0`
- `pyproject.toml` 的 `version` 与 `project_context/__init__.py` 的 `__version__` 必须一致

### 7.2 发布前检查

- [ ] `git status` 干净
- [ ] `pytest -ra` 通过
- [ ] GUI 测试通过
- [ ] `python -m build` 成功
- [ ] `twine check dist/*` 通过
- [ ] wheel 在干净环境可安装
- [ ] `CHANGELOG.md` 已更新
- [ ] `LICENSE` 存在
- [ ] 无敏感信息

### 7.3 发布步骤

```bash
# 1. 更新版本号（pyproject.toml + __init__.py）
# 2. 更新 CHANGELOG.md
# 3. 提交
git add -A
git commit -m "chore: release v0.1.0"

# 4. 打 tag
git tag v0.1.0

# 5. 推送
git push origin main --tags
```

发布完成后验证：

```bash
pip install --index-url https://test.pypi.org/simple/ project-context
pip install project-context
project-context --help
```

### 7.4 回滚

PyPI 不允许删除已发布版本，只能 yank。若发布错误：

1. 在 PyPI 上 yank 该版本
2. 修复后发 PATCH 版本
3. 在 `CHANGELOG` 说明 yank 原因
4. 不要复用已发布的版本号

---

## 8. 设计原则

1. **单一事实来源**
   `PARAM_MAP` 定义所有参数语义，CLI 与 API 都从它派生。

2. **配置与引擎解耦**
   引擎层只接受 `ContextConfig`，不接触 argparse 或文件路径字符串。

3. **不可变优先**
   配置合并返回新实例，避免副作用。

4. **失败可诊断**
   所有配置错误包含来源文件、字段与可用值。

5. **兼容旧行为**
   旧脚本入口、旧参数语义 100% 保留。

6. **本地 = CI**
   GitHub Actions 执行的命令必须能在本地用同一条命令复现。

---

## 9. 贡献方式

1. Fork 仓库，创建分支：`feat/xxx` 或 `fix/xxx`
2. 修改代码，补充测试
3. 本地跑通：
   ```bash
   pytest -ra
   python scripts/dev/run_gui_tests.py
   ```
4. 提交 PR，描述变更与测试方式
5. 等待 CI 全绿与维护者 review

提交信息建议使用 Conventional Commits：

```
feat: 增加 xxx
fix: 修复 xxx
docs: 更新 xxx
test: 补充 xxx
chore: 杂项
```

---

## 参见

- [CLI 使用手册](cli.md)
- [配置系统](configuration.md)
- [Python API](api.md)
- [常见问题](faq.md)