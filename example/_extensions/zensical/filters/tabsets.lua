-- Quarto tabsets (::: {.panel-tabset}) -> marker Divs, one per tab, turned
-- into pymdownx.blocks.tab by blocks.lua.
--
-- Relies on Quarto's `Tabset` custom node (Quarto >= 1.4):
--   el.tabs        list of Tab nodes, each with
--     tab.title    Block (the original tab header)
--     tab.content  Block(s)
-- The first tab of every set gets `new: true`, so adjacent tabsets are
-- not merged into one by pymdownx.

function Tabset(el)
  local out = pandoc.Blocks({})
  for i, tab in ipairs(el.tabs) do
    local attrs = {
      ["zensical-block"] = "tab",
      ["zensical-title"] = pandoc.utils.stringify(tab.title),
    }
    if i == 1 then
      attrs["zensical-new"] = "true"
    end
    out:insert(pandoc.Div(quarto.utils.as_blocks(tab.content),
      pandoc.Attr("", { "zensical-block" }, attrs)))
  end
  return out
end
