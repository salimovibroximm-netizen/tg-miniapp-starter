"""Photo storage: resize, thumbnail, date stamp and signed links.

Photos are not served from the web root. Each link carries a short HMAC
signature, so a photo URL cannot be guessed from another one.
"""
import hashlib
import hmac
import io
import uuid

from PIL import Image, ImageDraw, ImageFont, ImageOps, UnidentifiedImageError

from .config import settings
from .db import now

FULL_SIZE = 1600
THUMB_SIZE = 320
MAX_BYTES = 15 * 1024 * 1024


class BadImage(ValueError):
    pass


def _font(size: int):
    for name in ("DejaVuSans-Bold.ttf", "arialbd.ttf", "DejaVuSans.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def stamp(img: Image.Image, text: str) -> Image.Image:
    """Draws `text` in the bottom-right corner on a dark plate, readable on any photo."""
    img = img.convert("RGB")
    draw = ImageDraw.Draw(img)
    size = max(14, img.width // 40)
    font = _font(size)
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    w, h = right - left, bottom - top
    pad = size // 2
    x, y = img.width - w - pad * 3, img.height - h - pad * 3
    draw.rectangle([x - pad, y - pad, x + w + pad, y + h + pad], fill=(0, 0, 0))
    draw.text((x - left, y - top), text, font=font, fill=(255, 255, 255))
    return img


def save_image(data: bytes, folder: str, stamp_text: str | None = None) -> tuple[str, str]:
    """Saves a photo and its thumbnail. Returns (path, thumb) relative to the media dir."""
    if len(data) > MAX_BYTES:
        raise BadImage("Photo is too large")
    try:
        img = Image.open(io.BytesIO(data))
        img = ImageOps.exif_transpose(img)  # phones store rotation in EXIF
        img.load()
    except (UnidentifiedImageError, OSError):
        raise BadImage("This file is not a photo")
    img = img.convert("RGB")
    img.thumbnail((FULL_SIZE, FULL_SIZE))
    if stamp_text:
        img = stamp(img, stamp_text)
    sub = f"{folder}/{now():%Y/%m}"
    target = settings.data_dir / "media" / sub
    target.mkdir(parents=True, exist_ok=True)
    name = uuid.uuid4().hex
    img.save(target / f"{name}.jpg", "JPEG", quality=84, optimize=True)
    thumb = img.copy()
    thumb.thumbnail((THUMB_SIZE, THUMB_SIZE))
    thumb.save(target / f"{name}_t.jpg", "JPEG", quality=78, optimize=True)
    return f"{sub}/{name}.jpg", f"{sub}/{name}_t.jpg"


def _sig(path: str) -> str:
    return hmac.new(settings.secret.encode(), path.encode(), hashlib.sha256).hexdigest()[:20]


def media_url(path: str, absolute: bool = False) -> str:
    url = f"/media/{path}?s={_sig(path)}"
    return settings.public_url + url if absolute else url


def check_sig(path: str, sig: str) -> bool:
    return hmac.compare_digest(_sig(path), sig or "")
