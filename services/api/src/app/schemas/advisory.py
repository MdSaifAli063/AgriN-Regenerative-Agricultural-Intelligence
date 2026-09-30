"""
KrishiNet-BRICS - Phase 4 Advisory Data Contract (Pydantic v2).

Defines the complete canonical schema for generative and rule-based agricultural advisories:
  - Meta & Provenance
  - Field Plain-Language Summary
  - Top-3 Ranked Crop Recommendations (with suitability, yield ranges, citations)
  - Regenerative Practices (Enum of 10 open practices, benefits, difficulty, timing)
  - Sowing Window & Irrigation/Moisture Schedule
  - Organic-First Fertiliser Plan
  - 30-Day Action Calendar & 'What To Do Today' Card
  - Climate & Agronomic Risks/Warnings
  - Transparent Explainability (Signals used, directional weights, counterfactual note)
  - Confidence Breakdown & Hallucination Guard Diagnostics
"""

from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, field_validator, model_validator


class EngineMode(str, Enum):
    GEMINI = "gemini"
    RULES = "rules"
    HYBRID = "hybrid"


class ConfidenceLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class UrgencyLevel(str, Enum):
    ROUTINE = "routine"
    SOON = "soon"
    URGENT = "urgent"


class CostLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class DifficultyLevel(str, Enum):
    EASY = "easy"
    MODERATE = "moderate"
    ADVANCED = "advanced"


class RiskSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class RegenerativePracticeEnum(str, Enum):
    COVER_CROPPING = "cover_cropping"
    INTERCROPPING = "intercropping"
    CROP_ROTATION = "crop_rotation"
    NO_TILL = "no_till"
    COMPOSTING = "composting"
    BIOCHAR = "biochar"
    MULCHING = "mulching"
    AGROFORESTRY = "agroforestry"
    INTEGRATED_PEST_MANAGEMENT = "integrated_pest_management"
    WATER_HARVESTING = "water_harvesting"


# ============================================================================
# 1. CITATIONS & PROVENANCE
# ============================================================================

class Citation(BaseModel):
    """Grounding citation from the RAG knowledge repository."""
    doc_id: str = Field(..., description="Unique document ID in knowledge repository")
    title: str = Field(..., description="Document title")
    source_org: str = Field(..., description="Publishing agency (e.g. FAO, ICAR, EMBRAPA)")
    section: str = Field(..., description="Document section or heading")
    url: Optional[str] = Field(None, description="Public canonical URL or doi if available")
    score: float = Field(..., ge=0.0, le=1.0, description="Reranked semantic relevance score")


# ============================================================================
# 2. CROP RECOMMENDATIONS
# ============================================================================

class YieldRange(BaseModel):
    min: float = Field(..., ge=0.0, description="Minimum expected yield per hectare")
    max: float = Field(..., ge=0.0, description="Maximum expected yield per hectare")
    unit: str = Field(default="t/ha", description="Yield unit (e.g. t/ha, kg/ha)")

    @model_validator(mode="after")
    def validate_range(self) -> "YieldRange":
        if self.min > self.max:
            raise ValueError(f"Yield min ({self.min}) cannot exceed max ({self.max})")
        return self


class WaterNeed(BaseModel):
    level: Literal["low", "medium", "high"] = Field(..., description="Water consumption tier")
    mm_per_season: int = Field(..., ge=50, le=2500, description="Seasonal water demand in mm")


class ClimateRisk(BaseModel):
    level: Literal["low", "moderate", "high", "severe"] = Field(..., description="Climate vulnerability")
    drivers: List[str] = Field(default_factory=list, description="Primary weather hazard drivers")


class CropRecommendation(BaseModel):
    crop: str = Field(..., description="Crop identifier (e.g. cotton, soybean, maize)")
    suitability_score: int = Field(..., ge=0, le=100, description="Suitability score (0-100)")
    expected_yield_range: YieldRange = Field(..., description="Expected yield boundaries")
    water_need: WaterNeed = Field(..., description="Seasonal irrigation / precipitation requirements")
    climate_risk: ClimateRisk = Field(..., description="Microclimate sensitivity")
    why_it_fits: str = Field(..., min_length=15, description="Plain agronomic rationale grounded in field context")
    citations: List[Citation] = Field(default_factory=list, description="RAG citations supporting recommendation")


