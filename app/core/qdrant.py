from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Single client instance reused across all requests
client = QdrantClient(url=settings.QDRANT_URL)


def get_qdrant() -> QdrantClient:
    """Return the Qdrant client. Used as a FastAPI dependency."""
    return client


async def init_collection() -> None:
    """Create the documents collection if it does not exist yet.
    Called once at app startup."""
    collections = client.get_collections().collections
    names = [c.name for c in collections]

    if settings.QDRANT_COLLECTION_NAME not in names:
        client.create_collection(
            collection_name=settings.QDRANT_COLLECTION_NAME,
            vectors_config=VectorParams(
                size=3072,        # geminI text-embedding-3-small output size
                distance=Distance.COSINE,  # measure similarity by angle
            ),
        )
        logger.info(
            "qdrant_collection_created",
            collection=settings.QDRANT_COLLECTION_NAME,
        )
    else:
        logger.info(
            "qdrant_collection_exists",
            collection=settings.QDRANT_COLLECTION_NAME,
        )