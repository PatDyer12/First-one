#!/usr/bin/env python3
"""Turns each page of the study-guide PDF into a PNG (for viewing on a phone/laptop)."""
from pathlib import Path

import sys

import pymupdf

ROOT = Path(__file__).resolve().parent.parent
NAME = sys.argv[1] if len(sys.argv) > 1 else "geol211_exam2_study_guide"
PDF = ROOT / f"{NAME}.pdf"
OUT = ROOT / (sys.argv[2] if len(sys.argv) > 2 else "pages")

OUT.mkdir(exist_ok=True)
for old in OUT.glob("*.png"):
    old.unlink()
doc = pymupdf.open(PDF)
for i, pg in enumerate(doc, 1):
    pg.get_pixmap(dpi=170).save(OUT / f"page-{i:02d}.png")
print(f"{len(doc)} pages -> {OUT}")
