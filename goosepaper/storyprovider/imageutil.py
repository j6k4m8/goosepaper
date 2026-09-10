"""Shared image re-encoding for any externally-fetched image embedded into a goosepaper PDF.

Embedding a source image unmodified - at whatever resolution, color mode/metadata, and format
the source happens to serve - is a known way to make WeasyPrint's PDF image embedding silently
drop content with no exception and no log line: a gap where an image (or, once combined with the
size/weight of everything else already in a full newspaper, sometimes an entire story) should
have been. Three contributing factors have been identified in practice: (1) some sources serve
images at print resolution (2800px+ wide) with no smaller variant requested; (2) even at a
source's own default resolution, a lossless PNG re-encode of photo-like or gradient-heavy content
is itself several times larger than the same content as JPEG; (3) some sources ship CMYK-mode
JPEGs with large embedded Photoshop/ICC metadata blocks, or formats (e.g. WebP) that WeasyPrint's
image backend cannot decode at all. Re-encoding through Pillow first - bounding pixel dimensions,
normalizing color mode, and always emitting JPEG - keeps every embedded image in the same
reasonable, predictable size/format range regardless of what the source happens to serve on a
given day.
"""

import base64
import io

from PIL import Image


def reencode_image_as_data_uri(image_bytes: bytes, max_dimension: int, quality: int = 90) -> str:
    """Decodes and re-encodes a fetched image as a clean, size-capped JPEG `data:` URI.

    Bounds pixel dimensions to `max_dimension` on the long edge, normalizes color mode (e.g.
    CMYK -> RGB), and composites any transparency onto white rather than leaving whatever RGB
    value was stored underneath a transparent pixel (Pillow's plain `convert("RGB")` does not
    composite - it just drops the alpha channel and keeps whatever was there, which can leave
    visible phantom colors/edges where transparency was meant to show through).
    """
    image = Image.open(io.BytesIO(image_bytes))
    if image.mode not in ("RGB", "L"):
        has_transparency = (
            image.mode in ("RGBA", "LA", "PA") or "transparency" in image.info
        )
        if has_transparency:
            background = Image.new("RGB", image.size, (255, 255, 255))
            rgba_image = image.convert("RGBA")
            background.paste(rgba_image, mask=rgba_image.split()[-1])
            image = background
        else:
            image = image.convert("RGB")
    if max(image.size) > max_dimension:
        image.thumbnail((max_dimension, max_dimension), Image.LANCZOS)
    jpeg_buffer = io.BytesIO()
    image.save(jpeg_buffer, format="JPEG", quality=quality)
    return f"data:image/jpeg;base64,{base64.b64encode(jpeg_buffer.getvalue()).decode('ascii')}"
