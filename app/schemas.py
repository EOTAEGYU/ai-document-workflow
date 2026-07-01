from datetime import datetime

from pydantic import BaseModel


class DocumentUploadResponse(BaseModel):
    document_id: int
    status: str


class DocumentStatusResponse(BaseModel):
    document_id: int
    status: str
    error_message: str | None = None


class DocumentDetailResponse(BaseModel):
    document_id: int
    file_name: str
    file_type: str
    status: str
    page_count: int | None
    extracted_text: str | None
    summary: str | None
    created_at: datetime
    updated_at: datetime
