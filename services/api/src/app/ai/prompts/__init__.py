"""
KrishiNet-BRICS - AI Prompt Layer.
Semantic versioning for sovereign agronomic prompts.
"""

from app.ai.prompts.v1_0 import SYSTEM_PROMPT_V1, FEW_SHOT_EXAMPLES_V1
from app.ai.prompts.context_builder import ContextBuilder, context_builder

__all__ = [
    "SYSTEM_PROMPT_V1",
    "FEW_SHOT_EXAMPLES_V1",
    "ContextBuilder",
    "context_builder",
]
