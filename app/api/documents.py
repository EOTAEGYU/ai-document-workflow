import os
import uuid

from fastapi import APIRouter, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.config import STORAGE_DIR
from app.database import get_session
from app.models import Document
from app.schemas import (
    DocumentDetailResponse,
    DocumentListResponse,
    DocumentListItem,
    DocumentStatusResponse,
    DocumentUploadResponse,
)
from app.timezones import to_kst
from shared.types import ALLOWED_EXTENSIONS, DocumentProcessingInput, DocumentStatus
from workflows.document_processing_workflow import DocumentProcessingWorkflow

router = APIRouter(prefix="/documents", tags=["documents"])

FILE_MEDIA_TYPES = {
    "pdf": "application/pdf",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
}


def list_documents_query(
    session: Session,
    q: str | None,
    status: str | None,
    page: int,
    page_size: int,
) -> tuple[list[Document], int]:
    query = session.query(Document)

    if q:
        pattern = f"%{q}%"
        query = query.filter(
            or_(Document.file_name.ilike(pattern), Document.extracted_text.ilike(pattern))
        )
    if status:
        query = query.filter(Document.status == status)

    total = query.count()
    items = (
        query.order_by(Document.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return items, total


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(request: Request, file: UploadFile) -> DocumentUploadResponse:
    original_name = file.filename or "upload"
    extension = original_name.rsplit(".", 1)[-1].lower() if "." in original_name else ""

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {extension}. Allowed: {sorted(ALLOWED_EXTENSIONS)}",
        )

    os.makedirs(STORAGE_DIR, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex}.{extension}"
    file_path = os.path.join(STORAGE_DIR, stored_name)

    with open(file_path, "wb") as out_file:
        out_file.write(await file.read())

    with get_session() as session:
        document = Document(
            file_name=original_name,
            file_type=extension,
            file_path=file_path,
            status=DocumentStatus.UPLOADED.value,
        )
        session.add(document)
        session.commit()
        document_id = document.id

    temporal_client = request.app.state.temporal_client
    await temporal_client.start_workflow(
        DocumentProcessingWorkflow.run,
        DocumentProcessingInput(
            document_id=document_id, file_path=file_path, file_type=extension
        ),
        id=f"document-{document_id}",
        task_queue=request.app.state.temporal_task_queue,
    )

    return DocumentUploadResponse(document_id=document_id, status=DocumentStatus.UPLOADED.value)


@router.get("", response_model=DocumentListResponse)
def list_documents(
    q: str | None = None, status: str | None = None, page: int = 1, page_size: int = 10
) -> DocumentListResponse:
    with get_session() as session:
        items, total = list_documents_query(session, q, status, page, page_size)

        return DocumentListResponse(
            items=[
                DocumentListItem(
                    document_id=doc.id,
                    file_name=doc.file_name,
                    file_type=doc.file_type,
                    status=doc.status,
                    page_count=doc.page_count,
                    created_at=to_kst(doc.created_at),
                )
                for doc in items
            ],
            total=total,
            page=page,
            page_size=page_size,
        )


@router.get("/{document_id}/file")
def get_document_file(document_id: int) -> FileResponse:
    with get_session() as session:
        document = session.get(Document, document_id)
        if document is None:
            raise HTTPException(status_code=404, detail="Document not found")
        if not os.path.exists(document.file_path):
            raise HTTPException(status_code=404, detail="File not found on disk")

        media_type = FILE_MEDIA_TYPES.get(document.file_type.lower(), "application/octet-stream")
        return FileResponse(document.file_path, media_type=media_type, filename=document.file_name)


@router.get("/{document_id}", response_model=DocumentDetailResponse)
def get_document(document_id: int) -> DocumentDetailResponse:
    with get_session() as session:
        document = session.get(Document, document_id)
        if document is None:
            raise HTTPException(status_code=404, detail="Document not found")

        return DocumentDetailResponse(
            document_id=document.id,
            file_name=document.file_name,
            file_type=document.file_type,
            status=document.status,
            page_count=document.page_count,
            extracted_text=document.extracted_text,
            summary=document.summary,
            created_at=to_kst(document.created_at),
            updated_at=to_kst(document.updated_at),
        )


@router.get("/{document_id}/status", response_model=DocumentStatusResponse)
def get_document_status(document_id: int) -> DocumentStatusResponse:
    with get_session() as session:
        document = session.get(Document, document_id)
        if document is None:
            raise HTTPException(status_code=404, detail="Document not found")

        return DocumentStatusResponse(
            document_id=document.id,
            status=document.status,
            error_message=document.error_message,
        )
