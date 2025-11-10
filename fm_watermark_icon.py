#!/usr/bin/env python3
"""
FileMaker App Icon Watermarker + Optional Tinting + Background Recoloring
Adds a watermark number to FM12App.icns files with embedded FileMaker icon data.
Optionally tints any colored regions of the icon while preserving lighting and shadows.
Optionally recolors white/light background regions to a custom color.

When run without an output path, the watermarked icon will be saved to the Desktop.
When run with an output path, the watermarked icon will be saved to that location.
When run with the --app option, the watermarked icon will be applied directly to the specified FileMaker Pro app automatically.

The --color option allows you to recolor the colored parts of the icon.

The --bg-color option allows you to recolor white/light background areas of the icon.

Author:
	Josh Willing Halpern
History:
	- 2025-11-06: Initial version
	- 2025-11-07: Added fileicon integration for automatic app icon updates
	- 2025-11-07: Added tinting functionality for colored regions
	- 2025-11-09: Embedded base64-encoded .icns file, removed --app dependency
"""

import sys
import argparse
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import tempfile
import numpy as np
import base64
from typing import Tuple

# Import the embedded icon data
try:
    from .fm_watermark_icon_data import FM12APP_ICNS_B64
except ImportError:
    # Fallback for when running as a standalone script
    import importlib.util
    script_dir = Path(__file__).parent
    data_file = script_dir / "fm_watermark_icon_data.py"
    if data_file.exists():
        spec = importlib.util.spec_from_file_location("fm_watermark_icon_data", data_file)
        data_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(data_module)
        FM12APP_ICNS_B64 = data_module.FM12APP_ICNS_B64
    else:
        print("Error: fm_watermark_icon_data.py not found!")
        print(f"Please ensure fm_watermark_icon_data.py is in the same directory as this script.")
        print(f"Script location: {Path(__file__).parent}")
        sys.exit(1)

def create_icns_from_base64(base64_data, output_path):
    """
    Decode base64 data and save as .icns file.
    
    Args:
        base64_data: Base64 encoded .icns data
        output_path: Path where to save the decoded .icns file
    
    Returns:
        True if successful, False otherwise
    """
    try:
        icns_data = base64.b64decode(base64_data)
        with open(output_path, 'wb') as f:
            f.write(icns_data)
        return True
    except Exception as e:
        print(f"Error decoding base64 .icns data: {e}")
        return False

def create_embedded_icns(temp_dir):
    """
    Create FM12App.icns file from embedded base64 data.
    
    Args:
        temp_dir: Temporary directory to save the .icns file
    
    Returns:
        Path to the created FM12App.icns or None if failed
    """
    icns_path = Path(temp_dir) / "FM12App.icns"
    
    if create_icns_from_base64(FM12APP_ICNS_B64, icns_path):
        return icns_path
    
    print("Error: Failed to create FM12App.icns from embedded data")
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

def recolor_background_region(
    image_path,
    target_hex: str,
    tolerance: int = 15
) -> None:
    """
    Recolor white and near-white pixels to target color while preserving transparency.
    
    Args:
        image_path: Path to the image file
        target_hex: Target color in hex format (e.g., "#F0F0F0")
        tolerance: RGB tolerance for matching white-ish pixels (default: 15)
    """
    img_rgba = Image.open(image_path).convert("RGBA")
    
    # Get RGB and alpha arrays
    rgb_array = np.array(img_rgba.convert("RGB"))
    alpha_array = np.array(img_rgba.split()[-1], dtype=np.uint8)
    
    # Target RGB
    target_rgb = _hex_to_rgb(target_hex)
    
    # Create mask for white-ish pixels (within tolerance) that are not transparent
    white_mask = (
        (rgb_array[:, :, 0] >= (255 - tolerance)) &
        (rgb_array[:, :, 1] >= (255 - tolerance)) &
        (rgb_array[:, :, 2] >= (255 - tolerance)) &
        (alpha_array > 0)
    )
    
    # Replace white pixels with target color
    rgb_array[white_mask] = target_rgb
    
    # Reconstruct the image
    new_img = Image.fromarray(rgb_array, "RGB")
    out = Image.merge("RGBA", (*new_img.split(), Image.fromarray(alpha_array, "L")))
    out.save(image_path, "PNG")
    img_rgba.close()

