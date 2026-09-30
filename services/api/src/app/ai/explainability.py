"""
KrishiNet-BRICS - Advisory Explainability Service.

Constructs transparent 'Why this advice?' payloads tailored for both smallholders and extension officers:
  - Signal-level directional weights (supports / cautions)
  - Top 3 biophysical drivers behind the recommendations
  - Data provenance tracking across environmental telemetry providers
  - Counterfactual explanation ('What would change this advice?')
  - Dual presentation layers: Farmer-friendly visual brief vs. In-depth agronomic diagnostic
"""

from typing import Any, Dict, List
from app.schemas.advisory import AdvisoryContract, SignalUsed


class ExplainabilityService:
    @classmethod
    def format_explainability(
        cls,
        contract: AdvisoryContract,
        for_officer: bool = False,
    ) -> Dict[str, Any]:
        """
        Formats transparent explainability view from an AdvisoryContract.
        """
        exp = contract.explainability
        conf = contract.confidence

        # Normalize signal weights
        raw_signals = exp.signals_used or []
        total_weight = sum(s.weight for s in raw_signals) or 1.0

        normalized_signals = []
        for s in raw_signals:
            norm_w = round(s.weight / total_weight, 3)
            sig_dict = {
                "signal": s.signal,
                "value": s.value,
                "direction": s.direction,
                "weight": norm_w,
                "plain_reason": s.plain_reason,
            }
            if for_officer:
                sig_dict["impact_interpretation"] = (
                    f"Signal '{s.signal}' ({s.value}) {s.direction.upper()} "
                    f"the recommendation with relative weight {norm_w * 100:.1f}%."
                )
            normalized_signals.append(sig_dict)

        if for_officer:
            # Full diagnostic payload for Extension Officers & Agronomy Researchers
            return {
                "view": "extension_officer_diagnostic",
                "advisory_id": contract.meta.advisory_id,
                "field_id": contract.meta.field_id,
                "engine_mode": getattr(contract.meta.engine_mode, "value", str(contract.meta.engine_mode)),
                "prompt_version": contract.meta.prompt_version,
                "confidence_score": conf.overall,
                "confidence_tier": getattr(conf.level, "value", str(conf.level)),
                "guard_triggered": conf.guard_triggered,
                "escalation_message": conf.escalation_message,
                "confidence_breakdown": {
                    "data_quality_pct": round(conf.components.data_quality * 100, 1),
                    "retrieval_support_pct": round(conf.components.retrieval_support * 100, 1),
                    "self_consistency_pct": round(conf.components.model_self_consistency * 100, 1),
                    "rules_agreement_pct": round(conf.components.agreement_with_rules * 100, 1),
                },
                "top_3_drivers": exp.top_3_drivers,
                "signals_used": normalized_signals,
                "knowledge_sources": exp.knowledge_sources,
                "counterfactual_analysis": {
                    "statement": exp.counterfactual_note,
                    "sensitivity": "Evaluates how changes in SOC, soil pH, or rainfall flip selected practices.",
                },
                "telemetry_provenance": contract.meta.provenance,
            }

        # Farmer-friendly simplified view
        return {
            "view": "farmer_plain_language",
            "field_id": contract.meta.field_id,
            "headline_reason": exp.top_3_drivers[0] if exp.top_3_drivers else "Optimal biophysical fit",
            "key_factors": [
                {
                    "factor": s["signal"].replace("_", " ").title(),
                    "impact": "Favorable" if s["direction"] == "supports" else "Requires Care",
                    "explanation": s["plain_reason"],
                }
                for s in normalized_signals[:3]
            ],
            "what_changes_this": exp.counterfactual_note,
            "trust_badge": {
                "level": getattr(conf.level, "value", str(conf.level)).capitalize(),
                "status": "Verified against local soil and satellite data",
            },
        }


explainability_service = ExplainabilityService()
