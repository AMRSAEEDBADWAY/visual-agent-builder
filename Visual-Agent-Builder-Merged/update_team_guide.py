import subprocess
import sys
import os

print("Installing dependencies...")
subprocess.check_call([sys.executable, "-m", "pip", "install", "reportlab", "pypdf"])

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from pypdf import PdfReader, PdfWriter

pdf_path = "TEAM_GUIDE.pdf"
temp_pdf = "temp_appendix.pdf"
output_pdf = "TEAM_GUIDE_updated.pdf"

print("Creating appendix PDF...")
c = canvas.Canvas(temp_pdf, pagesize=letter)
c.setFont("Helvetica-Bold", 16)
c.drawString(72, 750, "Team Member: Antigravity (AI Architect & Developer)")

c.setFont("Helvetica-Bold", 12)
c.drawString(72, 710, "Contributions & Implemented Features:")

c.setFont("Helvetica", 11)
tasks = [
    "- Designed and implemented the 'FlowBuilder' core logic for managing nodes and dependencies.",
    "- Created the interactive 'Visual Flow Editor' with a custom HTML5 canvas in Streamlit.",
    "- Built the 'Vision Agent' utilizing the Gemini API for image description, OCR, and data extraction.",
    "- Implemented real-time dynamic UI updates, agent properties panel, and flow validation.",
    "- Handled dependency management, API integration, and model fallback resolutions.",
]

y = 680
for t in tasks:
    c.drawString(90, y, t)
    y -= 25

c.setFont("Helvetica-Oblique", 10)
c.drawString(72, y - 40, "Added by Antigravity AI on behalf of the Visual Agent Builder project.")

c.save()

print("Merging with original PDF...")
reader = PdfReader(pdf_path)
writer = PdfWriter()

for page in reader.pages:
    writer.add_page(page)

reader_app = PdfReader(temp_pdf)
writer.add_page(reader_app.pages[0])

with open(output_pdf, "wb") as f:
    writer.write(f)

# Ensure the file isn't open elsewhere
try:
    os.replace(output_pdf, pdf_path)
    if os.path.exists(temp_pdf):
        os.remove(temp_pdf)
    print("Successfully updated TEAM_GUIDE.pdf!")
except Exception as e:
    print(f"Error replacing file: {e}")
