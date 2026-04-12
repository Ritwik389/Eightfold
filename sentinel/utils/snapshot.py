"""
SENTINEL — Snapshot Utilities

Frame capture and disk save helpers.
"""

import os
from datetime import datetime

from sentinel.config import SNAPSHOT_DIR


def ensure_snapshot_dir() -> str:
    """Create and return the snapshot directory path."""
    os.makedirs(SNAPSHOT_DIR, exist_ok=True)
    return SNAPSHOT_DIR


def save_snapshot_from_array(frame_array, prefix: str = "snap") -> str:
    """
    Save a numpy array frame to disk as JPEG.

    Args:
        frame_array: BGR numpy array (OpenCV format).
        prefix: Filename prefix.

    Returns:
        Path to saved image.
    """
    ensure_snapshot_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filepath = os.path.join(SNAPSHOT_DIR, f"{prefix}_{timestamp}.jpg")

    try:
        import cv2
        cv2.imwrite(filepath, frame_array)
    except ImportError:
        try:
            from PIL import Image
            import numpy as np
            # Convert BGR to RGB for PIL
            if len(frame_array.shape) == 3 and frame_array.shape[2] == 3:
                rgb = frame_array[:, :, ::-1]
            else:
                rgb = frame_array
            img = Image.fromarray(rgb)
            img.save(filepath)
        except Exception:
            pass

    return filepath


def generate_placeholder_snapshot(text: str = "No camera", prefix: str = "placeholder") -> str:
    """
    Generate a placeholder image with text for text-only mode.

    Args:
        text: Text to render on the placeholder.
        prefix: Filename prefix.

    Returns:
        Path to saved image.
    """
    ensure_snapshot_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filepath = os.path.join(SNAPSHOT_DIR, f"{prefix}_{timestamp}.jpg")

    try:
        from PIL import Image, ImageDraw, ImageFont
        img = Image.new("RGB", (640, 480), color=(30, 30, 40))
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("Helvetica", 24)
        except Exception:
            font = ImageFont.load_default()
        draw.text((220, 230), text, fill=(150, 150, 150), font=font)
        img.save(filepath)
    except Exception:
        # Absolute fallback - create an empty file
        with open(filepath, "wb") as f:
            f.write(b"")

    return filepath
