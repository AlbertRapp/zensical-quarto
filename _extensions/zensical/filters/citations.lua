-- Run citeproc from inside the filter chain.
--
-- pandoc normally runs citeproc *after* all Lua filters, so the
-- bibliography Div it creates would never reach divs.lua and its Markdown
-- would stay unparsed by Python-Markdown. The format sets `citeproc: false`
-- and this filter (post-render, before divs.lua) does the work instead.

function Pandoc(doc)
  if doc.meta.bibliography or doc.meta.references then
    return pandoc.utils.citeproc(doc)
  end
end
