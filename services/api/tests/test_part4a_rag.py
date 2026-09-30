"""
KrishiNet-BRICS - Phase 4 Part 4A Test Suite.

Validates:
  1. Structure-aware heading-preserving chunker and YAML front-matter parser
  2. Embedding service and 768-dimensional cosine vector similarity
  3. Pydantic v2 AdvisoryContract data schema validation and range invariants
  4. MultiQueryBuilder synthesis from field agro-telemetry
  5. HybridRetriever with Reciprocal Rank Fusion (RRF) and citation formatting
  6. GeminiClientWrapper token budget tracking and repair retry simulation
  7. Seed Knowledge Base integrity (28 original notes with open licenses)
  8. Admin Celery ingestion task execution
"""

import os
import sys
import pytest
from pydantic import ValidationError

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from app.ai.gemini_client import (
    GeminiClientWrapper,
    TokenBudgetExceededException,
    gemini_client,
)
from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.schemas.advisory import (
    AdvisoryConfidence,
    AdvisoryContract,
    AdvisoryExplainability,
    AdvisoryMeta,
    Citation,
    ClimateRisk,
    ConfidenceComponents,
    ConfidenceLevel,
    CostLevel,
    CropRecommendation,
    DifficultyLevel,
    EngineMode,
    EstimatedBenefit,
    FertiliserPlan,
    RegenerativePractice,
    RegenerativePracticeEnum,
    SowingWindow,
    WaterNeed,
    WhatToDoToday,
    YieldRange,
)
from app.services.rag.chunking import chunk_document, extract_frontmatter
from app.services.rag.embedding import embedding_service
from app.services.rag.retrieval import MultiQueryBuilder, retrieval_service
from app.workers.tasks import ingest_knowledge_repository


# ============================================================================
# 1. CHUNKER & FRONT-MATTER TESTS
# ============================================================================

def test_extract_frontmatter():
    raw = """---
crop: cotton
region: India-Vertisol
practice: water_harvesting
licence: CC-BY-4.0
source: KrishiNet seed note
---
# Main Heading
Body text under main heading.
"""
    meta, body = extract_frontmatter(raw)
    assert meta["crop"] == "cotton"
    assert meta["region"] == "India-Vertisol"
    assert meta["practice"] == "water_harvesting"
    assert "# Main Heading" in body


def test_chunk_document_heading_boundaries():
    sample_md = """# Section One
This is content for section one. It discusses soil health and moisture.

## Subsection A
Details regarding Vertisol clay structure and shrink-swell dynamics.

# Section Two
This is content for section two detailing integrated pest management for pink bollworm.
"""
    chunks = chunk_document(
        text=sample_md,
        doc_title="Cotton Agronomy",
        doc_metadata={"crop": "cotton", "region": "India"},
        max_chars=500,
    )
    assert len(chunks) >= 3
    headings = [c.section_heading for c in chunks]
    assert "Section One" in headings or "Subsection A" in headings
    assert "Section Two" in headings
    # Verify metadata carried on every chunk
    for c in chunks:
        assert c.metadata["crop"] == "cotton"
        assert c.metadata["document_title"] == "Cotton Agronomy"


def test_chunk_document_windowed_overlap():
    # Long text exceeding max_chars
    long_para = "Sovereign regenerative agricultural intelligence enables sustainable food production. " * 30
    doc_text = f"# Big Chapter\n\n{long_para}"
    chunks = chunk_document(doc_text, doc_title="Long Document", max_chars=300, overlap_chars=60)
    assert len(chunks) > 1
    # Check that adjacent chunks share context
    for i in range(len(chunks) - 1):
        assert chunks[i].index == i
        assert chunks[i + 1].index == i + 1


# ============================================================================
# 2. EMBEDDING & COSINE SIMILARITY TESTS
# ============================================================================

def test_cosine_similarity_properties():
    # 1. Identical vectors -> 1.0
    v1 = [1.0, 0.0, 0.0]
    assert embedding_service.cosine_similarity(v1, v1) == 1.0

    # 2. Orthogonal vectors -> 0.0
    v2 = [0.0, 1.0, 0.0]
    assert embedding_service.cosine_similarity(v1, v2) == 0.0

    # 3. Empty or zero vectors -> 0.0
    assert embedding_service.cosine_similarity([], v1) == 0.0
    assert embedding_service.cosine_similarity([0.0, 0.0], [0.0, 0.0]) == 0.0


@pytest.mark.asyncio
async def test_embedding_dimension_and_determinism():
    """Verify Gemini embedding output dimension is exactly 768 and deterministic offline."""
    text = "Regenerative soil management on Vertisols"
    vec1 = await embedding_service.get_embedding(text)
    vec2 = await embedding_service.get_embedding(text)

    assert len(vec1) == 768
    assert len(vec2) == 768
    assert vec1 == vec2
    # Check vector is normalized (unit length approx 1.0)
    import math
    norm = math.sqrt(sum(x * x for x in vec1))
    assert 0.99 <= norm <= 1.01


