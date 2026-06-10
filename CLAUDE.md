# gitnudge

Python CLI that nudges you to commit, renders a terminal commit heatmap, and
grades how "organic" a repo's commit history is. Invoked as `gitnudge <cmd>`
or `git nudge <cmd>` (same entry point, exposed as `git-nudge` on PATH).

Full design lives in [docs/gitnudge-design.md](docs/gitnudge-design.md) — read it before
making non-trivial changes. This file captures the constraints that aren't
obvious from the code alone.

## Stack & tooling

- Python >= 3.12, managed with `uv` (src layout from `uv init --package`).
- Runtime deps: `typer`, `rich`. Dev: `pytest`.
- Common commands:
  - `uv run gitnudge <cmd>` — run the CLI
  - `uv run pytest` — run tests
  - `uv add <pkg>` / `uv add --dev <pkg>` — manage deps

## Architecture — the testing firewall

The module layout is deliberate. Respect it:

- `gitio.py` is the **only** module allowed to import `subprocess` or shell
  out to git. It returns plain dataclasses (`Commit`, `DiffStats`).
- `status.py`, `graph.py`, `health.py` are **pure** — they take dataclasses
  in, return dataclasses / renderables out. No I/O, no subprocess.
- `cli.py` is dispatch only: parse args → check `in_repo()` → call `gitio`
  → call the logic module → render with rich. **No logic in cli.py.**

This split is what makes the logic testable without a git fixture. Don't
collapse it for convenience.

## Conventions

- Scoring weights, thresholds, and vague-message lists live as
  module-level constants so they're tunable in one place. Don't inline them.
- Errors users see (not-a-repo, empty repo) print one friendly line and
  exit non-zero. Never let a traceback escape to the user.
- `git log` is parsed with `%x09` (tab) separators, not commas — commit
  messages contain commas.

## Commit history matters here

This tool grades commit history, so its own history is graded too (by the
assignment, and by itself). When committing work in this repo:

- Commit module-by-module, test-by-test as you go. **Do not squash.**
- Write specific subjects. Don't use any of the vague messages that
  `health.py` flags (`update`, `fix`, `wip`, `stuff`, `final`, `done`, …)
  — eating your own dogfood is the point.
- Avoid bursts: don't fire 3+ commits inside 60 seconds (the burst check
  flags scripted history).

## Project context

- DSC final project. Due 2026-06-10, late deadline 2026-06-11.
- Must remain installable via `uv add "git+https://github.com/<user>/gitnudge.git"`
  (autograder requirement). Don't break the entry points in `pyproject.toml`.
- README format is assignment-mandated: `# gitnudge`, description paragraph,
  `## Usage` with example commands.
