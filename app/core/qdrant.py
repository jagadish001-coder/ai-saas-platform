from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

client = QdrantClient(
    url=settings.QDRANT_URL,
    api_key=settings.QDRANT_API_KEY,
)


def get_qdrant() -> QdrantClient:
    return client


async def init_collection() -> None:
    collections = client.get_collections().collections
    names = [c.name for c in collections]

    if settings.QDRANT_COLLECTION_NAME not in names:
        client.create_collection(
            collection_name=settings.QDRANT_COLLECTION_NAME,
            vectors_config=VectorParams(
                size=3072,
                distance=Distance.COSINE,
            ),
        )
        logger.info("qdrant_collection_created", collection=settings.QDRANT_COLLECTION_NAME)
    else:
        logger.info("qdrant_collection_exists", collection=settings.QDRANT_COLLECTION_NAME)