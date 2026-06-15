import uuid
from fastapi import APIRouter, File, Form, UploadFile
from typing import Optional

from app.api.dependencies import CurrentUser, DBSession
from app.core.qdrant import get_qdrant
from app.schemas.document import AskRequest, AskResponse, DocumentResponse
from app.services.document_service import DocumentService
from fastapi import Depends
from qdrant_client import QdrantClient

router = APIRouter(prefix="/documents", tags=["Documents"])


def get_document_service(
    db: DBSession,
    qdrant: QdrantClient = Depends(get_qdrant),
) -> DocumentService:
    return DocumentService(db, qdrant)


# ─── Upload ───────────────────────────────────────────────────────────────────

@router.post("/upload", response_model=DocumentResponse, status_code=201)
async def upload_document(
    current_user: CurrentUser,
    file: UploadFile = File(...),
    service: DocumentService = Depends(get_document_service),
):
    """
    Upload a PDF document.
    The file is processed immediately — text is extracted,
    split into chunks, embedded, and stored in Qdrant.
    """
    file_bytes = await file.read()

    document = await service.upload_document(
        user_id=current_user.id,
        filename=file.filename,
        file_bytes=file_bytes,
    )

    return document


# ─── List ─────────────────────────────────────────────────────────────────────

@router.get("", response_model=list[DocumentResponse])
async def list_documents(
    current_user: CurrentUser,
    service: DocumentService = Depends(get_document_service),
):
    """Return all documents uploaded by the current user."""
    return await service.list_documents(current_user.id)


# ─── Ask ──────────────────────────────────────────────────────────────────────

@router.post("/ask", response_model=AskResponse)
async def ask_question(
    body: AskRequest,
    current_user: CurrentUser,
    service: DocumentService = Depends(get_document_service),
):
    """
    Ask a question about your uploaded documents.
    Optionally pass document_id to search a specific document.
    Leave it empty to search across all your documents.
    """
    answer, sources = await service.ask_question(
        question=body.question,
        user_id=current_user.id,
        document_id=body.document_id,
    )

    return AskResponse(
        answer=answer,
        sources=sources,
        document_id=body.document_id,
    )


# ─── Delete ───────────────────────────────────────────────────────────────────

@router.delete("/{document_id}")
async def delete_document(
    document_id: uuid.UUID,
    current_user: CurrentUser,
    service: DocumentService = Depends(get_document_service),
):
    """Delete a document and all its chunks from Qdrant."""
    await service.delete_document(document_id, current_user.id)
    return {"success": True, "message": "Document deleted"}