PYTHON ?= python3

.PHONY: help export validate clean

help:
	@echo "make export    regenerate every format under dist/ from data/"
	@echo "make validate  run integrity checks on data/"
	@echo "make clean     remove dist/"

export:
	$(PYTHON) tools/export.py data dist

validate:
	$(PYTHON) tools/validate.py data

clean:
	rm -rf dist
