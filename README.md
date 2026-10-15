# project_context

> 把任意代码项目整理成一份 Markdown 上下文文档 —— 用于人工快速理解项目，也用于给 AI 提供完整工程上下文。

`project_context` 会遍历项目目录、过滤噪音、提取代码结构、汇总 Git 历史，最终生成一份结构清晰、可直接喂给大语言模型的 Markdown 文档。

---

## 特性

- 🔍 **语言感知降噪** — 自动识别项目使用了哪些语言，只应用相关语言的忽略规则
- ⚙️ **高度可配置** — 通用配置 + 语言级配置分层合并，用户可覆盖 / 新增
- 🔁 **双执行模式** — 命令行参数与 Python API 行为字节级一致
- 🧠 **AST 代码结构摘要** — 从 Python 源码提取类 / 函数签名，无需读全文即可把握骨架
- 📜 **Git 历史汇总** — 分支、最新提交、提交概览与变更文件清单
- 🔎 **可诊断** — `--dump-config` 打印最终生效配置与来源，`--list-languages` 列出可用语言
- 🧩 **零强制依赖** — 仅用标准库（Python 3.10 及以下需 `tomli`）
- 🔄 **向后兼容** — 保留旧版脚本入口与全部旧参数

---

## 安装

无需安装，直接使用即可。要求 **Python 3.9+**。

```bash
# Python 3.11+ 无需额外依赖
# Python 3.9 / 3.10 需要 tomli
pip install tomli
```

可选：安装为可编辑包（如需从任意目录调用）

```bash
pip install -e .
```

---

## 图形界面（GUI）

除命令行外，本项目提供图形界面，用鼠标完成"选目录 → 点运行 → 打开输出文件夹"。

### 安装

```bash
pip install -e .[gui]
``` {data-source-line="397"}

### 启动

```bash
# 方式一：模块入口 {#方式一模块入口-1  data-source-line="402"}
python -m project_context_gui

# 方式二：脚本入口 {#方式二脚本入口  data-source-line="405"}
project-context-gui
``` {data-source-line="407"}

### 功能

- 选项目文件夹、输出文件（全部用鼠标点选，不用手输路径）
- 语言模式（自动检测 / 全部 / 手动选择）
- 章节开关（源码 / AST / Git / 时间戳）
- 过滤降噪（排除 glob / 目录 / 后缀，高级折叠）
- 实时命令预览，所见即所跑
- 查看与编辑 `.project_context/` 下的 TOML（行号、高亮、校验、格式化）
- 运行日志按级别过滤、搜索、导出
- 主题（跟随系统 / 浅色 / 深色）
- 最近项目、拖拽打开、快捷键
- 成功后一键打开输出文件夹

### 与 CLI 的一致性

GUI 通过 `python -m project_context` 子进程执行原 CLI，参数拼装与手工输入**完全一致**。
关闭时间戳后，GUI 输出与手工 CLI 输出**字节级一致**（`run_gui_tests.py` 中有专项测试）。

### 完整文档

见 [`docs/gui.md`](docs/gui.md)。


---

## 快速开始

### 方式一：命令行

```bash
# 分析当前目录，输出到 ./PROJECT_CONTEXT.md
python -m project_context .

# 指定输出路径
python -m project_context /path/to/project -o context.md

# 兼容旧入口脚本（等价）
python generate_project_context.py .
```

### 方式二：Python API

```python
from project_context import generate_context

# 最简用法：输出到 <root>/PROJECT_CONTEXT.md
generate_context(root=".")

# 只要 Markdown 字符串，不落盘
md = generate_context(root=".", output=None)

# 精细控制
generate_context(
    root=".",
    output="ctx.md",
    languages=["python", "node"],
    exclude=["*.pb.go"],
    exclude_dirs=["third_party"],
    max_file_size_kb=300,
)
```

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

**第三章示例**（AST 摘要）：

```markdown
### `user_service.py`

- **class** `UserService`  — 用户业务逻辑。
  - **def** `__init__(self, repo: UserRepo, cache: Cache | None = None)`
  - **async def** `get(self, uid: int) -> User`  — 按 id 查询用户。
  - **def** `list_active(self, limit: int = 100) -> list[User]`  — 列出活跃用户。
```

---

## 配置系统

配置分三层，优先级从低到高：

```
内置配置 → 项目本地配置 → 命令行 / API 显式指定
```

### 项目本地配置

放在项目根的 `.project_context/` 目录下，脚本会自动加载：

```
myproject/
├── .project_context/
│   ├── common.toml               # 通用配置
│   └── languages/
│       ├── python.toml           # 覆盖内置 Python 规则
│       └── mydsl.toml            # 新增自定义语言
└── ...
```

### 通用配置 `.project_context/common.toml`

```toml
inherit_defaults = true           # 是否继承内置配置

[filter]
ignore_dirs    = ["third_party"]  # 追加忽略目录
ignore_suffixes = [".bak"]        # 追加忽略后缀
exclude_globs  = ["tests/fixtures/*"]

[limits]
max_file_size_kb     = 300
max_git_commits      = 100
max_files_per_commit = 30

[features]
include_content = true
include_ast     = true
include_git     = true

[languages]
active           = "auto"         # 或 ["python", "go"] 或 "all"
detect_min_files = 1
```

