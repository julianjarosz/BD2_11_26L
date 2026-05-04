PYTHON := python3
BLACK := $(PYTHON) -m black
PYLINT := $(PYTHON) -m pylint

.PHONY: format lint

format:
	$(BLACK) scripts

lint:
	$(PYLINT) scripts/*.py
