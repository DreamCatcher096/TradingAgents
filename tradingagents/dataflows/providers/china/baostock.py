from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd

from tradingagents.dataflows.providers.base_provider import BaseChinaDataProvider
from tradingagents.utils.stock_utils import StockUtils


class BaoStockProvider(BaseChinaDataProvider):
    def __init__(self):
        super().__init__("baostock")
        self.bs = None
        try:
            import baostock as bs

            self.bs = bs
            self.connected = True
        except Exception:
            self.connected = False

    def get_stock_data(
        self, symbol: str, start_date: str, end_date: str
    ) -> pd.DataFrame | None:
        if not self.connected or self.bs is None:
            return None

        login_result = None
        try:
            login_result = self.bs.login()
            if getattr(login_result, "error_code", "1") != "0":
                return None

            rs = self.bs.query_history_k_data_plus(
                code=self._to_baostock_code(symbol),
                fields="date,open,high,low,close,volume,amount",
                start_date=start_date,
                end_date=end_date,
                frequency="d",
                adjustflag="2",
            )
            if getattr(rs, "error_code", "1") != "0":
                return None

            rows = []
            while rs.error_code == "0" and rs.next():
                rows.append(rs.get_row_data())
            if not rows:
                return None
            return pd.DataFrame(rows, columns=rs.fields)
        except Exception:
            return None
        finally:
            if login_result is not None and self.bs is not None:
                try:
                    self.bs.logout()
                except Exception:
                    pass

    def get_fundamentals(self, symbol: str) -> dict:
        if not self.connected or self.bs is None:
            return {}

        result = {}
        quote = self.get_stock_quotes(symbol)
        valuation = self.get_valuation_data(symbol)
        financial_data = self.get_financial_data(symbol)

        if quote:
            result["quote"] = quote
        if valuation:
            result["valuation"] = valuation
        if financial_data:
            result["financial_data"] = financial_data
        return result

    def get_news(self, symbol: str, limit: int = 10) -> list[dict]:
        return []

    def get_stock_quotes(self, symbol: str) -> dict:
        if not self.connected or self.bs is None:
            return {}

        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")
        rows = self._query_history_rows(
            symbol,
            fields="date,code,open,high,low,close,preclose,volume,amount,pctChg",
            start_date=start_date,
            end_date=end_date,
            adjustflag="3",
        )
        if not rows:
            return {}

        latest = rows[-1]
        close = self._safe_float(latest[5])
        pre_close = self._safe_float(latest[6])
        return {
            "symbol": StockUtils.normalize_symbol(symbol),
            "open": self._safe_float(latest[2]),
            "high": self._safe_float(latest[3]),
            "low": self._safe_float(latest[4]),
            "close": close,
            "pre_close": pre_close,
            "volume": self._safe_int(latest[7]),
            "amount": self._safe_float(latest[8]),
            "change_percent": self._safe_float(latest[9]),
            "change": (close or 0.0) - (pre_close or 0.0),
        }

    def get_valuation_data(self, symbol: str, trade_date: str | None = None) -> dict:
        if not self.connected or self.bs is None:
            return {}

        end_date = trade_date or datetime.now().strftime("%Y-%m-%d")
        start_date = trade_date or (datetime.now() - timedelta(days=5)).strftime(
            "%Y-%m-%d"
        )
        rows = self._query_history_rows(
            symbol,
            fields="date,code,close,peTTM,pbMRQ,psTTM,pcfNcfTTM",
            start_date=start_date,
            end_date=end_date,
            adjustflag="3",
        )
        if not rows:
            return {}

        latest = rows[-1]
        return {
            "date": latest[0],
            "symbol": StockUtils.normalize_symbol(symbol),
            "close": self._safe_float(latest[2]),
            "pe_ttm": self._safe_float(latest[3]),
            "pb_mrq": self._safe_float(latest[4]),
            "ps_ttm": self._safe_float(latest[5]),
            "pcf_ttm": self._safe_float(latest[6]),
        }

    def get_financial_data(
        self, symbol: str, year: int | None = None, quarter: int | None = None
    ) -> dict:
        if not self.connected or self.bs is None:
            return {}

        if year is None:
            year = datetime.now().year
        if quarter is None:
            quarter = ((datetime.now().month - 1) // 3) + 1

        tables = {
            "profit_data": self.bs.query_profit_data,
            "operation_data": self.bs.query_operation_data,
            "growth_data": self.bs.query_growth_data,
            "balance_data": self.bs.query_balance_data,
            "cash_flow_data": self.bs.query_cash_flow_data,
        }

        result = {}
        for name, method in tables.items():
            record = self._query_financial_table_with_fallback(
                method,
                symbol,
                year,
                quarter,
            )
            if record:
                result[name] = record
        return result

    def _to_baostock_code(self, symbol: str) -> str:
        normalized = StockUtils.normalize_symbol(symbol)
        digits, exchange = normalized.split(".", 1)
        prefix_map = {
            "SH": "sh",
            "SZ": "sz",
            "BJ": "bj",
        }
        prefix = prefix_map.get(exchange, "sz")
        return f"{prefix}.{digits}"

    def _query_history_rows(
        self,
        symbol: str,
        *,
        fields: str,
        start_date: str,
        end_date: str,
        adjustflag: str,
    ) -> list[list[str]]:
        login_result = None
        try:
            login_result = self.bs.login()
            if getattr(login_result, "error_code", "1") != "0":
                return []

            rs = self.bs.query_history_k_data_plus(
                code=self._to_baostock_code(symbol),
                fields=fields,
                start_date=start_date,
                end_date=end_date,
                frequency="d",
                adjustflag=adjustflag,
            )
            if getattr(rs, "error_code", "1") != "0":
                return []

            rows = []
            while rs.error_code == "0" and rs.next():
                rows.append(rs.get_row_data())
            return rows
        except Exception:
            return []
        finally:
            if login_result is not None:
                try:
                    self.bs.logout()
                except Exception:
                    pass

    def _query_financial_table(
        self, method, symbol: str, year: int, quarter: int
    ) -> dict:
        login_result = None
        try:
            login_result = self.bs.login()
            if getattr(login_result, "error_code", "1") != "0":
                return {}

            rs = method(code=self._to_baostock_code(symbol), year=year, quarter=quarter)
            if getattr(rs, "error_code", "1") != "0":
                return {}

            rows = []
            while rs.error_code == "0" and rs.next():
                rows.append(rs.get_row_data())
            if not rows:
                return {}
            return pd.DataFrame(rows, columns=rs.fields).to_dict("records")[0]
        except Exception:
            return {}
        finally:
            if login_result is not None:
                try:
                    self.bs.logout()
                except Exception:
                    pass

    def _query_financial_table_with_fallback(
        self,
        method,
        symbol: str,
        year: int,
        quarter: int,
        max_periods: int = 4,
    ) -> dict:
        current_year = year
        current_quarter = quarter
        for _ in range(max_periods):
            record = self._query_financial_table(
                method,
                symbol,
                current_year,
                current_quarter,
            )
            if record:
                return record
            current_year, current_quarter = self._previous_period(
                current_year,
                current_quarter,
            )
        return {}

    def _previous_period(self, year: int, quarter: int) -> tuple[int, int]:
        if quarter <= 1:
            return year - 1, 4
        return year, quarter - 1

    def _safe_float(self, value: str | None) -> float | None:
        try:
            if value in (None, ""):
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

    def _safe_int(self, value: str | None) -> int:
        try:
            if value in (None, ""):
                return 0
            return int(float(value))
        except (TypeError, ValueError):
            return 0
