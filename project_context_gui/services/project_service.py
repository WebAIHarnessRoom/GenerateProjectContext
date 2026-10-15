"""轻量项目预扫描（不读文件内容，只看目录与文件名）。"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

# 与原包内置语言检测保持近似的信号（只用于提示，不参与执行）
_SUFFIX_SIGNALS: dict[str, tuple[str, ...]] = {
    "python": (".py", ".pyi"),
    "node": (".js", ".ts", ".tsx", ".jsx", ".mjs", ".cjs"),
    "go": (".go",),
    "rust": (".rs",),
    "java": (".java",),
    "cpp": (".cpp", ".cc", ".cxx", ".hpp", ".h", ".hxx"),
    "php": (".php",),
    "ruby": (".rb",),
    "dotnet": (".cs", ".csproj", ".sln"),
}

_MARKER_FILES: dict[str, tuple[str, ...]] = {
    "python": ("pyproject.toml", "setup.py", "requirements.txt"),
    "node": ("package.json",),
    "go": ("go.mod",),
    "rust": ("Cargo.toml",),
    "java": ("pom.xml", "build.gradle"),
    "dotnet": ("*.csproj", "*.sln"),
}

_SKIP_DIRS = {
    ".git", ".hg", ".svn",
    "node_modules", "__pycache__", ".venv", "venv",
    "target", "build", "dist", ".idea", ".vscode",
}


@dataclass
class ProjectScan:
    root: Path
    has_project_context_dir: bool = False
    has_common_toml: bool = False
    language_toml_count: int = 0
    has_git: bool = False
    suffix_hits: dict[str, int] = field(default_factory=dict)
    marker_hits: dict[str, list[str]] = field(default_factory=list)

    @property
    def detected_languages(self) -> list[str]:
        langs = set(self.suffix_hits) | set(self.marker_hits)
        return sorted(langs)


def scan_project(root: str | Path) -> ProjectScan:
    root = Path(root)
    scan = ProjectScan(root=root)

    if not root.is_dir():
        return scan

    # .project_context/
    cfg_dir = root / ".project_context"
    if cfg_dir.is_dir():
        scan.has_project_context_dir = True
        if (cfg_dir / "common.toml").is_file():
            scan.has_common_toml = True
        lang_dir = cfg_dir / "languages"
        if lang_dir.is_dir():
            scan.language_toml_count = len(list(lang_dir.glob("*.toml")))

    scan.has_git = (root / ".git").exists()

    # 预扫描（限深度，避免大项目卡）
    suffix_hits: dict[str, int] = {}
    marker_hits: dict[str, list[str]] = {}
    for path in _walk_limited(root, max_entries=5000):
        name = path.name
        for lang, markers in _MARKER_FILES.items():
            for pat in markers:
                if pat.startswith("*"):
                    if name.endswith(pat[1:]):
                        marker_hits.setdefault(lang, []).append(name)
                elif name == pat:
                    marker_hits.setdefault(lang, []).append(name)

        suf = path.suffix.lower()
        if suf:
            for lang, suffixes in _SUFFIX_SIGNALS.items():
                if suf in suffixes:
                    suffix_hits[lang] = suffix_hits.get(lang, 0) + 1
                    break

    scan.suffix_hits = suffix_hits
    scan.marker_hits = marker_hits
    return scan


def _walk_limited(root: Path, max_entries: int):
    count = 0
    stack = [root]
    while stack and count < max_entries:
        cur = stack.pop()
        try:
            entries = list(cur.iterdir())
        except (OSError, PermissionError):
            continue
        for e in entries:
            if e.name in _SKIP_DIRS:
                continue
            if e.is_dir():
                stack.append(e)
            else:
                yield e
                count += 1
                if count >= max_entries:
                    return