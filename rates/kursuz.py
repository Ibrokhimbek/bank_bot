import re

import httpx
from bs4 import BeautifulSoup

from rates.base import BankRate

KURSUZ_URL = "https://kurs.uz/uz/"
LOGO_URL_TEMPLATE = "https://kurs.uz/images/banks/{slug}.png"

NAMES_RU = {
    "aab": "Asia Alliance Bank",
    "agrobank": "Агробанк",
    "infinbank": "Infinbank",
    "ipotekabank": "Ипотека банк",
    "saderatbank": "Saderat bank",
    "sqb": "Узпромстройбанк",
    "trustbank": "Trustbank",
    "xalqbank": "Народный банк",
}


def _parse_amount(text: str) -> float | None:
    m = re.search(r"\d[\d\s.,]*\d|\d", text)
    if not m:
        return None
    cleaned = m.group(0).replace(" ", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


async def fetch_bank_rates(client: httpx.AsyncClient) -> list[BankRate]:
    r = await client.get(KURSUZ_URL, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "lxml")

    rates: list[BankRate] = []
    seen: set[str] = set()
    for a in soup.find_all("a", href=re.compile(r"^/uz/banks/[^/]+/USD$")):
        slug = a["href"].rstrip("/").split("/")[-2]
        if slug in seen or slug == "cbu":
            continue
        seen.add(slug)

        tr = a.find_parent("tr")
        if tr is None:
            continue
        tds = tr.find_all("td", recursive=False)
        if len(tds) < 3:
            continue

        name_uz = a.get_text(" ", strip=True)
        # Buy and sell live in the first <div> of td[1] and td[2]
        buy = _parse_amount(tds[1].get_text(" ", strip=True))
        sell = _parse_amount(tds[2].get_text(" ", strip=True))

        rates.append(
            BankRate(
                slug=slug,
                name_uz=name_uz,
                name_ru=NAMES_RU.get(slug, name_uz),
                buy=buy,
                sell=sell,
            )
        )
    return rates


def logo_url(slug: str) -> str:
    return LOGO_URL_TEMPLATE.format(slug=slug)
