# Repository Guidelines

## Project Structure
- `sweagent/`: core Python package and CLI entrypoints.
- `config/`: YAML and template configs for agent behavior.
- `tests/`: pytest suites and fixtures.
- `docs/`: MkDocs content; site config in `mkdocs.yml`.
- `assets/`: images and static assets used by docs/README.
- `tools/`: utility scripts.
- `trajectories/`: example run outputs and artifacts.

## Build, Test, and Development Commands
- `pip install -e '.[dev]'`: install package with dev tooling.
- `pre-commit install`: enable lint/format hooks.
- `pre-commit run --all-files`: run formatting/linting across the repo.
- `pytest`: run all tests.
- `pytest -m "not slow"`: skip slow tests.
- `pytest -n auto`: run tests in parallel.
- `mkdocs serve`: build docs locally on port 8000.
- `sweagent --help`: CLI entrypoint for running the agent.

## Coding Style & Naming Conventions
- Python 3.11+; 4-space indentation; line length 120.
- Use `ruff` for linting and `ruff-format` for formatting (via pre-commit).
- Prefer double quotes and sorted imports (ruff isort rules).
- `snake_case` for functions/vars, `PascalCase` for classes, `test_*.py` for tests.

## Testing Guidelines
- Framework: pytest; tests live under `tests/`.
- Use markers `slow` and `ctf` to group long-running tests.
- When debugging, `pytest -k <name> -s --capture=no --log-cli-level=DEBUG` is supported.

## Commit & Pull Request Guidelines
- Commit messages are Conventional-Commit-ish: `type(scope): summary` (e.g., `fix: ...`, `docs(keys): ...`, `chore(deps): ...`), often with `(#1234)` PR references.
- Keep one issue per PR; open an issue first for large or experimental changes.
- Include tests or rationale for behavior changes and update docs when user-facing.

## Security & Configuration
- Do not commit API keys or secrets; prefer environment variables or `.env` files.
- See `SECURITY.md` for reporting guidance and expectations.
