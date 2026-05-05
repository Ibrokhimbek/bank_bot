from io import BytesIO

import httpx
from PIL import Image

API = "https://api.telegram.org/bot{token}/{method}"


async def send_photo(
    token: str,
    channel_id: str,
    image: Image.Image,
    caption: str | None = None,
) -> dict:
    buf = BytesIO()
    image.save(buf, format="PNG", optimize=True)
    buf.seek(0)

    data: dict[str, str] = {"chat_id": channel_id}
    if caption:
        data["caption"] = caption
        data["parse_mode"] = "HTML"

    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            API.format(token=token, method="sendPhoto"),
            data=data,
            files={"photo": ("rates.png", buf, "image/png")},
        )
        r.raise_for_status()
        result = r.json()
        if not result.get("ok"):
            raise RuntimeError(f"Telegram API error: {result}")
        return result
