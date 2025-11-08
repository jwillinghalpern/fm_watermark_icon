#!/usr/bin/env python3
"""
FileMaker App Icon Watermarker + Optional Tinting
Adds a watermark number to FM12App.icns files in FileMaker for MacOS application bundles.
Optionally tints any colored regions of the icon while preserving lighting and shadows.

When run without an output path, the script will automatically update the app bundle's icon
using the fileicon command (must be installed separately: brew install fileicon).

When run with an output path, the watermarked icon will be saved to that location instead
of updating the app bundle directly.

The --tint option allows you to recolor any colored parts of the icon (non-whitish,
non-black/grayish regions) to a new color while preserving the original gradients.

Author:
	Josh Willing Halpern
History:
	- 2025-11-06: Initial version
	- 2025-11-07: Added fileicon integration for automatic app icon updates
	- 2025-11-07: Added tinting functionality for colored regions
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import tempfile
import shutil
import numpy as np
from typing import Tuple

def find_fm12app_icns(app_path):
    """
    Find FM12App.icns file in the application bundle's Resources folder.
    
    Args:
        app_path: Path to the .app bundle
    
    Returns:
        Path to FM12App.icns or None if not found
    """
    app_path = Path(app_path)
    
    if not app_path.exists():
        print(f"Error: Application path does not exist: {app_path}")
        return None
    
    # Look in Contents/Resources/
    resources_path = app_path / "Contents" / "Resources"
    if not resources_path.exists():
        print(f"Error: Resources folder not found in {app_path}")
        return None
    
    icns_path = resources_path / "FM12App.icns"
    if icns_path.exists():
        return icns_path
    
    print(f"Error: FM12App.icns not found in {resources_path}")
    return None

def extract_icns_images(icns_path, temp_dir):
    """
    Extract images from .icns file using iconutil.
    
    Args:
        icns_path: Path to the .icns file
        temp_dir: Temporary directory for extraction
    
    Returns:
        Path to the iconset directory
    """
    iconset_path = Path(temp_dir) / "icon.iconset"
    iconset_path.mkdir(exist_ok=True)
    
    # Use iconutil to convert icns to iconset
    try:
        subprocess.run(
            ["iconutil", "--convert", "iconset", str(icns_path), "-o", str(iconset_path)],
            check=True,
            capture_output=True
        )
        return iconset_path
    except subprocess.CalledProcessError as e:
        print(f"Error extracting icns: {e}")
        print(f"stderr: {e.stderr.decode()}")
        return None

def _hex_to_rgb(hexstr: str) -> Tuple[int, int, int]:
    """Convert hex color string to RGB tuple."""
    s = hexstr.strip().lstrip("#")
    if len(s) == 3:
        s = "".join(ch * 2 for ch in s)
    if len(s) != 6:
        raise ValueError(f"Invalid hex color: {hexstr}")
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))

def _deg_to_ph(deg: float) -> int:
    """Convert degrees to Pillow hue (0-255 range)."""
    return int(round((deg % 360.0) / 360.0 * 255.0))

def tint_colored_region(
    image_path,
    target_hex: str,
    min_sat: int = 65,
    min_val: int = 45,
    max_sat_for_gray: int = 30,
    min_val_for_white: int = 195
) -> None:
    """
    Tint any colored pixels (non-whitish, non-black/grayish) to target hue while preserving saturation/value.
    
    Args:
        image_path: Path to the image file
        target_hex: Target color in hex format (e.g., "#FF8A00")
        min_sat: Minimum saturation to consider a pixel "colored" (0-255)
        min_val: Minimum value/brightness to consider a pixel "colored" (0-255)
        max_sat_for_gray: Maximum saturation to consider a pixel "gray" (0-255)
        min_val_for_white: Minimum value/brightness to consider a pixel "whitish" (0-255)
    """
    img_rgba = Image.open(image_path).convert("RGBA")
    a = np.array(img_rgba.split()[-1], dtype=np.uint8)
    
    hsv = img_rgba.convert("RGB").convert("HSV")
    h, s, v = [np.array(ch, dtype=np.uint8) for ch in hsv.split()]
    
    # Create mask for colored regions (more inclusive thresholds):
    # - Must have moderate saturation (s >= 65) to avoid most grayish pixels
    # - Must have some brightness (v >= 45) to avoid very dark pixels
    # - Exclude whitish pixels (high value with very low saturation)
    # - Has alpha (not transparent)
    mask = (
        (s >= min_sat) &  # Must have moderate saturation (not gray/desaturated)
        (v >= min_val) &  # Not too dark
        (v <= 250) &  # Not too bright (avoid very light pixels)
        ~((v >= min_val_for_white) & (s <= max_sat_for_gray)) &  # Not whitish
        (a > 0)  # Not transparent
    )
    
    # Convert target hex to HSV hue
    target_h = Image.new("RGB", (1, 1), _hex_to_rgb(target_hex)).convert("HSV").getpixel((0, 0))[0]
    
    # Replace hue only for masked pixels
    h2 = h.copy()
    h2[mask] = np.uint8(target_h)
    
    # Reconstruct the image
    hsv_new = Image.merge("HSV", (
        Image.fromarray(h2, "L"),
        Image.fromarray(s, "L"),
        Image.fromarray(v, "L"),
    )).convert("RGB")
    
    out = Image.merge("RGBA", (*hsv_new.split(), Image.fromarray(a, "L")))
    out.save(image_path, "PNG")
    img_rgba.close()

def add_watermark_to_image(image_path, watermark_text):
    """
    Add a watermark number to the bottom right of an image.
    
    Args:
        image_path: Path to the image file
        watermark_text: Text to use as watermark
    """
    img = Image.open(image_path).convert("RGBA")
    width, height = img.size
    
    # Create a drawing context
    draw = ImageDraw.Draw(img)
    
    # Calculate font size based on image size (roughly 1/7 of height)
    font_size = max(8, height // 7)
    
    # Try to use a system font, fall back to default if not available
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
    except:
        try:
            font = ImageFont.truetype("/System/Library/Fonts/SFNSDisplay.ttf", font_size)
        except:
            font = ImageFont.load_default()
    
    # Get text bounding box
    bbox = draw.textbbox((0, 0), watermark_text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # Position in bottom right with much more padding (higher and farther left)
    padding = max(10, width // 5)  # Even more padding
    # padding = width // 5  # Even more padding
    x = width - text_width - padding
    y = height - text_height - padding
    
    # Draw text in nice gray color
    draw.text((x, y), watermark_text, font=font, fill=(38, 44, 42, 255))
    
    # Save the image
    img.save(image_path, "PNG")

def create_icns_from_iconset(iconset_path, output_path):
    """
    Create .icns file from iconset using iconutil.
    
    Args:
        iconset_path: Path to the .iconset directory
        output_path: Path for the output .icns file
    """
    try:
        subprocess.run(
            ["iconutil", "--convert", "icns", str(iconset_path), "-o", str(output_path)],
            check=True,
            capture_output=True
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error creating icns: {e}")
        print(f"stderr: {e.stderr.decode()}")
        return False

def update_app_icon(app_path, icns_path):
    """
    Update the app bundle's icon using fileicon command.
    
    Args:
        app_path: Path to the .app bundle
        icns_path: Path to the .icns file to set as icon
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # Check if fileicon is available
        subprocess.run(
            ["which", "fileicon"],
            check=True,
            capture_output=True
        )
        
        # Use fileicon to set the app's icon
        subprocess.run(
            ["fileicon", "set", str(app_path), str(icns_path)],
            check=True,
            capture_output=True
        )
        return True
    except subprocess.CalledProcessError as e:
        if "which" in str(e.cmd):
            print("Error: fileicon command not found. Please install fileicon first:")
            print("brew install fileicon")
        else:
            print(f"Error updating app icon: {e}")
            if e.stderr:
                print(f"stderr: {e.stderr.decode()}")
        return False

