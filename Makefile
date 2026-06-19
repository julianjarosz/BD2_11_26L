UV := uv
PYTHON := $(UV) run python
BLACK := $(UV) run black
MYPY := $(UV) run mypy
PYTEST := $(UV) run pytest
PYLINT := $(UV) run pylint

.PHONY: format format-check lint test test-unit test-integration type-check

format:
	$(BLACK) scripts

format-check:
	$(BLACK) --check scripts

lint:
	$(PYLINT) scripts

test:
	$(PYTEST) scripts/tests

test-unit:
	$(PYTEST) -m "not integration" scripts/tests

test-integration:
	$(PYTEST) -m integration scripts/tests

type-check:
	$(MYPY) scripts
