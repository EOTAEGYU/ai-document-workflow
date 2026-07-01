from dataclasses import dataclass
from enum import Enum


class DocumentStatus(str, Enum):
    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    OCR_COMPLETED = "OCR_COMPLETED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg"}


@dataclass
class DocumentProcessingInput:
    document_id: int
    file_path: str
    file_type: str


@dataclass
class UpdateStatusInput:
    document_id: int
    status: str
    error_message: str | None = None


@dataclass
class SaveExtractedTextInput:
    document_id: int
    extracted_text: str
    page_count: int