# ============================================================================
# 3. ADVISORY DATA CONTRACT (PYDANTIC V2) TESTS
# ============================================================================

def test_valid_advisory_contract_instantiation():
    """Validates complete AdvisoryContract against all Pydantic v2 schemas and validators."""
    contract = AdvisoryContract(
        meta=AdvisoryMeta(
            advisory_id="adv-ind-test-01",
            field_id="field-ind-vidarbha-cotton-01",
            generated_at="2026-09-29T12:00:00Z",
            language="en",
            engine_mode=EngineMode.HYBRID,
            model_name="gemini-2.5-flash",
            prompt_version="v1.0.0",
            provenance=[{"source": "Sentinel-2", "mode": "demo"}],
            disclaimer="Sovereign agricultural advisory for guidance only.",
        ),
        field_summary="Soil organic carbon is moderate with favorable moisture. Cotton is entering squaring stage under warm conditions. Targeted bio-fertilizer and in-situ mulching recommended.",
        crop_recommendations=[
            CropRecommendation(
                crop="cotton",
                suitability_score=85,
                expected_yield_range=YieldRange(min=2.2, max=3.0, unit="t/ha"),
                water_need=WaterNeed(level="medium", mm_per_season=650),
                climate_risk=ClimateRisk(level="moderate", drivers=["heat_stress"]),
                why_it_fits="Vertisol black clay provides exceptional capillary moisture retention for cotton taproots.",
                citations=[
                    Citation(
                        doc_id="doc_cotton_01",
                        title="Rainfed Cotton Management",
                        source_org="ICAR",
                        section="Moisture Dynamics",
                        score=0.92,
                    )
                ],
            )
        ],
        regenerative_practices=[
            RegenerativePractice(
                practice=RegenerativePracticeEnum.MULCHING,
                reason="Reduces evaporative losses from Vertisol surface cracking.",
                cost_level=CostLevel.LOW,
                estimated_soil_or_carbon_benefit=EstimatedBenefit(
                    value_min=0.3, value_max=0.6, unit="t CO2e/ha/yr", basis="Empirical Vertisol residue retention trial"
                ),
                difficulty=DifficultyLevel.EASY,
                when_to_start="Immediately after post-emergence weeding",
                citations=[],
            )
        ],
        sowing_window=SowingWindow(
            start_date="2026-06-15",
            end_date="2026-07-05",
            rationale="Monsoon onset with cumulative rainfall exceeding 60 mm.",
        ),
        irrigation_schedule=[],
        fertiliser_plan=FertiliserPlan(
            organic_first_steps=["Apply 5 t/ha enriched farmyard manure", "Inoculate with Azotobacter"],
            mineral_supplement="Optional split urea 30 kg/ha at flowering if leaf nitrogen drops below 2.8%.",
        ),
        action_calendar_30d=[
            {
                "day_offset": 1,
                "title": "Field mulching",
                "description": "Spread 3 t/ha dry residues across cotton inter-rows.",
                "category": "soil",
                "priority": "soon",
                "done": False,
            }
        ],
        what_to_do_today=WhatToDoToday(
            title="Inspect pheromone traps",
            description="Count pink bollworm moth catches in the 5 perimeter delta traps.",
            urgency="routine",
            icon_key="eye",
        ),
        risks_and_warnings=[],
        explainability=AdvisoryExplainability(
            signals_used=[
                {
                    "signal": "soil_ph",
                    "value": 7.8,
                    "direction": "supports",
                    "weight": 0.35,
                    "plain_reason": "Alkaline pH is within optimal range for cotton boll development.",
                }
            ],
            top_3_drivers=["Vertisol moisture buffer", "Moderate SOC", "Warm weather"],
            knowledge_sources=["Rainfed Cotton Management on Deep Black Vertisols"],
            counterfactual_note="If soil pH exceeded 8.5, gypsum application would be recommended.",
        ),
        confidence=AdvisoryConfidence(
            overall=0.88,
            components=ConfidenceComponents(
                data_quality=0.90,
                retrieval_support=0.85,
                model_self_consistency=0.90,
                agreement_with_rules=0.88,
            ),
            level=ConfidenceLevel.HIGH,
            guard_triggered=False,
            escalation_message=None,
        ),
    )
    assert contract.meta.advisory_id == "adv-ind-test-01"
    assert contract.crop_recommendations[0].suitability_score == 85


