# gitnudge

`gitnudge` is a Python command-line tool that helps you maintain an
organic git commit history. It nudges you to commit when your working
tree has accumulated too many changes, visualizes your commit activity
as a terminal heatmap, and grades the "organic-ness" of your existing
history. The tool is meta: it audits the very habit it is built to
encourage — the same checks it runs on any repo, it runs on its own.

It can be invoked two ways with the same entry point:

- `gitnudge <command>` — standalone CLI.
- `git nudge <command>` — git picks up the `git-nudge` executable on
  PATH as an external subcommand, so it integrates cleanly into your
  existing git workflow.

## Install

```bash
uv add "git+https://github.com/KhaleelKarim/gitnudge.git"
```

To get the `git nudge ...` invocation, install as a global tool so the
entry points land on PATH:

```bash
uv tool install "git+https://github.com/KhaleelKarim/gitnudge.git"
```

## Usage

### `gitnudge status` — should you commit soon?

Looks at your working tree (staged + unstaged + untracked) and nudges
you if you've changed too much since your last commit.

```bash
gitnudge status
gitnudge status --threshold 100   # raise the line-change bar
```

It nudges when changed lines (insertions + deletions) hit the
threshold (default 50) **or** when 5+ files have been touched. Output
includes time since last commit, e.g.
`⚠ 6 file(s) changed, +142/-38 since last commit (2h 14m ago).
Consider committing.`

### `gitnudge graph` — GitHub-style commit heatmap

Renders your recent commit activity as a 7-row weekday grid colored
by intensity (`·` empty, `░` low, `▓` mid, `█` high).

```bash
gitnudge graph
gitnudge graph --weeks 26   # last half year
```

Defaults to the last 12 weeks.

### `gitnudge health` — grade your history's organic-ness

Reports on three checks and assigns a letter grade:

- **Message quality** — flags vague subjects (`fix`, `wip`, `update`,
  `stuff`, …) and messages used 3+ times.
- **Pacing** — flags bursts of 3+ commits inside a 60-second window
  (a signature of scripted, inorganic history) and warns when the
  entire history spans less than an hour.
- **Volume** — warns when there are fewer than 5 commits to grade.

```bash
gitnudge health
```

Score starts at 100; penalties are capped per category so one bad
habit can't tank the grade alone. Grades are A ≥ 90, B ≥ 80,
C ≥ 70, D ≥ 60, otherwise F.

## Future work

- Per-repo adaptive thresholds (compare against your own average
  commit size instead of a global default).
- Month labels on the heatmap and `--author` filtering.
- Config file for tuning thresholds and the vague-message list per
  project.
- Shell-prompt integration so the nudge surfaces in your prompt.
- Time-based background nudges (a quiet daemon that pings you after
  N minutes of unchanged tracked work).
