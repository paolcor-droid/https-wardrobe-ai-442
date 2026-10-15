#!/usr/bin/env python3
"""Exercise actual MediaPipe Pose Landmarker inference with a synthetic blank image.

No customer photographs, database connections or external AI services are used.
The model is downloaded separately by install_pose_model.py.
"""
import os
from pathlib import Path

from PIL import Image

from services.tryon_preflight import detect_pose


def main():
    model = Path(os.environ.get(
        "LUMIERE_POSE_MODEL_PATH",
        str(Path(__file__).resolve().parents[1] / ".lumiere-models" / "pose_landmarker_lite.task"),
    ))
    if not model.is_file() or model.stat().st_size < 100_000:
        raise SystemExit("FAIL: Pose Landmarker model missing or incomplete")
    try:
        import mediapipe as mp
        from mediapipe.tasks import python
        from mediapipe.tasks.python import vision
        import numpy as np

        options = vision.PoseLandmarkerOptions(
            base_options=python.BaseOptions(model_asset_path=str(model)),
            running_mode=vision.RunningMode.IMAGE,
            num_poses=1,
        )
        # Calls the real native detector, not a mock. No real person should be found.
        synthetic = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=np.full((640, 480, 3), 128, dtype=np.uint8),
        )
        with vision.PoseLandmarker.create_from_options(options) as detector:
            result = detector.detect(synthetic)
        if result.pose_landmarks:
            raise RuntimeError("Unexpected pose on synthetic blank image")
        screening = detect_pose(Image.new("RGB", (480, 640), (128, 128, 128)))
        if screening["status"] != "no_person_detected":
            raise RuntimeError(f"Unexpected preflight result: {screening['status']}")
    except Exception as exc:
        raise SystemExit(f"FAIL: Local MediaPipe inference: {type(exc).__name__}: {exc}") from exc
    print("PASS: MediaPipe Tasks model loaded; native inference executed; no person detected.")
    print("All images were synthetic and processed locally.")


if __name__ == "__main__":
    main()
