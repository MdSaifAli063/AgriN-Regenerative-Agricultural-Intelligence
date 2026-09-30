"""
KrishiNet-BRICS - Image Quality & Retake Recommendation Service.

Evaluates field captures before model inference:
  1. Blur detection via discrete 2D Laplacian operator variance
  2. Darkness / underexposure analysis
  3. Glare / overexposure analysis
  4. Dimension / minimum aspect ratio checks
  5. Actionable, farmer-friendly retake instructions
"""

from dataclasses import dataclass, field
from typing import List
import numpy as np
from PIL import Image


@dataclass
class ImageQualityReport:
    is_acceptable: bool
    blur_score: float  # Higher = sharper; < 60.0 indicates blur
    brightness_score: float  # 0.0 - 255.0; < 35.0 = dark, > 230.0 = glare
    width: int
    height: int
    issues: List[str] = field(default_factory=list)
    retake_tips: List[str] = field(default_factory=list)


def compute_laplacian_variance(gray_array: np.ndarray) -> float:
    """
    Computes variance of the Laplacian using standard 3x3 convolution:
    Kernel = [[0, 1, 0], [1, -4, 1], [0, 1, 0]]
    Implemented in pure numpy to eliminate external OpenCV/scikit-image runtime dependencies.
    """
    if gray_array.ndim != 2 or gray_array.shape[0] < 3 or gray_array.shape[1] < 3:
        return 0.0

    # Fast 2D convolution for 3x3 Laplacian
    top = gray_array[:-2, 1:-1]
    bottom = gray_array[2:, 1:-1]
    left = gray_array[1:-1, :-2]
    right = gray_array[1:-1, 2:]
    center = gray_array[1:-1, 1:-1]

    laplacian = top + bottom + left + right - (4.0 * center)
    return float(np.var(laplacian))


def check_image_quality(
    image: Image.Image,
    blur_threshold: float = 60.0,
    dark_threshold: float = 35.0,
    bright_threshold: float = 230.0,
    min_dimension: int = 150,
) -> ImageQualityReport:
    """
    Audits image quality and returns structured issues and actionable retake tips.
    """
    width, height = image.size
    issues = []
    retake_tips = []

    # 1. Dimension Check
    if width < min_dimension or height < min_dimension:
        issues.append("low_resolution")
        retake_tips.append("Move closer so the leaf fills the entire camera frame.")

    # Convert to grayscale for optical metrics
    gray = image.convert("L")
    gray_np = np.array(gray, dtype=np.float32)

    # 2. Brightness Check
    mean_luminance = float(np.mean(gray_np))
    if mean_luminance < dark_threshold:
        issues.append("underexposed_dark")
        retake_tips.append("Image is too dark. Turn on your flashlight or move out of heavy shadows.")
    elif mean_luminance > bright_threshold:
        issues.append("overexposed_glare")
        retake_tips.append("Image has strong glare. Angle the camera away from direct sunlight reflection.")

    # 3. Blur Detection
    blur_var = compute_laplacian_variance(gray_np)
    if blur_var < blur_threshold:
        issues.append("motion_or_focus_blur")
        retake_tips.append("Image is blurry. Hold your phone steady and tap the diseased spot to focus.")

    # An image is acceptable if it has at most 1 minor issue and is not completely dark/unusable
    is_acceptable = len(issues) == 0 or (len(issues) == 1 and "low_resolution" not in issues and mean_luminance >= 25.0)

    return ImageQualityReport(
        is_acceptable=is_acceptable,
        blur_score=round(blur_var, 2),
        brightness_score=round(mean_luminance, 2),
        width=width,
        height=height,
        issues=issues,
        retake_tips=retake_tips,
    )
