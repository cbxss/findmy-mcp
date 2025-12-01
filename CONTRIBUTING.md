# Contributing to FindMyMCP

Thank you for your interest in contributing to FindMyMCP! This document provides guidelines and instructions for contributing.

## Getting Started

### Prerequisites

- Python 3.12 or higher
- [uv](https://github.com/astral-sh/uv) installed
- A Shodan API key for testing

### Development Setup

1. Fork and clone the repository:

```bash
git clone https://github.com/yourusername/findmy-mcp.git
cd findmy-mcp
```

2. Install dependencies:

```bash
uv sync --extra dev
```

3. Create a `.env` file:

```bash
cp .env.example .env
# Edit .env and add your Shodan API key
```

## Development Workflow

### Code Style

We use `ruff` for linting and formatting:

```bash
# Format code
uv run ruff format .

# Check linting
uv run ruff check .

# Fix linting issues
uv run ruff check --fix .
```

### Type Checking

We use `mypy` in strict mode:

```bash
uv run mypy src
```

### Testing

Run tests with pytest:

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=findmy_mcp --cov-report=html

# Run specific test file
uv run pytest tests/test_models.py

# Run with verbose output
uv run pytest -v
```

### Before Committing

Make sure your code passes all checks:

```bash
# Format
uv run ruff format .

# Lint
uv run ruff check --fix .

# Type check
uv run mypy src

# Test
uv run pytest
```

## Pull Request Process

1. Create a feature branch from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes following our coding standards

3. Add tests for new functionality

4. Update documentation as needed

5. Ensure all checks pass

6. Commit your changes with clear, descriptive messages:
   ```bash
   git commit -m "Add feature: description of feature"
   ```

7. Push to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```

8. Open a Pull Request with:
   - Clear title and description
   - Reference to any related issues
   - Summary of changes
   - Test results

## Coding Standards

### Python Style

- Follow PEP 8 (enforced by ruff)
- Use type hints for all function signatures
- Maximum line length: 100 characters
- Use descriptive variable names

### Documentation

- Add docstrings to all modules, classes, and functions
- Use Google-style docstrings
- Update README.md for user-facing changes
- Add inline comments for complex logic

### Example Docstring

```python
def verify_server(self, server: DiscoveredServer) -> VerifiedServer | None:
    """Verify if a discovered server is a valid MCP server.

    Args:
        server: Discovered server to verify

    Returns:
        Verified server if valid MCP server, None otherwise

    Raises:
        ValueError: If server is invalid
    """
    pass
```

### Testing

- Write tests for new features
- Maintain or improve code coverage
- Use descriptive test names
- Test edge cases and error conditions

## Project Structure

```
findmy-mcp/
├── src/
│   └── findmy_mcp/
│       ├── __init__.py      # Package exports
│       ├── cli.py           # CLI interface
│       ├── config.py        # Configuration
│       ├── models.py        # Data models
│       ├── scanner.py       # Scanner logic
│       ├── verifier.py      # Verification
│       └── filters.json     # Shodan filters
├── tests/                   # Test suite
├── examples/                # Example scripts
└── docs/                    # Documentation
```

## Adding New Features

### New Shodan Filters

1. Edit `src/findmy_mcp/filters.json`
2. Add filters to appropriate category or create new category
3. Test filters don't exceed rate limits
4. Update documentation

### New Configuration Options

1. Add field to `ScannerConfig` in `config.py`
2. Add validation if needed
3. Update `.env.example`
4. Document in README.md

### New Output Formats

1. Add export method to `scanner.py`
2. Add tests for new format
3. Update CLI if needed
4. Document in README.md

## Reporting Issues

When reporting issues, include:

- Description of the problem
- Steps to reproduce
- Expected behavior
- Actual behavior
- Environment details (OS, Python version, uv version)
- Relevant logs or error messages

## Security

If you discover a security vulnerability:

1. **Do not** open a public issue
2. Email the maintainers privately
3. Include details of the vulnerability
4. Allow time for a fix before disclosure

## Code of Conduct

### Our Standards

- Be respectful and inclusive
- Welcome newcomers
- Accept constructive criticism
- Focus on what's best for the community
- Show empathy towards others

### Unacceptable Behavior

- Harassment or discrimination
- Trolling or insulting comments
- Publishing others' private information
- Other unprofessional conduct

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## Questions?

Feel free to open an issue for:
- Questions about contributing
- Feature requests
- Bug reports
- Documentation improvements

Thank you for contributing to FindMyMCP!
