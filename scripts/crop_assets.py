# -*- coding: utf-8 -*-
"""Turn a paper PDF into slide-ready crops: figures, tables, and one crop per formula.

Two ideas make the output trustworthy:

* everything is cut from a 300 dpi page render, so nothing is redrawn or retyped;
* every crop is trimmed to its ink box, so no half page-header or neighbouring
  column sneaks in (the classic "why is there stray text at the top?" bug).

Usage::

    python crop_assets.py --spec assets.json            # render + crop + contact sheet
    python crop_assets.py --spec assets.json --no-render

Spec (relative paths resolve against the spec file's folder)::

    {
      "pdf": "paper.pdf",
      "pages_dir": "build/pages",
      "dpi": 300,
      "renderer": {"node": "C:/.../node.exe", "cli": "C:/.../libreoffice-kit/lib/cli.js"},
      "crops": {
        "fig1": {"page": 2, "box": [0.045, 0.062, 0.500, 0.412]}
      },
      "formula_blocks": [
        {"page": 4, "area": [0.507, 0.815, 0.975, 0.952], "numbers": [1, 2, 3, 4]}
      ],
      "out": "build/crops",
      "sheet": {"out": "build/sheet-assets.png"}
    }

Box coordinates are normalized (0–1) fractions of the page, top-left origin.
That way a 144 dpi preview and a 300 dpi render share the same numbers.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

THR = 150  # ink threshold on a white page


# ------------------------------------------------------------------ render ---
def render_pages(pdf: Path, out_dir: Path, dpi: int, renderer: dict, force: bool = False) -> None:
    if out_dir.exists() and any(out_dir.glob("page-*.png")) and not force:
        print(f"[render] reuse {len(list(out_dir.glob('page-*.png')))} pages in {out_dir}")
        return
    out_dir.parent.mkdir(parents=True, exist_ok=True)
    cmd = [renderer["node"], renderer["cli"], "render", "--input", str(pdf),
           "--output-dir", str(out_dir), "--dpi", str(dpi)]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        sys.exit(f"[render] failed: {res.stderr.strip()[:400]}")
    manifest = json.loads(res.stdout.strip().splitlines()[0])
    print(f"[render] {manifest['images'].__len__()} pages @ {manifest['dpi']} dpi -> {out_dir}")


# ------------------------------------------------------------------- crops ---
def ink_bbox(gray: np.ndarray, pad: int) -> tuple[int, int, int, int] | None:
    ys, xs = np.where(gray < THR)
    if len(ys) == 0:
        return None
    return (max(0, xs.min() - pad), max(0, ys.min() - pad),
            min(gray.shape[1], xs.max() + 1 + pad), min(gray.shape[0], ys.max() + 1 + pad))


def crop(page_img: Path, box, pad: int = 6) -> Image.Image:
    im = Image.open(page_img).convert("RGB")
    w, h = im.size
    x0, y0, x1, y1 = box
    sub = im.crop((int(x0 * w), int(y0 * h), int(x1 * w), int(y1 * h)))
    gray = np.array(sub.convert("L"))
    bb = ink_bbox(gray, pad)
    if bb is None:
        raise SystemExit(f"[crop] empty region {box} in {page_img.name}")
    return sub.crop(bb)


def row_bands(page_img: Path, area, gap_px: int = 12) -> list[tuple[float, float]]:
    """Ink rows inside a rectangle, merged across gaps smaller than gap_px.

    Used to split a block of numbered formulas into one band per formula; a gap
    of ~12 px at 300 dpi separates two display equations without splitting the
    limits that belong to one summation sign.
    """
    gray = np.array(Image.open(page_img).convert("L"))
    h, w = gray.shape
    x0, y0, x1, y1 = area
    sub = gray[int(y0 * h):int(y1 * h), int(x0 * w):int(x1 * w)]
    ink = (sub < THR).sum(axis=1)
    flags = (ink >= 1).astype(int)
    bands, i, n = [], 0, len(flags)
    while i < n:
        if flags[i]:
            j, k, g = i, i, 0
            while k < n:
                if flags[k]:
                    j, g = k, 0
                else:
                    g += 1
                    if g >= gap_px:
                        break
                k += 1
            bands.append((y0 + i / h, y0 + j / h))
            i = j + 1
        else:
            i += 1
    return bands


# ------------------------------------------------------------- contact sheet ---
def _font(size: int):
    for name in (r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\arial.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            continue
    return ImageFont.load_default()


def contact_sheet(images: list[tuple[str, Path]], out: Path, cols: int = 3,
                  width: int = 760) -> Path:
    cells = []
    for name, path in images:
        im = Image.open(path).convert("RGB")
        scale = min((width - 36) / im.width, 1.0)
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))),
                       Image.LANCZOS)
        cells.append((name, im))
    rows = (len(cells) + cols - 1) // cols
    heights = [max(im.height for _, im in cells[r * cols:(r + 1) * cols]) + 56
               for r in range(rows)]
    canvas = Image.new("RGB", (cols * width, sum(heights)), "white")
    draw = ImageDraw.Draw(canvas)
    fnt = _font(20)
    y = 0
    for r in range(rows):
        x = 0
        for name, im in cells[r * cols:(r + 1) * cols]:
            draw.rectangle([x + 2, y + 2, x + width - 2, y + heights[r] - 2],
                           outline=(210, 214, 220))
            draw.text((x + 10, y + 6), name, font=fnt, fill=(31, 73, 125))
            canvas.paste(im, (x + 18, y + 34))
            x += width
        y += heights[r]
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out)
    print(f"[sheet] {out} {canvas.size}")
    return out


# --------------------------------------------------------------------- main ---
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", required=True)
    ap.add_argument("--no-render", action="store_true")
    ap.add_argument("--force-render", action="store_true")
    args = ap.parse_args()

    spec_path = Path(args.spec).resolve()
    spec = json.loads(spec_path.read_text(encoding="utf-8-sig"))  # tolerate Windows BOM
    root = spec_path.parent

    pages_dir = (root / spec.get("pages_dir", "build/pages")).resolve()
    out_dir = (root / spec.get("out", "build/crops")).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    if not args.no_render and spec.get("renderer"):
        render_pages((root / spec["pdf"]).resolve(), pages_dir,
                     int(spec.get("dpi", 300)), spec["renderer"], force=args.force_render)

    def page_img(page: int) -> Path:
        return pages_dir / f"page-{page:04d}.png"

    made: list[tuple[str, Path]] = []
    for name, cfg in spec.get("crops", {}).items():
        im = crop(page_img(int(cfg["page"])), cfg["box"], int(cfg.get("pad", 6)))
        im.save(out_dir / f"{name}.png")
        made.append((name, out_dir / f"{name}.png"))

    for block in spec.get("formula_blocks", []):
        prefix = block.get("prefix", "eq")
        page = int(block["page"])
        area = block["area"]
        numbers = block["numbers"]
        bands = row_bands(page_img(page), area, int(block.get("gap_px", 12)))
        if len(bands) != len(numbers):
            raise SystemExit(f"[formula] page {page}: found {len(bands)} bands "
                             f"for {len(numbers)} formulas — adjust area/gap_px")
        x0, _, x1, _ = area
        for num, (a, b) in zip(numbers, bands):
            im = crop(page_img(page), [x0, a - 0.001, x1, b + 0.001], pad=4)
            im.save(out_dir / f"{prefix}{num:02d}.png")
            made.append((f"{prefix}{num:02d}", out_dir / f"{prefix}{num:02d}.png"))

    print(f"[crop] {len(made)} assets -> {out_dir}")
    for name, path in made:
        im = Image.open(path)
        print(f"   {name:14s} {im.width:5d} x {im.height:<5d}")

    sheet = spec.get("sheet")
    if sheet:
        contact_sheet(made, (root / sheet["out"]).resolve(),
                      cols=int(sheet.get("cols", 3)), width=int(sheet.get("width", 760)))


if __name__ == "__main__":
    main()