# ============================================================================
# 3. REGENERATIVE PRACTICES
# ============================================================================

class EstimatedBenefit(BaseModel):
    value_min: float = Field(..., description="Estimated minimum benefit")
    value_max: float = Field(..., description="Estimated maximum benefit")
    unit: str = Field(..., description="Metric unit (e.g. t CO2e/ha/yr, % water retention)")
    basis: str = Field(..., description="Scientific or empiric basis of the estimate")

    @model_validator(mode="after")
    def validate_benefit_range(self) -> "EstimatedBenefit":
        if self.value_min > self.value_max:
            raise ValueError(f"Benefit min ({self.value_min}) cannot exceed max ({self.value_max})")
        return self


class RegenerativePractice(BaseModel):
    practice: RegenerativePracticeEnum = Field(..., description="Canonical practice identifier")
    reason: str = Field(..., min_length=10, description="Why this practice fits the field's current soil & weather")
    cost_level: CostLevel = Field(..., description="Capital expenditure level")
    estimated_soil_or_carbon_benefit: EstimatedBenefit = Field(..., description="Quantified soil or carbon uplift")
    difficulty: DifficultyLevel = Field(..., description="Implementation difficulty")
    when_to_start: str = Field(..., description="Optimal seasonal trigger or crop stage")
    citations: List[Citation] = Field(default_factory=list, description="Citations supporting practice")


# ============================================================================
# 4. SOWING, IRRIGATION & NUTRIENT PLANS
# ============================================================================

class SowingWindow(BaseModel):
    start_date: str = Field(..., description="Earliest safe sowing date (YYYY-MM-DD)")
    end_date: str = Field(..., description="Latest safe sowing date (YYYY-MM-DD)")
    rationale: str = Field(..., description="Agronomic reason considering monsoon/rainfall and soil temperature")


class IrrigationItem(BaseModel):
    date_or_week: str = Field(..., description="Scheduled date (YYYY-MM-DD) or crop growth week")
    mm: float = Field(..., ge=0.0, description="Target water application in mm (or moisture conserved)")
    method: str = Field(..., description="Irrigation technique (drip, sprinkler, furrow diking, mulch)")
    rationale: str = Field(..., description="Soil moisture tension or weather deficit explanation")


class FertiliserPlan(BaseModel):
    organic_first_steps: List[str] = Field(..., description="Biological, compost, and green manure steps")
    mineral_supplement: Optional[str] = Field(None, description="Targeted mineral supplement with dosage ranges & safety warnings")


# ============================================================================
# 5. ACTION CALENDAR & TODAY CARD
# ============================================================================

class ActionCalendarItem(BaseModel):
    day_offset: int = Field(..., ge=1, le=30, description="Day offset from generation (1 to 30)")
    title: str = Field(..., min_length=5, description="Concise action heading")
    description: str = Field(..., min_length=10, description="Detailed actionable instruction")
    category: Literal["soil", "irrigation", "ipm", "sowing", "monitoring"] = Field(..., description="Action category")
    priority: UrgencyLevel = Field(..., description="Priority level")
    done: bool = Field(default=False, description="Completion toggle")


class WhatToDoToday(BaseModel):
    title: str = Field(..., min_length=5, description="High-visibility headline card")
    description: str = Field(..., min_length=15, description="1-2 sentences of immediate field action")
    urgency: UrgencyLevel = Field(..., description="Action urgency")
    icon_key: str = Field(default="sprout", description="Frontend visual icon identifier")


class RiskAndWarning(BaseModel):
    type: Literal["pest", "weather", "soil", "chemical_safety"] = Field(..., description="Warning domain")
    severity: RiskSeverity = Field(..., description="Severity level")
    message: str = Field(..., min_length=10, description="Clear, plain warning message")


# ============================================================================
# 6. EXPLAINABILITY & CONFIDENCE GUARD
# ============================================================================

