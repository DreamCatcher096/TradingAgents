from __future__ import annotations

import json
import time

import pandas as pd

from tradingagents.dataflows.providers.base_provider import BaseChinaDataProvider
from tradingagents.utils.stock_utils import StockUtils


class AKShareProvider(BaseChinaDataProvider):
    def __init__(self):
        super().__init__("akshare")
        self.ak = None
        self._initialize_akshare()

    def _initialize_akshare(self) -> None:
        try:
            import akshare as ak

            self.ak = ak
            self.connected = True
        except Exception:
            self.connected = False

    def get_stock_data(
        self, symbol: str, start_date: str, end_date: str
    ) -> pd.DataFrame | None:
        if not self.connected or self.ak is None:
            return None

        try:
            normalized = StockUtils.normalize_symbol(symbol)
            digits = normalized.split(".", 1)[0]
            return self.ak.stock_zh_a_hist(
                symbol=digits,
                period="daily",
                start_date=start_date.replace("-", ""),
                end_date=end_date.replace("-", ""),
                adjust="qfq",
            )
        except Exception:
            return None

    def get_fundamentals(self, symbol: str) -> dict:
        if not self.connected or self.ak is None:
            return {}

        try:
            basic_info = self.get_stock_basic_info(symbol)
            quote = self.get_stock_quotes(symbol)
            financial_data = self.get_financial_data(symbol)

            result = {}
            if basic_info:
                result["basic_info"] = basic_info
            if quote:
                result["quote"] = quote
            if financial_data:
                result["financial_data"] = financial_data
            return result
        except Exception:
            return {}

    def get_stock_basic_info(self, symbol: str) -> dict:
        if not self.connected or self.ak is None:
            return {}

        try:
            normalized = StockUtils.normalize_symbol(symbol)
            digits = normalized.split(".", 1)[0]
            data = self.ak.stock_individual_info_em(symbol=digits)
            if data is None or data.empty:
                return {}
            return dict(zip(data.iloc[:, 0], data.iloc[:, 1], strict=False))
        except Exception:
            return {}

    def get_stock_quotes(self, symbol: str) -> dict:
        normalized = StockUtils.normalize_symbol(symbol)
        return self.get_batch_stock_quotes([normalized]).get(normalized, {})

    def get_batch_stock_quotes(self, symbols: list[str]) -> dict[str, dict]:
        if not self.connected or self.ak is None or not symbols:
            return {}

        snapshot = self._get_spot_snapshot()
        if snapshot is None or snapshot.empty:
            return {}

        requested_symbols = {
            StockUtils.normalize_symbol(symbol).split(".", 1)[
                0
            ]: StockUtils.normalize_symbol(symbol)
            for symbol in symbols
        }

        quotes = {}
        for _, row in snapshot.iterrows():
            digits = str(row.get("代码", "")).strip().zfill(6)
            normalized = requested_symbols.get(digits)
            if normalized is None:
                continue
            quotes[normalized] = self._build_quote(normalized, row)
        return quotes

    def get_news(self, symbol: str, limit: int = 10) -> list[dict]:
        if not self.connected:
            return []

        return self._get_stock_news_direct(symbol, limit)

    def _get_stock_news_direct(self, symbol: str, limit: int = 10) -> list[dict]:
        try:
            from curl_cffi import requests as curl_requests

            digits = StockUtils.normalize_symbol(symbol).split(".", 1)[0].zfill(6)
            url = "https://search-api-web.eastmoney.com/search/jsonp"
            payload = {
                "uid": "",
                "keyword": digits,
                "type": ["cmsArticleWebOld"],
                "client": "web",
                "clientType": "web",
                "clientVersion": "curr",
                "param": {
                    "cmsArticleWebOld": {
                        "searchScope": "default",
                        "sort": "default",
                        "pageIndex": 1,
                        "pageSize": limit,
                        "preTag": "<em>",
                        "postTag": "</em>",
                    }
                },
            }
            response = curl_requests.get(
                url,
                params={
                    "cb": f"jQuery{int(time.time() * 1000)}",
                    "param": json.dumps(payload),
                    "_": str(int(time.time() * 1000)),
                },
                timeout=10,
                impersonate="chrome120",
            )
            if response.status_code != 200:
                return []

            text = response.text
            if text.startswith("jQuery"):
                text = text[text.find("(") + 1 : text.rfind(")")]

            data = json.loads(text)
            articles = data.get("result", {}).get("cmsArticleWebOld", [])
            return [
                {
                    "title": article.get("title", ""),
                    "content": article.get("content", ""),
                    "published_at": article.get("date", ""),
                    "url": article.get("url", ""),
                    "source": article.get("source", "东方财富网"),
                }
                for article in articles[:limit]
            ]
        except Exception:
            return []

    def get_financial_data(self, symbol: str) -> dict:
        if not self.connected or self.ak is None:
            return {}

        digits = StockUtils.normalize_symbol(symbol).split(".", 1)[0]
        datasets = {
            "main_indicators": getattr(self.ak, "stock_financial_abstract", None),
            "balance_sheet": getattr(self.ak, "stock_balance_sheet_by_report_em", None),
            "income_statement": getattr(
                self.ak, "stock_profit_sheet_by_report_em", None
            ),
            "cash_flow": getattr(self.ak, "stock_cash_flow_sheet_by_report_em", None),
        }

        result = {}
        for name, method in datasets.items():
            if method is None:
                continue
            try:
                frame = method(symbol=digits)
            except Exception:
                continue
            if frame is not None and not frame.empty:
                result[name] = frame.to_dict("records")
        return result

    def _get_spot_snapshot(self) -> pd.DataFrame | None:
        try:
            return self.ak.stock_zh_a_spot()
        except Exception:
            try:
                return self.ak.stock_zh_a_spot_em()
            except Exception:
                return None

    def _build_quote(self, normalized_symbol: str, row: pd.Series) -> dict:
        def _to_float(value, *, scale: float = 1.0) -> float | None:
            try:
                if value in (None, ""):
                    return None
                return float(value) / scale
            except (TypeError, ValueError):
                return None

        return {
            "symbol": normalized_symbol,
            "name": str(row.get("名称", normalized_symbol.split(".", 1)[0])),
            "price": _to_float(row.get("最新价")) or 0.0,
            "change": _to_float(row.get("涨跌额")) or 0.0,
            "change_percent": _to_float(row.get("涨跌幅")) or 0.0,
            "volume": int(_to_float(row.get("成交量")) or 0),
            "amount": _to_float(row.get("成交额")) or 0.0,
            "open": _to_float(row.get("今开")) or 0.0,
            "high": _to_float(row.get("最高")) or 0.0,
            "low": _to_float(row.get("最低")) or 0.0,
            "pre_close": _to_float(row.get("昨收")) or 0.0,
            "turnover_rate": _to_float(row.get("换手率")),
            "volume_ratio": _to_float(row.get("量比")),
            "pe": _to_float(row.get("市盈率-动态")),
            "pb": _to_float(row.get("市净率")),
            "total_mv": _to_float(row.get("总市值"), scale=1e8),
            "circ_mv": _to_float(row.get("流通市值"), scale=1e8),
        }
