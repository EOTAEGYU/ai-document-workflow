import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from temporalio.client import Client

from app.api.documents import router as documents_router
from app.config import STORAGE_DIR, TEMPORAL_ADDRESS, TEMPORAL_TASK_QUEUE
from app.database import Base, engine
from app.models import Document  # noqa: F401 (ensures table metadata is registered)


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(STORAGE_DIR, exist_ok=True)
    Base.metadata.create_all(bind=engine)

    app.state.temporal_client = await Client.connect(TEMPORAL_ADDRESS)
    app.state.temporal_task_queue = TEMPORAL_TASK_QUEUE

    yield


app = FastAPI(title="AI Document Workflow", lifespan=lifespan)
app.include_router(documents_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
