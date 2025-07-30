import os
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
from PIL import Image
import logging
from datetime import datetime

try:
    import pytesseract
except ImportError:
    pytesseract = None
try:
    import PyPDF2
except ImportError:
    PyPDF2 = None
try:
    import docx
except ImportError:
    docx = None
try:
    import fitz  # PyMuPDF
    # Note: fitz.open and fitz.Pixmap are correct for PyMuPDF, linter may not recognize them.
except ImportError:
    fitz = None
try:
    from langdetect import detect
except ImportError:
    detect = None

logging.basicConfig(level=logging.INFO)

def extract_images_from_pdf_page(file_path: str, page_num: int) -> List[Image.Image]:
    """
    Extract images from a PDF page using fitz (PyMuPDF). Returns a list of PIL Images.
    """
    if fitz is None:
        raise ImportError("PyMuPDF (fitz) is required for image extraction from PDFs. Please install it.")
    images = []
    doc = fitz.open(file_path)
    page = doc[page_num]
    for img_index, img in enumerate(page.get_images(full=True)):
        xref = img[0]
        pix = fitz.Pixmap(doc, xref)
        try:
            if pix.n < 5:
                img_pil = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                images.append(img_pil)
            else:
                # Convert CMYK or other to RGB
                pix = fitz.Pixmap(fitz.csRGB, pix)
                img_pil = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                images.append(img_pil)
        finally:
            pix = None
    return images

def detect_language(text: str, override: Optional[str] = None) -> str:
    if override:
        return override
    if detect is None:
        return 'eng'  # Default to English if langdetect is not available
    try:
        lang = detect(text)
        # Map langdetect codes to Tesseract codes if needed
        return lang
    except Exception as e:
        logging.warning(f"Language detection failed: {e}")
        return 'eng'

def extract_text_from_pdf(file_path: str, language_hint: Optional[str] = None) -> Dict[str, Any]:
    if PyPDF2 is None:
        raise ImportError("PyPDF2 is required for PDF processing. Please install it.")
    if pytesseract is None:
        raise ImportError("pytesseract is required for OCR. Please install it.")
    text_by_page: List[str] = []
    ocr_pages: List[bool] = []
    lang_by_page: List[str] = []
    with open(file_path, 'rb') as f:
        reader = PyPDF2.PdfReader(f)
        for i, page in enumerate(reader.pages):
            try:
                text = page.extract_text() or ''
            except Exception as e:
                logging.error(f"Error extracting text from page {i}: {str(e)}")
                text = ''
            if text.strip():
                text_by_page.append(text)
                ocr_pages.append(False)
                lang_by_page.append(detect_language(text, language_hint))
            else:
                try:
                    images = extract_images_from_pdf_page(file_path, i)
                except Exception as e:
                    logging.error(f"Error extracting images from page {i}: {str(e)}")
                    images = []
                ocr_text = ''
                lang = language_hint or 'eng'
                if images:
                    # Try to detect language from previous text or fallback
                    if len(text_by_page) > 0:
                        lang = lang_by_page[-1]
                    for img in images:
                        try:
                            ocr_result = pytesseract.image_to_string(img, lang=lang)
                            ocr_text += ocr_result + '\n'
                        except Exception as e:
                            logging.error(f"OCR failed on page {i}: {str(e)}")
                    lang_by_page.append(lang)
                text_by_page.append(ocr_text.strip())
                ocr_pages.append(True)
    meta = os.stat(file_path)
    return {
        'text_by_page': text_by_page,
        'ocr_pages': ocr_pages,
        'file_type': 'pdf',
        'file_name': os.path.basename(file_path),
        'file_size_kb': round(meta.st_size / 1024, 2),
        'last_modified': datetime.fromtimestamp(meta.st_mtime).isoformat(),
        'num_pages': len(text_by_page)
    }

def extract_text_from_docx(file_path: str) -> Dict[str, Any]:
    if docx is None:
        raise ImportError("python-docx is required for DOCX processing. Please install it.")
    try:
        doc = docx.Document(file_path)
        text = '\n'.join([para.text for para in doc.paragraphs])
    except Exception as e:
        logging.error(f"Error extracting text from DOCX: {str(e)}")
        text = ''
    meta = os.stat(file_path)
    return {
        'text': text,
        'file_type': 'docx',
        'file_name': os.path.basename(file_path),
        'file_size_kb': round(meta.st_size / 1024, 2),
        'last_modified': datetime.fromtimestamp(meta.st_mtime).isoformat(),
        'num_pages': None
    }

def extract_text_from_txt(file_path: str) -> Dict[str, Any]:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
    except Exception as e:
        logging.error(f"Error reading TXT file: {str(e)}")
        text = ''
    meta = os.stat(file_path)
    return {
        'text': text,
        'file_type': 'txt',
        'file_name': os.path.basename(file_path),
        'file_size_kb': round(meta.st_size / 1024, 2),
        'last_modified': datetime.fromtimestamp(meta.st_mtime).isoformat(),
        'num_pages': None
    }

def ingest_document(file_path: str, language_hint: Optional[str] = None) -> Dict[str, Any]:
    """
    Ingest a document (PDF, DOCX, TXT) and extract text and metadata.
    Optionally, provide a language_hint to override language detection for OCR.
    """
    ext = Path(file_path).suffix.lower()
    if ext == '.pdf':
        return extract_text_from_pdf(file_path, language_hint=language_hint)
    elif ext == '.docx':
        return extract_text_from_docx(file_path)
    elif ext == '.txt':
        return extract_text_from_txt(file_path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")
