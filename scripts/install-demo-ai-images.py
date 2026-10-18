#!/usr/bin/env python3
"""Convert approved synthetic demo-image bundle to an optional TS data URI manifest.

Usage: python3 scripts/install-demo-ai-images.py /path/to/lumiere_ai_demo_garment_images.zip
Never commits raw supplier images; generated imagery is labelled in Discover.
"""
import base64
import pathlib
import sys
import zipfile

FILENAMES = {
    "taupe-polo": "taupe_polo_ai_demo.jpg",
    "cream-chinos": "cream_chinos_ai_demo.jpg",
    "navy-loafers": "navy_loafers_ai_demo.jpg",
    "pearl-grey-oxford": "pearl_grey_oxford_ai_demo.jpg",
    "taupe-polo-new": "taupe_polo_updated_ai_demo.jpg",
    "beige-tshirt": "beige_tshirt_ai_demo.jpg",
    "navy-tshirt": "navy_tshirt_ai_demo.jpg",
    "sand-chinos": "sand_chinos_ai_demo.jpg",
    "olive-chinos": "olive_chinos_ai_demo.jpg",
    "navy-chinos": "navy_chinos_ai_demo.jpg",
    "camel-loafers": "camel_loafers_ai_demo.jpg",
}
OPTIONAL_FILES = {
    "sand-shirt": "sand_shirt_ai_demo.jpg",
    "grey-polo": "grey_polo_ai_demo.jpg",
    "beige-polo": "beige_polo_ai_demo.jpg",
    "olive-tshirt": "olive_tshirt_ai_demo.jpg",
    "taupe-chinos": "taupe_chinos_ai_demo.jpg",
    "navy-shorts": "navy_shorts_ai_demo.jpg",
    "grey-tailored": "grey_tailored_ai_demo.jpg",
    "camel-tailored": "camel_tailored_ai_demo.jpg",
    "cream-sneakers": "cream_sneakers_ai_demo.jpg",
    "navy-sneakers": "navy_sneakers_ai_demo.jpg",
    "beige-sneakers": "beige_sneakers_ai_demo.jpg",
    "pearl-grey-sneakers": "pearl_grey_sneakers_ai_demo.jpg",
    "tan-loafers": "tan_loafers_ai_demo.jpg",
}
OUT = pathlib.Path(__file__).resolve().parents[1] / "frontend/src/demo-ai-assets.ts"

def main():
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python3 scripts/install-demo-ai-images.py <image-bundle.zip>")
    src = pathlib.Path(sys.argv[1])
    if not src.is_file():
        raise SystemExit(f"Archive not found: {src}")
    with zipfile.ZipFile(src) as z:
        files = {}
        for key, filename in {**FILENAMES, **OPTIONAL_FILES}.items():
            if key in OPTIONAL_FILES and filename not in z.namelist():
                continue
            data = z.read(filename)
            if not data.startswith(bytes.fromhex('ffd8ff')):
                raise ValueError(f"{filename} is not a JPEG")
            if len(data) > 250_000:
                raise ValueError(f"{filename} exceeds demo size limit")
            files[key] = "data:image/jpeg;base64," + base64.b64encode(data).decode("ascii")
    lines = ["/** AI-generated illustrative demo assets: not real products. Auto-generated. */",
             "export const DEMO_AI_ASSETS: Record<string, string> = {"]
    for key, uri in files.items():
        lines.append(f"  {key!r}: {uri!r},")
    lines.append("};")
    OUT.write_text(chr(10).join(lines) + chr(10), encoding="utf8")
    print("Installed", len(files), "synthetic demo images into", OUT)
if __name__ == "__main__":
    main()
