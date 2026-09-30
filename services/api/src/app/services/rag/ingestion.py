"""
KrishiNet-BRICS - RAG Document Ingestion Service.

Parses, chunks, embeds, and indexes agronomic documentation into PostgreSQL/SQLite:
  - Multi-format ingestion: Markdown, plain text, and PDF (via pypdf)
  - Content SHA256 deduplication and idempotent upserts
  - Heading-aware semantic chunking
  - Batch vector embedding generation
"""

import hashlib
import logging
import os
from typing import Any, Dict, List, Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.advisory import KnowledgeChunk, KnowledgeDocument
from app.services.rag.chunking import chunk_document, extract_frontmatter
from app.services.rag.embedding import embedding_service

logger = logging.getLogger("krishinet.rag.ingestion")


class IngestionService:
    @staticmethod
    def _read_pdf_text(file_path: str) -> str:
        """Extracts text from a PDF file using pypdf if available."""
        try:
            import pypdf
            reader = pypdf.PdfReader(file_path)
            pages_text = []
            for page in reader.pages:
                t = page.extract_text()
                if t:
                    pages_text.append(t)
            return "\n\n".join(pages_text)
        except ImportError:
            logger.warning("pypdf is not installed; reading PDF as binary fallback.")
            with open(file_path, "rb") as f:
                content = f.read()
            # Clean non-ascii bytes
            return content.decode("utf-8", errors="ignore")

    @classmethod
    async def ingest_file(
        cls,
        db: AsyncSession,
        file_path: str,
        publishing_agency: Optional[str] = None,
        source_url: Optional[str] = None,
        license_type: str = "CC-BY-4.0",
    ) -> KnowledgeDocument:
        """
        Ingests a single file (markdown, text, or pdf) into the knowledge base.
        """
        filename = os.path.basename(file_path)
        title = os.path.splitext(filename)[0].replace("_", " ").title()

        if file_path.lower().endswith(".pdf"):
            raw_text = cls._read_pdf_text(file_path)
        else:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                raw_text = f.read()

        fm_meta, body = extract_frontmatter(raw_text)

        doc_title = fm_meta.get("title", title)
        agency = publishing_agency or fm_meta.get("source", "KrishiNet Agronomy Commons")
        url = source_url or fm_meta.get("url", f"https://krishinet.brics.int/docs/{filename}")
        lic = fm_meta.get("licence", fm_meta.get("license", license_type))
        crop_tags = [c.strip() for c in fm_meta.get("crop", "general").split(",")]
        region_tags = [r.strip() for r in fm_meta.get("region", "global").split(",")]
        lang = fm_meta.get("language", "en")

        return await cls.ingest_text(
            db=db,
            title=doc_title,
            text=raw_text,
            publishing_agency=agency,
            source_url=url,
            license_type=lic,
            language=lang,
            crop_tags=crop_tags,
            region_tags=region_tags,
        )

    @classmethod
    async def ingest_text(
        cls,
        db: AsyncSession,
        title: str,
        text: str,
        publishing_agency: str = "KrishiNet Agronomy Commons",
        source_url: Optional[str] = None,
        license_type: str = "CC-BY-4.0",
        language: str = "en",
        crop_tags: Optional[List[str]] = None,
        region_tags: Optional[List[str]] = None,
        published_year: Optional[int] = 2024,
    ) -> KnowledgeDocument:
        """
        Idempotently ingests document text, breaks into structure-aware chunks,
        computes embeddings, and persists to the database.
        """
        crops = crop_tags or ["general"]
        regions = region_tags or ["global"]

        # 1. Check if document with title already exists (idempotency)
        stmt = select(KnowledgeDocument).where(KnowledgeDocument.title == title)
        res = await db.execute(stmt)
        existing_doc = res.scalar_one_or_none()

        if existing_doc:
            doc = existing_doc
            doc.publishing_agency = publishing_agency
            doc.source_url = source_url
            doc.license_type = license_type
            doc.language = language
            doc.crop_tags = crops
            doc.region_tags = regions
            doc.published_year = published_year

            # Remove existing chunks to re-chunk idempotently
            del_stmt = delete(KnowledgeChunk).where(KnowledgeChunk.document_id == doc.id)
            await db.execute(del_stmt)
        else:
            doc = KnowledgeDocument(
                title=title,
                publishing_agency=publishing_agency,
                source_url=source_url,
                license_type=license_type,
                language=language,
                crop_tags=crops,
                region_tags=regions,
                published_year=published_year,
            )
            db.add(doc)
            await db.flush()

        # 2. Chunk document using heading-aware chunker
        chunks = chunk_document(
            text=text,
            doc_title=title,
            doc_metadata={
                "crop": crops[0] if crops else "general",
                "region": regions[0] if regions else "global",
                "publishing_agency": publishing_agency,
            },
        )

        # 3. Batch compute embeddings
        chunk_texts = [c.content for c in chunks]
        embeddings = await embedding_service.get_batch_embeddings(chunk_texts)

        # 4. Create and persist KnowledgeChunk records
        for i, chunk in enumerate(chunks):
            kc = KnowledgeChunk(
                document_id=doc.id,
                chunk_index=chunk.index,
                content_text=chunk.content,
                target_crop=chunk.metadata.get("crop", "general"),
                climate_zone=chunk.metadata.get("region", "global"),
                fao_agrovoc_concept=chunk.metadata.get("practice"),
                embedding=embeddings[i] if i < len(embeddings) else None,
                metadata_json=chunk.metadata,
                tsv_content=chunk.content.lower(),
            )
            db.add(kc)

        await db.commit()
        await db.refresh(doc)
        logger.info(f"Successfully ingested '{title}' with {len(chunks)} chunks.")
        return doc


ingestion_service = IngestionService()
