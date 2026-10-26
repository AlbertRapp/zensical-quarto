// Draw Plotly figures emitted by zensical_plotly.py.
// document$ fires on the first load and after every instant navigation.
document$.subscribe(() => {
  for (const el of document.querySelectorAll(".zensical-plotly[data-plotly]")) {
    if (el.dataset.rendered) continue;
    const fig = JSON.parse(el.dataset.plotly);
    Plotly.newPlot(el, fig.data, fig.layout, { responsive: true });
    el.dataset.rendered = "true";
  }
});
