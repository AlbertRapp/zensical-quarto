-- Keep section ids: `## Tabsets {#sec-tabsets}`.
--
-- The gfm writer drops heading attributes, so Zensical would only give the
-- heading its own slug ("tabsets") and every @sec- link would point to
-- nothing. Headings with a `sec-` id are written as raw Markdown with an
-- attr_list id instead.

function Header(el)
  if not el.identifier:match("^sec%-") then
    return nil
  end
  local text = pandoc.write(pandoc.Pandoc({ pandoc.Plain(el.content) }), "gfm")
  return pandoc.RawBlock("markdown",
    string.rep("#", el.level) .. " " .. text:gsub("%s+$", "") .. " { #" .. el.identifier .. " }")
end
