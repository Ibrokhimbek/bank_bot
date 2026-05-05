import asyncio
from datetime import date
from pathlib import Path

import httpx
from PIL import Image, ImageDraw, ImageFont

from logo_cache import get_logo
from rates.base import BankRate, OfficialRate

WIDTH = 1080
HEIGHT = 1400
MARGIN = 48

BG = (245, 247, 250)
CARD = (255, 255, 255)
INK = (20, 28, 40)
MUTED = (110, 122, 140)
ACCENT = (16, 110, 230)
ACCENT_DARK = (10, 78, 170)
GREEN = (36, 152, 100)
RED = (215, 67, 67)
ROW_ALT = (248, 250, 253)

FONT_CANDIDATES = [
    "/Library/Fonts/Arial Unicode.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/System/Library/Fonts/SFNS.ttf",
]
FONT_BOLD_CANDIDATES = [
    "/Library/Fonts/Arial Unicode.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/System/Library/Fonts/SFNS.ttf",
]


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    for path in FONT_BOLD_CANDIDATES if bold else FONT_CANDIDATES:
        if Path(path).exists():
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def _fmt_amount(v: float | None) -> str:
    if v is None:
        return "—"
    return f"{v:,.0f}".replace(",", " ")


def _format_date_uz(d: date) -> str:
    months_uz = [
        "yanvar", "fevral", "mart", "aprel", "may", "iyun",
        "iyul", "avgust", "sentabr", "oktabr", "noyabr", "dekabr",
    ]
    return f"{d.day} {months_uz[d.month - 1]} {d.year}"


def _format_date_ru(d: date) -> str:
    months_ru = [
        "января", "февраля", "марта", "апреля", "мая", "июня",
        "июля", "августа", "сентября", "октября", "ноября", "декабря",
    ]
    return f"{d.day} {months_ru[d.month - 1]} {d.year}"


def _rounded_rect(draw: ImageDraw.ImageDraw, xy, radius, fill):
    draw.rounded_rectangle(xy, radius=radius, fill=fill)


def _text_w(draw: ImageDraw.ImageDraw, text: str, font) -> int:
    return draw.textlength(text, font=font)


async def _gather_logos(banks: list[BankRate]) -> dict[str, Image.Image | None]:
    async with httpx.AsyncClient(follow_redirects=True) as client:
        results = await asyncio.gather(*(get_logo(client, b.slug) for b in banks))
    return {b.slug: img for b, img in zip(banks, results)}


