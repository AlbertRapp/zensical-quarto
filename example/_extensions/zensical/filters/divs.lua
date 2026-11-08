-- Remaining Divs -> raw `<div ... markdown="1">` ... `</div>`.
--
-- pandoc's gfm writer emits a Div as `<div ...>` with Markdown inside, and
-- Python-Markdown leaves that Markdown unparsed unless md_in_html sees a
-- `markdown` attribute. Setting the attribute on the Div doesn't help: the
-- writer renames it to `data-markdown`. So the tags are written as raw
-- markdown instead. Affects e.g. the bibliography (Div#refs) and cell
-- output Divs. Quarto's internal `quarto-scaffold` Divs are not written as
-- HTML, so they are left alone.

local function escape(s)
  return (s:gsub("&", "&amp;"):gsub('"', "&quot;"):gsub("<", "&lt;"))
end

local function open_tag(el)
  local parts = { "<div" }
  if el.identifier ~= "" then
    parts[#parts + 1] = ' id="' .. escape(el.identifier) .. '"'
  end
  if #el.classes > 0 then
    parts[#parts + 1] = ' class="' .. escape(table.concat(el.classes, " ")) .. '"'
  end
  for k, v in pairs(el.attributes) do
    -- pandoc's HTML writers prefix non-standard attributes with data-
    parts[#parts + 1] = " data-" .. k:gsub("^data%-", "") .. '="' .. escape(v) .. '"'
  end
  parts[#parts + 1] = ' markdown="1">'
  return table.concat(parts)
end

function Div(el)
  if el.classes:includes("quarto-scaffold") or el.classes:includes("zensical-block") then
    return nil
  end
  local out = pandoc.Blocks({ pandoc.RawBlock("markdown", open_tag(el)) })
  out:extend(el.content)
  out:insert(pandoc.RawBlock("markdown", "</div>"))
  return out
end
