import argparse
import asyncio
import logging
import os
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from dotenv import load_dotenv

from image_gen import render_post
from rates import fetch_all
from telegram_client import send_photo

log = logging.getLogger("bank_bot")

OUT_DIR = Path(__file__).parent / "out"


def _build_caption(today: date) -> str:
    months_uz = [
        "yanvar", "fevral", "mart", "aprel", "may", "iyun",
        "iyul", "avgust", "sentabr", "oktabr", "noyabr", "dekabr",
    ]
    months_ru = [
        "января", "февраля", "марта", "апреля", "мая", "июня",
        "июля", "августа", "сентября", "октября", "ноября", "декабря",
    ]
    uz = f"{today.day} {months_uz[today.month - 1]} {today.year}"
    ru = f"{today.day} {months_ru[today.month - 1]} {today.year}"
    return (
        f"<b>O'zbekiston banklari dollar kursi</b> — {uz}\n"
        f"<b>Курс доллара в банках Узбекистана</b> — {ru}"
    )


async def post_once(dry_run: bool = False) -> Path:
    today = date.today()
    log.info("Fetching rates for %s", today)
    official, banks = await fetch_all()

    if not banks:
        log.error("No bank rates fetched, skipping post")
        raise RuntimeError("no bank rates available")

    log.info("Got %d bank rates; official=%s", len(banks), official)
    img = await render_post(official, banks, today)

    OUT_DIR.mkdir(exist_ok=True)
    out_path = OUT_DIR / f"rates_{today.isoformat()}.png"
    img.save(out_path, "PNG", optimize=True)
    log.info("Saved %s", out_path)

    if dry_run:
        log.info("Dry run: skipping Telegram upload")
        return out_path

    token = os.environ["TELEGRAM_BOT_TOKEN"]
    channel = os.environ["TELEGRAM_CHANNEL_ID"]
    log.info("Posting to %s", channel)
    await send_photo(token, channel, img, caption=_build_caption(today))
    log.info("Posted")
    return out_path


def _scheduled_job():
    asyncio.create_task(_safe_post())


async def _safe_post():
    try:
        await post_once()
    except Exception:
        log.exception("Post failed")


def run_scheduler(every_minutes: int | None = None):
    tz_name = os.environ.get("TIMEZONE", "Asia/Tashkent")
    tz = ZoneInfo(tz_name)
    scheduler = AsyncIOScheduler(timezone=tz)

    if every_minutes is not None:
        scheduler.add_job(
            _scheduled_job,
            IntervalTrigger(minutes=every_minutes),
            id="interval_post",
            name=f"Interval post every {every_minutes}m",
            next_run_time=datetime.now(tz),
        )
        scheduler.start()
        log.info(
            "Scheduler started in INTERVAL mode: every %d min (firing now, then every %d min)",
            every_minutes, every_minutes,
        )
    else:
        post_time = os.environ.get("POST_TIME", "09:00")
        hour, minute = (int(x) for x in post_time.split(":"))
        scheduler.add_job(
            _scheduled_job,
            CronTrigger(hour=hour, minute=minute),
            id="daily_post",
            name="Daily bank rates post",
        )
        scheduler.start()
        log.info(
            "Scheduler started; daily at %02d:%02d %s — next: %s",
            hour, minute, tz_name,
            scheduler.get_job("daily_post").next_run_time,
        )

    loop = asyncio.get_event_loop()
    try:
        loop.run_forever()
    except (KeyboardInterrupt, SystemExit):
        log.info("Shutting down")
        scheduler.shutdown()


def main() -> None:
    load_dotenv()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_run = sub.add_parser("run", help="Run scheduler (daily post at POST_TIME)")
    p_run.add_argument(
        "--every",
        type=int,
        metavar="MINUTES",
        help="Test mode: post every N minutes instead of daily cron",
    )
    sub.add_parser("post", help="Post once now")
    sub.add_parser("preview", help="Render image without posting (saves to out/)")
    args = parser.parse_args()

    if args.cmd == "run":
        run_scheduler(every_minutes=args.every)
    elif args.cmd == "post":
        asyncio.run(post_once(dry_run=False))
    elif args.cmd == "preview":
        asyncio.run(post_once(dry_run=True))


if __name__ == "__main__":
    main()
