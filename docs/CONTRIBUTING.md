# Contributing to EmbedForge

Thank you for contributing! This document explains how to get involved.

## Development Setup

```bash
git clone https://github.com/EchoSNS/embedforge.git
cd embedforge
uv sync
uv pip install -e ".[dev]"
```

### External Tools (optional but recommended)

```bash
# Static analysis
winget install Cppcheck.Cppcheck

# ARM cross-compiler (for STM32 builds)
winget install Arm.GnuArmEmbeddedToolchain

# Firmware flashing
uv pip install -e ".[flash]"
```

## Code Style

- **Formatter/Linter**: [Ruff](https://docs.astral.sh/ruff/) (configured in `pyproject.toml`)
- **Type hints**: Use them on all public functions
- **Line length**: 100 characters
- **Docstrings**: One-line for simple functions, Google style for complex ones
- **Imports**: Sorted by `ruff` (isort-compatible)

Run before committing:
```bash
ruff check .
ruff format .
mypy core/ plugins/
```

## Testing

```bash
pytest                    # Run all tests
pytest tests/ -v          # Verbose
pytest --cov=core         # Coverage
```

## PR Process

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/your-feature`
3. Make changes with tests
4. Run linting and tests
5. Submit PR with a clear description

## What to Contribute

### High-Impact Contributions
- **New plugins** — ESP-IDF, Zephyr, NXP MCUXpresso, TI DriverLib, etc.
- **More board templates** — popular dev boards for existing plugins
- **Test coverage** — unit tests for core modules
- **Documentation** — tutorials, examples, guides

### Plugin Submissions
- Must implement all 5 interfaces
- Include at least one board template
- Add a test file in `tests/test_plugin_<name>.py`
- Document in the plugin's own README

### Bug Fixes
- Include a test that reproduces the issue
- Reference the issue number in the PR

## Architecture Decisions

If you're making a significant change, open an issue first to discuss the approach.
Key principles to maintain:
- Core must not depend on any specific vendor SDK
- All vendor knowledge lives in plugins
- Human-in-the-loop gates are non-negotiable (no fully-autonomous mode)
- LLM provider choice stays flexible (no hard-coding to one provider)
