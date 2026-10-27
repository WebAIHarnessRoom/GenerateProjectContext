# GenerateProjectContext

> 把任意代码项目整理成一份 Markdown 上下文文档 —— 用于人工快速理解项目，也用于给 AI 提供完整工程上下文。

`GenerateProjectContext` 是一个项目上下文文档生成工具。仓库包含两个 Python 包：

- `project_context`：核心库，提供 CLI `project-context` 与 Python API
- `project_context_gui`：图形界面，提供 `project-context-gui`

当前版本：**0.1.0**

仓库地址：https://github.com/WebAIHarnessRoom/GenerateProjectContext

---

## 名称约定

| 层面 | 名称 | 用途 |
|---|---|---|
| 仓库 / 项目 | `GenerateProjectContext` | GitHub 仓库、本地文件夹 |
| PyPI 包 | `project-context` | `pip install project-context` |
| 核心导入包 | `project_context` | `import project_context`、`python -m project_context` |
| GUI 导入包 | `project_context_gui` | `import project_context_gui`、`python -m project_context_gui` |
| CLI 命令 | `project-context` | 命令行调用 |
| GUI 命令 | `project-context-gui` | 图形界面调用 |
| exe 文件 | `generate-project-context.exe` | Windows 分发包 |

---

## 特性

- **语言感知降噪** — 自动识别项目使用了哪些语言，只应用相关语言的忽略规则
- **高度可配置** — 通用配置 + 语言级配置分层合并，用户可覆盖或新增
- **双执行模式** — 命令行参数与 Python API 行为字节级一致
- **AST 代码结构摘要** — 从 Python 源码提取类与函数签名
- **Git 历史汇总** — 分支、最新提交、提交概览与变更文件清单
- **可诊断** — `--dump-config` 打印最终生效配置与来源
- **零强制依赖** — 仅用标准库（Python 3.9/3.10 需 `tomli`）
- **图形界面** — 可选 PySide6 GUI，鼠标完成选目录、运行、打开输出

---

## 安装

要求 **Python 3.9+**。

```bash
# 核心 CLI，无第三方依赖
pip install project-context

# 需要 GUI
pip install "project-context[gui]"

# 从源码安装（开发用）
git clone https://github.com/WebAIHarnessRoom/GenerateProjectContext.git
cd GenerateProjectContext
pip install -e ".[dev,gui]"
```

---

## 30 秒快速开始

### 命令行

```bash
# 分析当前目录，输出到 ./PROJECT_CONTEXT.md
project-context .

# 指定输出路径
project-context /path/to/project -o context.md

# 只出结构，不输出源码（适合大项目喂给 AI）
project-context . --no-content
```

### Python API

```python
from project_context import generate_context

# 输出到 <root>/PROJECT_CONTEXT.md
generate_context(root=".")

# 只要 Markdown 字符串，不落盘
md = generate_context(root=".", output=None)
```

### GUI

```bash
project-context-gui
```

打开项目文件夹 → 点“开始生成” → 点“打开输出文件夹”。

---

## 生成的文档结构

```markdown
# 项目上下文文档：myproject

## 1. 项目概览        # 文件数、行数、激活语言、Git 分支、配置来源
## 2. 目录结构        # tree 风格（已过滤噪音）
## 3. 代码结构总览     # Python 类 / 函数签名（AST 摘要）
## 4. 源码与配置文件内容 # 每个文件的完整内容（带代码块语言标签）
## 5. Git 提交历史     # 分支、提交概览表、提交详情
```

---

## 仓库结构

```
GenerateProjectContext/
├── project_context/            核心库
│   ├── cli.py                  CLI 入口
│   ├── api.py                  generate_context
│   ├── config/                 配置加载与合并
│   ├── engine/                 收集、读取、渲染、AST、Git
│   └── configs/                内置配置
├── project_context_gui/        GUI
│   ├── app.py                  启动入口
│   ├── main_window.py          主窗口
│   ├── dialogs/                设置、配置说明、固化规则
│   ├── services/               CLI 子进程、配置读写、引擎解析
│   ├── tabs/                   运行配置、配置文件、运行日志
│   └── widgets/                折叠面板、文件选择、TOML 编辑器
├── tests/                      pytest 用例
├── scripts/dev/                开发脚本
├── docs/                       文档
├── pyproject.toml              包元数据
├── pytest.ini                  测试配置
└── .coveragerc                 覆盖率配置
```

---

## 文档

| 文档 | 适合谁 |
|---|---|
| [CLI 使用手册](docs/cli.md) | 用命令行或源码运行 |
| [GUI 使用手册](docs/gui.md) | 用图形界面 |
| [exe 分发版手册](docs/exe.md) | 使用打包好的 exe |
| [配置系统](docs/configuration.md) | 定制忽略规则、新增语言 |
| [Python API](docs/api.md) | 在代码里调用 |
| [开发指南](docs/development.md) | 贡献代码、跑测试、发布 |
| [常见问题](docs/faq.md) | 遇到问题先看这里 |

---

## 设计原则

1. **单一事实来源** — 参数语义由 `PARAM_MAP` 定义，CLI 与 API 都从它派生
2. **配置与引擎解耦** — 引擎只接受 `ContextConfig`，不接触 argparse 或文件路径字符串
3. **不可变优先** — 配置合并返回新实例，避免副作用
4. **失败可诊断** — 配置错误包含来源文件、字段与可用值
5. **兼容旧行为** — 旧脚本入口与旧参数语义保留

更多设计说明见 [开发指南](docs/development.md)。

---

## 贡献

欢迎 Issue 与 PR。提交前请阅读 [开发指南](docs/development.md)，并在本地跑通测试：

```bash
pytest -ra
```

---

## 许可证

[MIT](LICENSE)