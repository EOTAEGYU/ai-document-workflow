import os
import uuid

from fastapi import APIRouter, HTTPException, Request, UploadFile

from app.config import STORAGE_DIR
from app.database import get_session
from app.models import Document
from app.schemas import DocumentDetailResponse, DocumentStatusResponse, DocumentUploadResponse
from shared.types import ALLOWED_EXTENSIONS, DocumentProcessingInput, DocumentStatus
from workflows.document_processing_workflow import DocumentProcessingWorkflow

router = APIRouter(prefix="/documents", tags=["documents"])


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
            created_at=document.created_at,
            updated_at=document.updated_at,
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
