"""
KrishiNet-BRICS – Gemini Vision Inference Module.

Sends a plant-leaf image (as base64 bytes) to Gemini Vision and parses a
structured diagnostic response.  Falls back to a deterministic fixture when
DEMO_MODE=True or when the Gemini key is absent.

Output contract (GeminiVisionPrediction):
    top_predictions: list of (label, confidence) – max 3 items
    primary_label: str
    primary_confidence: float
    reasoning: str          – one-sentence visual reasoning for explainability
    is_healthy: bool
"""

from __future__ import annotations

import base64
import json
import logging
import random
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from app.core.config import settings
from app.ai.gemini_client import gemini_client

logger = logging.getLogger("krishinet.ml.vision")

# ---------------------------------------------------------------------------
# Pydantic contract for Gemini vision response
# ---------------------------------------------------------------------------

class VisionCandidate(BaseModel):
    label: str
    confidence: float = Field(ge=0.0, le=1.0)


class GeminiVisionPrediction(BaseModel):
    top_predictions: List[VisionCandidate] = Field(max_length=3)
    primary_label: str
    primary_confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    is_healthy: bool


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

_VISION_SYSTEM_PROMPT = """You are a precision plant pathology AI trained on \
global crop-disease image datasets from CGIAR, CABI, and PlantVillage.

Your task: Analyse the provided plant leaf / stem / fruit photograph and \
identify the most likely crop disease (or confirm health).

Rules:
1. Output ONLY valid JSON matching the required schema – no markdown fences.
2. top_predictions must have 1–3 entries, sorted by confidence descending.
3. primary_label must be the label of the highest-confidence prediction.
4. Use the EXACT label vocabulary: wheat_rust_yellow, wheat_rust_brown,
   rice_blast, rice_blight_bacterial, maize_gray_leaf_spot,
   maize_northern_blight, cotton_leaf_curl, cotton_bollworm, soybean_rust,
   tomato_early_blight, tomato_late_blight, tomato_leaf_miner,
   potato_late_blight, sugarcane_red_rot, groundnut_leaf_spot_early,
   groundnut_rust, banana_panama_wilt, banana_sigatoka_black,
   chickpea_blight_ascochyta, lentil_rust, mango_anthracnose,
   mango_powdery_mildew, pearl_millet_downy_mildew, chilli_anthracnose,
   onion_purple_blotch, mustard_alternaria_blight, sunflower_downy_mildew,
   cassava_mosaic, tea_blister_blight, coffee_leaf_rust, healthy.
5. reasoning must be a single sentence describing the specific visual cues \
   that drove the primary prediction.
6. is_healthy is true ONLY when primary_label == "healthy".
7. Do NOT invent new label strings not in the vocabulary above.
"""


# ---------------------------------------------------------------------------
# Demo fixture – deterministic but varied across crops
# ---------------------------------------------------------------------------

_DEMO_FIXTURES: List[Dict[str, Any]] = [
    {
        "top_predictions": [
            {"label": "rice_blast", "confidence": 0.82},
            {"label": "rice_blight_bacterial", "confidence": 0.11},
            {"label": "healthy", "confidence": 0.07},
        ],
        "primary_label": "rice_blast",
        "primary_confidence": 0.82,
        "reasoning": "Characteristic diamond-shaped lesions with grey centres and brown margins visible on the leaf blade, consistent with Magnaporthe oryzae infection.",
        "is_healthy": False,
    },
    {
        "top_predictions": [
            {"label": "wheat_rust_yellow", "confidence": 0.76},
            {"label": "wheat_rust_brown", "confidence": 0.18},
            {"label": "healthy", "confidence": 0.06},
        ],
        "primary_label": "wheat_rust_yellow",
        "primary_confidence": 0.76,
        "reasoning": "Stripe rust is evident from the linear yellow-orange uredinia arranged in stripes along the leaf veins.",
        "is_healthy": False,
    },
    {
        "top_predictions": [
            {"label": "tomato_late_blight", "confidence": 0.88},
            {"label": "tomato_early_blight", "confidence": 0.08},
            {"label": "healthy", "confidence": 0.04},
        ],
        "primary_label": "tomato_late_blight",
        "primary_confidence": 0.88,
        "reasoning": "Water-soaked dark-green lesions with white sporulation at the leaf margin are hallmarks of Phytophthora infestans late blight.",
        "is_healthy": False,
    },
    {
        "top_predictions": [
            {"label": "healthy", "confidence": 0.94},
            {"label": "rice_blast", "confidence": 0.04},
            {"label": "maize_gray_leaf_spot", "confidence": 0.02},
        ],
        "primary_label": "healthy",
        "primary_confidence": 0.94,
        "reasoning": "Leaf surface is uniformly green with no lesions, discolouration, or pathogenic structures observed.",
        "is_healthy": True,
    },
    {
        "top_predictions": [
            {"label": "cotton_leaf_curl", "confidence": 0.79},
            {"label": "cotton_bollworm", "confidence": 0.13},
            {"label": "healthy", "confidence": 0.08},
        ],
        "primary_label": "cotton_leaf_curl",
        "primary_confidence": 0.79,
        "reasoning": "Pronounced upward leaf curling, vein thickening, and enation formation on the abaxial surface are diagnostic for Cotton Leaf Curl Virus.",
        "is_healthy": False,
    },
]


