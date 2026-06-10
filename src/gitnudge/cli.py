"""Typer app: arg parsing and dispatch only. No logic lives here."""

from __future__ import annotations

import subprocess

import typer
from rich.console import Console

from . import gitio
from .graph import DEFAULT_WEEKS, bucket_by_day, render
from .health import score
from .status import DEFAULT_LINE_THRESHOLD, evaluate

app = typer.Typer(
    name="gitnudge",
    help="Nudge yourself to commit, visualize your heatmap, grade your history.",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()


def _require_repo() -> None:
    if not gitio.in_repo():
        console.print(
            "[red]not a git repository[/red] — run inside a checkout, "
            "or `git init` first."
        )
        raise typer.Exit(code=1)


def _format_duration(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds}s"
    if seconds < 3600:
        return f"{seconds // 60}m"
    if seconds < 86400:
        h, m = divmod(seconds, 3600)
        return f"{h}h {m // 60}m"
    return f"{seconds // 86400}d"


@app.command()
def status(
    threshold: int = typer.Option(
        DEFAULT_LINE_THRESHOLD,
        "--threshold",
        "-t",
        help="Changed-line threshold for nudging.",
    ),
) -> None:
    """Should you commit soon?"""
    _require_repo()
    try:
        stats = gitio.get_diff_stats()
        last_ts = gitio.last_commit_timestamp()
    except subprocess.CalledProcessError as e:
        console.print(f"[red]git error:[/red] {e}")
        raise typer.Exit(code=1) from None

    report = evaluate(stats, last_ts, threshold=threshold)
    since = (
        f" since last commit ({_format_duration(report.seconds_since_last)} ago)"
        if report.seconds_since_last is not None
        else " (no prior commits)"
    )

    if report.should_nudge:
        console.print(
            f"[yellow]⚠[/yellow]  [bold]{report.files_touched} file(s) changed, "
            f"[green]+{report.insertions}[/green]/"
            f"[red]-{report.deletions}[/red][/bold]{since}. "
            "Consider committing."
        )
    else:
        lines = report.insertions + report.deletions
        console.print(
            f"[green]✓[/green] {lines} line(s) changed across "
            f"{report.files_touched} file(s){since} — you're fine."
        )


@app.command()
def graph(
    weeks: int = typer.Option(
        DEFAULT_WEEKS, "--weeks", "-w", help="Number of weeks to show."
    ),
) -> None:
    """Terminal commit heatmap, GitHub-style."""
    _require_repo()
    try:
        commits = gitio.get_commits()
    except subprocess.CalledProcessError as e:
        console.print(f"[red]git error:[/red] {e}")
        raise typer.Exit(code=1) from None

    if not commits:
        console.print("[dim]no commits yet[/dim]")
        return

    buckets = bucket_by_day([c.timestamp for c in commits])
    console.print(render(buckets, weeks=weeks))


@app.command()
def health() -> None:
    """Grade the commit history's organic-ness."""
    _require_repo()
    try:
        commits = gitio.get_commits()
    except subprocess.CalledProcessError as e:
        console.print(f"[red]git error:[/red] {e}")
        raise typer.Exit(code=1) from None

    if not commits:
        console.print("[dim]no commits yet — nothing to grade[/dim]")
        return

    report = score(commits)
    for f in report.findings:
        icon = "[green]✓[/green]" if f.status == "pass" else "[yellow]⚠[/yellow]"
        console.print(f"{icon} [bold]{f.check}[/bold] — {f.detail}")
    grade_color = {"A": "green", "B": "green", "C": "yellow", "D": "yellow", "F": "red"}[report.grade]
    console.print(
        f"\n[bold]score:[/bold] {report.score}/100   "
        f"[bold {grade_color}]grade: {report.grade}[/bold {grade_color}]"
    )
