
"""
File text extraction utilities.
Handles PDF, plain text, and image files (OCR via Gemini Vision).
"""
import io
import base64
from pathlib import Path
 
 
def extract_text_from_file(file_bytes: bytes, suffix: str, filename: str) -> str:
    """
    Extract raw text from uploaded file based on its type.
    Supports: .pdf, .txt, .png, .jpg, .jpeg
    """
    suffix = suffix.lower()
 
    if suffix == ".txt":
        return _extract_from_text(file_bytes)
 
    elif suffix == ".pdf":
        return _extract_from_pdf(file_bytes)
 
    elif suffix in [".png", ".jpg", ".jpeg"]:
        return _extract_from_image_via_gemini(file_bytes, suffix)
 
    else:
        raise ValueError(f"Unsupported file extension: {suffix}")
 
 
def _extract_from_text(file_bytes: bytes) -> str:
    """Decode plain text file."""
    try:
        return file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return file_bytes.decode("latin-1", errors="replace")
 
 
def _extract_from_pdf(file_bytes: bytes) -> str:
    """
    Extract text from PDF using pdfplumber.
    Falls back to PyMuPDF if pdfplumber fails.
    """
    text_parts = []
 
    # Try pdfplumber first
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        if text_parts:
            return "\n\n".join(text_parts)
    except Exception:
        pass
 
    # Fallback: PyMuPDF (fitz)
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        for page in doc:
            text_parts.append(page.get_text())
        doc.close()
        if text_parts:
            return "\n\n".join(text_parts)
    except Exception:
        pass
 
    raise ValueError("Could not extract text from PDF. The PDF may be scanned/image-based — try uploading as an image.")
 
 
def _extract_from_image_via_gemini(file_bytes: bytes, suffix: str) -> str:
    """
    Use Gemini Vision to extract text from an image (OCR).
    """
    import google.generativeai as genai
    import os
 
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set.")
 
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("models/gemini-3.5-flash")
 
    mime_map = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}
    mime_type = mime_map.get(suffix, "image/jpeg")
 
    image_part = {
        "inline_data": {
            "mime_type": mime_type,
            "data": base64.b64encode(file_bytes).decode("utf-8"),
        }
    }
 
    prompt = (
        "You are an OCR engine. Extract ALL text visible in this image exactly as it appears. "
        "Preserve structure, layout, and formatting as much as possible. "
        "Return only the extracted text, nothing else."
    )
 
    response = model.generate_content([prompt, image_part])
    return response.text.strip()