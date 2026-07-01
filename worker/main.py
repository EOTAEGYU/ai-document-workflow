import asyncio
import concurrent.futures
import logging

from temporalio.client import Client
from temporalio.worker import Worker

from activities.db_activities import save_extracted_text, update_status
from activities.file_activities import validate_file
from activities.ocr_activities import extract_text
from activities.text_activities import clean_text
from app.config import TEMPORAL_ADDRESS, TEMPORAL_TASK_QUEUE
from workflows.document_processing_workflow import DocumentProcessingWorkflow

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main() -> None:
    client = await Client.connect(TEMPORAL_ADDRESS)

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as activity_executor:
        worker = Worker(
            client,
            task_queue=TEMPORAL_TASK_QUEUE,
            workflows=[DocumentProcessingWorkflow],
            activities=[
                validate_file,
                extract_text,
                clean_text,
                save_extracted_text,
                update_status,
            ],
            activity_executor=activity_executor,
        )
        logger.info("Starting Temporal worker on task queue '%s'", TEMPORAL_TASK_QUEUE)
        await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
