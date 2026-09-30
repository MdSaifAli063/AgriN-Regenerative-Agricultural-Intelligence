"""
KrishiNet-BRICS - Hybrid Agronomic RAG Retrieval Service.

Implements Reciprocal Rank Fusion (RRF) combining dense vector similarity
and sparse full-text search:
  - Multi-query synthesis from field telemetry
  - Vector cosine similarity + full-text token rank scoring
  - Metadata filtering (crop, region, language)
  - 2-stage retrieval: Top-8 RRF candidate pool -> Reranking -> Top-5 grounded chunks
  - Standardized Citation generation for advisory explainability
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.gemini_client import gemini_client
from app.models.advisory import KnowledgeChunk, KnowledgeDocument
from app.schemas.advisory import Citation
from app.services.rag.embedding import embedding_service

logger = logging.getLogger("krishinet.rag.retrieval")


class MultiQueryBuilder:
    """Generates targeted retrieval queries based on field agronomic indicators."""

    @staticmethod
    def build_queries(
        crop: str,
        soil_texture: str,
        soil_ph: float,
        soc_pct: float,
        water_deficit_mm: float,
        region: str,
        heat_days: int = 0,
    ) -> List[str]:
        queries = []

        # 1. Primary crop & regenerative system query
        queries.append(f"{crop} regenerative agriculture practices {soil_texture} soil {region}")

        # 2. Climate or stress-specific query
        if heat_days > 0 or water_deficit_mm > 20.0:
            queries.append(f"{crop} heat drought stress mitigation moisture conservation mulching {region}")
        else:
            queries.append(f"{crop} integrated pest management biological control and crop rotation")

        # 3. Soil restoration & fertility query
        if soil_ph < 6.0:
            queries.append(f"acidic soil liming organic carbon recovery cover crops {crop}")
        elif soil_ph > 7.5:
            queries.append(f"alkaline vertisol drainage gypsum soil organic carbon {crop}")
        elif soc_pct < 1.0:
            queries.append(f"low soil organic carbon biochar compost green manure {region}")
        else:
            queries.append(f"soil biological health fertility balancing organic fertilizers {crop}")

        return queries


class HybridRetriever:
    """Executes hybrid vector + full-text search with RRF fusion and reranking."""

    def __init__(self):
        self.rrf_k = 60

    @staticmethod
    def _text_match_score(query: str, text: str) -> float:
        """Token-level BM25-like overlap score for sparse retrieval."""
        q_tokens = set(re.findall(r"\w+", query.lower()))
        if not q_tokens:
            return 0.0

        t_tokens = re.findall(r"\w+", text.lower())
        if not t_tokens:
            return 0.0

        t_set = set(t_tokens)
        overlap = q_tokens.intersection(t_set)
        return len(overlap) / (len(q_tokens) + 0.1)

    async def retrieve(
        self,
        db: AsyncSession,
        queries: List[str],
        crop: Optional[str] = None,
        region: Optional[str] = None,
        top_k: int = 5,
    ) -> List[Tuple[KnowledgeChunk, Citation]]:
        """
        Executes hybrid search across knowledge base chunks using RRF and reranking.
        """
        # 1. Fetch active knowledge chunks from DB
        stmt = (
            select(KnowledgeChunk, KnowledgeDocument)
            .join(KnowledgeDocument, KnowledgeChunk.document_id == KnowledgeDocument.id)
        )
        res = await db.execute(stmt)
        rows = res.fetchall()

        if not rows:
            logger.info("No knowledge chunks found in database; using empty retrieval pool.")
            return []

        # 2. Score chunks across multi-queries using Vector + Text
        chunk_scores: Dict[str, Dict[str, Any]] = {}

        for query in queries:
            q_emb = await embedding_service.get_embedding(query, is_query=True)

            # Collect vector and text scores for each candidate
            vector_ranks: List[Tuple[float, str]] = []
            text_ranks: List[Tuple[float, str]] = []

            for chunk, doc in rows:
                cid = chunk.id
                # Metadata pre-filtering
                if crop and chunk.target_crop and chunk.target_crop.lower() != "general":
                    if crop.lower() not in chunk.target_crop.lower():
                        continue

                # Vector similarity
                c_emb = chunk.embedding
                if not c_emb:
                    c_emb = await embedding_service.get_embedding(chunk.content_text)
                sim = embedding_service.cosine_similarity(q_emb, c_emb)
                vector_ranks.append((sim, cid))

                # Sparse text overlap
                txt_score = self._text_match_score(query, chunk.content_text)
                text_ranks.append((txt_score, cid))

                if cid not in chunk_scores:
                    chunk_scores[cid] = {
                        "chunk": chunk,
                        "doc": doc,
                        "rrf_score": 0.0,
                        "best_sim": 0.0,
                    }

            # Sort and apply RRF
            vector_ranks.sort(key=lambda x: x[0], reverse=True)
            text_ranks.sort(key=lambda x: x[0], reverse=True)

            for rank, (sim, cid) in enumerate(vector_ranks):
                chunk_scores[cid]["rrf_score"] += 1.0 / (self.rrf_k + rank + 1)
                chunk_scores[cid]["best_sim"] = max(chunk_scores[cid]["best_sim"], sim)

            for rank, (score, cid) in enumerate(text_ranks):
                chunk_scores[cid]["rrf_score"] += 1.0 / (self.rrf_k + rank + 1)

        # 3. Take Top-8 Candidates from RRF fusion
        sorted_candidates = sorted(
            chunk_scores.values(),
            key=lambda x: x["rrf_score"],
            reverse=True,
        )[:8]

        # 4. Rerank Top-8 to select Top-K (default 5)
        reranked = await self._rerank(queries[0], sorted_candidates)
        final_pool = reranked[:top_k]

        # 5. Format Citations
        results = []
        for item in final_pool:
            c: KnowledgeChunk = item["chunk"]
            d: KnowledgeDocument = item["doc"]
            score = round(min(1.0, item.get("final_score", item["best_sim"])), 3)

            citation = Citation(
                doc_id=d.id,
                title=d.title,
                source_org=d.publishing_agency,
                section=c.metadata_json.get("section_heading", "Agronomic Guidance"),
                url=d.source_url or "https://krishinet.brics.int/knowledge",
                score=score,
            )
            results.append((c, citation))

        return results

    async def _rerank(
        self,
        primary_query: str,
        candidates: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Reranks candidate chunks with heuristic agronomic relevance or Gemini scoring."""
        if not candidates:
            return []

        # If Gemini is available and not in demo mode, perform structured scoring
        if gemini_client.is_available:
            try:
                prompt = (
                    f"You are an agronomy relevance scorer. Given the farmer's primary query:\n"
                    f"'{primary_query}'\n\n"
                    f"Rate the relevance of each candidate text from 0.0 to 1.0:\n"
                )
                for idx, c in enumerate(candidates):
                    prompt += f"[{idx}] {c['chunk'].content_text[:300]}\n"

                prompt += "\nOutput JSON: {\"scores\": [float for each item]}"
                res = await gemini_client.generate_text(prompt=prompt, temperature=0.1)
                clean = res.replace("```json", "").replace("```", "").strip()
                import json
                scores = json.loads(clean).get("scores", [])
                for i, score in enumerate(scores):
                    if i < len(candidates):
                        candidates[i]["final_score"] = float(score)
                candidates.sort(key=lambda x: x.get("final_score", 0.0), reverse=True)
                return candidates
            except Exception as e:
                logger.warning(f"Gemini reranking failed ({e}); falling back to heuristic scoring.")

        # Deterministic Heuristic Reranker
        for c in candidates:
            base_sim = c["best_sim"]
            rrf = c["rrf_score"]
            # Boost if chunk contains primary keywords
            txt = c["chunk"].content_text.lower()
            boost = 0.0
            if "regenerative" in txt or "organic" in txt:
                boost += 0.05
            if "soil" in txt:
                boost += 0.05
            if "moisture" in txt or "irrigation" in txt:
                boost += 0.05

            c["final_score"] = min(1.0, base_sim * 0.7 + rrf * 5.0 + boost)

        candidates.sort(key=lambda x: x.get("final_score", 0.0), reverse=True)
        return candidates


retrieval_service = HybridRetriever()
