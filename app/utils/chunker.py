from typing import List
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def split_into_chunks(text: str) -> List[str]:
    """
    Splits a long text into overlapping chunks.

    Why overlapping? If an answer sits at the boundary between
    two chunks, overlap ensures it is fully captured in at least
    one chunk.
    """
    if not text or not text.strip():
        return []

    words = text.split()
    chunks = []
    start = 0

    while start < len(words):
        end = start + settings.CHUNK_SIZE
        chunk_words = words[start:end]
        chunk = " ".join(chunk_words)

        if chunk.strip():
            chunks.append(chunk)

        # Move forward by CHUNK_SIZE minus overlap
        # This creates the overlap between consecutive chunks
        start += settings.CHUNK_SIZE - settings.CHUNK_OVERLAP

    logger.info(
        "text_chunked",
        total_words=len(words),
        total_chunks=len(chunks),
        chunk_size=settings.CHUNK_SIZE,
        overlap=settings.CHUNK_OVERLAP,
    )

    return chunks