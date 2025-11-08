#!/usr/bin/env python3
"""
FileMaker App Icon Watermarker
Adds a watermark number to FM12App.icns files in FileMaker for MacOS application bundles.

When run without an output path, the script will automatically update the app bundle's icon
using the fileicon command (must be installed separately: brew install fileicon).

When run with an output path, the watermarked icon will be saved to that location instead
of updating the app bundle directly.

Author:
	Josh Willing Halpern
History:
	- 2025-11-06: Initial version
	- 2025-11-07: Added fileicon integration for automatic app icon updates
"""

import os
import sys
import argparse
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
  %(prog)s /Applications/MyApp.app 22
  %(prog)s /Applications/MyApp.app 22 -o ~/Desktop/FM12App_watermarked.icns
  %(prog)s --app /Applications/MyApp.app --watermark 22 --output ~/Desktop/output.icns

If no output path is provided, the app's icon will be updated directly using fileicon.
If output path is provided, the watermarked icon will be saved to that location instead.
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        'app_path',
        metavar='APP_PATH',
        help='Path to the .app bundle containing FM12App.icns'
    )
    
    parser.add_argument(
        'watermark',
        metavar='WATERMARK_TEXT',
        help='Text to use as watermark (typically a number)'
    )
    
    parser.add_argument(
        '-o', '--output',
        dest='output_path',
        metavar='OUTPUT_PATH',
        help='Optional: Path to save the watermarked .icns file. If not provided, the app\'s icon will be updated directly using fileicon.'
    )
    
    return parser.parse_args()

def main():
    args = parse_arguments()
    
    app_path = args.app_path
    watermark_text = args.watermark
    output_path = args.output_path
    
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