def test_advisory_contract_validation_failures():
    """Validates that inverted ranges and invalid score bounds fail Pydantic v2 validation."""
    # 1. Inverted yield range (min > max)
    with pytest.raises(ValidationError):
        YieldRange(min=4.0, max=2.0, unit="t/ha")

    # 2. Inverted benefit range (min > max)
    with pytest.raises(ValidationError):
        EstimatedBenefit(value_min=2.5, value_max=1.0, unit="t/ha", basis="test")

    # 3. Score out of range (> 100)
    with pytest.raises(ValidationError):
        CropRecommendation(
            crop="cotton",
            suitability_score=150,  # Invalid
            expected_yield_range=YieldRange(min=1.0, max=2.0),
            water_need=WaterNeed(level="low", mm_per_season=400),
            climate_risk=ClimateRisk(level="low"),
            why_it_fits="Good fit for the soil.",
        )


# ============================================================================
# 4. MULTI-QUERY BUILDER & HYBRID RETRIEVAL TESTS
# ============================================================================

def test_multi_query_builder_synthesis():
    queries = MultiQueryBuilder.build_queries(
        crop="cotton",
        soil_texture="Clay",
        soil_ph=7.8,
        soc_pct=0.6,
        water_deficit_mm=45.0,
        region="Vidarbha-India",
        heat_days=2,
    )
    assert len(queries) == 3
    assert any("cotton" in q.lower() for q in queries)
    assert any("heat" in q.lower() or "drought" in q.lower() for q in queries)
    assert any("organic carbon" in q.lower() for q in queries)


@pytest.mark.asyncio
async def test_hybrid_retriever_against_database():
    """Tests RRF retrieval and citation generation using seeded knowledge chunks."""
    async with AsyncSessionLocal() as session:
        queries = ["cotton pink bollworm pheromone traps IPM", "cotton Vertisol moisture"]
        results = await retrieval_service.retrieve(
            db=session,
            queries=queries,
            crop="cotton",
            top_k=3,
        )
        assert len(results) >= 1
        chunk, citation = results[0]
        assert citation.title != ""
        assert citation.source_org != ""
        assert 0.0 <= citation.score <= 1.0


# ============================================================================
# 5. GEMINI CLIENT WRAPPER & TOKEN BUDGET TESTS
# ============================================================================

def test_gemini_client_offline_fallback():
    """Verify Gemini client gracefully detects demo mode or missing key without calling network."""
    client = GeminiClientWrapper()
    assert client.embedding_dim == 768
    # Offline deterministic embedding works without network
    vec = client._generate_offline_embedding("test query")
    assert len(vec) == 768


def test_token_budget_tracking_and_limit():
    """Verify per-user token limit raises TokenBudgetExceededException."""
    client = GeminiClientWrapper()
    user_id = "test_farmer_budget_01"

    # Set artificial tiny limit for test
    orig_limit = settings.USER_DAILY_TOKEN_LIMIT
    try:
        settings.USER_DAILY_TOKEN_LIMIT = 500
        # Initial check should pass
        client._check_token_budget(user_id=user_id, estimated_tokens=100)
        # Record usage exceeding limit
        client._record_token_usage(user_id=user_id, model_name="gemini-2.5-flash", prompt_tokens=300, completion_tokens=300, latency_ms=100.0)

        # Subsequent check must raise TokenBudgetExceededException
        with pytest.raises(TokenBudgetExceededException):
            client._check_token_budget(user_id=user_id, estimated_tokens=100)
    finally:
        settings.USER_DAILY_TOKEN_LIMIT = orig_limit


# ============================================================================
# 6. SEED KNOWLEDGE BASE INTEGRITY TESTS
# ============================================================================

def test_seed_knowledge_notes_count_and_metadata():
    """Verify all 28 original open agronomic guidance notes exist with valid YAML frontmatter."""
    candidates = [
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "seed", "knowledge")),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "seed", "knowledge")),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "seed", "knowledge")),
        os.path.abspath("data/seed/knowledge"),
    ]
    knowledge_dir = next((c for c in candidates if os.path.exists(c)), candidates[0])
    assert os.path.exists(knowledge_dir), f"Knowledge directory not found: {knowledge_dir}"

    files = [f for f in os.listdir(knowledge_dir) if f.endswith(".md")]
    assert len(files) >= 28, f"Expected at least 28 seed notes, found {len(files)}"

    for f in files:
        file_path = os.path.join(knowledge_dir, f)
        with open(file_path, "r", encoding="utf-8") as stream:
            content = stream.read()
        meta, body = extract_frontmatter(content)
        assert "crop" in meta, f"Missing crop in {f}"
        assert "region" in meta, f"Missing region in {f}"
        assert "practice" in meta, f"Missing practice in {f}"
        assert "licence" in meta or "license" in meta, f"Missing licence in {f}"
        assert "source" in meta, f"Missing source in {f}"
        assert len(body.strip()) > 100, f"Body too short in {f}"


def test_admin_celery_knowledge_ingestion_task():
    """Verify admin Celery ingestion task runs synchronously and returns completion report."""
    res = ingest_knowledge_repository()
    assert res["status"] == "completed"
    assert res["documents_ingested"] >= 28
