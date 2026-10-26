-- Math -> raw `$...$` / `$$...$$` for pymdownx.arithmatex (generic mode).
--
-- Emitting raw output keeps the LaTeX verbatim regardless of the writer's
-- math extensions. Display math must be its own block for arithmatex, so
-- paragraphs containing DisplayMath are split around it.

local function inline_math(m)
  return pandoc.RawInline("markdown", "$" .. m.text .. "$")
end

local function display_math(m)
  return pandoc.RawBlock("markdown", "$$\n" .. m.text:gsub("^%s+", ""):gsub("%s+$", "") .. "\n$$")
end

local function split_para(el)
  local has_display = false
  for _, inl in ipairs(el.content) do
    if inl.t == "Math" and inl.mathtype == "DisplayMath" then
      has_display = true
    end
  end
  if not has_display then
    return nil
  end
  local out, current = pandoc.Blocks({}), pandoc.Inlines({})
  local function flush()
    -- drop whitespace left over at the split points
    while #current > 0 and (current[1].t == "Space" or current[1].t == "SoftBreak") do
      current:remove(1)
    end
    while #current > 0 and (current[#current].t == "Space" or current[#current].t == "SoftBreak") do
      current:remove(#current)
    end
    if #current > 0 then
      out:insert(el.t == "Plain" and pandoc.Plain(current) or pandoc.Para(current))
    end
    current = pandoc.Inlines({})
  end
  for _, inl in ipairs(el.content) do
    if inl.t == "Math" and inl.mathtype == "DisplayMath" then
      flush()
      out:insert(display_math(inl))
    else
      current:insert(inl)
    end
  end
  flush()
  return out
end

return {
  { Para = split_para, Plain = split_para },
  { Math = function(m)
      if m.mathtype == "InlineMath" then
        return inline_math(m)
      end
    end },
}
