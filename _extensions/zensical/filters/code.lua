-- Code blocks without a language (e.g. cell output) -> fenced ```text blocks.
--
-- pandoc's gfm writer emits such blocks as *indented* code. Two indented
-- blocks separated only by a blank line (e.g. the outputs of consecutive
-- cells with `echo: false`) are merged into one by Python-Markdown, so give
-- them a language and let the writer use fences instead.

function CodeBlock(el)
  if #el.classes == 0 then
    el.classes = { "text" }
    return el
  end
end

-- Quarto's code-fold wrapper is raw HTML (`<details class="code-fold">`);
-- md_in_html only parses the fenced code inside it with a markdown attribute.
function RawBlock(el)
  if el.format == "markdown" or el.format == "html" then
    local text, n = el.text:gsub('^<details class="code%-fold">', '<details class="code-fold" markdown="1">')
    if n > 0 then
      return pandoc.RawBlock("markdown", text)
    end
  end
end
