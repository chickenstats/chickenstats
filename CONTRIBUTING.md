# Contributing to chickenstats

Thank you for your interest in contributing! This guide covers the essentials for getting started.

---

## Quick start

```sh
# Fork and clone the repo, then install all dev dependencies
uv sync --group dev

# Install pre-commit hooks (ruff, ty, conventional commits, nb-clean)
uv run pre-commit install
```

---

## Running tests

Run the local coverage suite (clean → test → report):

```sh
uv run tox run -m local
```

Run the full CI matrix (Python 3.10–3.13, Linux/macOS/Windows):

```sh
uv run tox run -m ci
```

Run a targeted subset during development:

```sh
uv run pytest tests/tests_chicken_nhl/ -x
```

Coverage threshold is 80% — the CI gate will fail if it drops below that.

Regression tests (specific historical game IDs) and live API tests are excluded by default. Run them explicitly when needed:

```sh
uv run pytest -m regression
uv run pytest -m live   # requires a live API endpoint and credentials
```

---

## Code style

```sh
uv run ruff format .          # format
uv run ruff check .           # lint
uv run ty check src/          # type checking
```

Docstrings follow [Google style](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings). Ruff and ty run automatically on commit via pre-commit.

---

## Commit format

[Conventional commits](https://www.conventionalcommits.org/) are required and enforced by a pre-commit hook:

```
feat: add new feature
fix: correct a bug
docs: documentation only
refactor: no behavior change
test: add or update tests
build: build system or dependency changes
ci: CI/CD changes
chore: maintenance tasks
```

For a breaking change, append `!` after the type:

```
feat!: remove deprecated parameter
```

---

## Pull requests

- Branch from `main`; target `main`
- Keep PRs focused — one concern per PR
- Tests must pass and coverage must not drop below 80%
- Reference the relevant GitHub issue in the PR description if applicable

---

## Bug reports & feature requests

Please open an [issue](https://github.com/chickenandstats/chickenstats/issues). Before filing a bug, check the [known issues](https://chickenstats.com/contribute/known_issues/) page — it may already be documented. Before requesting a feature, check the [roadmap](https://chickenstats.com/contribute/roadmap/).

---

## Architecture

See [CLAUDE.md](CLAUDE.md) for a map of the codebase: submodule roles, class inheritance chains, internal file descriptions, and key patterns.
