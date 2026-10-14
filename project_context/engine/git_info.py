"""Git 信息采集。"""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import List, Optional, Tuple


def run_git(root: Path, args: List[str]) -> Optional[str]:
    try:
        proc = subprocess.run(
            ["git", "-C", str(root)] + args,
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
    except (FileNotFoundError, OSError):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout


def parse_git_log(root: Path, max_commits: int) -> List[dict]:
    fmt = "%x1e%h%x1f%ad%x1f%an%x1f%s"
    raw = run_git(root, [
        "log", f"--max-count={max_commits}", "--date=short",
        f"--pretty=format:{fmt}", "--numstat", "--no-merges",
    ])
    if not raw:
        return []

    commits: List[dict] = []
    for chunk in raw.split("\x1e"):
        chunk = chunk.strip("\n")
        if not chunk:
            continue
        lines = chunk.split("\n")
        parts = lines[0].split("\x1f")
        if len(parts) < 4:
            continue
        sha, date, author = parts[0], parts[1], parts[2]
        subject = "\x1f".join(parts[3:])
        files: List[Tuple[str, str, str]] = []
        added_total = 0
        deleted_total = 0
        for line in lines[1:]:
            if not line.strip():
                continue
            seg = line.split("\t")
            if len(seg) < 3:
                continue
            a, d, path = seg[0], seg[1], "\t".join(seg[2:])
            if a.isdigit():
                added_total += int(a)
            if d.isdigit():
                deleted_total += int(d)
            files.append((path, a, d))
        commits.append({
            "sha": sha, "date": date, "author": author, "subject": subject,
            "files": files, "added": added_total, "deleted": deleted_total,
        })
    return commits


def gather_git_info(root: Path, max_commits: int, enabled: bool = True) -> dict:
    info = {"is_repo": False, "branch": "", "head": "", "commits": []}
    if not enabled:
        return info
    branch = run_git(root, ["rev-parse", "--abbrev-ref", "HEAD"])
    if branch is None:
        return info
    info["is_repo"] = True
    info["branch"] = branch.strip()
    head = run_git(root, ["log", "-1", "--date=short", "--pretty=format:%h · %ad · %an · %s"])
    info["head"] = (head or "").strip()
    info["commits"] = parse_git_log(root, max_commits)
    return info