import sys, pypdfium2 as pdfium
pdf = pdfium.PdfDocument(sys.argv[1])
for s in sys.argv[3:]:
    i=int(s)-1
    pdf[i].render(scale=1.1).to_pil().save(f"{sys.argv[2]}_{s}.png")
print(len(pdf))
