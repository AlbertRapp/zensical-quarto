"""End-to-end checks: render with Quarto, build with Zensical, inspect HTML.

Two sites are built once per session:

* the fixture site -- tests/fixtures/ (one page per feature) copied to
  tests/_build/, rendered with the zensical-gfm format and built with the
  example's zensical.toml (minus its nav);
* the example site -- example/, built exactly like `make site`.
"""

import functools
import http.server
import json
import os
import re
import shutil
import subprocess
import threading
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"
BUILD = ROOT / "tests" / "_build"
EXAMPLE = ROOT / "example"

ENV = {**os.environ, "QUARTO_PYTHON": str(ROOT / ".venv" / "bin" / "python")}


def run(cmd, cwd):
    result = subprocess.run(cmd, cwd=cwd, env=ENV, capture_output=True, text=True)
    output = result.stdout + result.stderr
    assert result.returncode == 0, f"{' '.join(cmd)} failed:\n{output}"
    return output


def zensical_config_without_nav():
    config = (EXAMPLE / "zensical.toml").read_text()
    return re.sub(r"^nav = \[.*?^\]\n", "", config, flags=re.S | re.M)


@pytest.fixture(scope="session")
def fixture_site():
    shutil.rmtree(BUILD, ignore_errors=True)
    shutil.copytree(FIXTURES, BUILD)
    (BUILD / "_extensions").symlink_to(ROOT / "_extensions")
    (BUILD / "zensical.toml").write_text(zensical_config_without_nav())
    # The fixture pages don't ship MathJax config; the HTML checks don't need it
    quarto_log = run(["quarto", "render"], BUILD)
    zensical_log = run(["zensical", "build", "--clean"], BUILD)
    return {"root": BUILD, "quarto_log": quarto_log, "zensical_log": zensical_log}


@pytest.fixture(scope="session")
def example_site():
    run(["quarto", "render"], EXAMPLE)
    log = run(["zensical", "build", "--clean"], EXAMPLE)
    return {"root": EXAMPLE, "zensical_log": log}


def page(site, name):
    path = site["root"] / "site" / name / "index.html"
    assert path.exists(), f"{path} was not built"
    return BeautifulSoup(path.read_text(), "html.parser")


def article(site, name):
    return page(site, name).select_one("article")


def text_of(el):
    """Text with all whitespace (incl. Quarto's non-breaking spaces) collapsed."""
    return " ".join(el.get_text().split())


def title_of(el):
    return el.select_one(".admonition-title, summary").get_text(strip=True)


# Milestone 1: bare pipeline -------------------------------------------------


def test_pipeline_page_title(fixture_site):
    soup = page(fixture_site, "pipeline")
    assert soup.title.get_text().startswith("Pipeline page")
    assert soup.select_one("article h1").get_text(strip=True).startswith("Pipeline page")


def test_pipeline_code_output(fixture_site):
    assert "hello from python 6*7 = 42" in article(fixture_site, "pipeline").get_text()


def test_pipeline_figure_resolves(fixture_site):
    html_path = fixture_site["root"] / "site" / "pipeline" / "index.html"
    imgs = article(fixture_site, "pipeline").select("img")
    assert imgs, "no <img> in page"
    for img in imgs:
        assert (html_path.parent / img["src"]).resolve().is_file(), img["src"]


def test_quarto_source_not_in_docs(fixture_site):
    assert not list((fixture_site["root"] / "site").rglob("*.qmd"))


def test_zensical_reports_no_issues(fixture_site):
    assert "No issues found" in fixture_site["zensical_log"]


# Callouts ---------------------------------------------------------------------

CALLOUT_TYPES = ["note", "tip", "warning", "caution", "important"]


@pytest.mark.parametrize("kind", CALLOUT_TYPES)
def test_callout_untitled(fixture_site, kind):
    art = article(fixture_site, "callouts")
    matches = [el for el in art.select(f"div.admonition.{kind}") if el.get_text().find(f"Untitled {kind}.") >= 0]
    assert len(matches) == 1
    assert title_of(matches[0]) == kind.capitalize()


@pytest.mark.parametrize(
    "kind, title",
    [
        ("note", "Titled note"),
        ("tip", "Header tip"),
        ("warning", "Titled warning"),
        ("caution", "Titled caution"),
        ("important", "Titled important"),
    ],
)
def test_callout_titled(fixture_site, kind, title):
    art = article(fixture_site, "callouts")
    titles = [title_of(el) for el in art.select(f"div.admonition.{kind}")]
    assert title in titles


def test_callout_body_markdown(fixture_site):
    art = article(fixture_site, "callouts")
    box = next(el for el in art.select("div.admonition.warning") if title_of(el) == "Titled warning")
    assert box.select_one("strong").get_text() == "bold"


def test_callout_header_not_duplicated(fixture_site):
    art = article(fixture_site, "callouts")
    assert not [h for h in art.select("h2, h3") if "Header tip" in h.get_text()]


def test_collapsed_callout(fixture_site):
    art = article(fixture_site, "callouts")
    box = art.select_one("details.tip")
    assert box is not None
    assert title_of(box) == "Collapsed tip"
    assert not box.has_attr("open")


