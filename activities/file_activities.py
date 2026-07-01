import os

from temporalio import activity
from temporalio.exceptions import ApplicationError

from app.config import MAX_UPLOAD_SIZE_MB
from shared.types import ALLOWED_EXTENSIONS, DocumentProcessingInput


@activity.defn
def validate_file(input: DocumentProcessingInput) -> None:
    if not os.path.exists(input.file_path):
        raise ApplicationError(
            f"File not found: {input.file_path}", non_retryable=True
        )

    extension = input.file_type.lower().lstrip(".")
    if extension not in ALLOWED_EXTENSIONS:
        raise ApplicationError(
            f"Unsupported file type: {extension}", non_retryable=True
        )

    size_mb = os.path.getsize(input.file_path) / (1024 * 1024)
    if size_mb > MAX_UPLOAD_SIZE_MB:
        raise ApplicationError(
            f"File too large: {size_mb:.1f}MB (max {MAX_UPLOAD_SIZE_MB}MB)",
            non_retryable=True,
        )
