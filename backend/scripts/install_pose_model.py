#!/usr/bin/env python3
"""Install public MediaPipe Lite model locally; never send customer photographs."""
import os
from pathlib import Path
import requests

URL = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task"
destination = Path(__file__).resolve().parents[1] / ".lumiere-models" / "pose_landmarker_lite.task"
destination.parent.mkdir(parents=True, exist_ok=True)
if destination.is_file() and destination.stat().st_size > 100_000:
    print("Pose model already present:", destination)
    raise SystemExit(0)
temp = destination.with_suffix(".task.part")
try:
    with requests.get(URL, stream=True, timeout=45) as response:
        response.raise_for_status()
        size = 0
        with temp.open("wb") as file:
            for chunk in response.iter_content(1024 * 256):
                size += len(chunk)
                if size > 20 * 1024 * 1024:
                    raise RuntimeError("Unexpected model size")
                file.write(chunk)
    if size < 100_000:
        raise RuntimeError("Incomplete model download")
    os.replace(temp, destination)
except Exception:
    temp.unlink(missing_ok=True)
    raise
print("Installed local pose model:", destination)
print("No customer photos were transmitted.")
