# FM Watermark Icon Generator

add a watermark to your FileMaker Pro icons to quickly differentiate filemaker versions. For example, you can add a "20" watermark to your FileMaker Pro 20 app and a "21" watermark to your FileMaker Pro 21 app.

![icons](readme.png)

## Installation

1. Download or clone this repository to your local machine.

   ```bash
   git clone https://github.com/jwillinghalpern/fm_watermark_icon.git
   cd fm_watermark_icon
   ```

2. Install pillow

   ```bash
   python3 -m pip install --upgrade pip && python3 -m pip install pillow
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

1. Run the script from the terminal with the following command:

   ```bash
   python3 fm_watermark_icon.py '/Applications/FileMaker Pro.app' 22
   ```

   Or if you moved it to your PATH, even easier!

   ```bash
   fm_watermark_icon '/Applications/FileMaker Pro.app' 22
   ```

2. Right-click on the FileMaker Pro app in Finder and select "Get Info". Then drag or paste the new icon over the old one in the top left corner of the Info window.

## Notes

This only works on macos.