def colored_region(
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

def add_watermark_to_image(image_path, watermark_text, text_color=(38, 44, 42, 255)):
    """
    Add a watermark number to the bottom right of an image.
    
    Args:
        image_path: Path to the image file
        watermark_text: Text to use as watermark
        text_color: RGBA tuple for text color (default: dark gray)
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
    
    # Draw text with specified color
    draw.text((x, y), watermark_text, font=font, fill=text_color)
    
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

def save_icon_to_desktop(icns_path, watermark_text=None, color=None, bg_color=None):
    """
    Save the watermarked icon to the Desktop with a descriptive name.
    
    Args:
        icns_path: Path to the .icns file
        watermark_text: Text used for watermarking (optional)
        color: Color used for tinting (optional) 
        bg_color: Background color used (optional)
    
    Returns:
        Path to the saved file or None if failed
    """
    try:
        # Build a descriptive filename
        base_name = "FM12App"
        if watermark_text:
            base_name += f"_watermark_{watermark_text}"
        if color:
            base_name += f"_tinted_{color.replace('#', '')}"
        if bg_color:
            base_name += f"_bg_{bg_color.replace('#', '')}"
        
        desktop_path = Path.home() / "Desktop" / f"{base_name}.icns"
        
        # Copy the file to Desktop
        import shutil
        shutil.copy2(icns_path, desktop_path)
        
        return desktop_path
    except Exception as e:
        print(f"Error saving icon to desktop: {e}")
        return None

def parse_arguments():
    """
    Parse command-line arguments using argparse.
    
    Returns:
        Namespace object containing parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Add a watermark number to embedded FM12App.icns file with optional tinting and background recoloring.",
        epilog=r"""
Examples:
  %(prog)s --text 22
  %(prog)s --text 22 --app /Applications/FileMaker\ Pro.app
  %(prog)s --text 22 -o ~/Desktop/FM12App_watermarked.icns
  %(prog)s --text 22 --color "#FF8A00" --app /Applications/FileMaker\ Pro.app
  %(prog)s --color "#00A7FF" -o ~/Desktop/output.icns
  %(prog)s --color "#FF8A00" --text 22
  %(prog)s --text 22 --bg-color "#F0F0F0" --app /Applications/FileMaker\ Pro.app
  %(prog)s --color "#FF8A00" --bg-color "#E8E8E8" --text 22
  %(prog)s --text 22 --text-color "#FF0000"
  %(prog)s --text 22 --text-color "#FFFFFF" --bg-color "#000000"

If --app is provided, the app's icon will be updated directly using fileicon.
If --output is provided, the watermarked icon will be saved to that location.
If neither --app nor --output is provided, the icon will be saved to your Desktop.

The --color option allows you to recolor any colored parts of the icon (non-whitish,
non-black/grayish regions) while preserving the original lighting and shadows.

The --bg-color option allows you to recolor white/light background regions while
preserving gradients and shadows.

The --text-color option allows you to customize the watermark text color.
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '-a', '--app',
        dest='app_path',
        metavar='APP_PATH',
        help='Optional: Path to the .app bundle to update with the watermarked icon using fileicon.'
    )
    
    parser.add_argument(
        '-o', '--output',
        dest='output_path',
        metavar='OUTPUT_PATH',
        help='Optional: Path to save the watermarked .icns file. If not provided and --app is not specified, the watermarked icon will be saved to your Desktop.'
    )
    
    parser.add_argument(
        '-t', '--text',
        dest='watermark_text',
        metavar='WATERMARK_TEXT',
        help='Optional: Text to use as watermark (typically a number). If not provided, no watermark will be added.'
    )
    
    parser.add_argument(
        '-c', '--color',
        dest='color',
        metavar='HEX_COLOR',
        help='Optional: Hex color to tint colored regions of the icon (e.g., #FF8A00). Targets any non-whitish and non-black/grayish parts.'
    )
    
    parser.add_argument(
        '-bg', '-bc', '--bg-color',
        dest='bg_color',
        metavar='HEX_COLOR',
        help='Optional: Hex color to replace white/light background regions (e.g., #F0F0F0). Preserves gradients and shading.'
    )
    
    parser.add_argument(
        '-tc', '--text-color',
        dest='text_color',
        metavar='HEX_COLOR',
        help='Optional: Hex color for watermark text (e.g., #FF0000). Default is dark gray.'
    )
    
    # Check if no arguments provided
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)
    
    return parser.parse_args()

def main():
    args = parse_arguments()
    
    app_path = args.app_path
    watermark_text = args.watermark_text
    output_path = args.output_path
    color = args.color
    bg_color = args.bg_color
    text_color = args.text_color
    
    # Convert text color from hex to RGBA if provided
    text_color_rgba = (38, 44, 42, 255)  # Default dark gray
    if text_color:
        try:
            rgb = _hex_to_rgb(text_color)
            text_color_rgba = (*rgb, 255)
        except ValueError as e:
            print(f"Warning: Invalid text color '{text_color}': {e}")
            print("Using default text color instead.")
    
    # Create temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        print("Creating FM12App.icns from embedded data...")
        icns_path = create_embedded_icns(temp_dir)
        
        if not icns_path:
            sys.exit(1)
        
        print(f"Created FM12App.icns at: {icns_path}")
        
        print("Extracting images from .icns file...")
        iconset_path = extract_icns_images(icns_path, temp_dir)
        
        if not iconset_path:
            sys.exit(1)
        
        # Get all PNG files in the iconset
        png_files = list(iconset_path.glob("*.png"))
        
        if not png_files:
            print("Error: No PNG files found in iconset")
            sys.exit(1)
        
        print(f"Found {len(png_files)} images to process")
        
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
            if color:
                try:
                    print(f"Tinting colored regions in {png_file.name} -> {color}")
                    colored_region(png_file, color)
                except Exception as e:
                    print(f"Warning: tint failed on {png_file.name}: {e}")
            
            # Apply background recoloring if specified
            if bg_color:
                try:
                    print(f"Recoloring background in {png_file.name} -> {bg_color}")
                    recolor_background_region(png_file, bg_color)
                except Exception as e:
                    print(f"Warning: background recolor failed on {png_file.name}: {e}")
            
            # Apply watermark if specified
            if watermark_text:
                print(f"Adding watermark to {png_file.name}...")
                add_watermark_to_image(png_file, watermark_text, text_color_rgba)
        
        # Determine output behavior based on arguments
        if app_path:
            # Update app bundle icon using fileicon
            temp_icns = Path(temp_dir) / "watermarked.icns"
            print("Creating watermarked .icns file...")
            if create_icns_from_iconset(iconset_path, temp_icns):
                print(f"Updating app icon for {app_path}...")
                if update_app_icon(app_path, temp_icns):
                    print(f"Success! App icon updated for: {app_path}")
                    print("Note: You may need to refresh Finder or restart the app to see the changes.")
                else:
                    print("Failed to update app icon. You can manually drag the icon to the app:")
                    fallback_path = Path.home() / "Desktop" / "FM12App_watermarked.icns"
                    import shutil
                    shutil.copy2(temp_icns, fallback_path)
                    print(f"Watermarked icon saved to: {fallback_path}")
                    sys.exit(1)
            else:
                sys.exit(1)
        elif output_path:
            # Save to specified output path
            output_icns = Path(output_path)
            print(f"Creating watermarked .icns file at {output_icns}...")
            if create_icns_from_iconset(iconset_path, output_icns):
                print(f"Success! Watermarked icon saved to: {output_icns}")
            else:
                sys.exit(1)
        else:
            # Save to Desktop with descriptive name
            temp_icns = Path(temp_dir) / "watermarked.icns"
            print("Creating watermarked .icns file...")
            if create_icns_from_iconset(iconset_path, temp_icns):
                desktop_path = save_icon_to_desktop(temp_icns, watermark_text, color, bg_color)
                if desktop_path:
                    print(f"Success! Watermarked icon saved to: {desktop_path}")
                else:
                    # Fallback: save with simple name
                    fallback_path = Path.home() / "Desktop" / "FM12App_watermarked.icns"
                    import shutil
                    shutil.copy2(temp_icns, fallback_path)
                    print(f"Watermarked icon saved to: {fallback_path}")
            else:
                sys.exit(1)

if __name__ == "__main__":
    main()