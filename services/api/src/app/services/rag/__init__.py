"""
KrishiNet-BRICS - RAG Knowledge Base Package.
"""

from app.services.rag.chunking import TextChunk, chunk_document, extract_frontmatter
from app.services.rag.embedding import EmbeddingService, embedding_service
from app.services.rag.ingestion import IngestionService, ingestion_service
from app.services.rag.retrieval import HybridRetriever, MultiQueryBuilder, retrieval_service

__all__ = [
    "TextChunk",
    "chunk_document",
    "extract_frontmatter",
    "EmbeddingService",
    "embedding_service",
    "IngestionService",
    "ingestion_service",
    "HybridRetriever",
    "MultiQueryBuilder",
    "retrieval_service",
]
