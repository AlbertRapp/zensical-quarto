-- Quarto callouts -> marker Divs, turned into pymdownx.blocks by blocks.lua.
--
-- Relies on Quarto's `Callout` custom node (Quarto >= 1.3):
--   el.type     "note" | "tip" | "warning" | "caution" | "important"
--   el.title    Inlines or Blocks, or nil when no title was given
--   el.collapse "true" | "false" (strings), or nil when not collapsible
--   el.content  Blocks
-- A leading header inside the callout is already moved into el.title.

local function title_text(el)
  if el.title ~= nil and pandoc.utils.stringify(el.title) ~= "" then
    return pandoc.utils.stringify(el.title)
  end
  -- Quarto's default title is the capitalised type
  return (el.type:gsub("^%l", string.upper))
end

function Callout(el)
  local attrs = {
    ["zensical-title"] = title_text(el),
    ["zensical-type"] = el.type,
  }
  local collapse = el.collapse ~= nil and tostring(el.collapse) or nil
  if collapse == "true" or collapse == "false" then
    attrs["zensical-block"] = "details"
    if collapse == "false" then
      attrs["zensical-open"] = "true"
    end
  else
    attrs["zensical-block"] = "admonition"
  end
  return pandoc.Div(el.content, pandoc.Attr("", { "zensical-block" }, attrs))
end
