import uuid
from typing import List, Tuple
import google.generativeai as genai
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, Filter, FieldCondition, MatchValue

from app.core.config import settings
from app.core.logging import get_logger
from app.utils.chunker import split_into_chunks

logger = get_logger(__name__)

genai.configure(api_key=settings.GEMINI_API_KEY)


class RAGService:

    def __init__(self, qdrant: QdrantClient):
        self.qdrant = qdrant
        self.chat_model = genai.GenerativeModel("models/gemini-2.0-flash-lite")
    def get_embedding(self, text: str) -> List[float]:
        result = genai.embed_content(
            model="models/gemini-embedding-001",
            content=text,
            task_type="retrieval_document",
        )
        return result["embedding"]

    def index_document(
        self,
        document_id: uuid.UUID,
        user_id: uuid.UUID,
        text: str,
    ) -> int:
        chunks = split_into_chunks(text)

        if not chunks:
            raise ValueError("No text could be extracted from this document")

        points = []
        for i, chunk in enumerate(chunks):
            embedding = self.get_embedding(chunk)
            point = PointStruct(
                id=str(uuid.uuid4()),
                vector=embedding,
                payload={
                    "document_id": str(document_id),
                    "user_id": str(user_id),
                    "chunk_index": i,
                    "text": chunk,
                },
            )
            points.append(point)

        self.qdrant.upsert(
            collection_name=settings.QDRANT_COLLECTION_NAME,
            points=points,
        )

        logger.info(
            "document_indexed",
            document_id=str(document_id),
            chunks=len(chunks),
        )

        return len(chunks)

    def search_chunks(
        self,
        question: str,
        user_id: uuid.UUID,
        document_id: uuid.UUID | None = None,
        top_k: int = 5,
    ) -> List[str]:
        result = genai.embed_content(
            model="models/gemini-embedding-001",
            content=question,
            task_type="retrieval_query",
        )
        question_embedding = result["embedding"]

        must_conditions = [
            FieldCondition(
                key="user_id",
                match=MatchValue(value=str(user_id)),
            )
        ]

        if document_id:
            must_conditions.append(
                FieldCondition(
                    key="document_id",
                    match=MatchValue(value=str(document_id)),
                )
            )

        search_filter = Filter(must=must_conditions)

        results = self.qdrant.search(
            collection_name=settings.QDRANT_COLLECTION_NAME,
            query_vector=question_embedding,
            query_filter=search_filter,
            limit=top_k,
        )

        chunks = [r.payload["text"] for r in results]

        logger.info(
            "chunks_retrieved",
            question=question[:50],
            chunks_found=len(chunks),
        )

        return chunks

    def generate_answer(
        self,
        question: str,
        chunks: List[str],
    ) -> str:
        if not chunks:
            return "I could not find relevant information in your documents to answer this question."

        context = "\n\n---\n\n".join(chunks)

        prompt = f"""You are a helpful assistant that answers questions based strictly on the provided document excerpts.

Only use the information from the excerpts below to answer the question.
If the answer is not in the excerpts, say "I could not find this information in the uploaded documents."
Be concise and precise.

Document excerpts:
{context}

Question: {question}

Answer:"""

        response = self.chat_model.generate_content(prompt)
        return response.text.strip()

    def ask(
        self,
        question: str,
        user_id: uuid.UUID,
        document_id: uuid.UUID | None = None,
    ) -> Tuple[str, List[str]]:
        chunks = self.search_chunks(question, user_id, document_id)
        answer = self.generate_answer(question, chunks)
        return answer, chunks