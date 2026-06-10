"""All subprocess/git interaction. The only module that imports subprocess."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class Commit:
    timestamp: int
    author: str
    message: str


@dataclass(frozen=True)
class DiffStats:
    files_changed: int
    insertions: int
    deletions: int
    untracked: int


def _run(args: list[str]) -> str:
    return subprocess.run(
        args, capture_output=True, text=True, check=True
    ).stdout


def in_repo() -> bool:
    try:
        _run(["git", "rev-parse", "--is-inside-work-tree"])
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def get_commits() -> list[Commit]:
    try:
        out = _run(["git", "log", "--format=%ct%x09%an%x09%s"])
    except subprocess.CalledProcessError:
        return []
    commits: list[Commit] = []
    for line in out.splitlines():
        ts, author, message = line.split("\t", 2)
        commits.append(Commit(int(ts), author, message))
    return commits


_SHORTSTAT_RE = re.compile(
    r"(?:(\d+) files? changed)?"
    r"(?:.*?(\d+) insertions?\(\+\))?"
    r"(?:.*?(\d+) deletions?\(-\))?"
)


def get_diff_stats() -> DiffStats:
    shortstat = _run(["git", "diff", "--shortstat"]).strip()
    files_changed = insertions = deletions = 0
    if shortstat:
        m = _SHORTSTAT_RE.search(shortstat)
        if m:
            files_changed = int(m.group(1) or 0)
            insertions = int(m.group(2) or 0)
            deletions = int(m.group(3) or 0)

    porcelain = _run(["git", "status", "--porcelain"])
    untracked = sum(1 for line in porcelain.splitlines() if line.startswith("??"))

    return DiffStats(files_changed, insertions, deletions, untracked)


def last_commit_timestamp() -> int | None:
    try:
        out = _run(["git", "log", "-1", "--format=%ct"]).strip()
    except subprocess.CalledProcessError:
        return None
    return int(out) if out else None
