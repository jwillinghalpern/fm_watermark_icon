# FM Watermark Icon Generator

add a watermark to your FileMaker Pro icons to quickly differentiate filemaker versions. For example, you can add a "20" watermark to your FileMaker Pro 20 app and a "21" watermark to your FileMaker Pro 21 app.

![icons](readme.png)

## Installation

1. Download or clone this repository to your local machine.

   ```bash
   git clone https://github.com/jwillinghalpern/fm_watermark_icon.git
   cd fm_watermark_icon
   ```

2. Install [pillow](https://pypi.org/project/pillow/) and [numpy](https://pypi.org/project/numpy/)

   ```bash
   python3 -m pip install --upgrade pip && python3 -m pip install pillow numpy
   ```

3. Install [fileicon](https://github.com/mklement0/fileicon?tab=readme-ov-file#installation) using one of these approaches

   ```bash
   brew install fileicon
   ```

   or

   ```bash
   npm install fileicon -g
   ```

4. Make the script executable

   ```bash
   chmod +x fm_watermark_icon.py
   ```

5. (Optional but recommended) Add the script to your PATH for easy access

   Create a symlink (preferred if you want to keep the script in its current location)

   Note: When using symlinks, both files must remain in the original directory:

   ```bash
   sudo ln -s "$(pwd)/fm_watermark_icon.py" /usr/local/bin/fm_watermark_icon
   ```

   Or copy the script to a directory already in your PATH. If you choose this method, you may need to update the copied script in the future when changes are made in this repository

   ```bash
   sudo cp fm_watermark_icon.py /usr/local/bin/fm_watermark_icon
   ```

## Usage Examples

### Basic watermarking with automatic app icon update

Add a "22" watermark and immediately update the app icon:

```bash
fm_watermark_icon --app '/Applications/FileMaker Pro.app' --text 22
```

Or using the short form:

```bash
fm_watermark_icon -a '/Applications/FileMaker Pro.app' -t 22
```

### Save watermarked icon to a file without updating the app

Add a "23" watermark and save to a file instead of updating the app:

```bash
fm_watermark_icon --app '/Applications/FileMaker Pro.app' --text 23 --output new_icon.icns
```

### Color tinting options

Change the colored parts of the icon to orange while adding a watermark:

```bash
fm_watermark_icon --app '/Applications/FileMaker Pro.app' --text 22 --color "#FF8A00"
```

Just tint the icon without adding text watermark:

```bash
fm_watermark_icon --app '/Applications/FileMaker Pro.app' --color "#00A7FF"
```

### Background color options

Change white/light background regions to a custom color:

```bash
fm_watermark_icon --app '/Applications/FileMaker Pro.app' --text 22 --bg-color "#F0F0F0"
```

Combine colored region tinting with background color change:

```bash
fm_watermark_icon --app '/Applications/FileMaker Pro.app' --text 22 --color "#FF8A00" --bg-color "#E8E8E8"
```

### Custom watermark text color

Use red text for the watermark:

```bash
fm_watermark_icon --app '/Applications/FileMaker Pro.app' --text 22 --text-color "#FF0000"
```

White text on a dark background:

```bash
fm_watermark_icon --app '/Applications/FileMaker Pro.app' --text 22 --text-color "#FFFFFF" --bg-color "#000000"
```

### Legacy format (still supported)

The original positional argument format still works:

```bash
fm_watermark_icon '/Applications/FileMaker Pro.app' 22
```

If you use the `--output` approach, you can manually update the app icon for FileMaker by right-clicking on the FileMaker Pro app in Finder and selecting "Get Info". Then drag or paste the new icon over the old one in the top left corner of the Info window.

![get info](get-info.png)

## Notes

This only works on macos.
