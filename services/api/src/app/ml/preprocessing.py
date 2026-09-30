"""
KrishiNet-BRICS - Image Preprocessing & Test-Time Augmentation (TTA).

Handles:
  1. EXIF orientation correction (prevents upside-down phone photos from failing)
  2. RGB conversion and robust dimension resizing
  3. ImageNet mean/std normalization
  4. Test-Time Augmentation (TTA) generation for uncertain field samples
"""

import io
from typing import Generator, List, Tuple
import numpy as np
from PIL import Image, ImageOps

# ImageNet normalization parameters
IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
IMAGENET_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


def load_and_orient_image(image_bytes: bytes) -> Image.Image:
    """
    Loads raw image bytes into a PIL Image and automatically corrects EXIF orientation.
    Converts image to RGB mode.
    """
    img = Image.open(io.BytesIO(image_bytes))
    try:
        # Correct orientation if EXIF tags exist
        img = ImageOps.exif_transpose(img)
    except Exception:
        pass
    return img.convert("RGB")


def preprocess_for_onnx(
    image: Image.Image,
    target_size: Tuple[int, int] = (224, 224),
    channel_first: bool = True,
) -> np.ndarray:
    """
    Prepares a PIL Image for MobileNetV3 ONNX inference:
    1. High-quality bicubic resize to target_size
    2. Rescaling pixels to [0.0, 1.0]
    3. Normalizing by ImageNet mean and std
    4. Formatting to float32 tensor (1, 3, H, W) or (1, H, W, 3)
    """
    resized = image.resize(target_size, Image.Resampling.BICUBIC)
    arr = np.array(resized, dtype=np.float32) / 255.0

    # Apply ImageNet normalization: (x - mean) / std
    arr = (arr - IMAGENET_MEAN) / IMAGENET_STD

    if channel_first:
        # (H, W, C) -> (C, H, W)
        arr = np.transpose(arr, (2, 0, 1))

    # Add batch dimension: (1, C, H, W)
    return np.expand_dims(arr, axis=0).astype(np.float32)


def generate_tta_variants(
    image: Image.Image,
    target_size: Tuple[int, int] = (224, 224),
    channel_first: bool = True,
) -> List[np.ndarray]:
    """
    Generates test-time augmentation (TTA) batch:
    - Original image
    - Horizontal mirror flip
    - +10 degree rotation
    - -10 degree rotation
    """
    variants = [
        image,
        ImageOps.mirror(image),
        image.rotate(10, resample=Image.Resampling.BICUBIC),
        image.rotate(-10, resample=Image.Resampling.BICUBIC),
    ]

    return [preprocess_for_onnx(v, target_size, channel_first=channel_first) for v in variants]
