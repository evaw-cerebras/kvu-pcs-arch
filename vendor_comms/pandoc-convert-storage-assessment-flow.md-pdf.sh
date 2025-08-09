pandoc cluster_storage_vendor_assessments_flow.v0.2.0.md \
  -f gfm+hard_line_breaks \
  --pdf-engine="C:\Program Files\MiKTeX\miktex\bin\x64\xelatex.exe" \
  -V mainfont="Segoe UI" \
  -V mathfont="Cambria Math" \
  -V classoption=portrait \
  -V geometry=margin=0.5in,paperwidth=11in,paperheight=17in \
  -V header-includes='\usepackage{ltablex}\usepackage{array}\usepackage{etoolbox}\usepackage{ragged2e}\setlength\LTleft{0pt}\setlength\LTright{0pt}\AtBeginEnvironment{ltablex}{\RaggedRight}\renewcommand{\tabularxcolumn}[1]{>{\RaggedRight\arraybackslash}p{##1}}\newcolumntype{Y}{>{\RaggedRight\arraybackslash}X}\keepXColumns' \
  --lua-filter=tablewrap.lua \
  -o cluster_storage_vendor_assessments_flow.v0.2.0.md.pdf
