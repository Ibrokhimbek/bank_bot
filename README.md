# bank_bot

Telegram bot that posts daily USD exchange rates from Uzbek commercial banks as a single image, in Uzbek and Russian.

- Official rate: [cbu.uz](https://cbu.uz) JSON API
- Per-bank rates: scraped from [kurs.uz](https://kurs.uz) (8 commercial banks)
- Image: rendered locally with Pillow (1080×1400 PNG)
- Schedule: APScheduler cron, default 09:00 Asia/Tashkent

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edit .env with your bot token + channel ID
```

The bot must be added as an **administrator** of your Telegram channel before it can post.

## Usage

```bash
python bot.py preview   # render image only, save to out/, don't post
python bot.py post      # post immediately to the channel
python bot.py run       # start scheduler; posts daily at POST_TIME
```

## Configuration (`.env`)

| Variable | Default | Notes |
| --- | --- | --- |
| `TELEGRAM_BOT_TOKEN` | — | from [@BotFather](https://t.me/BotFather) |
| `TELEGRAM_CHANNEL_ID` | — | `@channel_username` or numeric `-100…` ID |
| `POST_TIME` | `09:00` | 24-hour, local to `TIMEZONE` |
| `TIMEZONE` | `Asia/Tashkent` | any IANA tz name |

## Project layout

```
rates/         CBU + kurs.uz fetchers
image_gen.py   Pillow image renderer
logo_cache.py  bank logo download + cache (assets/logos/_cache_*.png)
telegram_client.py  sendPhoto wrapper
bot.py         CLI entry point + scheduler
```

## Replacing bank logos

kurs.uz logos are favicons — some are tiny and pixelate. To use a higher-quality logo, drop a PNG named `{slug}.png` into `assets/logos/`. The slug matches the kurs.uz URL: `aab`, `agrobank`, `infinbank`, `ipotekabank`, `saderatbank`, `sqb`, `trustbank`, `xalqbank`. User-supplied logos take precedence over the cache.

## Adding more banks

Edit [rates/kursuz.py](rates/kursuz.py) — the scraper picks up every bank linked from the kurs.uz homepage automatically. To pull from a different source, add a new module under `rates/` and merge its results in [rates/aggregator.py](rates/aggregator.py).

## Notes

- kurs.uz is a third-party aggregator. If their HTML structure changes, the scraper in [rates/kursuz.py](rates/kursuz.py) needs an update.
- The CBU endpoint is stable but only returns the official rate, not commercial bank rates — that's why kurs.uz is used.
- Generated images are saved to `out/rates_YYYY-MM-DD.png` for inspection.
