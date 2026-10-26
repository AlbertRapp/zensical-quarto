# Quarto renders example/src/*.qmd -> example/docs/*.md,
# Zensical builds example/docs -> example/site.
EXAMPLE := example
export QUARTO_PYTHON := $(CURDIR)/.venv/bin/python

.PHONY: site render build serve test clean

site: render build

render:
	uv run quarto render $(EXAMPLE)

build:
	cd $(EXAMPLE) && uv run zensical build --clean

serve: render
	uv run python scripts/dev.py $(EXAMPLE)

test:
	uv run pytest

clean:
	rm -rf $(EXAMPLE)/docs $(EXAMPLE)/site $(EXAMPLE)/_freeze tests/_build
