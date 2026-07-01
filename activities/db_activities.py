from temporalio import activity
from temporalio.exceptions import ApplicationError

from app.database import get_session
from app.models import Document
from shared.types import SaveExtractedTextInput, UpdateStatusInput


@activity.defn
def save_extracted_text(input: SaveExtractedTextInput) -> None:
    with get_session() as session:
        document = session.get(Document, input.document_id)
        if document is None:
            raise ApplicationError(
                f"Document not found: {input.document_id}", non_retryable=True
            )
        document.extracted_text = input.extracted_text
        document.page_count = input.page_count
        session.commit()


@activity.defn
def update_status(input: UpdateStatusInput) -> None:
    with get_session() as session:
        document = session.get(Document, input.document_id)
        if document is None:
            raise ApplicationError(
                f"Document not found: {input.document_id}", non_retryable=True
            )
        document.status = input.status
        if input.error_message is not None:
            document.error_message = input.error_message
        session.commit()
