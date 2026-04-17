from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd


class BaseChinaDataProvider(ABC):
    def __init__(self, provider_name: str):
        self.provider_name = provider_name
        self.connected = False

    def is_available(self) -> bool:
        return self.connected

    @abstractmethod
    def get_stock_data(
        self, symbol: str, start_date: str, end_date: str
    ) -> pd.DataFrame | None:
        """Return historical OHLCV data for a symbol."""

    @abstractmethod
    def get_fundamentals(self, symbol: str) -> dict:
        """Return a fundamentals snapshot for a symbol."""

    @abstractmethod
    def get_news(self, symbol: str, limit: int = 10) -> list[dict]:
        """Return recent news items for a symbol."""
