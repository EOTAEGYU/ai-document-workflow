from dataclasses import dataclass

import pytesseract
from pdf2image import convert_from_path
from PIL import Image
from temporalio import activity

from shared.types import DocumentProcessingInput

OCR_LANGUAGES = "kor+eng"


@dataclass
class ExtractTextResult:
    text: str
    page_count: int


@activity.defn
def extract_text(input: DocumentProcessingInput) -> ExtractTextResult:
    extension = input.file_type.lower().lstrip(".")

    if extension == "pdf":
        pages = convert_from_path(input.file_path)
        page_texts = []
        for page_no, page in enumerate(pages, start=1):
            page_texts.append(pytesseract.image_to_string(page, lang=OCR_LANGUAGES))
            activity.heartbeat(f"ocr page {page_no}/{len(pages)}")
        return ExtractTextResult(text="\n\n".join(page_texts), page_count=len(pages))

    image = Image.open(input.file_path)
    text = pytesseract.image_to_string(image, lang=OCR_LANGUAGES)
    return ExtractTextResult(text=text, page_count=1)