def parse_arguments():
    """
    Parse command-line arguments using argparse.
    
    Returns:
        Namespace object containing parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Add a watermark number to FM12App.icns files in FileMaker for MacOS application bundles.",
        epilog="""
Examples:
  %(prog)s /Applications/MyApp.app --text 22
  %(prog)s /Applications/MyApp.app --text 22 -o ~/Desktop/FM12App_watermarked.icns
  %(prog)s /Applications/MyApp.app --text 22 --tint "#FF8A00"
  %(prog)s /Applications/MyApp.app --tint "#00A7FF" -o ~/Desktop/output.icns
  %(prog)s /Applications/MyApp.app --tint "#FF8A00" --text 22

If no output path is provided, the app's icon will be updated directly using fileicon.
If output path is provided, the watermarked icon will be saved to that location instead.

The --tint option allows you to recolor any colored parts of the icon (non-whitish,
non-black/grayish regions) while preserving the original lighting and shadows.
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        'app_path',
        metavar='APP_PATH',
        help='Path to the .app bundle containing FM12App.icns'
    )
    
    parser.add_argument(
        '-o', '--output',
        dest='output_path',
        metavar='OUTPUT_PATH',
        help='Optional: Path to save the watermarked .icns file. If not provided, the app\'s icon will be updated directly using fileicon.'
    )
    
    parser.add_argument(
        '--text',
        dest='watermark_text',
        metavar='WATERMARK_TEXT',
        help='Optional: Text to use as watermark (typically a number). If not provided, no watermark will be added.'
    )
    
    parser.add_argument(
        '--tint',
        dest='tint_color',
        metavar='HEX_COLOR',
        help='Optional: Hex color to tint colored regions of the icon (e.g., #FF8A00). Targets any non-whitish and non-black/grayish parts.'
    )
    
    return parser.parse_args()

