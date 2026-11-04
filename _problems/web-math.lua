-- pandoc filter for £robl€m bodies: keep LaTeX equation numbering/references
-- working under MathJax (tags: 'ams', enabled in head.html for layout: problem).
--  * display math carrying a \label  -> raw equation/align environment
--  * \ref / \eqref links             -> raw \ref{} / \eqref{} for MathJax
local function esc(s)
  return (s:gsub('&', '&amp;'):gsub('<', '&lt;'):gsub('>', '&gt;'))
end

function Math(el)
  if el.mathtype == 'DisplayMath' and el.text:find('\\label') then
    local t = el.text
    if t:match('^%s*\\begin{aligned}') then
      t = t:gsub('\\begin{aligned}', '\\begin{align}', 1)
           :gsub('\\end{aligned}%s*$', '\\end{align}')
      return pandoc.RawInline('html', esc(t))
    end
    return pandoc.RawInline('html', '\\begin{equation}' .. esc(t) .. '\\end{equation}')
  end
end

function Link(el)
  local ty = el.attributes['reference-type']
  if ty == 'eqref' or ty == 'ref' then
    return pandoc.RawInline('html', '\\' .. ty .. '{' .. el.attributes['reference'] .. '}')
  end
end

-- Literal dollar signs (\$20 in LaTeX/Markdown) -> \$ so MathJax (processEscapes)
-- shows "$" instead of pairing it with another "$" as a math delimiter.
function Str(el)
  if el.text:find('%$') then
    return pandoc.Str((el.text:gsub('%$', '\\$')))
  end
end

-- No line breaks inside amounts or at formula boundaries:
--  * number <space> currency  ->  number <nbsp> currency    (20 USD, 5 EUR, 3 €)
--  * inline math glued to adjacent text (e.g. "$x$," or "($x$)") -> one nowrap span
local currency = { USD = true, EUR = true, CHF = true, INR = true, GBP = true,
                   ['€'] = true, ['£'] = true, ['₹'] = true }

function Inlines(inl)
  local out = pandoc.Inlines{}
  local i = 1
  while i <= #inl do
    local a, b, c = inl[i], inl[i + 1], inl[i + 2]
    if a.t == 'Str' and a.text:match('%d$') and b and b.t == 'Space'
       and c and c.t == 'Str' and currency[c.text:gsub('[%p]*$', '')] then
      out:insert(pandoc.Str(a.text .. '\u{00A0}' .. c.text))
      i = i + 3
    elseif a.t == 'Math' and a.mathtype == 'InlineMath' then
      local grp = pandoc.Inlines{}
      if #out > 0 and out[#out].t == 'Str' then grp:insert(out:remove(#out)) end
      grp:insert(a)
      while inl[i + 1] and (inl[i + 1].t == 'Str' or (inl[i + 1].t == 'Math'
            and inl[i + 1].mathtype == 'InlineMath')) do
        i = i + 1
        grp:insert(inl[i])
      end
      out:insert(pandoc.Span(grp, pandoc.Attr('', { 'nobr' })))
      i = i + 1
    else
      out:insert(a)
      i = i + 1
    end
  end
  return out
end

-- \begin{abstract}..\end{abstract} (LaTeX) or `abstract:` in a Markdown YAML block:
-- pandoc's reader moves it into the metadata; put it back as the first block,
-- <div class="abstract">, styled in _layouts/problem.html.  Its first paragraph is
-- the teaser in the £robl€m$ list.
function Pandoc(doc)
  local ab = doc.meta.abstract
  if ab then
    local ty = pandoc.utils.type(ab)
    local blocks = ty == 'Blocks' and ab
                   or pandoc.Blocks{ pandoc.Para(ty == 'Inlines' and ab or pandoc.utils.stringify(ab)) }
    doc.blocks:insert(1, pandoc.Div(blocks, pandoc.Attr('', { 'abstract' })))
    doc.meta.abstract = nil
  end
  return doc
end
