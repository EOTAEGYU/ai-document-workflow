import math
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Request
from fastapi.templating import Jinja2Templates

from app.api.documents import list_documents_query
from app.database import get_session
from app.models import Document
from app.timezones import to_kst
from shared.types import DocumentStatus

router = APIRouter(prefix="/ui", tags=["web"])
templates = Jinja2Templates(directory="templates")
templates.env.filters["to_kst"] = to_kst


@router.get("/upload")
def upload_page(request: Request):
    return templates.TemplateResponse(
        "upload.html", {"request": request, "active_nav": "upload"}
    )


@router.get("/documents")
def documents_page(
    request: Request,
    q: str | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 10,
):
    with get_session() as session:
        items, total = list_documents_query(session, q, status, page, page_size)

        total_pages = max(1, math.ceil(total / page_size))

        def build_page_url(target_page: int) -> str:
            params = {"page": target_page, "page_size": page_size}
            if q:
                params["q"] = q
            if status:
                params["status"] = status
            return f"/ui/documents?{urlencode(params)}"

        return templates.TemplateResponse(
            "documents.html",
            {
                "request": request,
                "active_nav": "documents",
                "items": items,
                "q": q,
                "status": status,
                "page": page,
                "total_pages": total_pages,
                "status_options": [s.value for s in DocumentStatus],
                "build_page_url": build_page_url,
            },
        )


@router.get("/documents/{document_id}")
def document_detail_page(request: Request, document_id: int):
    with get_session() as session:
        document = session.get(Document, document_id)
        if document is None:
            raise HTTPException(status_code=404, detail="Document not found")

        return templates.TemplateResponse(
            "document_detail.html",
            {"request": request, "active_nav": "documents", "document": document},
        )