def main():
    args = parse_arguments()
    
    app_path = args.app_path
    watermark_text = args.watermark_text
    output_path = args.output_path
    tint_color = args.tint_color
    
    # Find the FM12App.icns file
    icns_path = find_fm12app_icns(app_path)
    if not icns_path:
        sys.exit(1)
    
    print(f"Found FM12App.icns at: {icns_path}")
    
    # Create temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        print("Extracting images from .icns file...")
        iconset_path = extract_icns_images(icns_path, temp_dir)
        
        if not iconset_path:
            sys.exit(1)
        
        # Get all PNG files in the iconset
        png_files = list(iconset_path.glob("*.png"))
        
        if not png_files:
            print("Error: No PNG files found in iconset")
            sys.exit(1)
        
        print(f"Found {len(png_files)} images to watermark")
        
        # Process images: tint first (if specified), then add watermark
        for i, png_file in enumerate(png_files):
            # Skip images smaller than 64px
            img_temp = Image.open(png_file)
            if min(img_temp.size) < 64:
                print(f"Skipping {png_file.name} (too small: {img_temp.size})")
                img_temp.close()
                continue
            img_temp.close()
            
            # Apply tint if specified
            if tint_color:
                try:
                    print(f"Tinting colored regions in {png_file.name} -> {tint_color}")
                    tint_colored_region(png_file, tint_color)
                except Exception as e:
                    print(f"Warning: tint failed on {png_file.name}: {e}")
            
            # Apply watermark if specified
            if watermark_text:
                print(f"Adding watermark to {png_file.name}...")
                add_watermark_to_image(png_file, watermark_text)
        
        # Determine output behavior
        if output_path:
            # Save to specified output path (disable app icon update)
            output_icns = Path(output_path)
            print(f"Creating watermarked .icns file at {output_icns}...")
            if create_icns_from_iconset(iconset_path, output_icns):
                print(f"Success! Watermarked icon saved to: {output_icns}")
            else:
                sys.exit(1)
        else:
            # Update app bundle icon directly using fileicon
            temp_icns = Path(temp_dir) / "watermarked.icns"
            print("Creating temporary watermarked .icns file...")
            if create_icns_from_iconset(iconset_path, temp_icns):
                print(f"Updating app icon for {app_path}...")
                if update_app_icon(app_path, temp_icns):
                    print(f"Success! App icon updated for: {app_path}")
                    print("Note: You may need to refresh Finder or restart the app to see the changes.")
                else:
                    print("Failed to update app icon. You can manually drag the icon to the app:")
                    fallback_path = Path.home() / "Desktop" / f"FM12App_watermarked.icns"
                    if create_icns_from_iconset(iconset_path, fallback_path):
                        print(f"Watermarked icon saved to: {fallback_path}")
                    sys.exit(1)
            else:
                sys.exit(1)

if __name__ == "__main__":
    main()