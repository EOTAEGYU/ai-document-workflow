from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from activities.db_activities import save_extracted_text, update_status
    from activities.file_activities import validate_file
    from activities.ocr_activities import extract_text
    from activities.text_activities import clean_text
    from shared.types import (
        DocumentProcessingInput,
        DocumentStatus,
        SaveExtractedTextInput,
        UpdateStatusInput,
    )


@workflow.defn
class DocumentProcessingWorkflow:
    @workflow.run
    async def run(self, input: DocumentProcessingInput) -> None:
        try:
            await workflow.execute_activity(
                validate_file,
                input,
                start_to_close_timeout=timedelta(seconds=5),
                retry_policy=RetryPolicy(maximum_attempts=1),
            )

            await workflow.execute_activity(
                update_status,
                UpdateStatusInput(
                    document_id=input.document_id, status=DocumentStatus.PROCESSING.value
                ),
                start_to_close_timeout=timedelta(seconds=10),
                retry_policy=RetryPolicy(maximum_attempts=3),
            )

            ocr_result = await workflow.execute_activity(
                extract_text,
                input,
                start_to_close_timeout=timedelta(minutes=30),
                heartbeat_timeout=timedelta(seconds=30),
                retry_policy=RetryPolicy(maximum_attempts=2),
            )

            await workflow.execute_activity(
                update_status,
                UpdateStatusInput(
                    document_id=input.document_id,
                    status=DocumentStatus.OCR_COMPLETED.value,
                ),
                start_to_close_timeout=timedelta(seconds=10),
                retry_policy=RetryPolicy(maximum_attempts=3),
            )

            cleaned_text = await workflow.execute_activity(
                clean_text,
                ocr_result.text,
                start_to_close_timeout=timedelta(seconds=10),
                retry_policy=RetryPolicy(maximum_attempts=1),
            )

            await workflow.execute_activity(
                save_extracted_text,
                SaveExtractedTextInput(
                    document_id=input.document_id,
                    extracted_text=cleaned_text,
                    page_count=ocr_result.page_count,
                ),
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=RetryPolicy(maximum_attempts=3),
            )

            await workflow.execute_activity(
                update_status,
                UpdateStatusInput(
                    document_id=input.document_id, status=DocumentStatus.COMPLETED.value
                ),
                start_to_close_timeout=timedelta(seconds=10),
                retry_policy=RetryPolicy(maximum_attempts=3),
            )
        except Exception as e:
            await workflow.execute_activity(
                update_status,
                UpdateStatusInput(
                    document_id=input.document_id,
                    status=DocumentStatus.FAILED.value,
                    error_message=str(e),
                ),
                start_to_close_timeout=timedelta(seconds=10),
                retry_policy=RetryPolicy(maximum_attempts=3),
            )
            raise
