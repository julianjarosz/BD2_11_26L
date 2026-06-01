UV := uv
PYTHON := $(UV) run python
BLACK := $(UV) run black
MYPY := $(UV) run mypy
PYLINT := $(UV) run pylint

.PHONY: format format-check lint test type-check

format:
	$(BLACK) scripts

format-check:
	$(BLACK) --check scripts

lint:
	$(PYLINT) scripts

test:
	$(PYTHON) -m unittest discover -s scripts/tests || test $$? -eq 5

type-check:
	$(MYPY) scripts