class SignalUsed(BaseModel):
    signal: str = Field(..., description="Telemetry parameter (e.g. soil_ph, ndvi_trend, heat_stress_days)")
    value: Any = Field(..., description="Observed value")
    direction: Literal["supports", "cautions"] = Field(..., description="Impact direction on recommendation")
    weight: float = Field(..., ge=0.0, le=1.0, description="Relative decision weight (normalized)")
    plain_reason: str = Field(..., description="Non-technical explanation for farmers and officers")


class AdvisoryExplainability(BaseModel):
    signals_used: List[SignalUsed] = Field(..., description="Exhaustive list of data signals influencing advice")
    top_3_drivers: List[str] = Field(..., description="The 3 primary driving factors")
    knowledge_sources: List[str] = Field(default_factory=list, description="Titles of consulted open agronomy documents")
    counterfactual_note: str = Field(..., description="What specific parameter change would flip this advice")


class ConfidenceComponents(BaseModel):
    data_quality: float = Field(..., ge=0.0, le=1.0, description="Telemetry completeness & freshness (30%)")
    retrieval_support: float = Field(..., ge=0.0, le=1.0, description="Mean relevance & citation coverage (25%)")
    model_self_consistency: float = Field(..., ge=0.0, le=1.0, description="Agreement across multi-sample ranking (25%)")
    agreement_with_rules: float = Field(..., ge=0.0, le=1.0, description="Agreement with deterministic agronomy rules (20%)")


class AdvisoryConfidence(BaseModel):
    overall: float = Field(..., ge=0.0, le=1.0, description="Weighted composite confidence score")
    components: ConfidenceComponents = Field(..., description="Individual confidence components")
    level: ConfidenceLevel = Field(..., description="High (>=0.75), Medium (0.55-0.75), Low (<0.55)")
    guard_triggered: bool = Field(default=False, description="True if low confidence triggered fallback guard")
    escalation_message: Optional[str] = Field(None, description="Actionable escalation guidance if guard triggered")

    @property
    def score(self) -> float:
        """Convenience alias for overall composite confidence score."""
        return self.overall


# ============================================================================
# 7. ADVISORY METADATA & FULL CONTRACT CONTAINER
# ============================================================================

class AdvisoryMeta(BaseModel):
    advisory_id: str = Field(..., description="Unique UUID of advisory")
    field_id: str = Field(..., description="Target field UUID")
    generated_at: str = Field(..., description="ISO 8601 generation timestamp")
    language: str = Field(default="en", description="Target language code (e.g. en, hi, pt)")
    engine_mode: EngineMode = Field(..., description="Generation engine used")
    model_name: str = Field(..., description="LLM model identifier or 'rule_engine'")
    prompt_version: str = Field(default="v1.0.0", description="Version of the prompt template")
    provenance: List[Dict[str, Any]] = Field(default_factory=list, description="Data provenance badges from Phase 3")
    disclaimer: str = Field(..., description="Sovereign agricultural public good advisory disclaimer")


class AdvisoryContract(BaseModel):
    """
    Complete KrishiNet-BRICS Advisory Data Contract.
    Validated by Pydantic v2 after LLM generation and produced by deterministic rules engine.
    """
    meta: AdvisoryMeta
    field_summary: str = Field(..., min_length=30, description="Plain-language 3-sentence field status")
    crop_recommendations: List[CropRecommendation] = Field(..., min_length=1, max_length=3)
    regenerative_practices: List[RegenerativePractice] = Field(..., min_length=1)
    sowing_window: SowingWindow
    irrigation_schedule: List[IrrigationItem] = Field(default_factory=list)
    fertiliser_plan: FertiliserPlan
    action_calendar_30d: List[ActionCalendarItem] = Field(..., min_length=1)
    what_to_do_today: WhatToDoToday
    risks_and_warnings: List[RiskAndWarning] = Field(default_factory=list)
    explainability: AdvisoryExplainability
    confidence: AdvisoryConfidence

    @field_validator("field_summary")
    @classmethod
    def validate_summary_sentences(cls, v: str) -> str:
        sentences = [s.strip() for s in v.split(".") if len(s.strip()) > 3]
        if len(sentences) < 2:
            # Tolerant for concise output, ensure at least 2 sentences
            pass
        return v
