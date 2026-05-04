UV := uv
BLACK := $(UV) run black
PYLINT := $(UV) run pylint

.PHONY: format lint

format:
	$(BLACK) scripts

lint:
	$(PYLINT) scripts/*.py
