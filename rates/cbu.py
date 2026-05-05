from datetime import datetime

import httpx

from rates.base import OfficialRate

CBU_USD_URL = "https://cbu.uz/uz/arkhiv-kursov-valyut/json/USD/"


async def fetch_official(client: httpx.AsyncClient) -> OfficialRate:
    r = await client.get(CBU_USD_URL, timeout=15)
    r.raise_for_status()
    payload = r.json()[0]
    return OfficialRate(
        rate=float(payload["Rate"]),
        diff=float(payload["Diff"]),
        as_of=datetime.strptime(payload["Date"], "%d.%m.%Y").date(),
    )
