# FabLab Visitor Logger Guidelines

## Build/Test/Lint Commands
- Full test suite: `make test` or `pytest --cov=fablab_visitor_logger tests/`
- Single test: `pytest tests/test_file.py::test_function -v`
- BLE tests: `pytest -m "ble_required"` (requires hardware)
- Lint: `make lint` or `flake8 fablab_visitor_logger/ tests/`
- Type check: `make typecheck` or `mypy fablab_visitor_logger/ tests/`
- Format code: `black fablab_visitor_logger/ tests/` and `isort fablab_visitor_logger/ tests/`
- All checks: `make check`

## Code Style
- Python 3.9+ with type hints required for all function signatures
- Line length: 88 characters (Black)
- Imports: Use isort with Black profile
- Naming: `snake_case` for variables/functions, `CamelCase` for classes
- Error handling: Use specific exception types, avoid broad `except Exception`
- Logging: Use standard logging module from `config.py`
- Testing: Aim for >90% coverage, use pytest markers for hardware tests
- Documentation: Google style docstrings for public modules, classes, functions
