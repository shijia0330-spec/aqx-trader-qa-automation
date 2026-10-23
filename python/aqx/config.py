import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(REPO_ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    base_url: str
    login: str
    password: str
    symbol: str
    volume: str
    allow_trading: bool

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            base_url=os.getenv("AQX_BASE_URL", "https://aqxtrader.aquariux.com"),
            login=os.getenv("AQX_LOGIN", ""),
            password=os.getenv("AQX_PASSWORD", ""),
            symbol=os.getenv("AQX_SYMBOL", "EURUSD"),
            volume=os.getenv("AQX_VOLUME", "0.01"),
            allow_trading=os.getenv("AQX_ALLOW_TRADING") == "1",
        )

    @property
    def has_credentials(self) -> bool:
        return bool(self.login and self.password)
