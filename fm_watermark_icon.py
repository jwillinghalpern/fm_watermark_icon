#!/usr/bin/env python3
"""
FileMaker App Icon Watermarker + Optional Green Recolor

Adds a version watermark to FM12App.icns files in FileMaker for macOS app bundles.
Optionally recolors the green "leaf" region by replacing its HUE only (keeps native
light/dark gradient), so v21/v22 can be visually distinct.

Usage examples:
  python fm_icon_mark.py "/Applications/FileMaker Pro 22.app" 22
  python fm_icon_mark.py "/Applications/FileMaker Pro 22.app" 22 --tint "#FF8A00"
  python fm_icon_mark.py "/Applications/FileMaker Pro 21.app" 21 --tint "#00A7FF" --output ~/Desktop/FM12App_21.icns

Notes:
  • macOS-only dependency: `iconutil` (normally present on macOS).
  • You can replace the app’s icon by opening the app’s Get Info window and dragging
    the generated .icns onto the top-left icon.

Author of original watermark idea and script: Josh Willing Halpern
Enhancements (argparse + recolor-by-hue): ChatGPT
History:
  - 2025-11-06: Initial version (shared)
  - 2025-11-07: argparse + hue-based recolor option
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Tuple

from PIL import Image, ImageDraw, ImageFont
import numpy as np

# -------------------------- Utilities & Checks -------------------------- #

def require_tool(name: str) -> None:
    if shutil.which(name) is None:
        print(f"Error: required tool '{name}' was not found in PATH.")
        sys.exit(1)

def find_fm12app_icns(app_path: Path) -> Path | None:
    """Find FM12App.icns in the app bundle."""
    app_path = Path(app_path)
    if not app_path.exists():
        print(f"Error: Application path does not exist: {app_path}")
        return None
    resources_path = app_path / "Contents" / "Resources"
    if not resources_path.exists():
        print(f"Error: Resources folder not found in {app_path}")
        return None
    icns_path = resources_path / "FM12App.icns"
    if icns_path.exists():
        return icns_path
    print(f"Error: FM12App.icns not found in {resources_path}")
    return None

def extract_icns_images(icns_path: Path, temp_dir: Path) -> Path | None:
    """iconutil: .icns -> .iconset directory"""
    iconset_path = Path(temp_dir) / "icon.iconset"
    iconset_path.mkdir(exist_ok=True)
    try:
        subprocess.run(
            ["iconutil", "--convert", "iconset", str(icns_path), "-o", str(iconset_path)],
            check=True, capture_output=True
        )
        return iconset_path
    except subprocess.CalledProcessError as e:
        print(f"Error extracting icns: {e}\nstderr: {e.stderr.decode()}")
        return None

def create_icns_from_iconset(iconset_path: Path, output_path: Path) -> bool:
    """iconutil: .iconset -> .icns"""
    try:
        subprocess.run(
            ["iconutil", "--convert", "icns", str(iconset_path), "-o", str(output_path)],
            check=True, capture_output=True
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error creating icns: {e}\nstderr: {e.stderr.decode()}")
        return False

# -------------------------- Recolor-by-Hue (optional) -------------------------- #

def _hex_to_rgb(hexstr: str) -> Tuple[int, int, int]:
    s = hexstr.strip().lstrip("#")
    if len(s) == 3:
        s = "".join(ch * 2 for ch in s)
    if len(s) != 6:
        raise ValueError(f"Invalid hex color: {hexstr}")
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))

def _deg_to_ph(deg: float) -> int:
    # Pillow hue is 0..255, maps to 0..360 degrees
    return int(round((deg % 360.0) / 360.0 * 255.0))

def recolor_green_region(
    image_path: Path,
    target_hex: str,
    green_center_deg: float = 120.0,
    green_width_deg: float = 40.0,
    min_sat: int = 60,
    min_val: int = 40
) -> None:
    """
    Recolor only green-ish pixels to target hue while preserving saturation/value (gradient).
    - green_center_deg: center hue for green
    - green_width_deg:  half-width around center to accept
    - min_sat/min_val:  ignore dull/very dark pixels
    """
    img_rgba = Image.open(image_path).convert("RGBA")
    a = np.array(img_rgba.split()[-1], dtype=np.uint8)

    hsv = img_rgba.convert("RGB").convert("HSV")
    h, s, v = [np.array(ch, dtype=np.uint8) for ch in hsv.split()]

    green_center = _deg_to_ph(green_center_deg)
    green_width = _deg_to_ph(green_width_deg)

    def circ_diff(arr: np.ndarray, b: int) -> np.ndarray:
        d = np.abs(arr.astype(np.int16) - int(b))
        return np.minimum(d, 255 - d)

    mask = (
        (circ_diff(h, green_center) <= green_width) &
        (s >= min_sat) &
        (v >= min_val) &
        (a > 0)
    )

    target_h = Image.new("RGB", (1, 1), _hex_to_rgb(target_hex)).convert("HSV").getpixel((0, 0))[0]

    h2 = h.copy()
    h2[mask] = np.uint8(target_h)

    hsv_new = Image.merge("HSV", (
        Image.fromarray(h2, "L"),
        Image.fromarray(s,  "L"),
        Image.fromarray(v,  "L"),
    )).convert("RGB")

    out = Image.merge("RGBA", (*hsv_new.split(), Image.fromarray(a, "L")))
    out.save(image_path, "PNG")
    img_rgba.close()

# -------------------------- Watermark -------------------------- #

def add_watermark_to_image(
    image_path: Path,
    watermark_text: str,
    padding_scale: float = 0.20,
    min_font_px: int = 8,
    font_path_candidates: tuple[str, ...] = (
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/SFNSDisplay.ttf",
    ),
    color_rgba: tuple[int, int, int, int] = (38, 44, 42, 255)
) -> None:
    """
    Draw watermark at bottom-right with scaled padding.
    """
    img = Image.open(image_path).convert("RGBA")
    width, height = img.size
    draw = ImageDraw.Draw(img)

    font_size = max(min_font_px, height // 7)
    font = None
    for fp in font_path_candidates:
        try:
            font = ImageFont.truetype(fp, font_size)
            break
        except Exception:
            pass
    if font is None:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), watermark_text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    padding = max(10, int(width * padding_scale))
    x = width - text_w - padding
    y = height - text_h - padding

    draw.text((x, y), watermark_text, font=font, fill=color_rgba)
    img.save(image_path, "PNG")
    img.close()

# -------------------------- Main flow -------------------------- #

def main():
    parser = argparse.ArgumentParser(description="Watermark FM12App.icns and optionally recolor the green region.")
    parser.add_argument("app_path", help="Path to the FileMaker .app bundle")
    parser.add_argument("watermark", help="Watermark text (e.g., version number like 22)")
    parser.add_argument("--output", help="Output .icns path (default: ~/Desktop/FM12App.icns)")
    parser.add_argument("--tint", help="Hex color to tint the green region (e.g., #FF8A00)")
    parser.add_argument("--tint-hue-center", type=float, default=120.0, help="Green hue center in degrees (default: 120)")
    parser.add_argument("--tint-hue-width", type=float, default=40.0, help="Half-width of green hue range (deg, default: 40)")
    parser.add_argument("--tint-min-sat", type=int, default=60, help="Min saturation (0-255) to be recolored (default: 60)")
    parser.add_argument("--tint-min-val", type=int, default=40, help="Min value/brightness (0-255) to be recolored (default: 40)")
    parser.add_argument("--skip-smaller-than", type=int, default=64, help="Skip icon PNGs smaller than this many pixels on the short side (default: 64)")
    parser.add_argument("--padding-scale", type=float, default=0.20, help="Watermark padding as fraction of width (default: 0.20)")

    args = parser.parse_args()

    # Ensure macOS iconutil is available
    require_tool("iconutil")

    icns_path = find_fm12app_icns(Path(args.app_path))
    if not icns_path:
        sys.exit(1)
    print(f"Found FM12App.icns at: {icns_path}")

    output_icns = Path(args.output) if args.output else (Path.home() / "Desktop" / "FM12App.icns")

    with tempfile.TemporaryDirectory() as td:
        temp_dir = Path(td)
        print("Extracting images from .icns file...")
        iconset_path = extract_icns_images(icns_path, temp_dir)
        if not iconset_path:
            sys.exit(1)

        png_files = sorted(iconset_path.glob("*.png"))
        if not png_files:
            print("Error: No PNG files found in iconset")
            sys.exit(1)

        print(f"Found {len(png_files)} images to process")

        for png_file in png_files:
            with Image.open(png_file) as im:
                size = im.size
            if min(size) < args.skip_smaller_than:
                print(f"Skipping {png_file.name} (too small: {size})")
                continue

            if args.tint:
                try:
                    print(f"Recoloring green region in {png_file.name} -> {args.tint}")
                    recolor_green_region(
                        png_file,
                        args.tint,
                        green_center_deg=args.tint_hue_center,
                        green_width_deg=args.tint_hue_width,
                        min_sat=args.tint_min_sat,
                        min_val=args.tint_min_val,
                    )
                except Exception as e:
                    print(f"Warning: tint failed on {png_file.name}: {e}")

            print(f"Watermarking {png_file.name} with '{args.watermark}'")
            add_watermark_to_image(
                png_file,
                args.watermark,
                padding_scale=args.padding_scale
            )

        print(f"Creating watermarked .icns at {output_icns} ...")
        if create_icns_from_iconset(iconset_path, output_icns):
            print(f"Success! Saved: {output_icns}")
        else:
            sys.exit(1)

if __name__ == "__main__":
    main()
