#!/usr/bin/env python3
"""Read-only asset manifest audit. Does not access profiles or live inventory."""
import argparse
import ast
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "frontend/src/demo-inspiration-images.ts"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", help="Optional ZIP of AI generated images to check")
    args = parser.parse_args()
    source = SOURCE.read_text(encoding="utf8")
    pairs = re.findall(r'\["([a-z_]+)","([a-z_]+)","([a-z]+)"\]', source)
    if not pairs:
        raise SystemExit("No women's asset expectations found")
    available=set()
    if args.bundle:
        with zipfile.ZipFile(args.bundle) as archive:
            available=set(archive.namelist())
    else:
        manifest=(ROOT/"frontend/src/demo-ai-assets.ts").read_text(encoding="utf8")
        available={key+".jpg" for key, _, _ in pairs if "women_"+key in manifest}
    found=0
    for key, subtype, colour in pairs:
        filename="women_"+key+".jpg"
        ok=(filename in available if args.bundle else "women_"+key+".jpg" in available)
        found+=ok
        print(f"women | {subtype:24} | {colour:6} | {'FOUND_EXACT' if ok else 'MISSING_EXACT'} | {filename}")
    print(f"{found}/{len(pairs)} expected women's demo photos present")
if __name__ == "__main__":
    main()
