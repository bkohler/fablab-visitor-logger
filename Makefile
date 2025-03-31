.PHONY: test lint typecheck security check

test:
	python -m pytest --cov=fablab_visitor_logger tests/

lint:
	flake8 fablab_visitor_logger/ tests/

typecheck:
	mypy fablab_visitor_logger/ tests/

security:
	bandit -r fablab_visitor_logger/

check: lint typecheck security test
