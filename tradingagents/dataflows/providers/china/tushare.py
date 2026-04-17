from __future__ import annotations

import os
from datetime import datetime, timedelta

import pandas as pd

from tradingagents.dataflows.providers.base_provider import BaseChinaDataProvider
from tradingagents.utils.stock_utils import StockUtils


class TushareProvider(BaseChinaDataProvider):
    def __init__(self):
        super().__init__("tushare")
        self.ts = None
        self.api = None
        self._connect_sync()

    def _connect_sync(self) -> None:
        token = os.getenv("TUSHARE_TOKEN")
        if not token:
            self.connected = False
            return

        try:
            import tushare as ts

            ts.set_token(token)
            self.ts = ts
            self.api = ts.pro_api()
            self.connected = self.api is not None
        except Exception:
            self.connected = False

    def get_stock_data(
        self, symbol: str, start_date: str, end_date: str
    ) -> pd.DataFrame | None:
        if not self.connected or self.ts is None:
            return None

        try:
            ts_code = StockUtils.normalize_symbol(symbol)
            return self.ts.pro_bar(
                ts_code=ts_code,
                start_date=start_date.replace("-", ""),
                end_date=end_date.replace("-", ""),
                adj="qfq",
            )
        except Exception:
            return None

    def get_fundamentals(self, symbol: str) -> dict:
        if not self.connected or self.api is None:
            return {}

        ts_code = StockUtils.normalize_symbol(symbol)
        try:
            daily_basic = self.api.daily_basic(ts_code=ts_code, limit=1)
        except Exception:
            daily_basic = None

        result = {}
        basic_info = self.get_stock_basic_info(symbol)
        quote = self.get_stock_quotes(symbol)
        financial_data = self.get_financial_data(symbol, limit=1)

        if basic_info:
            result["basic_info"] = basic_info
        if quote:
            result["quote"] = quote
        if daily_basic is not None and not daily_basic.empty:
            result["daily_basic"] = daily_basic.iloc[0].to_dict()
        if financial_data:
            result["financial_data"] = financial_data
        return result

    def get_stock_basic_info(self, symbol: str) -> dict:
        if not self.connected or self.api is None:
            return {}

        try:
            data = self.api.stock_basic(
                ts_code=StockUtils.normalize_symbol(symbol),
                fields="ts_code,symbol,name,area,industry,market,exchange,list_date",
            )
        except Exception:
            return {}

        if data is None or data.empty:
            return {}
        return data.iloc[0].to_dict()

    def get_stock_quotes(self, symbol: str) -> dict:
        if not self.connected or self.api is None:
            return {}

        ts_code = StockUtils.normalize_symbol(symbol)
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=3)).strftime("%Y%m%d")

        try:
            data = self.api.daily(
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date,
            )
        except Exception:
            return {}

        if data is None or data.empty:
            return {}

        row = data.iloc[0].to_dict()
        return {
            "ts_code": row.get("ts_code", ts_code),
            "symbol": ts_code,
            "trade_date": row.get("trade_date"),
            "open": row.get("open"),
            "high": row.get("high"),
            "low": row.get("low"),
            "close": row.get("close"),
            "pre_close": row.get("pre_close"),
            "change": row.get("change"),
            "pct_chg": row.get("pct_chg"),
            "volume": row.get("vol"),
            "amount": row.get("amount"),
        }

    def get_financial_data(self, symbol: str, limit: int = 4) -> dict:
        if not self.connected or self.api is None:
            return {}

        ts_code = StockUtils.normalize_symbol(symbol)
        frames = {
            "income_statement": self.api.income,
            "balance_sheet": self.api.balancesheet,
            "cashflow_statement": self.api.cashflow,
            "financial_indicators": self.api.fina_indicator,
        }

        result = {}
        for name, method in frames.items():
            try:
                frame = method(ts_code=ts_code, limit=limit)
            except Exception:
                continue
            if frame is not None and not frame.empty:
                result[name] = frame.to_dict("records")
        return result

    def get_news(self, symbol: str, limit: int = 10) -> list[dict]:
        if not self.connected or self.api is None:
            return []

        try:
            name = StockUtils.normalize_symbol(symbol).split(".", 1)[0]
            news = self.api.news(
                src="sina", start_date=None, end_date=None, limit=limit
            )
            if news is None or news.empty:
                return []
            filtered = news[news["title"].fillna("").str.contains(name)]
            return filtered.head(limit).to_dict("records")
        except Exception:
            return []
