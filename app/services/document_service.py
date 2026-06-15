import uuid
from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException, BadRequestException
from app.core.logging import get_logger
from app.models.document import Document
from app.services.rag_service import RAGService
from app.utils.pdf_parser import extract_text_from_pdf
from qdrant_client import QdrantClient

logger = get_logger(__name__)


class DocumentService:

    def __init__(self, db: AsyncSession, qdrant: QdrantClient):
        self.db = db
        self.rag = RAGService(qdrant)

    # ─── Upload and process ───────────────────────────────────────────────

    async def upload_document(
        self,
        user_id: uuid.UUID,
        filename: str,
        file_bytes: bytes,
    ) -> Document:
        """
        Full upload pipeline:
        1. Validate the file
        2. Save document record to PostgreSQL with status=processing
        3. Extract text from PDF
        4. Index chunks in Qdrant
        5. Update status to ready
        """

        # Step 1 — validate
        if not filename.lower().endswith(".pdf"):
            raise BadRequestException("Only PDF files are supported")

        if len(file_bytes) > 10 * 1024 * 1024:  # 10MB limit
            raise BadRequestException("File size must be under 10MB")

        # Step 2 — save to PostgreSQL with processing status
        document = Document(
            user_id=user_id,
            filename=filename,
            file_size=len(file_bytes),
            status="processing",
        )
        self.db.add(document)
        await self.db.flush()  # get the UUID before committing

        logger.info(
            "document_upload_started",
            document_id=str(document.id),
            filename=filename,
            file_size=len(file_bytes),
        )

        try:
            # Step 3 — extract text from PDF
            text = extract_text_from_pdf(file_bytes)

            if not text.strip():
                raise BadRequestException(
                    "Could not extract text from this PDF. "
                    "It may be a scanned image PDF."
                )

            # Step 4 — index in Qdrant
            chunk_count = self.rag.index_document(
                document_id=document.id,
                user_id=user_id,
                text=text,
            )

            # Step 5 — update status to ready
            document.status = "ready"
            document.chunk_count = chunk_count
            await self.db.flush()

            logger.info(
                "document_upload_complete",
                document_id=str(document.id),
                chunks=chunk_count,
            )

        except Exception as e:
            # If anything fails, mark as failed with the error message
            document.status = "failed"
            document.error_message = str(e)
            await self.db.flush()

            logger.error(
                "document_upload_failed",
                document_id=str(document.id),
                error=str(e),
            )
            raise

        return document

    # ─── List documents ───────────────────────────────────────────────────

    async def list_documents(self, user_id: uuid.UUID) -> List[Document]:
        """Return all documents belonging to this user."""
        result = await self.db.execute(
            select(Document)
            .where(Document.user_id == user_id)
            .order_by(Document.created_at.desc())
        )
        return result.scalars().all()

    # ─── Get single document ──────────────────────────────────────────────

    async def get_document(
        self,
        document_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Document:
        """
        Get a document by ID.
        Checks ownership — users can only access their own documents.
        """
        result = await self.db.execute(
            select(Document).where(
                Document.id == document_id,
                Document.user_id == user_id,
            )
        )
        document = result.scalar_one_or_none()

        if not document:
            raise NotFoundException("Document")

        return document

    # ─── Ask a question ───────────────────────────────────────────────────

    async def ask_question(
        self,
        question: str,
        user_id: uuid.UUID,
        document_id: uuid.UUID | None = None,
    ) -> tuple[str, list[str]]:
        """
        Ask a question against uploaded documents.
        If document_id is given, search only that document.
        Otherwise search all documents belonging to this user.
        """
        if not question.strip():
            raise BadRequestException("Question cannot be empty")

        if len(question) > 1000:
            raise BadRequestException("Question must be under 1000 characters")

        # If specific document requested, verify ownership first
        if document_id:
            await self.get_document(document_id, user_id)

        answer, sources = self.rag.ask(
            question=question,
            user_id=user_id,
            document_id=document_id,
        )

        logger.info(
            "question_answered",
            user_id=str(user_id),
            question=question[:50],
        )

        return answer, sources

    # ─── Delete document ──────────────────────────────────────────────────

    async def delete_document(
        self,
        document_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        """
        Delete a document from PostgreSQL and its chunks from Qdrant.
        """
        document = await self.get_document(document_id, user_id)

        # Delete chunks from Qdrant by filtering on document_id
        from qdrant_client.models import Filter, FieldCondition, MatchValue
        self.rag.qdrant.delete(
            collection_name="documents",
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="document_id",
                        match=MatchValue(value=str(document_id)),
                    )
                ]
            ),
        )

        # Delete from PostgreSQL
        await self.db.delete(document)
        await self.db.flush()

        logger.info(
            "document_deleted",
            document_id=str(document_id),
            user_id=str(user_id),
        )