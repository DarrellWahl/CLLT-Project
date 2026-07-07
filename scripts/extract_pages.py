import fitz
from pathlib import Path

# File locations
pdf_file = Path("assets/pdf/Road Traffic Signs.pdf")
output_dir = Path("assets/png/pages")
output_dir.mkdir(parents=True, exist_ok=True)

# Open the PDF
doc = fitz.open(pdf_file)

print(f"Found {len(doc)} pages.")

# Export each page
for page_number, page in enumerate(doc, start=1):
    pix = page.get_pixmap(matrix=fitz.Matrix(4, 4))
    output_file = output_dir / f"page_{page_number}.png"
    pix.save(output_file)
    print(f"Saved {output_file}")

print("Done!")