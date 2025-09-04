# src/extract_pdf.py
from pypdf import PdfReader
from pathlib import Path


def extract_text_from_pdf(pdf_path):
    reader = PdfReader(pdf_path)
    pages = []
    for p in reader.pages:
        text = p.extract_text() or ""
        pages.append(text)
    return "\n\n".join(pages)


def save_text(pdf_path: str, out_txt_path: str):
    out = Path(out_txt_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    text = extract_text_from_pdf(pdf_path=pdf_path)
    out.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    pdfs = {
        "automotivespice": "../data/raw/Automotive_SPICE_PAM_31_EN.pdf",
        "autosar_ecum": "../data/raw/AUTOSAR_SWS_ECUStateManager.pdf",
    }
    for name, p in pdfs.items():
        save_text(p, f"../data/txt/{name}.txt")
        print("Saved:", name)
