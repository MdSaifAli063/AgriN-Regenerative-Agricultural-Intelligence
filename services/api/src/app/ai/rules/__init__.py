"""
KrishiNet-BRICS - Agronomic Rules Package.
"""

from app.ai.rules.crop_config import CROP_AGRONOMIC_SPECS, CropSpec, get_crop_spec
from app.ai.rules.engine import DeterministicRuleEngine, deterministic_rules_engine

__all__ = [
    "CROP_AGRONOMIC_SPECS",
    "CropSpec",
    "get_crop_spec",
    "DeterministicRuleEngine",
    "deterministic_rules_engine",
]
