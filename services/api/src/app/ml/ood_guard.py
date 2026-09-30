"""
KrishiNet-BRICS - Out-Of-Distribution (OOD) & Non-Plant Guard.

Rejects photos that do not belong to the supported foliar classes
using dual criteria:
  1. Maximum softmax probability threshold
  2. Shannon information entropy threshold
"""

from dataclasses import dataclass
from typing import List, Optional
import numpy as np


@dataclass
class OODCheckResult:
    is_ood: bool
    max_confidence: float
    shannon_entropy: float
    reason: Optional[str] = None


def evaluate_ood_guard(
    probabilities: List[float],
    max_conf_threshold: float = 0.40,
    entropy_threshold: float = 2.85,
) -> OODCheckResult:
    """
    Computes Shannon entropy over class probability distribution.
    If max confidence is too low or entropy is excessively high, flags image as out-of-distribution.
    """
    probs = np.array(probabilities, dtype=np.float32)
    max_conf = float(np.max(probs))

    # Avoid log(0)
    safe_probs = np.clip(probs, 1e-12, 1.0)
    entropy = float(-np.sum(safe_probs * np.log(safe_probs)))

    is_ood = (max_conf < max_conf_threshold) or (entropy > entropy_threshold)
    reason = None
    if is_ood:
        if max_conf < max_conf_threshold and entropy > entropy_threshold:
            reason = "Image does not appear to contain a recognized crop leaf (low confidence and high entropy)."
        elif max_conf < max_conf_threshold:
            reason = "Model confidence is too low to produce a safe diagnosis; image may not be a supported crop."
        else:
            reason = "High prediction ambiguity across multiple classes; photo may be unclear or contain non-foliar objects."

    return OODCheckResult(
        is_ood=is_ood,
        max_confidence=round(max_conf, 4),
        shannon_entropy=round(entropy, 4),
        reason=reason,
    )
