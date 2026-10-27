# 配置系统

适用版本：**0.1.0**

本文档属于 **GenerateProjectContext** 项目。配置由核心包 `project_context` 读取。
`project_context` 支持三层配置，优先级从低到高：

```
内置配置  →  项目本地配置  →  命令行参数 / API 显式参数
```

本文介绍三层模型、配置文件字段、自定义语言与诊断方法。

---

## 目录

1. [三层配置模型](#1-三层配置模型)
2. [内置配置](#2-内置配置)
3. [项目本地配置](#3-项目本地配置)
4. [common.toml 字段](#4-commontoml-字段)
5. [languages/*.toml 字段](#5-languages-toml-字段)
6. [新增自定义语言](#6-新增自定义语言)
7. [诊断：--dump-config](#7-诊断--dump-config)
8. [常见误区](#8-常见误区)

---

## 1. 三层配置模型

| 层 | 位置 | 谁维护 | 是否随项目分发 |
|---|---|---|---|
| ① 内置配置 | 安装包内 `project_context/configs/` | 工具作者 | 否 |
| ② 项目配置 | `<项目根>/.project_context/` | 项目维护者 | 是 |
| ③ 本次追加 | 命令行参数 / GUI 过滤面板 | 当次运行者 | 否 |

合并规则：

- **filter 类字段**（`ignore_dirs`、`ignore_suffixes` 等）采用**并集**语义，三层叠加。
- **标量字段**（`max_file_size_kb`、`include_git` 等）采用**后者覆盖前者**语义。
- `inherit_defaults = false` 表示该层**替换**而不是追加。项目配置里写 `inherit_defaults = false`，内置规则会被丢弃，只用项目自己的。

命令行参数中，`--exclude*` 系列是**追加**到已有规则之上，不覆盖。`--no-inherit-defaults` 会丢弃内置层。

---

## 2. 内置配置

位置：

```
project_context/configs/
├── common.toml
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
```

内置配置**不要直接修改**，升级包时会被覆盖。要定制，请在项目根创建 `.project_context/`。

查看内置配置目录：

```bash
python -c "from project_context.config.loader import builtin_config_dir; print(builtin_config_dir())"
```

---

## 3. 项目本地配置

在项目根创建 `.project_context/` 目录：

```
myproject/
├── .project_context/
│   ├── common.toml               # 通用配置
│   └── languages/
│       ├── python.toml           # 覆盖内置 Python 规则
│       └── mydsl.toml            # 新增自定义语言
└── ...（项目文件）
```

之后运行 `project-context .` 会自动加载。

项目配置建议纳入版本控制，随项目分发，让团队成员与 CI 使用同一套规则。

---

## 4. common.toml 字段

完整示例：

```toml
schema_version = 1
inherit_defaults = true

[filter]
ignore_dirs       = ["third_party"]
ignore_dir_globs  = ["*_cache"]
ignore_suffixes   = [".bak"]
ignore_file_globs = ["*.min.js"]
exclude_globs     = ["tests/fixtures/*"]

[limits]
max_file_size_kb     = 300
max_git_commits      = 100
max_files_per_commit = 30

[features]
include_content = true
include_ast     = true
include_git     = true
no_timestamp    = false

[languages]
active           = "auto"
detect_min_files = 1
```

字段说明：

| 字段 | 类型 | 说明 |
|---|---|---|
| `schema_version` | int | 配置格式版本，当前为 1 |
| `inherit_defaults` | bool | `true` 在内置规则基础上追加；`false` 替换 |
| `filter.ignore_dirs` | 字符串数组 | 精确匹配目录名（不递归） |
| `filter.ignore_dir_globs` | 字符串数组 | 通配符匹配目录名，如 `"*_cache"` |
| `filter.ignore_suffixes` | 字符串数组 | 后缀匹配，如 `".log"` |
| `filter.ignore_file_globs` | 字符串数组 | 文件名 / 相对路径通配，如 `"*.min.js"` |
| `filter.exclude_globs` | 字符串数组 | 同 `ignore_file_globs`，语义更直观 |
| `limits.max_file_size_kb` | int | 单文件大小上限，超出截断 |
| `limits.max_git_commits` | int | 采集的提交数量 |
| `limits.max_files_per_commit` | int | 每条提交列出的文件数 |
| `features.include_content` | bool | 是否输出源码 |
| `features.include_ast` | bool | 是否输出 AST 摘要 |
| `features.include_git` | bool | 是否采集 Git |
| `features.no_timestamp` | bool | 是否关闭时间戳 |
| `languages.active` | 字符串或数组 | `auto` / `all` / `["python","go"]` |
| `languages.detect_min_files` | int | 自动检测阈值 |

未知字段会导致 `UnknownFieldError`，错误信息会列出可用字段。

---

## 5. languages/*.toml 字段

完整示例：

```toml
schema_version = 1
name = "python"
inherit_defaults = true
active = true

[detect]
suffixes    = [".py", ".pyi"]
file_globs  = []
dir_markers = ["pyproject.toml", "setup.py", "setup.cfg", "Pipfile"]

[filter]
ignore_dirs       = [".venv", "venv", "env"]
ignore_dir_globs  = ["*.egg-info", "*.dist-info"]
ignore_suffixes   = [".pyc", ".pyo"]
ignore_file_globs = ["*.pyc"]

[code_langs]
".py"  = "python"
".pyi" = "python"

[code_lang_names]
"requirements.txt" = "text"

[ast]
parser = "python"
```

字段说明：

| 字段 | 类型 | 说明 |
|---|---|---|
| `schema_version` | int | 格式版本 |
| `name` | string | 语言名，需与文件名一致 |
| `inherit_defaults` | bool | 是否继承同名的内置语言配置 |
| `active` | bool | 是否参与语言检测与激活 |
| `detect.suffixes` | 字符串数组 | 文件后缀信号 |
| `detect.file_globs` | 字符串数组 | 文件名通配信号 |
| `detect.dir_markers` | 字符串数组 | 目录标志文件信号 |
| `filter.*` | 同 common | 该语言特有的忽略规则 |
| `code_langs` | 表 | 后缀 → 代码块语言标签 |
| `code_lang_names` | 表 | 文件名 → 代码块语言标签 |
| `ast.parser` | string | AST 解析器名；目前仅 `python` 和 `none` |

`ast.parser = "none"` 表示该语言不生成代码结构摘要，源码仍会出现在第 4 章。

---

## 6. 新增自定义语言

以 `mydsl` 为例，在项目根创建 `.project_context/languages/mydsl.toml`：

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

之后显式激活：

```bash
project-context . --languages mydsl,python
```

或让自动检测发现它（项目中有 `.mydsl` 文件即可）。

注意事项：

- 新语言没有内置配置可继承，`inherit_defaults` 必须为 `false`。
- 目前只有 Python 支持 AST 摘要，其它语言用 `parser = "none"`。
- 代码块语言标签可以是任意字符串，常见值见 `project_context/engine/context.py` 的 `GENERIC_CODE_LANGS`。

---

## 7. 诊断：--dump-config

排查“为什么某规则没生效”时，先运行：

```bash
project-context . --dump-config
```

输出包含：

- 合并后的最终配置（可直接作为 `--config` 参考）
- 配置来源列表（按加载顺序）
- 激活的语言

示例输出见 [CLI 使用手册](cli.md) 第 3.5 节。

---

## 8. 常见误区

### 8.1 `ignore_dirs` 与 `ignore_dir_globs` 的区别

- `ignore_dirs = ["third_party"]`：精确匹配目录名 `third_party`，不匹配 `third_party_v2`。
- `ignore_dir_globs = ["third_party*"]`：匹配 `third_party`、`third_party_v2` 等。

`*.egg-info`、`cmake-build-*` 这类必须放 `ignore_dir_globs`，放 `ignore_dirs` 不会生效。

### 8.2 `ignore_dirs` 不匹配路径

`ignore_dirs = ["vendor/bundle"]` 不会生效，因为它只匹配单层目录名。要匹配路径，用 `ignore_dir_globs` 或 `exclude_globs`。

### 8.3 语言配置没生效

先确认该语言被激活：

```bash
project-context . --dump-config | grep active
```

若语言未出现在 `active` 列表中：

- 检查 `detect` 信号是否命中项目文件
- 检查 `--detect-min-files` 是否过高
- 或显式指定 `--languages python`

### 8.4 项目配置被内置配置“覆盖”

若项目配置写了 `inherit_defaults = false`，内置规则会被丢弃。如果你只想追加，保持 `inherit_defaults = true`（默认）。

### 8.5 `--exclude` 与项目配置的关系

命令行 `--exclude` 是**追加**，不会覆盖项目配置。三层最终取并集。

---

## 参见

- [CLI 使用手册](cli.md)
- [Python API](api.md)
- [常见问题](faq.md)