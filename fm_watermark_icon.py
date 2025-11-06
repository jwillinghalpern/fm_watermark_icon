#!/usr/bin/env python3
"""
FileMaker App Icon Watermarker
Adds a watermark number to FM12App.icns files in FileMaker for MacOS application bundles.
Once the watermark is added to the output file, you can right-click on the FMP application, Get Info,
and drag the icons over the icon in the Info window to replace the app icon.

Author:
	Josh Willing Halpern
History:
	- 2025-11-06: Initial version
"""

import os
import sys
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import tempfile
import shutil

def find_fm12app_icns(app_path):
    """
    Find FM12App.icns file in the application bundle's Resources folder.
    
    Args:
        app_path: Path to the .app bundle
        watermark_text: Text to use as watermark. e.g. "22" for FMP 22.
    
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

def main():
    if len(sys.argv) < 3:
        print("Usage: python watermark_icon.py <path_to_app> <watermark_number> [output_path]")
        print("Example: python watermark_icon.py /Applications/MyApp.app 22")
        print("Example: python watermark_icon.py /Applications/MyApp.app 22 ~/Desktop/FM12App_watermarked.icns")
        sys.exit(1)
    
    app_path = sys.argv[1]
    watermark_text = sys.argv[2]
    output_path = sys.argv[3] if len(sys.argv) > 3 else None
    
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
        
        # Add watermark to 
        for i, png_file in enumerate(png_files):
            # Skip images smaller than 64px
            img_temp = Image.open(png_file)
            if min(img_temp.size) < 64:
                print(f"Skipping {png_file.name} (too small: {img_temp.size})")
                continue
            print(f"Adding watermark to {png_file.name}...")
            add_watermark_to_image(png_file, watermark_text)
        
        # Determine output path
        if output_path:
            output_icns = Path(output_path)
        else:
            output_icns = Path.home() / "Desktop" / f"FM12App.icns"
        
        # Create the new .icns file
        print(f"Creating watermarked .icns file at {output_icns}...")
        if create_icns_from_iconset(iconset_path, output_icns):
            print(f"Success! Watermarked icon saved to: {output_icns}")
        else:
            sys.exit(1)

if __name__ == "__main__":
    main()