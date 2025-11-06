# FM Watermark Icon Generator

add a watermark to your FileMaker Pro icons to quickly differentiate filemaker versions. For example, you can add a "20" watermark to your FileMaker Pro 20 app and a "21" watermark to your FileMaker Pro 21 app.

This only works on macos.

## Installation

1. Download or clone this repository to your local machine.
2. install pillow library if you don't have it already:

   ```bash
   pip install Pillow
   ```

3. Make the script executable:

   ```bash
   chmod +x fm_watermark_icon.py
   ```

4. (Optional) Move the script to a directory in your PATH for easy access:

   ```bash
   cp fm_watermark_icon.py /usr/local/bin/fm_watermark_icon
   ```

## Usage

Run the script from the terminal with the following command:

```bash
python3 fm_watermark_icon.py /path/to/FileMaker Pro.app 22
```

Or if you moved it to your PATH, even easier!

```bash
fm_watermark_icon /path/to/FileMaker Pro.app 22
```
