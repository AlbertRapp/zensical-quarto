-- Marker Divs (class `zensical-block`, from callouts.lua / tabsets.lua) ->
-- pymdownx.blocks fences, emitted as raw "markdown" so pandoc's gfm writer
-- passes them through untouched:
--
--   /// admonition | Title
--       type: note
--
--   content
--
--   ///
--
-- pymdownx.blocks needs an outer block's fence to be longer than any fence
-- nested inside it, so the fence length is 3 + nesting depth below the block.
-- Runs at post-render, after Quarto has finished with the block contents.

local function is_marker(el)
  return el.t == "Div" and el.classes:includes("zensical-block")
end

-- Depth of marker Divs nested inside `blocks` (0 = none).
local function nested_depth(blocks)
  local depth = 0
  pandoc.Blocks(blocks):walk({
    Div = function(d)
      if is_marker(d) then
        depth = math.max(depth, 1 + nested_depth(d.content))
        return d, false
      end
    end,
  })
  return depth
end

local function header(el, fence)
  local kind = el.attributes["zensical-block"]
  local lines = { fence .. " " .. kind .. " | " .. el.attributes["zensical-title"] }
  if el.attributes["zensical-type"] then
    lines[#lines + 1] = "    type: " .. el.attributes["zensical-type"]
  end
  if el.attributes["zensical-open"] then
    lines[#lines + 1] = "    open: true"
  end
  if el.attributes["zensical-new"] then
    lines[#lines + 1] = "    new: true"
  end
  return table.concat(lines, "\n")
end

local convert

local function convert_blocks(blocks)
  local out = pandoc.Blocks({})
  for _, b in ipairs(blocks) do
    out:extend(convert(b))
  end
  return out
end

convert = function(b)
  if is_marker(b) then
    local fence = string.rep("/", 3 + nested_depth(b.content))
    local out = pandoc.Blocks({ pandoc.RawBlock("markdown", header(b, fence)) })
    out:extend(convert_blocks(b.content))
    out:insert(pandoc.RawBlock("markdown", fence))
    return out
  end
  -- Recurse into ordinary containers so nested markers are found too
  if b.content and (b.t == "Div" or b.t == "BlockQuote") then
    b.content = convert_blocks(b.content)
  end
  return { b }
end

function Pandoc(doc)
  doc.blocks = convert_blocks(doc.blocks)
  return doc
end
