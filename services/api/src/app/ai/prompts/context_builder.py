"""
KrishiNet-BRICS - Context Builder for Sovereign AI Agronomic Advisory.
Assembles cleanly delimited, injection-safe XML context from biophysical telemetry,
farmer constraints, retrieved knowledge passages, and deterministic rule envelopes.
"""

import html
import json
import re
from typing import Any, Dict, List, Optional


class ContextBuilder:
    """
    Constructs structured, prompt-injection-safe prompts for Gemini LLM.
    """

    @classmethod
    def sanitize_untrusted_input(cls, text: Optional[str]) -> str:
        """
        Escapes XML delimiters and neutralizing characters to prevent prompt breakout.
        """
        if not text:
            return ""
        # Strip control characters
        cleaned = re.sub(r"[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]", "", text)
        # Neutralize XML tags
        cleaned = cleaned.replace("<", "&lt;").replace(">", "&gt;")
        # Limit length to avoid prompt stuffing attacks
        return cleaned[:1000].strip()

    @classmethod
    def build_user_prompt(
        cls,
        field_id: str,
        farm_country: str,
        current_crop: str,
        irrigation_type: str,
        field_area_ha: float,
        target_season: str = "kharif_or_summer",
        farmer_notes: Optional[str] = None,
        satellite_snapshot: Optional[Dict[str, Any]] = None,
        soil_snapshot: Optional[Dict[str, Any]] = None,
        weather_snapshot: Optional[Dict[str, Any]] = None,
        retrieved_passages: Optional[List[Dict[str, Any]]] = None,
        rules_guidance: Optional[Dict[str, Any]] = None,
        language: str = "en",
    ) -> str:
        """
        Compiles all telemetry and agronomic contexts into delimited XML tags.
        """
        safe_field_id = cls.sanitize_untrusted_input(field_id)
        safe_country = cls.sanitize_untrusted_input(farm_country)
        safe_crop = cls.sanitize_untrusted_input(current_crop)
        safe_irrigation = cls.sanitize_untrusted_input(irrigation_type)
        safe_season = cls.sanitize_untrusted_input(target_season)
        safe_notes = cls.sanitize_untrusted_input(farmer_notes)

        # 1. Farmer Context
        farmer_block = f"""<farmer_context>
  field_id: {safe_field_id}
  country: {safe_country}
  current_crop: {safe_crop}
  irrigation_type: {safe_irrigation}
  field_area_ha: {field_area_ha}
  target_season: {safe_season}
  farmer_notes: {safe_notes if safe_notes else "None"}
  requested_language: {language}
</farmer_context>"""

        # 2. Satellite Data
        sat_data = satellite_snapshot or {}
        sat_block = f"""<satellite_data>
  indices:
    ndvi: {sat_data.get('ndvi', 0.52)}
    ndre: {sat_data.get('ndre', 0.38)}
    evi: {sat_data.get('evi', 0.44)}
    msavi: {sat_data.get('msavi', 0.48)}
  mean_cloud_cover_percent: {sat_data.get('cloud_cover_percent', 4.5)}
  vegetation_trend_90d: {sat_data.get('trend_summary', 'stable')}
  anomaly_detected: {sat_data.get('anomaly', False)}
</satellite_data>"""

        # 3. Soil Profile
        soil_data = soil_snapshot or {}
        soil_block = f"""<soil_profile>
  texture: {soil_data.get('texture', 'Loam')}
  ph: {soil_data.get('ph', 6.8)}
  soc_percent: {soil_data.get('soc_percent', 0.75)}
  nitrogen_mg_kg: {soil_data.get('nitrogen_mg_kg', 180.0)}
  phosphorus_mg_kg: {soil_data.get('phosphorus_mg_kg', 14.0)}
  potassium_mg_kg: {soil_data.get('potassium_mg_kg', 210.0)}
  soil_health_score: {soil_data.get('soil_health_score', 62.0)}
  primary_limiting_factors: {soil_data.get('limiting_factors', ['low_organic_carbon'])}
</soil_profile>"""

        # 4. Weather Forecast
        wx_data = weather_snapshot or {}
        wx_block = f"""<weather_forecast>
  current_temperature_c: {wx_data.get('current_temp_c', 28.0)}
  forecast_rainfall_7d_mm: {wx_data.get('rainfall_7d_mm', 18.0)}
  heat_stress_days_next_14d: {wx_data.get('heat_stress_days_next_14d', 1)}
  dry_spell_risk_days: {wx_data.get('dry_spell_risk_days', 0)}
  relative_humidity_percent: {wx_data.get('relative_humidity_percent', 65.0)}
  derived_indicators: {json.dumps(wx_data.get('derived_indicators', {}))}
</weather_forecast>"""

        # 5. Retrieved Knowledge Passages
        passages = retrieved_passages or []
        knowledge_items = []
        for p in passages:
            doc_id = p.get("doc_id", "DOC-UNKNOWN")
            title = p.get("title", "Open Agronomy Reference")
            content = p.get("content", "").strip()
            score = p.get("score", 0.0)
            knowledge_items.append(
                f"""  <passage doc_id="{doc_id}" title="{html.escape(title)}" relevance_score="{score:.2f}">
    {content}
  </passage>"""
            )
        knowledge_block = "<retrieved_knowledge>\n" + "\n".join(knowledge_items) + "\n</retrieved_knowledge>"

        # 6. Rules Guidance
        rg = rules_guidance or {}
        rules_block = f"""<rules_guidance>
  candidate_crops: {json.dumps(rg.get('candidate_crops', ['cotton', 'soybean', 'maize']))}
  deterministic_suitability: {json.dumps(rg.get('suitability_scores', {}))}
  mandatory_practices: {json.dumps(rg.get('mandatory_practices', []))}
  sowing_window_limits: {json.dumps(rg.get('sowing_window', {}))}
  baseline_irrigation_strategy: {json.dumps(rg.get('irrigation_strategy', {}))}
</rules_guidance>"""

        instructions = """Generate an AdvisoryContract matching the required schema. Ensure every recommendation is justified by the field telemetry, grounded in the retrieved passages with accurate doc_id citations, and conforms to the regenerative agronomy guidelines."""

        return f"""{farmer_block}

{sat_block}

{soil_block}

{wx_block}

{knowledge_block}

{rules_block}

{instructions}"""


context_builder = ContextBuilder()