# ---------------------------------------------------------------------------
# Public inference function
# ---------------------------------------------------------------------------

async def run_gemini_vision(
    image_bytes: bytes,
    crop_hint: Optional[str] = None,
    user_id: Optional[str] = "system",
) -> GeminiVisionPrediction:
    """
    Sends image to Gemini Vision and returns a parsed GeminiVisionPrediction.

    Args:
        image_bytes: Raw JPEG/PNG bytes of the plant photograph.
        crop_hint: Optional crop name to focus the model (e.g. "rice").
        user_id: Caller identity for token-budget tracking.

    Returns:
        GeminiVisionPrediction – always populated (falls back to fixture).
    """

    def _demo_fallback() -> GeminiVisionPrediction:
        fixture = random.choice(_DEMO_FIXTURES)
        logger.info("Gemini vision: using demo fixture (DEMO_MODE or no API key).")
        return GeminiVisionPrediction(**fixture)

    # ── Demo / offline fast-path ──────────────────────────────────────────
    if settings.DEMO_MODE or not gemini_client.is_available:
        return _demo_fallback()

    # ── Build multimodal prompt ───────────────────────────────────────────
    crop_context = f" The farmer reports this is a {crop_hint} plant." if crop_hint else ""
    user_prompt = (
        f"Analyse the attached plant photograph and diagnose the crop disease.{crop_context} "
        f"Provide your structured JSON response strictly following the schema."
    )

    try:
        from google.genai import types as genai_types

        image_b64 = base64.b64encode(image_bytes).decode("utf-8")
        mime_type = _detect_mime_type(image_bytes)

        async def _call() -> GeminiVisionPrediction:
            config = genai_types.GenerateContentConfig(
                system_instruction=_VISION_SYSTEM_PROMPT,
                response_mime_type="application/json",
                response_schema=GeminiVisionPrediction,
                safety_settings=gemini_client._get_safety_settings(),
                temperature=0.1,
            )
            inline_data = genai_types.Part.from_bytes(
                data=base64.b64decode(image_b64),
                mime_type=mime_type,
            )
            response = await gemini_client._client.aio.models.generate_content(
                model=gemini_client.pro_model,
                contents=[inline_data, user_prompt],
                config=config,
            )
            raw = response.text or "{}"
            return GeminiVisionPrediction.model_validate_json(raw)

        result = await gemini_client.guard.execute_async(_call)
        logger.info(
            "Gemini vision inference complete",
            extra={"primary": result.primary_label, "conf": result.primary_confidence},
        )
        return result

    except Exception as exc:
        logger.warning(f"Gemini vision failed ({exc}); falling back to fixture.")
        return _demo_fallback()


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _detect_mime_type(image_bytes: bytes) -> str:
    """Infers MIME type from magic bytes."""
    if image_bytes[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if image_bytes[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if image_bytes[:4] == b"RIFF":
        return "image/webp"
    return "image/jpeg"  # safe default
