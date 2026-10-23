from dataclasses import dataclass
from enum import Enum


class Side(str, Enum):
    BUY = "buy"
    SELL = "sell"


@dataclass(frozen=True)
class Position:
    order_id: str
    symbol: str
    side: str
    volume: str
    entry_price: float
    stop_loss: float | None
    take_profit: float | None


def parse_price(text: str) -> float | None:
    cleaned = text.strip().replace(",", "")
    if cleaned in ("", "--"):
        return None
    return float(cleaned)


def format_price(value: float, like: str) -> str:
    decimals = len(like.strip().split(".")[1]) if "." in like else 0
    return f"{value:.{decimals}f}"
