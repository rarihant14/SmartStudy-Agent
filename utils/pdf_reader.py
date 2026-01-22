from pypdf import PdfReader

def extract_text_from_pdf(pdf_path: str) -> str:
    reader = PdfReader(pdf_path)
    full_text = []

    for page in reader.pages:
        text = page.extract_text()
        if text:
            full_text.append(text)

    return "\n".join(full_text).strip()
