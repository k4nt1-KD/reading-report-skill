# -*- coding: utf-8 -*-
"""Mechanical checks before delivery, plus the full-page contact sheet.

Three things are checked, in increasing cost:

1. structure  — slide count, size, out-of-bounds shapes, empty slides;
2. sequence   — every slide's header and page title, in order (catches a slide
                built under the wrong section, or a duplicated title);
3. rendering  — every page rendered to PNG, assembled into one contact sheet so
                the whole deck can be reviewed at a glance.

    python verify_deck.py --pptx output/deck.pptx --out build/render \
        --node <node.exe> --cli <libreoffice-kit/lib/cli.js> --sheet build/sheet.png

Exit code 1 when a hard problem (out-of-bounds shape, unreadable file) is found.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from pptx import Presentation

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

IN = 914400
TOL = 0.02  # inches of slack before a shape counts as out of bounds


def structure(prs: Presentation) -> tuple[int, list[str]]:
    W, H = prs.slide_width / IN, prs.slide_height / IN
    problems: list[str] = []
    for i, sl in enumerate(prs.slides, 1):
        if not any(sh.has_text_frame and sh.text_frame.text.strip() for sh in sl.shapes):
            problems.append(f"slide {i}: no text at all")
        for sh in sl.shapes:
            try:
                l, t = sh.left / IN, sh.top / IN
                w, h = sh.width / IN, sh.height / IN
            except TypeError:
                continue
            if l < -0.05 or t < -0.05 or l + w > W + TOL or t + h > H + TOL:
                problems.append(f"slide {i}: {sh.name!r} out of bounds "
                                f"({l:.2f},{t:.2f})-({l + w:.2f},{t + h:.2f})")
    return len(prs.slides), problems


def sequence(prs: Presentation) -> None:
    print("page  header                          title")
    for i, sl in enumerate(prs.slides, 1):
        header = ""
        for ph in sl.placeholders:  # idx 0 = layout title placeholder
            if ph.placeholder_format.idx == 0:
                header = ph.text_frame.text.strip()
                break
        title = ""
        best = None
        for sh in sl.shapes:
            if sh.has_text_frame and sh.text_frame.text.strip() and sh.top is not None:
                top = sh.top / IN
                if 0.80 <= top <= 1.02 and (best is None or top < best):
                    best, title = top, sh.text_frame.text.strip().split("\n")[0]
        print(f"{i:>4}  {header[:30]:<30}  {title[:44]}")


def render(pptx: Path, out_dir: Path, node: str, cli: str, pages: str | None) -> list[Path]:
    out_dir.parent.mkdir(parents=True, exist_ok=True)
    cmd = [node, cli, "render", "--input", str(pptx), "--output-dir", str(out_dir)]
    if pages:
        cmd += ["--pages", pages]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"[render] failed: {res.stderr.strip()[:400]}")
        return []
    manifest = json.loads(res.stdout.strip().splitlines()[0])
    files = [Path(img["path"]) for img in manifest["images"]]
    print(f"[render] {len(files)} pages, dpi={manifest.get('dpi')}, "
          f"backend={manifest.get('rasterEngine')}")
    if manifest.get("missingFonts"):
        print(f"[render] missing fonts: {manifest['missingFonts']}")
    return files


def sheet(files: list[Path], out: Path, cols: int = 4, width: int = 480) -> None:
    if not files:
        return
    th = int(width * 9 / 16)
    rows = (len(files) + cols - 1) // cols
    pad, lab = 10, 22
    canvas = Image.new("RGB", (cols * (width + pad) + pad,
                               rows * (th + lab + pad) + pad), "white")
    draw = ImageDraw.Draw(canvas)
    try:
        fnt = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 15)
    except Exception:
        fnt = ImageFont.load_default()
    for i, p in enumerate(files):
        im = Image.open(p).convert("RGB").resize((width, th), Image.LANCZOS)
        c, r = i % cols, i // cols
        x, y = pad + c * (width + pad), pad + r * (th + lab + pad)
        canvas.paste(im, (x, y))
        draw.rectangle([x - 1, y - 1, x + width, y + th], outline=(190, 196, 204))
        draw.text((x + 2, y + th + 3), f"p{i + 1}", font=fnt, fill=(31, 73, 125))
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out)
    print(f"[sheet] {out} {canvas.size}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pptx", required=True)
    ap.add_argument("--out", default="build/render")
    ap.add_argument("--node")
    ap.add_argument("--cli")
    ap.add_argument("--pages")
    ap.add_argument("--sheet")
    args = ap.parse_args()

    pptx = Path(args.pptx).resolve()
    prs = Presentation(str(pptx))
    count, problems = structure(prs)
    print(f"[structure] {count} slides, {prs.slide_width / IN:.3f} x {prs.slide_height / IN:.3f} in")
    for p in problems:
        print("   !!", p)
    sequence(prs)

    if args.node and args.cli:
        files = render(pptx, Path(args.out).resolve(), args.node, args.cli, args.pages)
        if args.sheet:
            sheet(files, Path(args.sheet).resolve())

    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()


