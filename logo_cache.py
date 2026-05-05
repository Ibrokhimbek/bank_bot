from io import BytesIO
from pathlib import Path

import httpx
from PIL import Image

from rates.kursuz import logo_url

CACHE_DIR = Path(__file__).parent / "assets" / "logos"
USER_DIR = CACHE_DIR  # users can drop their own {slug}.png here too
SIZE = 96


def _normalize(img: Image.Image) -> Image.Image:
    img = img.convert("RGBA")
    img.thumbnail((SIZE, SIZE), Image.LANCZOS)
    canvas = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    x = (SIZE - img.width) // 2
    y = (SIZE - img.height) // 2
    canvas.paste(img, (x, y), img)
    return canvas


async def get_logo(client: httpx.AsyncClient, slug: str) -> Image.Image | None:
    user_path = USER_DIR / f"{slug}.png"
    if user_path.exists():
        try:
            return _normalize(Image.open(user_path))
        except Exception:
            pass

    cache_path = CACHE_DIR / f"_cache_{slug}.png"
    if cache_path.exists():
        try:
            return _normalize(Image.open(cache_path))
        except Exception:
            cache_path.unlink(missing_ok=True)

    try:
        r = await client.get(logo_url(slug), timeout=10)
        r.raise_for_status()
        img = Image.open(BytesIO(r.content))
        normalized = _normalize(img)
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        normalized.save(cache_path, "PNG")
        return normalized
    except Exception:
        return None
