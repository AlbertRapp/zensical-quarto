# NOTES — environment and VERIFY log

## Environment (2026-10-26)

| Tool | Version |
|---|---|
| Quarto | 1.10.18 |
| Pandoc (bundled, `quarto pandoc --version`) | 3.10 |
| Python (project venv via uv) | 3.12 (system python3 is 3.10.12, not used) |
| uv | 0.7.20 |
| Zensical | 0.0.73 |
| Python-Markdown / pymdown-extensions | 3.11.2 / 12.3 |
| watchexec / just | not installed → `make` + `scripts/dev.py` (watchfiles) |

## Zensical

- **Config:** both `zensical.toml` (settings under `[project]`) and `mkdocs.yml`
  are read (`zensical/config.py::parse_config` dispatches on the file extension).
  We use `zensical.toml`.
- **Markdown extensions:** any Python-Markdown / pymdownx extension can be listed.
  Supported and used here: `pymdownx.blocks.admonition`, `pymdownx.blocks.details`,
  `pymdownx.blocks.tab`, `pymdownx.arithmatex`, `footnotes`, `attr_list`,
  `md_in_html`, `pymdownx.superfences`, `pymdownx.highlight` — all verified by the
  HTML tests.
- **Surprise:** setting `markdown_extensions` *replaces* Zensical's default list
  (which doesn't include the `pymdownx.blocks.*` extensions), so the example
  config lists everything explicitly. `toc` and `tables` are always added.
- **Excluding files:** `exclude_docs` (gitignore-style multiline string), as in
  MkDocs. Not needed: the `src/` → `docs/` split means Zensical never sees `.qmd`.
- `pymdownx.blocks.details` output is `<details class="<type>">` (no `admonition`
  class); `blocks.admonition` gives `div.admonition.<type>`. Material's CSS has
  aliases for `caution` (→ warning style) and `important` (→ tip style), so all
  five Quarto callout types are styled without a mapping.

## Quarto AST (VERIFY: custom node field names, Quarto 1.10.18)

Dumped with a Lua filter on a test document:

- `Callout`: `el.type` (`"note"` …), `el.title` (nil when untitled; a leading
  `## Heading` inside the callout is moved into `title`), `el.collapse` is the
  **string** `"true"`/`"false"` or nil, `el.content`.
- `Tabset`: `el.tabs` (list), each tab has `tab.title` (a Block — the header) and
  `tab.content`; also `el.level`.
- `FloatRefTarget` (figures/tables with `#fig-`/`#tbl-` ids) is visible at
  `post-quarto` with `identifier`, `type`, `caption_long`, `order`, but Quarto's
  caption decoration ("Figure 1: …") is internal. So `figures.lua` runs at
  **post-render** instead, where the gfm renderer has produced a `Div.quarto-scaffold`:
  `RawBlock('<div id="fig-x">')`, content, `Plain("Figure 1: cap")`, `RawBlock('</div>')`
  (tables: caption first, then the `Table`).
- User filters listed without `at:` run before Quarto's main filters, and the
  custom-node handlers (`Callout`, `Tabset`) fire there, including for nested nodes.

## Format base (VERIFY — contradicts plan)

- The plan proposed contributing `md` → `zensical-md`. In Quarto, `md` maps to
  pandoc's **`markdown_strict`** writer, which warns *"Output format markdown_strict
  does not currently support FloatRefTarget nodes"* and drops figure/table
  captions and ids. **Decision:** contribute `gfm`, so the format is
  **`zensical-gfm`**. Quarto's gfm is `commonmark+…+tex_math_dollars+footnotes+pipe_tables`.

## preserve-yaml (VERIFY)

- `preserve-yaml: true` keeps the **entire** original front matter verbatim
  (including `format:`, `filters:`, `bibliography:` keys). Zensical ignores keys
  it doesn't know; `title` → `<title>`, `description` → `<meta name="description">`
  (tested).
- The gfm template also writes the title as an `# H1`. Kept: Material/Zensical
  uses an existing H1 instead of inserting the title again, so there's exactly one.

## output-dir (VERIFY — partially contradicts plan)

- `output-dir: docs` **does** copy figure folders (`*_files/figure-commonmark/…`)
  and referenced images for Markdown output.
- But Quarto keeps input paths relative to the project root, so `src/page.qmd` →
  `docs/src/page.md`. There is no "input dir" option. **Fix:** a project
  `post-render` script (`example/_scripts/flatten_docs.py`) moves `docs/src/*` up
  to `docs/`. It also runs for single-file renders (`quarto render src/x.qmd`),
  which the dev loop relies on (verified).

## Raw output (Milestone 2, VERIFY)

- With the gfm writer, `RawBlock`/`RawInline` with format `"markdown"`, `"gfm"`,
  `"commonmark"` and `"commonmark_x"` all pass through **verbatim** (tested with
  `/// admonition | T_x *y* \alpha`). We use **`"markdown"`**, which is also what
  Quarto itself uses for its own raw scaffolding in gfm output.

## Math (VERIFY)

- Quarto's gfm already has `tex_math_dollars`, so math is written as `$…$` /
  `$$…$$` without escaping. `math.lua` still emits it as raw output so it doesn't
  depend on writer extensions, and splits paragraphs around display math,
  because arithmatex only recognises `$$` blocks that stand on their own.
- Checked: backslashes, `_`, `*`, `\{ \}` survive into `span/div.arithmatex`.
- MathJax is loaded via `extra_javascript` plus a config file that re-typesets on
  `document$` (instant navigation).

## Surprises found while testing

1. **Divs:** the gfm writer emits Divs as `<div>` HTML with Markdown inside, which
   Python-Markdown leaves unparsed. Adding `markdown="1"` as a Div attribute doesn't
   work: the writer renames it to `data-markdown="1"`. `divs.lua` writes the
   tags as raw Markdown instead.
2. **Citations:** pandoc runs citeproc *after* all Lua filters, so the
   bibliography Div it creates never reaches `divs.lua`. With a `::: {#refs}`
   placeholder this also gave a duplicated `#refs`. Fix: the format sets
   `citeproc: false` and `citations.lua` calls `pandoc.utils.citeproc()` at
   post-render, before `divs.lua`.
3. **Cell output:** written as *indented* code. Outputs of consecutive cells
   (e.g. two `echo: false` cells) merge into one `<pre>`. `code.lua` gives
   language-less code blocks a `text` class so they are written fenced.
4. **Code folding:** Quarto writes `<details class="code-fold">` as raw HTML around
   the fenced code; `code.lua` adds `markdown="1"` so the code gets highlighted.
   Code folding therefore actually works.
5. **Figures:** the image is a `Plain` block directly followed by the caption, so
   `figures.lua` makes it a `Para` to get a blank line in between.
6. Jupyter prints `[IPKernelApp] WARNING | Kernel is running over TCP without
   encryption` on every execution. Harmless (local kernel), not ours to fix.
