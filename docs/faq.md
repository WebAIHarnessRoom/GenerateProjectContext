# 常见问题

适用版本：**0.1.0**

本文档属于 **GenerateProjectContext** 项目。核心包为 `project_context`，CLI 命令为 `project-context`，GUI 命令为 `project-context-gui`。

按主题分组。若这里没有你要的答案，请先运行：

```bash
project-context . --dump-config
project-context . --help
```

前者能看清当前生效的全部规则，后者列出全部参数。

---

## 目录

1. [名称与安装](#1-名称与安装)
2. [配置与过滤](#2-配置与过滤)
3. [输出与体积](#3-输出与体积)
4. [Git](#4-git)
5. [GUI](#5-gui)
6. [exe](#6-exe)

---

## 1. 名称与安装

### Q：仓库名、包名、命令名有什么区别？

| 层面 | 名称 | 用途 |
|---|---|---|
| 仓库 / 项目 | `GenerateProjectContext` | GitHub 仓库、本地文件夹 |
| PyPI 包 | `project-context` | `pip install project-context` |
| 核心导入包 | `project_context` | `import project_context` |
| GUI 导入包 | `project_context_gui` | `import project_context_gui` |
| CLI 命令 | `project-context` | 命令行调用 |
| GUI 命令 | `project-context-gui` | 图形界面调用 |
| exe 文件 | `generate-project-context.exe` | Windows 分发包 |

文件夹与导入包名用下划线，PyPI 包名与命令用连字符，这是 Python 生态的常见约定。

### Q：`pip install project-context` 后找不到命令？

确认安装成功：

```bash
pip show project-context
```

若命令不在 PATH，可用模块方式：

```bash
python -m project_context .
```

### Q：Python 3.9 / 3.10 报 `tomli` 缺失？

```bash
pip install tomli
```

Python 3.11+ 内置 `tomllib`，无需额外安装。

### Q：运行后没有看到 `PROJECT_CONTEXT.md`？

- 默认输出路径是 `<项目根>/PROJECT_CONTEXT.md`
- 用 `-o` 显式指定时以指定路径为准
- 检查当前目录是否为目标项目目录

### Q：项目路径含空格或中文？

支持。用引号包裹：

```bash
project-context "D:\我的项目\demo app"
```

### Q：环境没有 Git 会怎样？

自动降级：文档跳过第 5 章，其它章节正常生成。

---

## 2. 配置与过滤

### Q：为什么某个目录没被忽略？

按顺序排查：

1. 运行 `--dump-config` 看最终规则
2. 若规则没出现，检查该语言是否被激活（`active` 字段）
3. 若规则出现但目录还在，区分：
   - `ignore_dirs` 精确匹配目录名
   - `ignore_dir_globs` 支持通配符
4. 叠加命令行：

```bash
project-context . --exclude-dir 那个目录名
```

### Q：`ignore_dirs` 写了路径为什么没生效？

`ignore_dirs` 只匹配单层目录名，不匹配路径。要匹配路径，用：

- `ignore_dir_globs = ["vendor/*"]`
- 或 `exclude_globs = ["vendor/bundle/*"]`

### Q：`*.egg-info` 放 `ignore_dirs` 为什么没生效？

`ignore_dirs` 精确匹配，不支持通配符。改用：

```toml
[filter]
ignore_dir_globs = ["*.egg-info", "*.dist-info"]
```

### Q：项目里配置的规则没生效？

1. 确认 `.project_context/common.toml` 存在
2. 运行 `--dump-config`，看“配置来源”是否包含该文件
3. 注意区分 `inherit_defaults = true/false`
4. 若项目配置写了 `inherit_defaults = false`，内置规则会被丢弃

### Q：命令行 `--exclude` 和项目配置冲突怎么办？

不冲突，会叠加。三层最终取并集。

### Q：如何让一条规则永久生效？

编辑项目根的 `.project_context/common.toml` 或对应语言 TOML。保存后下次运行自动加载。

GUI 用户可以：在过滤面板输入规则 → 点“查看配置加载说明” → 在“③ 本次追加”卡片里点“固化到项目配置”。

### Q：如何新增自定义语言？

在 `.project_context/languages/mydsl.toml` 写入：

```toml
schema_version = 1
name = "mydsl"
inherit_defaults = false

[detect]
suffixes = [".mydsl"]

[filter]
ignore_dirs = ["mydsl_cache"]

[code_langs]
".mydsl" = "plaintext"

[ast]
parser = "none"
```

之后：

```bash
project-context . --languages mydsl,python
```

详见 [配置系统](configuration.md)。

---

## 3. 输出与体积

### Q：非 Python 语言没有代码结构摘要？

目前只有 Python 支持 AST 摘要。其它语言的代码会以原文形式出现在第 4 章。

### Q：大项目输出文件太大怎么办？

```bash
# 只出结构不出源码
project-context . --no-content

# 限制单文件大小
project-context . --max-file-size 50

# 排除大文件
project-context . --exclude "*.min.js" --exclude "*.map"
```

### Q：如何只输出部分章节？

```bash
project-context . --no-content --no-git
```

### Q：输出文档里的时间戳不想要？

```bash
project-context . --no-timestamp
```

关闭时间戳后，同一输入多次运行输出完全一致，便于版本控制对比。

### Q：如何只分析某个子目录？

把子目录当作 root：

```bash
project-context .\src -o src-context.md
```

### Q：AI 上下文窗口有限，如何压缩？

- `--no-content`：不出源码
- `--max-file-size 50`：限制单文件
- `--exclude`：过滤大文件
- `--no-git`：不采集历史

---

## 4. Git

### Q：为什么输出没有第 5 章（Git 历史）？

可能原因：

- 项目根没有 `.git` 目录
- 使用了 `--no-git`
- 配置文件里 `include_git = false`

### Q：如何只采集少量提交？

```bash
project-context . --max-git-commits 10
```

### Q：如何只看提交概览，不看文件列表？

```bash
project-context . --max-files-per-commit 0
```

### Q：如何审计完整历史？

```bash
project-context . --max-git-commits 500 -o history.md
```

---

## 5. GUI

### Q：GUI 启动报缺少 PySide6？

```bash
pip install "project-context[gui]"
```

### Q：GUI 的“格式化”按钮没反应？

需要 `tomlkit`：

```bash
pip install tomlkit
```

### Q：GUI 提示找不到 `generate-project-context.exe`？

在「设置」→「执行引擎」中：

1. 选择「Python」模式（需 Python 环境），或
2. 选择「EXE」模式并指定 exe 路径

详见 [GUI 手册](gui.md) 第 8 节。

### Q：GUI 提示 Python 模块不可用？

检查「设置」→「执行引擎」→「Python 模块路径」：

- 应填 `project_context` 的**父目录**
- 父目录下应有 `project_context/__init__.py`
- 若填成了包目录本身，状态行会提示

详见 [GUI 手册](gui.md) 第 8.5 节。

### Q：GUI 支持哪些快捷键？

| 快捷键 | 功能 |
|---|---|
| `Ctrl+O` | 打开项目 |
| `Ctrl+S` | 保存配置文件 |
| `F5` | 重新检测项目 |
| `Esc` | 停止运行 |
| `Ctrl+L` | 清空日志 |

---

## 6. exe

### Q：exe 运行后没生成文件？

- 默认输出到 `<项目根>/PROJECT_CONTEXT.md`
- 用 `-o` 显式指定
- 检查当前目录是否为目标项目

### Q：exe 被杀毒软件报毒？

打包工具（Nuitka / PyInstaller）的 exe 常被误报。可选：

- 加入杀毒软件白名单
- 使用 standalone 模式（误报率更低）
- 对 exe 做代码签名

### Q：控制台中文乱码？

```powershell
chcp 65001
.\generate-project-context.exe .
```

### Q：exe 参数忘了？

```powershell
.\generate-project-context.exe --help
```

### Q：exe 和源码版可以共用配置吗？

可以。两者读取相同的 `.project_context/` 目录，格式完全一致。

---

## 参见

- [CLI 使用手册](cli.md)
- [GUI 使用手册](gui.md)
- [exe 分发版手册](exe.md)
- [配置系统](configuration.md)
- [Python API](api.md)