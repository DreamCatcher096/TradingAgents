from __future__ import annotations

from enum import Enum
import re


class StockMarket(Enum):
    CHINA_A = "china_a"
    HONG_KONG = "hong_kong"
    US = "us"
    UNKNOWN = "unknown"


class StockUtils:
    _CHINA_PLAIN_SYMBOL_RE = re.compile(r"^[0-9]{6}$")
    _CHINA_PREFIXED_SYMBOL_RE = re.compile(r"^(SH|SZ|BJ)([0-9]{6})$")
    _CHINA_SUFFIXED_SYMBOL_RE = re.compile(r"^([0-9]{6})\.(SH|SZ|SS|BJ)$")
    _HK_SYMBOL_RE = re.compile(r"^[0-9]{4,5}(\.HK)?$")
    _US_SYMBOL_RE = re.compile(r"^[A-Z]{1,5}$")

    @staticmethod
    def identify_stock_market(symbol: str) -> StockMarket:
        normalized = StockUtils._clean_symbol(symbol)
        if not normalized:
            return StockMarket.UNKNOWN

        if StockUtils._is_china_symbol(normalized):
            return StockMarket.CHINA_A
        if StockUtils._HK_SYMBOL_RE.fullmatch(normalized):
            return StockMarket.HONG_KONG
        if StockUtils._US_SYMBOL_RE.fullmatch(normalized):
            return StockMarket.US
        return StockMarket.UNKNOWN

    @staticmethod
    def get_market_info(symbol: str) -> dict[str, object]:
        normalized = StockUtils.normalize_symbol(symbol)
        market = StockUtils.identify_stock_market(normalized)

        info_map = {
            StockMarket.CHINA_A: {
                "market_name": "China A",
                "currency_name": "Chinese Yuan",
                "currency_symbol": "¥",
                "timezone": "Asia/Shanghai",
            },
            StockMarket.HONG_KONG: {
                "market_name": "Hong Kong",
                "currency_name": "Hong Kong Dollar",
                "currency_symbol": "HK$",
                "timezone": "Asia/Hong_Kong",
            },
            StockMarket.US: {
                "market_name": "US",
                "currency_name": "US Dollar",
                "currency_symbol": "$",
                "timezone": "America/New_York",
            },
            StockMarket.UNKNOWN: {
                "market_name": "Unknown",
                "currency_name": "Unknown",
                "currency_symbol": "",
                "timezone": "UTC",
            },
        }

        info = info_map[market].copy()
        info.update(
            {
                "exchange": StockUtils._get_exchange(normalized, market),
                "is_china": market == StockMarket.CHINA_A,
                "is_hk": market == StockMarket.HONG_KONG,
                "is_us": market == StockMarket.US,
            }
        )
        return info

    @staticmethod
    def normalize_symbol(symbol: str) -> str:
        normalized = StockUtils._clean_symbol(symbol)
        if not normalized:
            return ""

        prefixed_match = StockUtils._CHINA_PREFIXED_SYMBOL_RE.fullmatch(normalized)
        if prefixed_match:
            exchange, digits = prefixed_match.groups()
            return f"{digits}.{exchange}"

        suffixed_match = StockUtils._CHINA_SUFFIXED_SYMBOL_RE.fullmatch(normalized)
        if suffixed_match:
            digits, exchange = suffixed_match.groups()
            if exchange == "SS":
                exchange = "SH"
            return f"{digits}.{exchange}"

        if StockUtils._CHINA_PLAIN_SYMBOL_RE.fullmatch(normalized):
            exchange = StockUtils._infer_china_exchange(normalized)
            if exchange:
                return f"{normalized}.{exchange}"

        if StockUtils._HK_SYMBOL_RE.fullmatch(normalized) and ".HK" not in normalized:
            return f"{normalized}.HK"

        return normalized

    @staticmethod
    def get_full_symbol(symbol: str) -> str:
        normalized = StockUtils.normalize_symbol(symbol)
        if normalized.endswith(".SH"):
            return normalized[:-3] + ".SS"
        return normalized

    @staticmethod
    def _clean_symbol(symbol: str) -> str:
        return str(symbol or "").strip().upper()

    @staticmethod
    def _is_china_symbol(symbol: str) -> bool:
        if StockUtils._CHINA_PLAIN_SYMBOL_RE.fullmatch(symbol):
            return StockUtils._infer_china_exchange(symbol) is not None
        if StockUtils._CHINA_PREFIXED_SYMBOL_RE.fullmatch(symbol):
            return True
        if StockUtils._CHINA_SUFFIXED_SYMBOL_RE.fullmatch(symbol):
            return True
        return False

    @staticmethod
    def _infer_china_exchange(symbol: str) -> str | None:
        if symbol.startswith(("5", "6", "9")):
            return "SH"
        if symbol.startswith(("0", "1", "2", "3")):
            return "SZ"
        if symbol.startswith(("4", "8")):
            return "BJ"
        return None

    @staticmethod
    def _get_exchange(symbol: str, market: StockMarket) -> str:
        if market == StockMarket.CHINA_A:
            if symbol.endswith(".BJ") or symbol.startswith(("4", "8")):
                return "Beijing Stock Exchange"
            if symbol.endswith(".SH") or symbol.startswith(("5", "6", "9")):
                return "Shanghai Stock Exchange"
            return "Shenzhen Stock Exchange"
        if market == StockMarket.HONG_KONG:
            return "Hong Kong Stock Exchange"
        if market == StockMarket.US:
            return "US Stock Market"
        return "Unknown"
