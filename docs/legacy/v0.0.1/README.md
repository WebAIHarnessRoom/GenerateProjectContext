## 了解python项目
读取 Python 项目结构、源码与 Git 日志，生成 Markdown 上下文文档。
## generate_project_context.py脚本参数和示例
常用参数
```python
# python执行参数定义
parser.add_argument("root", nargs="?", default=".",
                    help="项目根目录，默认当前目录")
parser.add_argument("-o", "--output", default=None,
                    help="输出 Markdown 文件路径，默认 <root>/PROJECT_CONTEXT.md")
parser.add_argument("--max-file-size", type=int, default=200,
                    help="单个文件最大读取大小（KB），超出则截断，默认 200")
parser.add_argument("--max-git-commits", type=int, default=50,
                    help="采集的 Git 提交数量，默认 50")
parser.add_argument("--max-files-per-commit", type=int, default=20,
                    help="每条提交最多列出的变更文件数，默认 20")
parser.add_argument("--no-git", action="store_true",
                    help="不采集 Git 信息")
parser.add_argument("--no-content", action="store_true",
                    help="不输出源码内容，只输出结构与 Git 历史")
parser.add_argument("--no-ast", action="store_true",
                    help="不输出 AST 代码结构摘要")
parser.add_argument("--exclude", action="append", default=[],
                    metavar="GLOB",
                    help="额外忽略的文件 glob（可重复），如 --exclude 'tests/fixtures/*'")
```
执行示例

```
python generate_project_context.py                     # 分析当前目录
python generate_project_context.py /path/to/project -o context.md #分析指定项目，输出到context.md
python generate_project_context.py . --max-git-commits 100 --max-file-size 300 #分析当前目录，指定git提交次数，指定单个文件最大读取尺寸
python generate_project_context.py . --no-content      # 只输出结构，不输出源码
python generate_project_context.py . --exclude "*.pb.go" --exclude "tests/fixtures/*" #排除文件或目录
```
### 项目上下文生成流程与配置
脚本把“扫描—摘要—输出”串成一条流水线，下面拆开看看。

项目扫描：自动忽略版本控制、虚拟环境、缓存等无关目录，同时按后缀过滤二进制和媒体文件，只保留代码与文本文件。

代码结构摘要：基于 AST 解析 Python 文件的类与函数签名，并提取首行文档字符串，快速呈现模块职责。

Git 日志集成：可选采集提交记录，列出每条提交的作者、日期、变更规模及具体文件，方便回溯开发脉络。

输出控制：支持通过命令行参数调整文件大小上限、提交数量，或跳过内容、跳过 AST 分析，灵活适配不同场景。

## 项目FrameClipStudio上下文生成
```shell
python generate_project_context.py D:\workspace\pycharm-wk\FrameClipStudio -o FrameClipStudioContext.md --max-git-commits 20 --exclude "Png2Ico.py" --exclude "DataInput.py"
```