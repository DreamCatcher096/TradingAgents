import unittest

import pandas as pd

from tradingagents.dataflows.china_router import ChinaDataRouter


class ChinaRouterFormatTests(unittest.TestCase):
    def test_format_stock_data_response_contains_chinese_technical_indicators(self):
        router = ChinaDataRouter()

        dates = pd.date_range(start="2025-03-01", periods=80, freq="B")
        base_price = 100.0
        df = pd.DataFrame(
            {
                "Date": dates,
                "Open": [base_price + i * 0.1 for i in range(80)],
                "High": [base_price + i * 0.1 + 1.0 for i in range(80)],
                "Low": [base_price + i * 0.1 - 1.0 for i in range(80)],
                "Close": [base_price + i * 0.15 for i in range(80)],
                "Volume": [10000 + i * 100 for i in range(80)],
                "Amount": [1000000 + i * 1000 for i in range(80)],
            }
        )

        text = router._format_stock_data_response(
            df, "600519.SH", "2025-03-01", "2025-06-15"
        )

        self.assertIn("600519.SH", text)
        self.assertIn("移动平均线", text)
        self.assertIn("MA5", text)
        self.assertIn("MA10", text)
        self.assertIn("MA20", text)
        self.assertIn("MA60", text)
        self.assertIn("MACD", text)
        self.assertIn("RSI", text)
        self.assertIn("布林带", text)
        self.assertIn("成交量", text)
        self.assertIn("¥", text)


if __name__ == "__main__":
    unittest.main()
