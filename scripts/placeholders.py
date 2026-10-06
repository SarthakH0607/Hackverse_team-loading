#!/usr/bin/env python3
"""
scripts/placeholders.py
-----------------------
STAGE 4: Optical RGB Placeholders (No Fabrication).
Checks for genuine optical RGB images. If absent, copies radar previews as
explicit PLACEHOLDER files and logs them in docs/A_TODO.md.
"""

from pathlib import Path
import shutil
from site_config import SIKKIM_SITE, ROOT_DIR

DATA_DIR = SIKKIM_SITE["data_dir"]
DOCS_DIR = ROOT_DIR / "docs"
TODO_FILE = DOCS_DIR / "A_TODO.md"

PRE_RGB = DATA_DIR / "pre_rgb.png"
POST_RGB = DATA_DIR / "post_rgb.png"
PRE_RADAR = DATA_DIR / "pre.png"
POST_RADAR = DATA_DIR / "post.png"
PRE_PLACEHOLDER = DATA_DIR / "pre_rgb_PLACEHOLDER.png"
POST_PLACEHOLDER = DATA_DIR / "post_rgb_PLACEHOLDER.png"


def update_todo():
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    todo_content = "# Project Action Items / Missing Data\n\n"
    if TODO_FILE.exists():
        todo_content = TODO_FILE.read_text(encoding="utf-8")

    section_header = "## Stage 4: Radar Placeholders for Optical RGB\n"
    note_text = (
        "- [ ] `data/pre_rgb_PLACEHOLDER.png` & `data/post_rgb_PLACEHOLDER.png`: "
        "These files are temporary radar placeholders (copied from Sentinel-1 VV backscatter data/pre.png and data/post.png). "
        "They MUST be replaced by real optical satellite images (e.g. Sentinel-2 / Landsat RGB). "
        "**Never present them as true optical imagery.**\n"
    )

    if section_header not in todo_content:
        todo_content += f"\n{section_header}\n{note_text}"
    elif note_text not in todo_content:
        todo_content += note_text

    TODO_FILE.write_text(todo_content, encoding="utf-8")


def main():
    print("=" * 60)
    print("STAGE 4: Optical Image Placeholder Management")
    print("=" * 60)

    if not PRE_RGB.exists() or not POST_RGB.exists():
        print("Optical RGB images (data/pre_rgb.png, data/post_rgb.png) not found.")
        if PRE_RADAR.exists():
            shutil.copyfile(PRE_RADAR, PRE_PLACEHOLDER)
            print(f"Copied {PRE_RADAR.name} -> {PRE_PLACEHOLDER.name}")
        else:
            print(f"Warning: {PRE_RADAR} missing.")

        if POST_RADAR.exists():
            shutil.copyfile(POST_RADAR, POST_PLACEHOLDER)
            print(f"Copied {POST_RADAR.name} -> {POST_PLACEHOLDER.name}")
        else:
            print(f"Warning: {POST_RADAR} missing.")

        update_todo()
        print("Updated docs/A_TODO.md with radar placeholder advisory.")
    else:
        print("True optical RGB images exist in data/. No placeholders needed.")


if __name__ == "__main__":
    main()
