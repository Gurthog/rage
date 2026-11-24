## Project

Rage is a rage-comic archive. Never generate images.

For frontend layout, styling, imagery or copy, read `docs/frontend-design.md` for era-specific direction.

## Engineering

- Use `uv` for Python commands and dependencies; keep SQLite.
- Treat existing migration files as permanent database history; create new migrations instead of modifying them.
- Place app tests in the app's `tests/` package and project-wide tests in `project/tests/`. Name files `test_<area>.py`, group related behavior by subject, and split files further when useful.
- Prefer Django's built-in features where sufficient; otherwise prefer htmx for interactive UI, without a client-side framework or build step.

## Agent skills

### Issue tracker

Issues are tracked in GitHub Issues. See `docs/agents/issue-tracker.md`.

### Triage labels

Triage uses the default five-label vocabulary. See `docs/agents/triage-labels.md`.

### Domain docs

This repo uses a single-context layout. See `docs/agents/domain.md`.
