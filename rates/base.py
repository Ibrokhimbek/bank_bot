from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class BankRate:
    slug: str
    name_uz: str
    name_ru: str
    buy: float | None
    sell: float | None


@dataclass(frozen=True)
class OfficialRate:
    rate: float
    diff: float
    as_of: date
