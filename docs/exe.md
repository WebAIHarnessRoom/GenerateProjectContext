# exe 分发版手册

适用版本：**0.1.0**

本文档属于 **GenerateProjectContext** 项目。exe 文件名 `generate-project-context.exe`，与源码版 `project-context` 功能一致。
本文档面向使用打包好的 `generate-project-context.exe` 的用户。exe 与源码版功能完全一致，参数与配置文件格式相同。本文只说明 exe 特有的部署、运行与问题排查。

若你使用源码或 pip 安装，请阅读 [CLI 使用手册](cli.md)。

---

## 目录

1. [简介](#1-简介)
2. [系统要求](#2-系统要求)
3. [部署方式](#3-部署方式)
4. [快速开始](#4-快速开始)
5. [与源码版的差异](#5-与源码版的差异)
6. [常见问题](#6-常见问题)
7. [卸载](#7-卸载)

---

## 1. 简介

`generate-project-context.exe` 是 `project-context` 的 Windows 独立打包版本，内置 Python 运行时，无需安装 Python。

生成内容包括：

- 项目概览（文件数、行数、激活语言、Git 信息）
- 目录结构（tree 风格）
- 代码结构总览（Python 类 / 函数签名摘要）
- 源码与配置文件内容
- Git 提交历史

用途：

- 接手陌生项目时快速了解全貌
- 把整份文档贴给 AI，让 AI 带着完整上下文分析代码
- 作为项目文档快照纳入版本管理

---

## 2. 系统要求

| 项 | 要求 |
|---|---|
| 操作系统 | Windows 10 / 11（64 位） |
| 依赖 | 无（已内置 Python 运行时） |
| 磁盘 | 约 30 MB（standalone 模式） |
| Git | 可选（有则输出 Git 历史章节） |

---

## 3. 部署方式

根据打包模式，分发方式不同。

### 3.1 Standalone 模式（推荐）

拿到的是一个目录：

```text
gpc/
├── generate-project-context.exe     ← 主程序
├── python310.dll
├── project_context/
│   └── configs/                     ← 内置配置文件
└── ...（其它依赖文件）
```

**部署步骤**：

1. 把整个 `gpc/` 目录拷贝到目标机器任意位置（如 `D:\tools\gpc\`）
2. **不要只拷贝 exe 文件**，同目录下的 dll、`project_context/` 等必须一起拷

**建议**：把 `gpc/` 目录加入系统 `Path`，之后可在任意位置直接调用：

```text
generate-project-context.exe .
```

### 3.2 Onefile 模式

拿到的是单个文件 `generate-project-context.exe`，直接拷走即可。

首次运行会解压到临时目录，**启动稍慢（约 2–5 秒）**，之后会快一些。

---

## 4. 快速开始

打开命令行（PowerShell 或 CMD），进入 exe 所在目录：

```powershell
# 分析当前目录，生成 PROJECT_CONTEXT.md
.\generate-project-context.exe .

# 分析指定项目，输出到指定文件
.\generate-project-context.exe D:\myproject -o context.md

# 已加入 PATH 后可以省略 .\
generate-project-context.exe D:\myproject

# 只出结构，不输出源码
.\generate-project-context.exe . --no-content

# 查看最终生效配置
.\generate-project-context.exe . --dump-config

# 列出可用语言
.\generate-project-context.exe . --list-languages
```

运行完成后会在目标目录看到 `PROJECT_CONTEXT.md`，用任意 Markdown 阅读器打开即可。

---

## 5. 与源码版的差异

exe 与源码版的功能、参数、配置文件格式**完全一致**。差异只在调用方式：

| 源码版 | exe 版 |
|---|---|
| `project-context .` | `generate-project-context.exe .` |
| `python -m project_context .` | `generate-project-context.exe .` |

因此：

- **参数**：全部参数见 [CLI 使用手册](cli.md) 第 3 节
- **配置文件**：三层配置、字段、自定义语言见 [配置系统](configuration.md)
- **语言检测**：见 [CLI 使用手册](cli.md) 第 4 节
- **输出结构**：见 [CLI 使用手册](cli.md) 第 5 节
- **常用示例**：见 [CLI 使用手册](cli.md) 第 6 节，把命令前缀换成 exe 即可

exe 特有的只有：

- 部署方式（第 3 节）
- 杀毒软件误报（第 6 节）
- 控制台编码（第 6 节）
- 路径含空格或中文（第 6 节）

---

## 6. 常见问题

### Q1：运行后没有看到 `PROJECT_CONTEXT.md`？

- 默认输出路径是 `<项目根>/PROJECT_CONTEXT.md`
- 用 `-o` 显式指定时以指定路径为准
- 检查当前目录是否为目标项目目录

### Q2：Windows Defender / 杀毒软件报毒？

Nuitka 或 PyInstaller 打包的 exe 有时被误报（尤其是 onefile 模式）。可选：

- 加入杀毒软件白名单
- 使用 standalone 模式（误报率更低）
- 对 exe 做代码签名（如有企业证书）

### Q3：控制台输出中文乱码？

已内置 UTF-8 兜底。若仍有问题：

```powershell
# 临时设置控制台为 UTF-8
chcp 65001
.\generate-project-context.exe .
```

### Q4：项目路径含空格或中文？

支持。用引号包裹即可：

```powershell
.\generate-project-context.exe "D:\我的项目\demo app"
```

### Q5：exe 参数忘了怎么办？

```powershell
.\generate-project-context.exe --help
```

### Q6：exe 和源码版可以共用配置文件吗？

可以。两者读取相同的 `.project_context/` 目录，配置文件格式完全一致。

### Q7：环境没有 Git 会怎样？

自动降级：文档跳过第 5 章，其它章节正常生成。

---

## 7. 卸载

**Standalone 模式**：直接删除整个 `gpc/` 目录。

**Onefile 模式**：删除 `generate-project-context.exe` 文件。

**不会**在系统其它位置残留任何文件（首次运行时的临时文件由系统自动清理）。

---

## 参见

- [CLI 使用手册](cli.md)
- [配置系统](configuration.md)
- [常见问题](faq.md)