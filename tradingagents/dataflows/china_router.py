from __future__ import annotations

import os

import pandas as pd

from tradingagents.dataflows.china_cache import ChinaDataCache
from tradingagents.dataflows.providers.china import (
    AKShareProvider,
    BaoStockProvider,
    TushareProvider,
)


class ChinaDataRouter:
    def __init__(self, provider_order: list[str] | None = None):
        self.provider_order = provider_order or ["akshare", "tushare", "baostock"]
        self.providers = self._build_providers()
        self.cache = ChinaDataCache()

    def _build_providers(self) -> list:
        provider_map = {
            "akshare": AKShareProvider,
            "tushare": TushareProvider,
            "baostock": BaoStockProvider,
        }

        providers = []
        for name in self.provider_order:
            provider_cls = provider_map.get(name)
            if provider_cls is None or not self._is_provider_enabled(name):
                continue
            provider = provider_cls()
            if provider.is_available():
                providers.append(provider)
        return providers

    def _is_provider_enabled(self, provider_name: str) -> bool:
        env_flags = {
            "akshare": os.getenv("AKSHARE_ENABLED", "true"),
            "baostock": os.getenv("BAOSTOCK_ENABLED", "true"),
        }
        return env_flags.get(provider_name, "true").strip().lower() not in {
            "0",
            "false",
            "no",
            "off",
        }

    def get_stock_data_raw(
        self, symbol: str, start_date: str, end_date: str
    ) -> pd.DataFrame:
        for provider in self.providers:
            provider_name = provider.__class__.__name__.lower().replace("provider", "")
            cached = self.cache.get_stock_data(
                symbol, start_date, end_date, provider_name
            )
            if cached is not None:
                return cached
            frame = provider.get_stock_data(symbol, start_date, end_date)
            if frame is not None and not frame.empty:
                standardized = self._standardize_historical_columns(frame)
                self.cache.save_stock_data(
                    standardized, symbol, start_date, end_date, provider_name
                )
                return standardized
        raise RuntimeError(f"Unable to fetch China market data for {symbol}")

    def get_stock_data(self, symbol: str, start_date: str, end_date: str) -> str:
        frame = self.get_stock_data_raw(symbol, start_date, end_date)
        return self._format_stock_data_response(frame, symbol, start_date, end_date)

    def get_fundamentals(self, symbol: str) -> dict:
        for provider in self.providers:
            provider_name = provider.__class__.__name__.lower().replace("provider", "")
            cached = self.cache.get_fundamentals(symbol, provider_name)
            if cached is not None:
                return cached
            data = provider.get_fundamentals(symbol)
            if data:
                self.cache.save_fundamentals(data, symbol, provider_name)
                return data
        return {}

    def get_news(self, symbol: str, limit: int = 10) -> list[dict]:
        for provider in self.providers:
            provider_name = provider.__class__.__name__.lower().replace("provider", "")
            cached = self.cache.get_news(symbol, provider_name, limit)
            if cached is not None:
                return cached
            news = provider.get_news(symbol, limit)
            if news:
                self.cache.save_news(news, symbol, provider_name, limit)
                return news
        return []

    def _standardize_historical_columns(self, frame: pd.DataFrame) -> pd.DataFrame:
        column_map = {
            "日期": "Date",
            "交易日期": "Date",
            "trade_date": "Date",
            "date": "Date",
            "Date": "Date",
            "开盘": "Open",
            "open": "Open",
            "Open": "Open",
            "最高": "High",
            "high": "High",
            "High": "High",
            "最低": "Low",
            "low": "Low",
            "Low": "Low",
            "收盘": "Close",
            "close": "Close",
            "Close": "Close",
            "成交量": "Volume",
            "vol": "Volume",
            "volume": "Volume",
            "Volume": "Volume",
            "成交额": "Amount",
            "amount": "Amount",
            "Amount": "Amount",
        }
        standardized = frame.rename(columns=column_map).copy()
        ordered_columns = [
            column
            for column in ["Date", "Open", "High", "Low", "Close", "Volume", "Amount"]
            if column in standardized.columns
        ]
        standardized = standardized[ordered_columns]
        if "Date" in standardized.columns:
            standardized["Date"] = pd.to_datetime(standardized["Date"], errors="coerce")
            standardized = standardized.dropna(subset=["Date"]).sort_values("Date")
        return standardized.reset_index(drop=True)

    def _format_stock_data_response(
        self, frame: pd.DataFrame, symbol: str, start_date: str, end_date: str
    ) -> str:
        df = frame.copy()
        df["Close"] = pd.to_numeric(df["Close"], errors="coerce")
        df["Volume"] = pd.to_numeric(df["Volume"], errors="coerce")
        df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce")
        df["High"] = pd.to_numeric(df["High"], errors="coerce")
        df["Low"] = pd.to_numeric(df["Low"], errors="coerce")
        df = df.dropna(subset=["Close"])

        close = df["Close"]
        latest = close.iloc[-1]

        def ma(n: int) -> float:
            return float(close.rolling(window=n).mean().iloc[-1])

        def ma_arrow(price: float, avg: float) -> str:
            return "↑" if price >= avg else "↓"

        ma5 = ma(5)
        ma10 = ma(10)
        ma20 = ma(20)
        ma60 = ma(60)

        # MACD
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        dif = ema12 - ema26
        dea = dif.ewm(span=9, adjust=False).mean()
        macd = (dif - dea) * 2
        latest_dif = float(dif.iloc[-1])
        latest_dea = float(dea.iloc[-1])
        latest_macd = float(macd.iloc[-1])
        macd_signal = ""
        if len(dif) >= 2:
            prev_dif = float(dif.iloc[-2])
            prev_dea = float(dea.iloc[-2])
            if prev_dif < prev_dea and latest_dif >= latest_dea:
                macd_signal = " (金叉)"
            elif prev_dif > prev_dea and latest_dif <= latest_dea:
                macd_signal = " (死叉)"

        # RSI
        def rsi(n: int) -> float:
            delta = close.diff()
            gain = delta.clip(lower=0)
            loss = -delta.clip(upper=0)
            avg_gain = gain.rolling(window=n).mean()
            avg_loss = loss.rolling(window=n).mean()
            rs = avg_gain / avg_loss
            value = 100 - (100 / (1 + rs))
            return float(value.iloc[-1])

        rsi6 = rsi(6)
        rsi12 = rsi(12)
        rsi24 = rsi(24)

        def rsi_label(value: float) -> str:
            if value >= 80:
                return "超买"
            if value <= 20:
                return "超卖"
            return ""

        # Bollinger Bands
        middle = close.rolling(window=20).mean()
        std = close.rolling(window=20).std()
        upper = middle + 2 * std
        lower = middle - 2 * std
        latest_upper = float(upper.iloc[-1])
        latest_lower = float(lower.iloc[-1])
        band_width = latest_upper - latest_lower
        position_pct = (
            ((latest - latest_lower) / band_width) * 100 if band_width != 0 else 50.0
        )

        high_price = float(df["High"].max())
        low_price = float(df["Low"].min())
        avg_price = float(close.mean())
        total_volume = int(df["Volume"].sum()) if "Volume" in df.columns else 0
        total_amount = float(df["Amount"].sum()) if "Amount" in df.columns else 0.0

        lines = [
            f"【{symbol} 历史行情分析】({start_date} ~ {end_date})",
            "",
            "= 移动平均线 =",
            f"MA5 : ¥{ma5:.2f} {ma_arrow(latest, ma5)}",
            f"MA10: ¥{ma10:.2f} {ma_arrow(latest, ma10)}",
            f"MA20: ¥{ma20:.2f} {ma_arrow(latest, ma20)}",
            f"MA60: ¥{ma60:.2f} {ma_arrow(latest, ma60)}",
            "",
            "= MACD =",
            f"DIF : {latest_dif:.3f}",
            f"DEA : {latest_dea:.3f}",
            f"MACD: {latest_macd:.3f}{macd_signal}",
            "",
            "= RSI =",
            f"RSI(6) : {rsi6:.2f} {rsi_label(rsi6)}",
            f"RSI(12): {rsi12:.2f} {rsi_label(rsi12)}",
            f"RSI(24): {rsi24:.2f} {rsi_label(rsi24)}",
            "",
            "= 布林带 =",
            f"上轨: ¥{latest_upper:.2f}",
            f"中轨: ¥{float(middle.iloc[-1]):.2f}",
            f"下轨: ¥{latest_lower:.2f}",
            f"价格位置: {position_pct:.1f}% (0%为下轨, 100%为上轨)",
            "",
            "= 统计摘要 =",
            f"区间最高价: ¥{high_price:.2f}",
            f"区间最低价: ¥{low_price:.2f}",
            f"区间平均价: ¥{avg_price:.2f}",
            f"总成交量: {total_volume:,}",
            f"总成交额: ¥{total_amount:,.2f}",
        ]

        return "\n".join(lines)
