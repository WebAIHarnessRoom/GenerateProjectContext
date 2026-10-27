# CLI 使用手册

适用版本：**0.1.0**

本文档属于 **GenerateProjectContext** 项目。核心包为 `project_context`，CLI 命令为 `project-context`。
本文档介绍 `project-context` 命令行工具的完整用法。若使用打包好的 exe，请同时阅读 [exe 手册](exe.md)；参数与源码版完全一致。

---

## 目录

1. [安装与入口](#1-安装与入口)
2. [快速开始](#2-快速开始)
3. [命令行参数](#3-命令行参数)
4. [语言自动检测](#4-语言自动检测)
5. [输出文档结构](#5-输出文档结构)
6. [常用示例](#6-常用示例)
7. [与 API 的一致性](#7-与-api-的一致性)

---

## 1. 安装与入口

```bash
pip install project-context
```

安装后提供两个命令：

| 命令 | 作用 |
|---|---|
| `project-context` | 命令行入口 |
| `project-context-gui` | 图形界面入口（需安装 `[gui]`） |

也可以模块方式运行：

```bash
python -m project_context .
```

Python 3.9 / 3.10 需要 `tomli`：

```bash
pip install tomli
```

---

## 2. 快速开始

```bash
# 分析当前目录，输出到 ./PROJECT_CONTEXT.md
project-context .

# 分析指定项目，输出到指定文件
project-context D:\myproject -o context.md

# 只出结构，不输出源码
project-context . --no-content

# 查看最终生效配置
project-context . --dump-config

# 列出可用语言
project-context . --list-languages
```

运行完成后默认在项目根生成 `PROJECT_CONTEXT.md`。

---

## 3. 命令行参数

### 3.1 位置参数与基础

| 参数 | 说明 | 默认 |
|---|---|---|
| `root` | 项目根目录（位置参数） | 当前目录 |
| `-o, --output PATH` | 输出文件路径 | `<root>/PROJECT_CONTEXT.md` |
| `--quiet` | 静默模式，不打印进度 | 关闭 |
| `--list-languages` | 列出所有可用语言并退出 | — |
| `--dump-config` | 打印合并后的最终配置并退出 | — |
| `--help` | 显示帮助 | — |

### 3.2 配置文件

| 参数 | 说明 |
|---|---|
| `--config PATH` | 指定通用配置文件 |
| `--inherit-defaults` | 继承内置配置（默认开启） |
| `--no-inherit-defaults` | 不继承内置配置，只用用户配置 |
| `--languages LIST` | 激活语言：`auto`（默认）/ `all` / `python,go` |
| `--detect-min-files N` | 自动检测阈值，默认 1 |
| `--language-dir DIR` | 额外语言配置目录（可重复） |
| `--language-config NAME=PATH` | 覆盖某语言配置（可重复） |

配置系统详见 [配置系统](configuration.md)。

### 3.3 降噪（叠加在配置之上）

| 参数 | 说明 |
|---|---|
| `--exclude GLOB` | 追加忽略文件 glob（可重复），如 `--exclude "*.pb.go"` |
| `--exclude-dir NAME` | 追加忽略目录名（可重复），如 `--exclude-dir third_party` |
| `--exclude-dir-glob PAT` | 追加忽略目录 glob（可重复），如 `--exclude-dir-glob "build/**"` |
| `--exclude-suffix SUF` | 追加忽略后缀（可重复），如 `--exclude-suffix .tmp` |

这些参数只对本次运行生效，不写回配置文件。若想永久生效，请编辑 `.project_context/` 下的 TOML。

### 3.4 行为限制与开关

| 参数 | 说明 | 默认 |
|---|---|---|
| `--max-file-size KB` | 单文件大小上限，超出截断 | 200 |
| `--max-git-commits N` | 采集的提交数量 | 50 |
| `--max-files-per-commit N` | 每条提交列出的文件数 | 20 |
| `--no-git` | 不采集 Git 信息 | — |
| `--no-content` | 不输出源码，只出结构与 Git | — |
| `--no-ast` | 不输出代码结构总览 | — |
| `--no-timestamp` | 关闭时间戳（便于快照对比） | — |

### 3.5 诊断

| 参数 | 说明 |
|---|---|
| `--dump-config` | 打印合并后的最终配置并退出 |
| `--list-languages` | 列出可用语言并退出 |

`--dump-config` 输出示例：

```toml
# 合并后的最终配置（只读展示，可用于 --config 参考）
# root = /path/to/project

[limits]
max_file_size_kb     = 200
max_git_commits      = 50
max_files_per_commit = 20

[features]
include_content = true
include_ast     = true
include_git     = true
no_timestamp    = false

[languages]
active = ['python', 'node']

[filter]
ignore_dirs = [
  '.git',
  '__pycache__',
  ...
]

# 配置来源（按加载顺序）
# - /path/to/site-packages/project_context/configs/common.toml
# - /path/to/project/.project_context/common.toml
```

---

## 4. 语言自动检测

默认行为 `--languages auto`：工具预扫描项目文件名（不读内容），根据三种信号判断激活哪些语言。

| 信号 | 含义 | 示例 |
|---|---|---|
| `suffixes` | 文件后缀 | `.py` → Python |
| `file_globs` | 文件名通配 | `go.mod` → Go |
| `dir_markers` | 目录标志文件 | `pyproject.toml` → Python |

**为什么要检测语言？** 不同语言的“垃圾目录”不同。比如 `target` 是 Rust 的构建产物，但对 Java 项目可能是有效目录。语言检测保证只应用相关规则，避免误删。

**内置语言（9 种）：**

`python` `node` `go` `rust` `java` `cpp` `php` `ruby` `dotnet`

**查看全部可用语言：**

```bash
project-context . --list-languages
```

**控制检测灵敏度：**

```bash
# 至少 3 个文件命中才激活该语言
project-context . --detect-min-files 3
```

**跳过检测，显式指定：**

```bash
project-context . --languages python,go
project-context . --languages all
```

语言配置字段详见 [配置系统](configuration.md)。

---

## 5. 输出文档结构

生成的 Markdown 包含 5 个章节：

```
# 项目上下文文档：<项目名>

## 1. 项目概览
   文件数、行数、激活语言、Git 分支、配置来源、文件类型分布

## 2. 目录结构
   tree 风格，已过滤噪音

## 3. 代码结构总览
   Python 类 / 函数签名摘要（--no-ast 时无此章）

## 4. 源码与配置文件内容
   每个文件的完整内容，带代码块语言标签（--no-content 时无此章）

## 5. Git 提交历史
   分支、提交概览表、提交详情（无 Git 或 --no-git 时无此章）
```

第 3 章示例：

```markdown
### `user_service.py`

- **class** `UserService`  — 用户业务逻辑。
  - **def** `__init__(self, repo: UserRepo, cache: Cache | None = None)`
  - **async def** `get(self, uid: int) -> User`  — 按 id 查询用户。
  - **def** `list_active(self, limit: int = 100) -> list[User]`  — 列出活跃用户。
```

---

## 6. 常用示例

### 6.1 接手陌生项目，快速了解全貌

```bash
project-context D:\new-project -o overview.md
```

先看第 1、2 章。

### 6.2 把项目喂给 AI

```bash
# 大型项目：不出源码，减小体积
project-context . --no-content -o ai-context.md

# 小型项目：完整输出
project-context . -o ai-context.md
```

### 6.3 排除项目特有的噪音

PowerShell：

```powershell
project-context . `
    --exclude "*.pb.go" `
    --exclude-dir third_party `
    --exclude-suffix .tmp
```

Bash：

```bash
project-context . \
    --exclude "*.pb.go" \
    --exclude-dir third_party \
    --exclude-suffix .tmp
```

### 6.4 只生成目录结构（超轻量）

```bash
project-context . --no-content --no-ast --no-git
```

### 6.5 用于版本控制 / 快照对比

```bash
# 关闭时间戳，同一输入多次运行输出完全一致
project-context . --no-timestamp -o PROJECT_CONTEXT.md
```

### 6.6 审计仓库历史演化

```bash
project-context . --max-git-commits 200 -o history.md
```

### 6.7 自定义语言的项目

在项目根创建 `.project_context/languages/mydsl.toml`，之后：

```bash
project-context . --languages mydsl,python
```

### 6.8 只分析某个子目录

```bash
project-context .\src -o src-context.md
```

---

## 7. 与 API 的一致性

相同输入下，CLI 与 API 生成的文档字节级一致（关闭时间戳后）。测试套件中 `tests/e2e/test_parity.py` 专门作为门禁：

```bash
pytest tests/e2e/test_parity.py -v
```

API 用法见 [Python API](api.md)。

---

## 参见

- [配置系统](configuration.md)
- [Python API](api.md)
- [exe 分发版手册](exe.md)
- [常见问题](faq.md)