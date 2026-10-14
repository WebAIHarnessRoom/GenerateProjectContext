# project_context

把 Python（及多语言）项目整理成一份 Markdown 上下文文档，用于人工理解项目
或为 AI 提供工程上下文。

## 安装

无第三方依赖（Python 3.9+；3.9/3.10 需 `pip install tomli`）。

## 快速开始

```bash
# 方式一：CLI
python generate_project_context.py . -o context.md

# 方式二：模块
python -m project_context . -o context.md

# 方式三：Python API
python -c "from project_context import generate_context; generate_context(root='.')"
```

## 特性

- **双执行模式**：CLI 参数与 Python API 行为一致
- **语言感知降噪**：自动识别项目使用哪些语言，只应用相关忽略规则
- **高度可配置**：内置 common.toml + 语言配置，用户可覆盖/新增
- **可诊断**：`--dump-config` 打印最终生效配置及来源

## 常用参数

| 参数 | 说明 |
|---|---|
| `--config PATH` | 通用配置文件 |
| `--languages python,go` | 显式激活语言（`auto`/`all`） |
| `--language-dir DIR` | 额外语言配置目录（可重复） |
| `--language-config NAME=PATH` | 覆盖某语言配置（可重复） |
| `--exclude GLOB` | 追加忽略 glob（可重复） |
| `--exclude-dir NAME` | 追加忽略目录（可重复） |
| `--exclude-suffix SUF` | 追加忽略后缀（可重复） |
| `--max-file-size N` | 单文件 KB 上限 |
| `--max-git-commits N` | 采集提交数 |
| `--no-git` / `--no-content` / `--no-ast` | 关闭对应章节 |
| `--no-timestamp` | 关闭时间戳（便于快照对比） |
| `--dump-config` | 打印最终配置并退出 |
| `--list-languages` | 列出可用语言并退出 |

## 配置

项目级覆盖放到 `.project_context/`：

```
myproject/
├── .project_context/
│   ├── common.toml
│   └── languages/
│       └── python.toml
└── ...
```

`common.toml` 示例：

```toml
[filter]
ignore_dirs   = ["third_party"]
exclude_globs = ["tests/fixtures/*"]

[limits]
max_file_size_kb = 300
```

`languages/python.toml` 示例：

```toml
[filter]
ignore_dirs = ["local_venv"]

[detect]
suffixes = [".py", ".pyi"]
```

自定义语言：`.project_context/languages/mydsl.toml`

```toml
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

## 语言自动检测

默认 `--languages auto`：脚本预扫描文件名/后缀/标志文件，判断项目
使用了哪些语言，只应用相关语言的忽略规则。可通过 `--detect-min-files`
调高阈值，或用 `--languages` 显式指定。

## 编程接口

```python
from project_context import generate_context

# 最简
generate_context(root=".")

# 精细控制
generate_context(
    root=".",
    output="ctx.md",
    config=".project_context/common.toml",
    languages=["python", "node"],
    exclude=["*.pb.go"],
    exclude_dirs=["third_party"],
    max_file_size_kb=300,
    include_git=True,
)

# 只要字符串
md = generate_context(root=".", output=None)
```