def render(
    official: OfficialRate | None,
    banks: list[BankRate],
    today: date,
    logos: dict[str, Image.Image | None],
) -> Image.Image:
    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    d = ImageDraw.Draw(img)

    # ----- Header card -----
    header_h = 220
    _rounded_rect(d, (MARGIN, MARGIN, WIDTH - MARGIN, MARGIN + header_h), 24, ACCENT)

    f_title = _font(46, bold=True)
    f_subtitle = _font(28)
    f_date = _font(24)

    title_uz = "O'zbekiston banklari dollar kursi"
    title_ru = "Курс доллара в банках Узбекистана"

    d.text((MARGIN + 36, MARGIN + 32), title_uz, font=f_title, fill=(255, 255, 255))
    d.text((MARGIN + 36, MARGIN + 92), title_ru, font=f_subtitle, fill=(220, 232, 255))
    date_str = f"{_format_date_uz(today)}  ·  {_format_date_ru(today)}"
    d.text((MARGIN + 36, MARGIN + 148), date_str, font=f_date, fill=(220, 232, 255))

    # ----- Official CBU rate card -----
    cbu_y = MARGIN + header_h + 24
    cbu_h = 140
    _rounded_rect(d, (MARGIN, cbu_y, WIDTH - MARGIN, cbu_y + cbu_h), 20, CARD)

    f_cbu_label = _font(22)
    f_cbu_value = _font(64, bold=True)
    f_cbu_diff = _font(22, bold=True)

    d.text(
        (MARGIN + 32, cbu_y + 22),
        "Markaziy bank kursi  ·  Курс ЦБ",
        font=f_cbu_label,
        fill=MUTED,
    )

    if official:
        value_text = f"{official.rate:,.2f}".replace(",", " ") + " so'm"
        d.text((MARGIN + 32, cbu_y + 56), value_text, font=f_cbu_value, fill=INK)
        diff = official.diff
        diff_color = GREEN if diff >= 0 else RED
        sign = "+" if diff >= 0 else ""
        d.text(
            (MARGIN + 32 + int(_text_w(d, value_text, f_cbu_value)) + 18, cbu_y + 78),
            f"{sign}{diff:.2f}",
            font=f_cbu_diff,
            fill=diff_color,
        )
    else:
        d.text((MARGIN + 32, cbu_y + 56), "—", font=f_cbu_value, fill=MUTED)

    # ----- Bank table -----
    table_y = cbu_y + cbu_h + 28
    table_x0 = MARGIN
    table_x1 = WIDTH - MARGIN

    f_th = _font(22, bold=True)
    f_td_name = _font(26, bold=True)
    f_td_rate = _font(30, bold=True)
    f_td_label = _font(18)

    header_pad = 16
    col_buy_x = table_x0 + 580
    col_sell_x = table_x0 + 800

    # Column headers (two lines for the rate columns to avoid overlap)
    d.text(
        (table_x0 + 24, table_y + header_pad + 8),
        "Bank  ·  Банк",
        font=f_th,
        fill=MUTED,
    )
    d.text((col_buy_x, table_y + header_pad - 4), "Sotib olish", font=f_th, fill=MUTED)
    d.text((col_buy_x, table_y + header_pad + 22), "Покупка", font=f_th, fill=MUTED)
    d.text((col_sell_x, table_y + header_pad - 4), "Sotish", font=f_th, fill=MUTED)
    d.text((col_sell_x, table_y + header_pad + 22), "Продажа", font=f_th, fill=MUTED)

    row_y = table_y + 70
    row_h = 92

    for i, bank in enumerate(banks):
        if i % 2 == 0:
            _rounded_rect(
                d,
                (table_x0, row_y, table_x1, row_y + row_h - 4),
                14,
                ROW_ALT,
            )

        # Logo
        logo = logos.get(bank.slug)
        if logo is not None:
            logo_resized = logo.resize((64, 64), Image.LANCZOS)
            img.paste(logo_resized, (table_x0 + 24, row_y + (row_h - 64) // 2 - 2), logo_resized)
        else:
            initials = "".join(w[0] for w in bank.name_uz.split()[:2]).upper() or "?"
            badge_x, badge_y = table_x0 + 24, row_y + (row_h - 64) // 2 - 2
            _rounded_rect(d, (badge_x, badge_y, badge_x + 64, badge_y + 64), 16, ACCENT_DARK)
            f_init = _font(26, bold=True)
            tw = _text_w(d, initials, f_init)
            d.text(
                (badge_x + (64 - tw) / 2, badge_y + 14),
                initials,
                font=f_init,
                fill=(255, 255, 255),
            )

        # Bank name
        name_x = table_x0 + 24 + 64 + 18
        d.text((name_x, row_y + 22), bank.name_uz, font=f_td_name, fill=INK)
        if bank.name_ru and bank.name_ru != bank.name_uz:
            d.text((name_x, row_y + 54), bank.name_ru, font=f_td_label, fill=MUTED)

        # Rates
        d.text((col_buy_x, row_y + 30), _fmt_amount(bank.buy), font=f_td_rate, fill=INK)
        d.text((col_sell_x, row_y + 30), _fmt_amount(bank.sell), font=f_td_rate, fill=INK)

        row_y += row_h

    # ----- Footer -----
    footer_y = HEIGHT - MARGIN - 36
    f_footer = _font(20)
    d.text(
        (MARGIN, footer_y),
        "Manba  ·  Источник: kurs.uz, cbu.uz",
        font=f_footer,
        fill=MUTED,
    )

    return img


async def render_post(
    official: OfficialRate | None,
    banks: list[BankRate],
    today: date,
) -> Image.Image:
    logos = await _gather_logos(banks)
    return render(official, banks, today, logos)
