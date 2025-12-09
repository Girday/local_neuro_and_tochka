from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile

from api_gateway.clients.documents import DocumentClient
from api_gateway.clients.ingestion import IngestionClient
from api_gateway.core.context import AuthenticatedUser
from api_gateway.core.rate_limit import RateLimiter
from api_gateway.dependencies import (
    get_current_user,
    get_document_client,
    get_ingestion_client,
    get_rate_limiter,
)
from api_gateway.schemas import DocumentDetail, DocumentItem, DocumentUploadResponse

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentUploadResponse, status_code=202)
async def upload_document(
    file: UploadFile = File(...),
    product: Optional[str] = Form(None),
    version: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    user: AuthenticatedUser = Depends(get_current_user),
    ingestion_client: IngestionClient = Depends(get_ingestion_client),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
) -> DocumentUploadResponse:
    await rate_limiter.check(key=f"doc-upload:{user.tenant_id}:{user.user_id}")
    file_bytes = await file.read()
    files = {"file": (file.filename, file_bytes, file.content_type or "application/octet-stream")}
    metadata = {"tenant_id": user.tenant_id, "product": product, "version": version, "tags": tags}
    cleaned_metadata = {k: v for k, v in metadata.items() if v}
    response = await ingestion_client.enqueue(cleaned_metadata, files)
    return DocumentUploadResponse(**response)


@router.get("", response_model=List[DocumentItem])
async def list_documents(
    status: Optional[str] = Query(default=None),
    product: Optional[str] = Query(default=None),
    tag: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
    user: AuthenticatedUser = Depends(get_current_user),
    document_client: DocumentClient = Depends(get_document_client),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
) -> List[DocumentItem]:
    await rate_limiter.check(key=f"doc-list:{user.tenant_id}:{user.user_id}")
    params = {
        "tenant_id": user.tenant_id,
        "status": status,
        "product": product,
        "tag": tag,
        "search": search,
    }
    cleaned = {k: v for k, v in params.items() if v}
    documents = await document_client.list_documents(cleaned)
    return [DocumentItem(**doc) for doc in documents]


@router.get("/{doc_id}", response_model=DocumentDetail)
async def get_document(
    doc_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
    document_client: DocumentClient = Depends(get_document_client),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
) -> DocumentDetail:
    await rate_limiter.check(key=f"doc-detail:{user.tenant_id}:{user.user_id}")
    _ = user
    document = await document_client.get_document(doc_id=doc_id)
    return DocumentDetail(**document)
