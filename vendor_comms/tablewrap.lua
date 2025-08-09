function Table(t)
  local n = #t.colspecs
  t.colspecs = {}
  for i = 1, n do
    t.colspecs[i] = { pandoc.AlignLeft, pandoc.ColWidthDefault }
  end
  t.attr = t.attr or pandoc.Attr("", {}, {})
  t.attr.attributes = t.attr.attributes or {}
  t.attr.attributes["tabularx"] = "true"
  return t
end
