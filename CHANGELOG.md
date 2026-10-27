# Changelog

本文件记录项目所有值得注意的变更。

格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

项目仓库：`GenerateProjectContext`  
GitHub：https://github.com/WebAIHarnessRoom/GenerateProjectContext  
PyPI 包名：`project-context`

## [Unreleased]

### 计划中
- 补齐 GUI“预览最终生效规则”对话框
- 统一 `pyproject.toml` 与包内版本号
- 增加 `.github/workflows/publish.yml`

## [0.1.0] - 2026-10-19

首个开源版本。

### 新增
- 核心 CLI：`project-context`，支持目录扫描、降噪、AST 摘要、Git 历史
- Python API：`generate_context()`
- 配置系统：三层合并（内置 / 项目 `.project_context/` / 命令行）
- 语言自动检测：9 种内置语言（python、node、go、rust、java、cpp、php、ruby、dotnet）
- 诊断命令：`--dump-config`、`--list-languages`
- 图形界面：`project-context-gui`
  - 运行配置、配置文件、运行日志三个 Tab
  - 执行引擎：自动 / Python / EXE
  - 配置加载说明与固化规则
- 测试：单元、回归、CLI/API 一致性门禁
- 文档：README、CLI 手册、GUI 手册、exe 手册、配置、API、开发指南、FAQ

### 已知问题
- `project_context_gui/dialogs/effective_rules_dialog.py` 为空，GUI“预览最终生效规则”不可用
- `pyproject.toml` 的 `packages` 未包含子包，从 wheel 安装后可能缺模块
- `pyproject.toml` 版本（0.1.0）与 `project_context/__init__.py`（2.0.0）不一致
- `gui` 可选依赖缺 `tomlkit`，“格式化”按钮静默失效

[Unreleased]: https://github.com/WebAIHarnessRoom/GenerateProjectContext/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/WebAIHarnessRoom/GenerateProjectContext/releases/tag/v0.1.0