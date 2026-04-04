.PHONY: lint typecheck test

lint:
	python -m ruff check app tests && python -m ruff format --check app tests

typecheck:
	python -m mypy app

test:
	python -m pytest tests
