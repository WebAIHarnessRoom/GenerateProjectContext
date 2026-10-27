# Python API

适用版本：**0.1.0**

本文档属于 **GenerateProjectContext** 项目。核心导入包为 `project_context`，PyPI 包名为 `project-context`。
`project_context` 提供两个公共函数：

- `generate_context()`：生成上下文文档
- `list_available_languages()`：列出可用语言

---

## 目录

1. [安装](#1-安装)
2. [generate_context 签名](#2-generate_context-签名)
3. [返回值约定](#3-返回值约定)
4. [示例](#4-示例)
5. [list_available_languages](#5-list_available_languages)
6. [异常](#6-异常)

---

## 1. 安装

```bash
pip install project-context
```

Python 3.9 / 3.10 需要 `tomli`：

```bash
pip install tomli
```

---

## 2. generate_context 签名

```python
from project_context import generate_context

generate_context(
    root=".",                              # 项目根目录
    *,
    output=None,                           # 输出路径；None 返回 str
    config=None,                           # 通用配置文件路径
    inherit_defaults=None,                 # bool | None
    languages=None,                        # "auto" | "all" | ["python"] | None
    detect_min_files=None,                 # int | None
    language_dirs=None,                    # [str | Path]
    language_configs=None,                 # {"python": "path.toml"}
    exclude=None,                          # ["*.pb.go"]
    exclude_dirs=None,                     # ["third_party"]
    exclude_dir_globs=None,                # ["build/**"]
    exclude_suffixes=None,                 # [".tmp"]
    max_file_size_kb=None,                 # int | None
    max_git_commits=None,                  # int | None
    max_files_per_commit=None,             # int | None
    include_git=None,                      # bool | None
    include_content=None,                  # bool | None
    include_ast=None,                      # bool | None
    no_timestamp=None,                     # bool | None
    dump_config=False,                     # True 返回配置 TOML 字符串 / Path
    verbose=False,                         # 保留参数
) -> Path | str
```

参数说明：

| 参数 | 类型 | 对应 CLI |
|---|---|---|
| `root` | `str \| Path` | 位置参数 `root` |
| `output` | `str \| Path \| None` | `-o, --output` |
| `config` | `str \| Path \| None` | `--config` |
| `inherit_defaults` | `bool \| None` | `--inherit-defaults` / `--no-inherit-defaults` |
| `languages` | `str \| list \| None` | `--languages` |
| `detect_min_files` | `int \| None` | `--detect-min-files` |
| `language_dirs` | `list \| None` | `--language-dir` |
| `language_configs` | `dict \| None` | `--language-config` |
| `exclude` | `list \| None` | `--exclude` |
| `exclude_dirs` | `list \| None` | `--exclude-dir` |
| `exclude_dir_globs` | `list \| None` | `--exclude-dir-glob` |
| `exclude_suffixes` | `list \| None` | `--exclude-suffix` |
| `max_file_size_kb` | `int \| None` | `--max-file-size` |
| `max_git_commits` | `int \| None` | `--max-git-commits` |
| `max_files_per_commit` | `int \| None` | `--max-files-per-commit` |
| `include_git` | `bool \| None` | `--no-git` 取反 |
| `include_content` | `bool \| None` | `--no-content` 取反 |
| `include_ast` | `bool \| None` | `--no-ast` 取反 |
| `no_timestamp` | `bool \| None` | `--no-timestamp` |
| `dump_config` | `bool` | `--dump-config` |

`None` 表示沿用配置文件的默认值。

---

## 3. 返回值约定

| `output` | `dump_config` | 返回 |
|---|---|---|
| 路径（`str` / `Path`） | `False` | `Path`（写盘后的绝对路径） |
| `None` | `False` | `str`（Markdown 内容） |
| 路径（`str` / `Path`） | `True` | `Path`（配置 TOML 写盘路径） |
| `None` | `True` | `str`（配置 TOML 内容） |

---

## 4. 示例

### 4.1 基础

```python
from project_context import generate_context

# 输出到 <root>/PROJECT_CONTEXT.md
generate_context(root="/path/to/project")
```

### 4.2 只要字符串

```python
md = generate_context(root=".", output=None)
print(md)
```

### 4.3 显式语言 + 追加降噪

```python
generate_context(
    root=".",
    languages=["python", "go"],
    exclude=["*.pb.go"],
    exclude_dirs=["third_party"],
    max_file_size_kb=300,
)
```

### 4.4 覆盖某语言配置

```python
generate_context(
    root=".",
    languages=["python"],
    language_configs={"python": "./my_python.toml"},
)
```

### 4.5 关闭时间戳，便于快照对比

```python
md = generate_context(root=".", output=None, no_timestamp=True)
```

### 4.6 探查最终配置

```python
text = generate_context(root=".", output=None, dump_config=True)
print(text)
```

### 4.7 只出结构

```python
generate_context(
    root=".",
    include_content=False,
    include_git=False,
)
```

---

## 5. list_available_languages

```python
from project_context import list_available_languages

langs = list_available_languages()
print(langs)
# ['cpp', 'dotnet', 'go', 'java', 'node', 'php', 'python', 'ruby', 'rust']
```

当前实现需要传入额外语言目录列表；若只想列出内置语言，传入空列表即可。推荐使用无参形式，若遇到签名错误，请升级到最新版本。

---

## 6. 异常

所有异常继承自 `ProjectContextError`：

| 异常 | 触发场景 |
|---|---|
| `ProjectContextError` | 所有异常的基类 |
| `ConfigError` | 配置相关错误 |
| `LanguageNotFoundError` | 显式指定的语言不存在 |
| `UnknownFieldError` | TOML 中出现未知字段 |
| `ValidationError` | 配置值不合法 |
| `FileReadError` | 文件读取失败 |

示例：

```python
from project_context import generate_context
from project_context import LanguageNotFoundError

try:
    generate_context(root=".", languages=["no_such_lang"])
except LanguageNotFoundError as e:
    print(e)
```

`LanguageNotFoundError` 的消息包含：

- 请求的语言名
- 可用语言列表
- 自定义语言的放置位置提示

---

## 参见

- [CLI 使用手册](cli.md)
- [配置系统](configuration.md)
- [常见问题](faq.md)