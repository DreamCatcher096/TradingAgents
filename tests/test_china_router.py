import tempfile
import unittest
import os
from unittest.mock import patch

import pandas as pd

from tradingagents.dataflows.china_router import ChinaDataRouter
from tradingagents.dataflows.providers.china.baostock import BaoStockProvider
from tradingagents.dataflows.stockstats_utils import load_ohlcv


class ChinaRouterTests(unittest.TestCase):
    def test_standardize_historical_columns_maps_chinese_names(self):
        router = ChinaDataRouter()
        raw = pd.DataFrame(
            {
                "日期": ["2025-04-14"],
                "开盘": [100.0],
                "最高": [101.0],
                "最低": [99.0],
                "收盘": [100.5],
                "成交量": [100000],
                "成交额": [10050000],
            }
        )

        standardized = router._standardize_historical_columns(raw)

        self.assertEqual(
            list(standardized.columns),
            ["Date", "Open", "High", "Low", "Close", "Volume", "Amount"],
        )

    def test_load_ohlcv_routes_a_shares_to_china_router(self):
        china_df = pd.DataFrame(
            {
                "Date": pd.to_datetime(["2025-04-14", "2025-04-15"]),
                "Open": [100.0, 101.0],
                "High": [102.0, 103.0],
                "Low": [99.0, 100.0],
                "Close": [101.0, 102.0],
                "Volume": [100000, 120000],
            }
        )

        with patch(
            "tradingagents.dataflows.stockstats_utils.ChinaDataRouter"
        ) as mock_router:
            mock_router.return_value.get_stock_data_raw.return_value = china_df

            result = load_ohlcv("600519.SH", "2025-04-15")

        mock_router.return_value.get_stock_data_raw.assert_called_once()
        self.assertEqual(len(result), 2)
        self.assertEqual(result.iloc[-1]["Close"], 102.0)

    def test_load_ohlcv_keeps_yfinance_path_for_us_symbols(self):
        market_df = pd.DataFrame(
            {
                "Open": [10.0, 11.0],
                "High": [11.0, 12.0],
                "Low": [9.5, 10.5],
                "Close": [10.5, 11.5],
                "Volume": [1000, 1100],
            },
            index=pd.to_datetime(["2025-04-14", "2025-04-15"]),
        )
        market_df.index.name = "Date"

        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch(
                "tradingagents.dataflows.stockstats_utils.get_config",
                return_value={"data_cache_dir": tmp_dir},
            ):
                with patch(
                    "tradingagents.dataflows.stockstats_utils.ChinaDataRouter"
                ) as mock_router:
                    with patch(
                        "tradingagents.dataflows.stockstats_utils.yf.download",
                        return_value=market_df,
                    ) as mock_download:
                        result = load_ohlcv("AAPL", "2025-04-15")

        mock_router.return_value.get_stock_data_raw.assert_not_called()
        mock_download.assert_called_once()
        self.assertEqual(len(result), 2)
        self.assertIn("Date", result.columns)

    def test_load_ohlcv_keeps_yfinance_path_for_hk_symbols(self):
        market_df = pd.DataFrame(
            {
                "Open": [300.0, 305.0],
                "High": [306.0, 307.0],
                "Low": [299.0, 304.0],
                "Close": [305.0, 306.0],
                "Volume": [2000, 2200],
            },
            index=pd.to_datetime(["2025-04-14", "2025-04-15"]),
        )
        market_df.index.name = "Date"

        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch(
                "tradingagents.dataflows.stockstats_utils.get_config",
                return_value={"data_cache_dir": tmp_dir},
            ):
                with patch(
                    "tradingagents.dataflows.stockstats_utils.ChinaDataRouter"
                ) as mock_router:
                    with patch(
                        "tradingagents.dataflows.stockstats_utils.yf.download",
                        return_value=market_df,
                    ) as mock_download:
                        result = load_ohlcv("0700.HK", "2025-04-15")

        mock_router.return_value.get_stock_data_raw.assert_not_called()
        mock_download.assert_called_once()
        self.assertEqual(len(result), 2)
        self.assertIn("Date", result.columns)

    def test_router_skips_disabled_optional_providers(self):
        with patch.dict(
            os.environ,
            {"AKSHARE_ENABLED": "false", "BAOSTOCK_ENABLED": "false"},
            clear=False,
        ):
            with patch(
                "tradingagents.dataflows.china_router.AKShareProvider"
            ) as mock_akshare:
                with patch(
                    "tradingagents.dataflows.china_router.BaoStockProvider"
                ) as mock_baostock:
                    with patch(
                        "tradingagents.dataflows.china_router.TushareProvider"
                    ) as mock_tushare:
                        mock_tushare.return_value.is_available.return_value = False

                        ChinaDataRouter()

        mock_akshare.assert_not_called()
        mock_baostock.assert_not_called()

    def test_baostock_code_conversion_keeps_beijing_exchange(self):
        provider = BaoStockProvider()

        self.assertEqual(provider._to_baostock_code("430047.BJ"), "bj.430047")


if __name__ == "__main__":
    unittest.main()
