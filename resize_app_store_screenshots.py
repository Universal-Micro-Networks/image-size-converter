#!/usr/bin/env python3
"""
resize_appstore_screenshots.py

Convert iPhone screenshots (e.g., 1179x2556 from iPhone 16 Pro) to App Store Connect
6.7"/6.9" required sizes: 1290x2796 and/or 1320x2868 (portrait) and optional landscape.

Default behavior:
- Preserve aspect ratio
- Resize to fit and center on a fixed-size canvas
- Pad with a background color (default black) to achieve exact pixels
- Optionally also export landscape variants by rotating 90°

Usage examples:
  pip install pillow
  python resize_app_store_screenshots.py --input ./screenshots --outdir ./out
  python resize_app_store_screenshots.py --input 1.png 2.png --sizes 1290x2796,1320x2868 --landscape

Notes:
- App Store Connect accepts PNG or JPEG. PNG is default.
- This script avoids distortion; no stretching unless --mode stretch is set.
"""

import argparse
import os
import sys
from typing import Iterable, List, Tuple
from PIL import Image, ImageOps

TARGETS_67 = [(1290, 2796)]  # 6.7"
TARGETS_69 = [(1320, 2868)]  # 6.9"

def parse_sizes(s: str) -> List[Tuple[int, int]]:
    out = []
    for token in s.split(","):
        token = token.strip().lower()
        if "x" not in token:
            raise ValueError(f"Bad size token: {token}")
        w, h = token.split("x", 1)
        out.append((int(w), int(h)))
    return out

def parse_hex_color(s: str) -> Tuple[int, int, int]:
    s = s.strip().lstrip("#")
    if len(s) not in (6, 3):
        raise ValueError("bg color must be #RGB or #RRGGBB")
    if len(s) == 3:
        s = "".join(c*2 for c in s)
    r = int(s[0:2], 16)
    g = int(s[2:4], 16)
    b = int(s[4:6], 16)
    return (r, g, b)

def fit_and_pad(im: Image.Image, target: Tuple[int, int], bg: Tuple[int, int, int]) -> Image.Image:
    """Resize preserving aspect ratio to fit within target, then pad to exact size."""
    tw, th = target
    # Respect EXIF orientation
    im = ImageOps.exif_transpose(im)
    # Convert to RGB
    if im.mode not in ("RGB", "RGBA"):
        im = im.convert("RGB")
    ow, oh = im.size

    # Compute scale to fit
    scale = min(tw / ow, th / oh)
    nw = max(1, int(round(ow * scale)))
    nh = max(1, int(round(oh * scale)))

    resized = im.resize((nw, nh), Image.LANCZOS)

    # Create canvas and paste centered
    canvas = Image.new("RGB", (tw, th), bg)
    x = (tw - nw) // 2
    y = (th - nh) // 2
    canvas.paste(resized, (x, y))
    return canvas

def cover_and_crop(im: Image.Image, target: Tuple[int, int]) -> Image.Image:
    """Resize preserving aspect ratio to cover target, then center-crop to exact size."""
    tw, th = target
    im = ImageOps.exif_transpose(im)
    if im.mode not in ("RGB", "RGBA"):
        im = im.convert("RGB")
    ow, oh = im.size
    scale = max(tw / ow, th / oh)
    nw = max(1, int(round(ow * scale)))
    nh = max(1, int(round(oh * scale)))
    resized = im.resize((nw, nh), Image.LANCZOS)
    # center crop
    x = (nw - tw) // 2
    y = (nh - th) // 2
    return resized.crop((x, y, x + tw, y + th))

def stretch_resize(im: Image.Image, target: Tuple[int, int]) -> Image.Image:
    """Resize with aspect ratio ignored (not recommended)."""
    tw, th = target
    im = ImageOps.exif_transpose(im)
    if im.mode not in ("RGB", "RGBA"):
        im = im.convert("RGB")
    return im.resize((tw, th), Image.LANCZOS)

def ensure_outdir(d: str) -> None:
    os.makedirs(d, exist_ok=True)

def gather_inputs(paths: Iterable[str]) -> List[str]:
    out = []
    for p in paths:
        if os.path.isdir(p):
            for root, _, files in os.walk(p):
                for f in files:
                    if f.lower().endswith((".png", ".jpg", ".jpeg", ".heic", ".webp")):
                        out.append(os.path.join(root, f))
        else:
            out.append(p)
    return out

def save_variant(img: Image.Image, outdir: str, base: str, size: Tuple[int, int], fmt: str, suffix: str = "") -> str:
    w, h = size
    name, _ = os.path.splitext(os.path.basename(base))
    fn = f"{name}_{w}x{h}{suffix}.{fmt.lower()}"
    path = os.path.join(outdir, fn)
    params = {}
    if fmt.lower() == "jpg" or fmt.lower() == "jpeg":
        params["quality"] = 95
        params["optimize"] = True
        if img.mode == "RGBA":
            img = img.convert("RGB")
    img.save(path, **params)
    return path

def main(argv=None):
    parser = argparse.ArgumentParser(description="Resize iPhone screenshots to App Store 6.7\"/6.9\" sizes.")
    parser.add_argument("--input", "-i", nargs="+", required=True, help="Input file(s) and/or directories")
    parser.add_argument("--outdir", "-o", default="./out_6p7", help="Output directory (default: ./out_6p7)")
    parser.add_argument("--sizes", default="1290x2796,1320x2868",
                        help="Comma-separated sizes WxH (default: 1290x2796,1320x2868)")
    parser.add_argument("--mode", choices=["pad", "crop", "stretch"], default="pad",
                        help="Resize mode: 'pad' (fit and pad), 'crop' (cover and crop), or 'stretch' (distort). Default: pad")
    parser.add_argument("--bg", default="#000000", help="Background color for pad mode (hex). Default: #000000 (black)")
    parser.add_argument("--format", choices=["png", "jpg", "jpeg"], default="png",
                        help="Output format (png/jpg). Default: png")
    parser.add_argument("--landscape", action="store_true",
                        help="Also export landscape variants by rotating 90°")
    args = parser.parse_args(argv)

    try:
        targets = parse_sizes(args.sizes)
    except Exception as e:
        print(f"Error parsing --sizes: {e}", file=sys.stderr)
        return 2

    try:
        bg = parse_hex_color(args.bg)
    except Exception as e:
        print(f"Error parsing --bg: {e}", file=sys.stderr)
        return 2

    inputs = gather_inputs(args.input)
    if not inputs:
        print("No input images found.", file=sys.stderr)
        return 2

    ensure_outdir(args.outdir)

    for path in inputs:
        try:
            with Image.open(path) as im:
                for (tw, th) in targets:
                    if args.mode == "pad":
                        out_im = fit_and_pad(im, (tw, th), bg)
                    elif args.mode == "crop":
                        out_im = cover_and_crop(im, (tw, th))
                    else:
                        out_im = stretch_resize(im, (tw, th))
                    saved = save_variant(out_im, args.outdir, path, (tw, th), args.format)
                    print(f"Wrote {saved}")
                    if args.landscape:
                        # rotate 90 degrees to create landscape variants
                        out_land = out_im.rotate(90, expand=True)
                        lw, lh = th, tw  # swapped
                        saved_l = save_variant(out_land, args.outdir, path, (lw, lh), args.format, suffix="_landscape")
                        print(f"Wrote {saved_l}")
        except Exception as e:
            print(f"Failed on {path}: {e}", file=sys.stderr)

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