### 语言配置 `.project_context/languages/python.toml`

```toml
inherit_defaults = true

[filter]
ignore_dirs = ["local_venv"]      # 追加项目特有目录

[detect]
suffixes = [".py", ".pyi"]
```

### 新增自定义语言

`.project_context/languages/mydsl.toml`：

```toml
schema_version = 1
name = "mydsl"
inherit_defaults = false          # 新语言无内置可继承

[detect]
suffixes = [".mydsl"]

[filter]
ignore_dirs = ["mydsl_cache"]

[code_langs]
".mydsl" = "plaintext"

[ast]
parser = "none"
```

显式激活：

```bash
python -m project_context . --languages mydsl,python
```

---

## 语言自动检测

默认 `--languages auto`。脚本会**预扫描项目**（不读文件内容），根据三种信号判断激活哪些语言：

| 信号 | 含义 | 示例 |
|---|---|---|
| `suffixes` | 文件后缀 | `.py` → Python |
| `file_globs` | 文件名通配 | `go.mod` → Go |
| `dir_markers` | 目录标志文件 | `pyproject.toml` → Python |

**内置语言**（9 种）：

`python` `node` `go` `rust` `java` `cpp` `php` `ruby` `dotnet`

**为什么要做语言检测？** 不同语言的"垃圾目录"不一样 —— 如果对所有项目套用所有规则，会把 `target`（Rust 构建产物）从 Java 项目里误删。语言检测保证只应用相关规则。

**控制阈值**：

```bash
# 至少 3 个文件命中才激活该语言
python -m project_context . --detect-min-files 3
```

**显式指定**（跳过检测）：

```bash
python -m project_context . --languages python,go
python -m project_context . --languages all
```

**列出所有可用语言**：

```bash
python -m project_context . --list-languages
```

---

## 命令行参数

### 位置参数与基础

| 参数 | 说明 |
|---|---|
| `root` | 项目根目录，默认 `.` |
| `-o, --output PATH` | 输出路径，默认 `<root>/PROJECT_CONTEXT.md` |
| `--quiet` | 静默模式（不打印进度） |

### 配置文件

| 参数 | 说明 |
|---|---|
| `--config PATH` | 指定通用配置文件 |
| `--inherit-defaults` | 继承内置配置（默认） |
| `--no-inherit-defaults` | 不继承内置配置 |
| `--languages LIST` | 激活语言：`auto` / `all` / `python,go` |
| `--detect-min-files N` | 自动检测阈值 |
| `--language-dir DIR` | 额外语言配置目录（可重复） |
| `--language-config NAME=PATH` | 覆盖某语言配置（可重复） |

### 降噪（追加到配置之上）

| 参数 | 说明 |
|---|---|
| `--exclude GLOB` | 追加忽略文件 glob（可重复） |
| `--exclude-dir NAME` | 追加忽略目录名（可重复） |
| `--exclude-dir-glob PAT` | 追加忽略目录 glob（可重复） |
| `--exclude-suffix SUF` | 追加忽略后缀（可重复） |

### 行为限制与开关

| 参数 | 默认 | 说明 |
|---|---|---|
| `--max-file-size KB` | 200 | 单文件大小上限，超出截断 |
| `--max-git-commits N` | 50 | 采集的提交数量 |
| `--max-files-per-commit N` | 20 | 每条提交列出的文件数 |
| `--no-git` | - | 不采集 Git 信息 |
| `--no-content` | - | 不输出源码（只出结构 + Git） |
| `--no-ast` | - | 不输出 AST 摘要 |
| `--no-timestamp` | - | 关闭时间戳（便于快照对比） |

### 诊断

| 参数 | 说明 |
|---|---|
| `--dump-config` | 打印合并后的最终配置并退出 |
| `--list-languages` | 列出可用语言并退出 |

### 常用示例

```bash
# 排除某种文件与某个目录
python -m project_context . --exclude "*.pb.go" --exclude-dir third_party

# 只出结构，不要源码（大项目更快）
python -m project_context . --no-content

# 查看最终生效配置
python -m project_context . --dump-config

# 显式指定语言 + 覆盖某语言配置
python -m project_context . \
    --languages python,node \
    --language-config python=./my_python.toml
```

---

## Python API

### 完整签名

```python
from project_context import generate_context

generate_context(
    root=".",                              # 项目根目录
    output="ctx.md",                       # None → 返回 str；否则返回 Path
    config=None,                           # 通用配置文件路径 / dict / None
    inherit_defaults=None,                 # bool | None
    languages=None,                        # "auto" | "all" | ["python"] | None
    detect_min_files=None,                 # int | None
    language_dirs=None,                    # [str|Path]
    language_configs=None,                 # {"python": "path.toml"}
    exclude=None,                          # ["*.pb.go"]
    exclude_dirs=None,                     # ["third_party"]
    exclude_dir_globs=None,
    exclude_suffixes=None,
    max_file_size_kb=None,
    max_git_commits=None,
    max_files_per_commit=None,
    include_git=None,
    include_content=None,
    include_ast=None,
    no_timestamp=None,
    dump_config=False,                     # True 返回配置 TOML 字符串 / Path
) -> Path | str
```