def test_expanded_callout(fixture_site):
    art = article(fixture_site, "callouts")
    box = art.select_one("details.warning")
    assert box is not None
    assert title_of(box) == "Expanded warning"
    assert box.has_attr("open")


def test_nested_callouts(fixture_site):
    art = article(fixture_site, "callouts")
    outer = next(el for el in art.select("div.admonition.note") if title_of(el) == "Outer note")
    inner = outer.select_one("div.admonition.warning")
    assert inner is not None and title_of(inner) == "Inner warning"
    innermost = inner.select_one("div.admonition.tip")
    assert innermost is not None and title_of(innermost) == "Innermost tip"
    assert "///" not in art.get_text()


# Tabsets -----------------------------------------------------------------------


def test_tabsets_separate_with_labels(fixture_site):
    art = article(fixture_site, "tabsets")
    sets = art.select(".tabbed-set")
    labels = [[l.get_text(strip=True) for l in s.select(".tabbed-labels > label")] for s in sets]
    assert labels == [["First A", "First B"], ["Second A", "Second B", "Second C"]]


def test_tab_content(fixture_site):
    art = article(fixture_site, "tabsets")
    blocks = art.select(".tabbed-set")[0].select(".tabbed-block")
    assert [b.get_text(strip=True) for b in blocks] == ["Content A1", "Content B1"]


def test_callout_inside_tab(fixture_site):
    art = article(fixture_site, "tabsets")
    box = art.select(".tabbed-set")[1].select_one("div.admonition.note")
    assert box is not None and title_of(box) == "Callout in tab"


# Math ----------------------------------------------------------------------------


def test_inline_math(fixture_site):
    art = article(fixture_site, "math")
    spans = art.select("span.arithmatex")
    assert [s.get_text() for s in spans] == [r"\(a_1 * b_2 + \alpha_{i} \{x\}\)"]
    # text after the math is still Markdown-processed
    assert art.select_one("em").get_text() == "emphasis"


def test_display_math(fixture_site):
    art = article(fixture_site, "math")
    divs = [d.get_text().strip() for d in art.select("div.arithmatex")]
    assert divs == [
        "\\[\n\\sum_{i=1}^{n} x_i^* \\quad \\mathbf{v}_\\text{out}\n\\]",
        "\\[\nE = mc^2\n\\]",
    ]
    text = art.get_text()
    assert "Text before" in text and "text after." in text


# Cross-references ----------------------------------------------------------------


@pytest.mark.parametrize("fig_id, caption", [("fig-line", "Figure 1: A line with emphasis"), ("fig-static", "Figure 2: A static figure")])
def test_figure_crossref(fixture_site, fig_id, caption):
    art = article(fixture_site, "crossrefs")
    fig = art.select_one(f"figure#{fig_id}")
    assert fig is not None
    assert text_of(fig.select_one("figcaption")) == caption
    img = fig.select_one("img")
    html_dir = fixture_site["root"] / "site" / "crossrefs"
    assert (html_dir / img["src"]).resolve().is_file()
    assert art.select_one(f'a[href="#{fig_id}"]') is not None


def test_figure_caption_markdown(fixture_site):
    fig = article(fixture_site, "crossrefs").select_one("figure#fig-line")
    assert fig.select_one("figcaption em").get_text() == "emphasis"


def test_table_crossref(fixture_site):
    art = article(fixture_site, "crossrefs")
    fig = art.select_one("figure#tbl-nums")
    assert fig is not None
    assert text_of(fig.select_one("figcaption")) == "Table 1: Numbers table"
    assert [th.get_text() for th in fig.select("table th")] == ["x", "y"]
    link = art.select_one('a[href="#tbl-nums"]')
    assert link is not None and text_of(link) == "Table 1"


# Citations -------------------------------------------------------------------------


def test_citations(fixture_site):
    art = article(fixture_site, "citations")
    text = art.get_text()
    assert "Knuth (1984)" in text
    assert "(Tufte 2001, 3)" in text
    refs = art.select("#refs .csl-entry")
    assert [r["id"] for r in refs] == ["ref-knuth1984", "ref-tufte2001"]
    assert refs[0].select_one("em").get_text() == "The TeXbook"
    assert len(art.select("#refs")) == 1


# Footnotes -------------------------------------------------------------------------


def test_footnotes(fixture_site):
    art = article(fixture_site, "footnotes")
    notes = art.select(".footnote li")
    assert len(notes) == 2
    assert "The first footnote." in notes[0].get_text()
    assert "An inline footnote." in notes[1].get_text()
    assert len(art.select("sup a.footnote-ref")) == 2


# Code cells ---------------------------------------------------------------------


def test_code_highlighted(fixture_site):
    art = article(fixture_site, "code")
    blocks = art.select("div.language-python.highlight")
    assert blocks
    assert blocks[0].select_one("code span.nb").get_text() == "print"


def test_code_output_present(fixture_site):
    pres = [p.get_text() for p in article(fixture_site, "code").select("pre")]
    assert any(p.strip() == "visible-output-123" for p in pres)


