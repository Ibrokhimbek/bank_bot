import asyncio
import logging

import httpx

from rates.base import BankRate, OfficialRate
from rates.cbu import fetch_official
from rates.kursuz import fetch_bank_rates

log = logging.getLogger(__name__)


async def fetch_all() -> tuple[OfficialRate | None, list[BankRate]]:
    async with httpx.AsyncClient(follow_redirects=True) as client:
        official_task = asyncio.create_task(fetch_official(client))
        banks_task = asyncio.create_task(fetch_bank_rates(client))

        official: OfficialRate | None
        try:
            official = await official_task
        except Exception as e:
            log.warning("CBU official rate fetch failed: %s", e)
            official = None

        try:
            banks = await banks_task
        except Exception as e:
            log.warning("Bank rates fetch failed: %s", e)
            banks = []

    banks.sort(key=lambda b: (b.sell or 0), reverse=True)
    return official, banks
