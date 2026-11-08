-- Crossref'd figures and tables -> <figure markdown="1"> for md_in_html.
--
-- At post-render, Quarto's gfm renderer has turned each FloatRefTarget into
-- a Div.quarto-scaffold with this shape (verified on Quarto 1.10):
--   figure: RawBlock `<div id="fig-x">`, <content>, Plain "Figure 1: cap", RawBlock `</div>`
--   table:  RawBlock `<div id="tbl-x">`, Plain "Table 1: cap", Table, RawBlock `</div>`
-- (plus RawBlocks containing only whitespace in between).
-- Python-Markdown ignores Markdown inside plain HTML blocks, so the wrapper
-- becomes <figure id=... markdown="1"> and the caption a <figcaption>.

local function is_blank_raw(b)
  return b.t == "RawBlock" and b.text:match("^%s*$")
end

local function caption_html(block)
  local md = pandoc.write(pandoc.Pandoc({ pandoc.Plain(block.content) }), "gfm")
  return pandoc.RawBlock("markdown",
    '<figcaption markdown="span">' .. md:gsub("%s+$", "") .. "</figcaption>")
end

function Div(el)
  if not el.classes:includes("quarto-scaffold") then
    return nil
  end
  local first, last = el.content[1], el.content[#el.content]
  if not (first and first.t == "RawBlock" and last.t == "RawBlock") then
    return nil
  end
  local id = first.text:match('^<div id="((%a+)%-[^"]*)">%s*$')
  local kind = id and id:match("^(%a+)%-")
  if not (kind == "fig" or kind == "tbl") or not last.text:match("^%s*</div>%s*$") then
    return nil
  end

  -- inner blocks without the wrapper and whitespace-only raw blocks
  local inner = pandoc.Blocks({})
  for i = 2, #el.content - 1 do
    local b = el.content[i]
    if not is_blank_raw(b) then
      -- Plain -> Para so the writer puts a blank line before </figcaption>
      inner:insert(b.t == "Plain" and pandoc.Para(b.content) or b)
    end
  end

  -- figures: caption is the last block; tables: caption is the first block
  local cap_index = kind == "fig" and #inner or 1
  local cap = inner[cap_index]
  if cap and (cap.t == "Plain" or cap.t == "Para") then
    inner[cap_index] = caption_html(cap)
  end

  local class = kind == "fig" and "quarto-figure" or "quarto-table"
  local out = pandoc.Blocks({
    pandoc.RawBlock("markdown", '<figure id="' .. id .. '" class="' .. class .. '" markdown="1">'),
  })
  out:extend(inner)
  out:insert(pandoc.RawBlock("markdown", "</figure>"))
  return out
end
