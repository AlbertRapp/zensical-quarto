"""Plotly renderer for the zensical-gfm format.

Importing this module makes `fig.show()` emit a placeholder
`<div class="zensical-plotly" data-plotly="...">` holding the figure JSON,
instead of Plotly's default HTML with inline scripts. zensical-plotly.js
(loaded via extra_javascript, after plotly.js) draws every placeholder on
each page load, including Zensical's instant navigation.
"""

import html

import plotly.io as pio
from plotly.io.base_renderers import MimetypeRenderer


class ZensicalRenderer(MimetypeRenderer):
    def to_mimebundle(self, fig_dict):
        fig_json = pio.to_json(fig_dict, validate=False)
        div = f'<div class="zensical-plotly" data-plotly="{html.escape(fig_json, quote=True)}"></div>'
        return {"text/html": div}


pio.renderers["zensical"] = ZensicalRenderer()
pio.renderers.default = "zensical"
