import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class DocumentResponse(BaseModel):
    id: uuid.UUID
    filename: str
    file_size: int
    status: str
    chunk_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class AskRequest(BaseModel):
    question: str
    document_id: Optional[uuid.UUID] = None  # None means search all documents


class AskResponse(BaseModel):
    answer: str
    sources: list[str]   # the chunks used to generate the answer
    document_id: Optional[uuid.UUID] = None