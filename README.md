# zensical-quarto

A Quarto format extension, **`zensical-gfm`**, that renders Quarto documents
(executable code included) to Markdown that [Zensical](https://zensical.org)
builds into a native-looking site: Quarto callouts become admonitions, tabsets
become content tabs, math is rendered by MathJax, and cross-references, citations
and footnotes all work.

```
src/*.qmd ──quarto render──▶ docs/*.md (+ figures) ──zensical build──▶ site/
```

## Quickstart

Requirements: [Quarto](https://quarto.org) ≥ 1.5 (tested with 1.10.18) and
[uv](https://docs.astral.sh/uv/).

```bash
uv sync          # Zensical, Jupyter, matplotlib, pandas, plotly, pytest, ...
make site        # quarto render example + zensical build
make serve       # dev loop (see below)
make test        # uv run pytest
```

The built example site ends up in `example/site/`.

### Using the format in your own project

1. Add the extension: `quarto add <github-user>/zensical-quarto`, or copy
   `_extensions/zensical/` into your project's `_extensions/` folder.
2. Set up the project like `example/`:

   ```yaml
   # _quarto.yml
   project:
     type: default
     output-dir: docs
     render: ["src/*.qmd"]
     resources: ["src/javascripts/*", "src/*.bib"]
     post-render: _scripts/flatten_docs.py   # docs/src/* -> docs/*
   format: zensical-gfm
   execute:
     freeze: auto
   ```

   Copy `example/_scripts/flatten_docs.py`: Quarto renders `src/page.qmd` to
   `docs/src/page.md`, and the script moves it up to `docs/page.md`.
3. Use `example/zensical.toml` as a starting point. It must enable the Markdown
   extensions the output relies on (`pymdownx.blocks.admonition`, `.details`,
   `.tab`, `pymdownx.arithmatex` with `generic = true`, `md_in_html`,
   `footnotes`, `attr_list`, `pymdownx.superfences`, `pymdownx.highlight`).
   Listing `markdown_extensions` replaces Zensical's defaults, so list them all.
   Set `site_url`, because Zensical disables instant navigation without it.
4. Point Quarto at the right Python: `export QUARTO_PYTHON=$PWD/.venv/bin/python`
   (the Makefile does this).

## Feature mapping

| Quarto feature | Becomes | Status |
|---|---|---|
| Callouts (note, tip, warning, caution, important), with/without title | `/// admonition \| Title` + `type:` | ✅ supported |
| Collapsible callouts (`collapse="true"/"false"`) | `/// details` (+ `open: true`) | ✅ supported |
| Nested callouts, callouts inside tabs | nested blocks with longer outer fences | ✅ supported |
| Tabsets (`.panel-tabset`) | `/// tab` (`new: true` starts each set) | ✅ supported |
| Inline/display math | `$…$`, `$$…$$` → arithmatex + MathJax 3 | ✅ supported |
| Figures and tables with `#fig-`/`#tbl-` ids, `@fig-x` refs | `<figure id=… markdown>` + `<figcaption>`, Quarto's numbering | ✅ supported |
| Citations + bibliography | resolved by citeproc during render | ✅ supported |
| Footnotes (`[^n]` and inline `^[…]`) | `footnotes` extension | ✅ supported |
| Code cells with output, `echo`/`output`/`warning`/`include` | highlighted fences, output as ```` ```text ```` | ✅ supported |
| Front matter `title`, `description` | preserved YAML → `<title>`, `<meta name="description">` | ✅ supported |
| Code folding (`code-fold`) | `<details class="code-fold">` around the code | ✅ supported (unstyled) |
| Plotly figures | JSON placeholder + `zensical-plotly.js` (see below) | ✅ supported |
| Code annotations (`# <1>`) | markers removed, annotation list shown as plain text after the code | ⚠️ degraded |
| Margin content (`.column-margin`), column layouts (`.columns`) | plain `<div>`s, content in the main column | ⚠️ degraded |
| Chapter/section numbering (`number-sections`) | ignored | ⚠️ degraded |
| Callout cross-references (`#nte-…`) | callout is rendered, but the reference shows as **?@nte-x** (Quarto warns) | ❌ unsupported (xfail test) |
| ipywidgets, htmlwidgets | not supported | ❌ out of scope |

### Plotly

Plotly's default output contains inline scripts (and loads MathJax 2), which don't
work once the page is part of a Zensical site. Import the bundled renderer in a
hidden setup cell:

````markdown
```{python}
#| include: false
import sys
sys.path.insert(0, "../_extensions/zensical/plotly")  # relative to the .qmd
import zensical_plotly
```
````

After that, `fig.show()` emits a `<div class="zensical-plotly" data-plotly="…">`.
Load plotly.js and `zensical-plotly.js` (copy it from
`_extensions/zensical/plotly/`) via `extra_javascript`. The script draws each
figure on every page load, including after instant navigation.

Alternative not implemented here: static images via `kaleido`
(`fig.show(renderer="png")`). That needs no JavaScript but loses interactivity.

## Limitations

- **Format name is `zensical-gfm`, not `zensical-md`.** Quarto's `md` base maps to
  pandoc's `markdown_strict` writer, which drops figure/table captions and ids.
- The Markdown output is meant for Zensical (Python-Markdown + pymdownx) and isn't
  portable GitHub Markdown: it contains `///` blocks and `markdown="1"` HTML.
- Code annotations, margin/column layouts and section numbering degrade
  gracefully (see table). Nothing errors, and the content stays readable.
- Callout cross-references (`@nte-x`) don't resolve: the callout filter has to run
  before Quarto's crossref pass, so the reference renders as **?@nte-x** and Quarto
  prints a warning. Use a normal Markdown link to the callout's id instead.
- `preserve-yaml` copies the entire front matter into `docs/`, including keys
  like `format:`. Zensical ignores keys it doesn't know.
- Citations are run by the format's own filter (`citeproc: false` + `citations.lua`),
  so `citeproc: true` in a document is not needed and should not be set.
- Jupyter prints `Kernel is running over TCP without encryption` during renders.
  It is harmless for local kernels.

## Dev loop

`make serve` renders once, then runs `zensical serve` together with
`scripts/dev.py`, which watches `src/` (via `watchfiles`) and re-renders each
changed `.qmd` with Quarto. Zensical picks up the new Markdown in `docs/` and
reloads the browser. Changes to `.bib`, `.yml` or `.js` files re-render the whole
project.

## Freeze and CI

The example uses `execute: freeze: auto`. Quarto stores computational results in
`example/_freeze/`, and re-executes a document only when its source changes.
**Commit `_freeze/`.** CI then rebuilds the site without needing your data or
long-running computations, and documents with unchanged sources reuse the
committed results. Delete `_freeze/` (or a document's folder in it) to force
re-execution.

`.github/workflows/site.yml` installs Quarto, uv and the dependencies, runs
`make site` and `uv run pytest`. Run the workflow manually with
**deploy = true** to publish `example/site` to GitHub Pages.

## Tests

`tests/check_site.py` (pytest) copies `tests/fixtures/` (one `.qmd` per feature)
to `tests/_build/`, renders and builds it with the example's `zensical.toml`, and
asserts on the HTML. It also builds the example site and, if Playwright's
Chromium is installed (`uv run playwright install chromium`), checks in a real
browser that Plotly and MathJax render across instant navigation (needs network
access for the CDNs).

## Layout

```
_extensions/zensical/        the format extension
  _extension.yml             contributes `gfm` → used as `zensical-gfm`
  filters/                   one concern per filter (see comments in each)
  plotly/                    Plotly renderer + client script
example/                     showcase site (src/ → docs/ → site/)
tests/                       fixtures + check_site.py
NOTES.md                     verified tool behaviour and surprises
```