def test_echo_false(fixture_site):
    text = article(fixture_site, "code").get_text()
    assert "echo-false-output-456" in text
    assert 'print("echo-false-output-456")' not in text


def test_output_false(fixture_site):
    text = article(fixture_site, "code").get_text()
    assert 'print("hidden-output-789")' in text
    assert "hidden-output-789\n" not in text.replace('print("hidden-output-789")', "")


def test_warning_false(fixture_site):
    text = text_of(article(fixture_site, "code"))
    assert "after-suppressed" in text
    # only the source line mentions it, no warning output
    assert text.count("suppressed-warning-xyz") == 1
    assert "UserWarning: shown-warning-abc" in text


# Front matter ---------------------------------------------------------------------


def test_front_matter(fixture_site):
    soup = page(fixture_site, "frontmatter")
    assert soup.title.get_text().startswith("Front matter: title")
    meta = soup.select_one('meta[name="description"]')
    assert meta["content"] == "A description from the front matter."


# Degraded features -------------------------------------------------------------


def test_degraded_page_builds_readably(fixture_site):
    art = article(fixture_site, "degraded")
    text = art.get_text()
    for snippet in ["Margin note content.", "Left column.", "Right column.", "print(x)", "Annotated line.", "Referenced callout body."]:
        assert snippet in text
    assert "<div" not in text and ":::" not in text and "```" not in text


def test_code_fold_becomes_details(fixture_site):
    art = article(fixture_site, "degraded")
    fold = art.select_one("details.code-fold")
    assert fold is not None
    assert fold.select_one("div.language-python.highlight") is not None


def test_callout_keeps_id(fixture_site):
    box = article(fixture_site, "degraded").select_one("div.admonition.note#nte-ref")
    assert box is not None


@pytest.mark.xfail(strict=True, reason="callouts are converted before Quarto's crossref pass; see README Limitations")
def test_callout_crossref_resolves(fixture_site):
    art = article(fixture_site, "degraded")
    assert "?@nte-ref" not in text_of(art)
    assert art.select_one('a[href="#nte-ref"]') is not None


# Example site ------------------------------------------------------------------


@pytest.mark.parametrize("name", ["", "callouts-tabs", "analysis", "math-citations"])
def test_example_pages_exist(example_site, name):
    path = example_site["root"] / "site" / name / "index.html"
    assert path.exists()


def test_example_no_issues(example_site):
    assert "No issues found" in example_site["zensical_log"]


def test_example_index(example_site):
    soup = page(example_site, "")
    assert soup.title.get_text().startswith("Introduction")
    art = soup.select_one("article")
    assert "execute + render" in art.get_text()
    img = art.select_one("figure#fig-intro img")
    assert (example_site["root"] / "site" / img["src"]).resolve().is_file()


# Plotly (Milestone 4) ------------------------------------------------------------


def test_plotly_placeholder(fixture_site):
    art = article(fixture_site, "plotly")
    divs = art.select("div.zensical-plotly")
    assert len(divs) == 1
    fig = json.loads(divs[0]["data-plotly"])
    # plotly >= 6 encodes arrays as base64 typed arrays; plotly.js decodes them
    assert fig["data"][0]["type"] == "scatter"
    assert "x" in fig["data"][0] and "y" in fig["data"][0]
    assert fig["layout"]["title"]["text"] == "Scatter & <b>friends</b>"
    # no inline scripts: they would run before plotly.js is loaded
    assert not art.select("script")


def test_plotly_js_copy_in_sync():
    shipped = ROOT / "_extensions" / "zensical" / "plotly" / "zensical-plotly.js"
    copy = EXAMPLE / "src" / "javascripts" / "zensical-plotly.js"
    assert copy.read_text() == shipped.read_text()


@pytest.fixture(scope="session")
def browser_page():
    sync_api = pytest.importorskip("playwright.sync_api")
    with sync_api.sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except Exception as exc:  # browser binaries not installed
            pytest.skip(f"chromium not available: {exc}")
        page_ = browser.new_page()
        yield page_
        browser.close()


@pytest.fixture(scope="session")
def served_example(example_site):
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=example_site["root"] / "site")
    handler.log_message = lambda *args: None
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}/"
    server.shutdown()


def test_instant_navigation_renders_plotly_and_math(served_example, browser_page):
    """Needs network access for the plotly.js / MathJax CDNs."""
    pg = browser_page
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(served_example)
    pg.wait_for_load_state("networkidle")
    pg.evaluate("window.__noReload = true")

    pg.click("nav a[href$='analysis/']")
    pg.wait_for_selector(".zensical-plotly .main-svg", timeout=15000)

    pg.click("nav a[href$='math-citations/']")
    pg.wait_for_selector("mjx-container", timeout=15000)

    pg.click("nav a[href$='analysis/']")
    pg.wait_for_selector(".zensical-plotly .main-svg", timeout=15000)

    assert pg.evaluate("window.__noReload") is True, "navigation was not instant"
    assert errors == []
