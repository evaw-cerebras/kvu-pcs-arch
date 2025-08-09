-- Force all tables to ltablex with wrapped, left-aligned X columns
function Table(t)
  local n = #t.colspecs
  -- make every column an X-like wrapped column
  t.colspecs = {}
  for i = 1, n do
    t.colspecs[i] = { pandoc.AlignLeft, pandoc.ColWidthDefault }
  end
  -- flag for tabularx/ltablex emission
  t.attr = t.attr or pandoc.Attr("", {}, {})
  t.attr.attributes = t.attr.attributes or {}
  t.attr.attributes["tabularx"] = "true"
  return t
end
