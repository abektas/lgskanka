# Video Reel Automation

This skill produces vertical (1080×1920) reels from a folder of images using ffmpeg.

## Always‑on rules
- Use only the local ffmpeg binary; do not rely on external services.
- Each image is shown 2 seconds. The total duration is calculated as `number_of_images * 2` seconds and capped at 60 s; if it exceeds this limit, only the first 30 images are used.
- Output format: MP4 with codec `libx264` and pixel format `yuv420p`.
- Scaling to 1080×1920; maintain aspect ratio by padding or stretching if necessary.

## Procedure
1. Gather all JPEG/PNG files in the specified folder; sort alphabetically.
2. Generate a temporary ffmpeg concat list file `images.txt` with entries:
   `file 'path/to/image.ext'`.
3. Run ffmpeg:
   ```bash
   ffmpeg -y -f concat -safe 0 -i images.txt \
          -vf "scale=1080:1920" -t <duration> \
          -c:v libx264 -pix_fmt yuv420p output.mp4
   ```
4. Delete the temporary `images.txt`.
5. Emit a log line indicating the successful creation and full path to the output.
6. Optional: move the output to a desired artifacts directory.

## Pitfalls
- **ffmpeg not found** – install the package or ensure the binary is in PATH.
- **Large images cause memory thrash** – consider downscaling before invoking the script.
- **Aspect‑ratio distortion** – use `pad` filter instead of direct scaling if preserving the image shape is critical.
- **Non‑image files present** – the script filters by `.jpg`, `.jpeg`, `.png` extensions only.
- **Duration > 60 s** – the script automatically truncates to 30 images to keep within the 60 s limit.

