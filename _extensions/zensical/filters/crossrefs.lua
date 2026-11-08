-- Cross-references: @sec-x on any page, and @fig-x / @tbl-x whose target
-- lives in another .qmd of the project.
--
-- In a `default` Quarto project every page is rendered on its own, so Quarto
-- only resolves refs within the page and leaves the rest as "?@sec-x".
-- This filter runs pre-quarto: it scans the project's other .qmd files for
-- those ids and replaces each unresolved Cite by a Markdown link
-- `[Figure 1](other.md#fig-x)`, which Zensical rewrites to the page URL.
-- (A plain link without attributes, so the gfm writer doesn't fall back to
-- raw HTML, which Zensical wouldn't rewrite.)
--
-- Section refs show the heading text, `[Tabsets](other.md#sec-tabsets)`:
-- headings are never numbered in the output, so Quarto's "Section 2" would
-- point to nothing the reader can see. Figures and tables count up in order
-- of appearance on their page, as Quarto numbers them.

local PREFIX = { sec = "Section", fig = "Figure", tbl = "Table" }

local function ref_kind(id)
  local kind = id:match("^(%a+)%-")
  return PREFIX[kind] and kind or nil
end

-- Chunk labels (`#| label: fig-x`) of a code block.
local function chunk_labels(code)
  local labels = {}
  for label in code.text:gmatch("#|%s*label:%s*[\"']?([%w_%-]+)") do
    labels[#labels + 1] = label
  end
  return labels
end

-- All ids defined in `doc` -> { kind = "fig", number = "1" }
-- (sections: { kind = "sec", title = <inlines> })
local function index_doc(doc)
  local ids, counts = {}, { fig = 0, tbl = 0 }

  local function add(id)
    local kind = ref_kind(id)
    if not kind or ids[id] or kind == "sec" then
      return
    end
    counts[kind] = counts[kind] + 1
    ids[id] = { kind = kind, number = tostring(counts[kind]) }
  end

  local function add_any(el)
    if el.identifier and el.identifier ~= "" then
      add(el.identifier)
    end
  end

  doc:walk({
    traverse = "topdown",
    Header = function(h)
      if ref_kind(h.identifier) == "sec" then
        ids[h.identifier] = { kind = "sec", title = h.content }
      end
    end,
    Div = add_any,
    CodeBlock = function(c)
      for _, label in ipairs(chunk_labels(c)) do
        add(label)
      end
    end,
    Table = add_any,
    Image = add_any,
    Span = add_any,
  })
  return ids
end

local function qmd_files(dir, skip, out)
  for _, name in ipairs(pandoc.system.list_directory(dir)) do
    local path = pandoc.path.join({ dir, name })
    if not name:match("^[_.]") and path ~= skip then
      if name:match("%.qmd$") then
        out[#out + 1] = path
      elseif pcall(pandoc.system.list_directory, path) then
        qmd_files(path, skip, out)
      end
    end
  end
  return out
end

-- id -> { kind, number or title, page } for every other .qmd in the project
local function index_project(current)
  local root = quarto.project.directory
  if not root then
    return {}
  end
  local ids = {}
  for _, path in ipairs(qmd_files(root, quarto.project.output_directory, {})) do
    if pandoc.path.normalize(path) ~= current then
      local f = io.open(path, "r")
      local text = f:read("a")
      f:close()
      -- ```{r} isn't a pandoc fence; ```r is, so chunk labels can be found
      text = text:gsub("\n(%s*```+)%s*{(%w+)[^}\n]*}", "\n%1%2")
      local ok, doc = pcall(pandoc.read, text, "markdown")
      if ok then
        local page = pandoc.path.make_relative(path, root):gsub("%.qmd$", ".md")
        for id, ref in pairs(index_doc(doc)) do
          ref.page = page
          ids[id] = ids[id] or ref
        end
      end
    end
  end
  return ids
end

function Pandoc(doc)
  local local_ids = index_doc(doc)
  local current = pandoc.path.normalize(quarto.doc.input_file)
  local project_ids -- built lazily, only if a ref points elsewhere

  -- also ids index_doc doesn't number (e.g. figures from executed chunks)
  doc:walk({
    Block = function(b)
      if b.identifier and b.identifier ~= "" then
        local_ids[b.identifier] = local_ids[b.identifier] or {}
      end
    end,
  })

  -- link from the current page's output location to `page`
  local root = quarto.project.directory or "."
  local here = pandoc.path.directory(pandoc.path.make_relative(current, root))

  return doc:walk({
    Cite = function(cite)
      if #cite.citations ~= 1 then
        return nil
      end
      local citation = cite.citations[1]
      local id = citation.id
      if not ref_kind(id) then
        return nil
      end
      local ref = local_ids[id]
      if ref and ref.kind ~= "sec" then
        return nil -- Quarto resolves figures and tables on the same page
      end
      if not ref then
        project_ids = project_ids or index_project(current)
        ref = project_ids[id]
      end
      if not ref then
        return nil
      end
      local label = ref.title or ref.number
      if not ref.title and citation.mode ~= "SuppressAuthor" then
        label = PREFIX[ref.kind] .. " " .. label
      end
      local target = ref.page and pandoc.path.make_relative(ref.page, here) or ""
      return pandoc.Link(label, target .. "#" .. id)
    end,
  })
end
