import io

from PIL import Image

from . import imageutil


def _image_bytes(fmt: str, mode: str = "RGB", size=(4, 3), color=(200, 50, 10)) -> bytes:
    image = Image.new(mode, size, color if mode != "L" else 128)
    buffer = io.BytesIO()
    image.save(buffer, format=fmt)
    return buffer.getvalue()


def _decode(data_uri: str) -> Image.Image:
    prefix = "data:image/jpeg;base64,"
    assert data_uri.startswith(prefix)
    import base64

    return Image.open(io.BytesIO(base64.b64decode(data_uri[len(prefix):])))


def test_oversized_image_is_downscaled():
    oversized = _image_bytes("PNG", size=(2800, 2000))

    result = imageutil.reencode_image_as_data_uri(oversized, max_dimension=1200)

    embedded = _decode(result)
    assert max(embedded.size) == 1200
    # Aspect ratio preserved: 2800x2000 is 1.4:1.
    assert embedded.size == (1200, int(2000 * 1200 / 2800))


def test_image_within_the_limit_is_left_at_its_own_size():
    small = _image_bytes("PNG", size=(50, 30))

    result = imageutil.reencode_image_as_data_uri(small, max_dimension=1200)

    assert _decode(result).size == (50, 30)


def test_cmyk_jpeg_is_converted_to_rgb_jpeg():
    """Regression test: some sources serve CMYK-mode JPEGs. Passing those through unmodified is
    a known way to make WeasyPrint silently drop the *entire* story - see module docstring."""
    cmyk_jpeg = _image_bytes("JPEG", mode="CMYK", size=(8, 8))

    result = imageutil.reencode_image_as_data_uri(cmyk_jpeg, max_dimension=1200)

    embedded = _decode(result)
    assert embedded.format == "JPEG"
    assert embedded.mode in ("RGB", "L")


def test_transparent_image_is_composited_onto_white():
    """Pillow's convert("RGB") does not composite transparent pixels against anything - it just
    drops the alpha channel and keeps whatever RGB value was stored underneath, which can leave
    visible phantom colors where transparency was meant to show through."""
    rgba = Image.new("RGBA", (2, 2), (255, 255, 255, 0))  # fully transparent white
    rgba.putpixel((0, 0), (0, 0, 0, 255))  # opaque black - must stay black
    rgba.putpixel((1, 1), (10, 20, 30, 0))  # fully transparent, garbage RGB - must become white
    buffer = io.BytesIO()
    rgba.save(buffer, format="PNG")

    result = imageutil.reencode_image_as_data_uri(buffer.getvalue(), max_dimension=1200)

    embedded = _decode(result)
    assert embedded.mode == "RGB"
    assert embedded.getpixel((0, 0)) == (0, 0, 0)
    assert embedded.getpixel((1, 1)) == (255, 255, 255)


def test_grayscale_image_is_left_as_grayscale():
    grayscale = _image_bytes("PNG", mode="L", size=(6, 6))

    result = imageutil.reencode_image_as_data_uri(grayscale, max_dimension=1200)

    assert _decode(result).mode == "L"


def test_quality_parameter_is_honored():
    # A flat color compresses about as well at any quality level - use noise so the JPEG quality
    # setting actually has DCT detail to trade off against.
    import random

    random.seed(0)
    noisy = Image.new("RGB", (60, 60))
    noisy.putdata([tuple(random.randint(0, 255) for _ in range(3)) for _ in range(60 * 60)])
    buffer = io.BytesIO()
    noisy.save(buffer, format="PNG")
    photo = buffer.getvalue()

    low = imageutil.reencode_image_as_data_uri(photo, max_dimension=1200, quality=10)
    high = imageutil.reencode_image_as_data_uri(photo, max_dimension=1200, quality=95)

    assert len(low) < len(high)