### 返回值约定

| `output` | 返回 |
|---|---|
| 路径（`str` / `Path`） | `Path`（写盘后的绝对路径） |
| `None` | `str`（Markdown 内容） |
| `dump_config=True` + `output=None` | `str`（TOML 配置） |

### 示例

```python
from project_context import generate_context, list_available_languages

# 1. 基础
generate_context(root="/path/to/project")

# 2. 只要字符串
md = generate_context(root=".", output=None)

# 3. 显式语言 + 追加降噪
generate_context(
    root=".",
    languages=["python", "go"],
    exclude=["*.pb.go"],
    exclude_dirs=["third_party"],
    max_file_size_kb=300,
)

# 4. 覆盖某语言配置
generate_context(
    root=".",
    languages=["python"],
    language_configs={"python": "./my_python.toml"},
)

# 5. 探查
print(list_available_languages())          # ['cpp', 'dotnet', 'go', ...]
print(generate_context(root=".", dump_config=True))
```

---

## CLI 与 API 一致性

相同输入下，CLI 与 API 生成的文档**字节级一致**（关闭时间戳后）。测试套件里有一条 `tests/e2e/test_parity.py` 专门作为门禁：

```bash
pytest tests/e2e/test_parity.py -v
```

---

## 目录结构

```
project_context/
├── __init__.py               # 公共 API 导出
├── __main__.py               # python -m project_context
├── cli.py                    # argparse + main
├── api.py                    # generate_context
├── params.py                 # PARAM_MAP（参数唯一事实来源）
├── errors.py                 # 异常层次
├── config/
│   ├── models.py             # 数据模型
│   ├── loader.py             # TOML 加载 + 校验
│   ├── merger.py             # 分层合并
│   ├── resolver.py           # 语言查找 + 自动检测
│   └── dumper.py             # --dump-config
├── engine/
│   ├── context.py            # ContextConfig 组装
│   ├── collector.py          # 目录遍历 + 降噪
│   ├── reader.py             # 编码兜底 + 截断
│   ├── git_info.py           # Git 采集
│   ├── renderer.py           # Markdown 组装
│   └── ast/
│       ├── __init__.py       # AST_PARSERS 注册表
│       └── python.py         # Python AST 摘要
└── configs/
    ├── common.toml           # 通用配置
    └── languages/
        ├── python.toml
        ├── node.toml
        ├── go.toml
        ├── rust.toml
        ├── java.toml
        ├── cpp.toml
        ├── php.toml
        ├── ruby.toml
        └── dotnet.toml

generate_project_context.py   # 兼容旧调用的入口
```

---

## 运行测试

```bash
# 全量
python run_tests.py

# 只跑某类
python run_tests.py tests/unit
python run_tests.py -k merger

# 带覆盖率
python run_tests.py --cov

# 只跑门禁
python run_tests.py --gates
```

当前状态：**103 passed**，整体覆盖率 ≥ 80%。

---

## 常见问题

### Q：为什么有的目录没被忽略？

先看 `--dump-config` 输出的最终规则：

```bash
python -m project_context . --dump-config
```

- 如果规则没出现 → 该语言的配置没被激活（可能没检测到对应文件类型，或 `detect_min_files` 太高）
- 如果规则出现了但目录还在 → 检查是 `ignore_dirs`（精确匹配目录名）还是 `ignore_dir_globs`（通配）

### Q：如何只输出部分章节？

```bash
python -m project_context . --no-content --no-git
```

### Q：AI 上下文窗口有限，如何压缩输出？

```bash
# 不出源码，只出结构 + 目录树
python -m project_context . --no-content

# 限制单文件大小
python -m project_context . --max-file-size 50
```

### Q：非 Python 语言能出 AST 摘要吗？

目前只有 Python 有 AST 摘要器。其它语言的代码会以原文形式出现在第 4 章。扩展新语言：在 `project_context/engine/ast/` 下新增解析器，注册到 `AST_PARSERS`，然后在对应 `languages/*.toml` 里设置 `ast.parser`。

### Q：Windows 上输出乱码？

CLI 已兼容 GBK 控制台。文档内容始终以 UTF-8 写入文件。

### Q：环境没有 Git 会怎样？

自动降级：文档跳过第 5 章，其它章节正常生成。

### Q：`--no-timestamp` 有什么用？

关闭文档头部的时间戳，便于**快照对比**与**版本控制**（同一输入多次运行输出完全一致）。

---

## 设计原则

1. **单一事实来源** — `PARAM_MAP` 定义所有参数语义，CLI 与 API 都从它派生
2. **配置与引擎解耦** — 引擎层只接受 `ContextConfig`，不接触 argparse / 文件路径字符串
3. **不可变优先** — 配置合并返回新实例，避免副作用
4. **失败可诊断** — 所有配置错误包含来源文件 + 字段 + 可用值
5. **兼容旧行为** — 旧脚本入口、旧参数语义 100% 保留

---

## 许可

MIT（或项目实际许可，请按需修改）