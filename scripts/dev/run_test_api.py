import sys
from pathlib import Path

def _find_project_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").is_file():
            return parent
    raise RuntimeError("未找到项目根")

PROJECT_ROOT = _find_project_root()
sys.path.insert(0, str(PROJECT_ROOT))

from project_context import generate_context

out = PROJECT_ROOT / "tmp" / "ctx_api.md"
out.parent.mkdir(parents=True, exist_ok=True)
md = generate_context(root=PROJECT_ROOT, output=str(out), no_timestamp=True)