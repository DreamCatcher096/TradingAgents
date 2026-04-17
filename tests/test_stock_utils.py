import unittest

from tradingagents.utils.stock_utils import StockMarket, StockUtils


class StockUtilsTests(unittest.TestCase):
    def test_identify_stock_market(self):
        cases = {
            "600519": StockMarket.CHINA_A,
            "000001.SZ": StockMarket.CHINA_A,
            "BJ430047": StockMarket.CHINA_A,
            "0700.HK": StockMarket.HONG_KONG,
            "AAPL": StockMarket.US,
        }

        for symbol, expected in cases.items():
            with self.subTest(symbol=symbol):
                self.assertEqual(StockUtils.identify_stock_market(symbol), expected)

    def test_normalize_symbol(self):
        self.assertEqual(StockUtils.normalize_symbol("600519"), "600519.SH")
        self.assertEqual(StockUtils.normalize_symbol("600519.SS"), "600519.SH")
        self.assertEqual(StockUtils.normalize_symbol("000001"), "000001.SZ")
        self.assertEqual(StockUtils.normalize_symbol("BJ430047"), "430047.BJ")

    def test_get_market_info_for_shanghai_a_share(self):
        info = StockUtils.get_market_info("600519")

        self.assertEqual(info["market_name"], "China A")
        self.assertEqual(info["exchange"], "Shanghai Stock Exchange")
        self.assertEqual(info["currency_name"], "Chinese Yuan")
        self.assertEqual(info["currency_symbol"], "¥")
        self.assertTrue(info["is_china"])


if __name__ == "__main__":
    unittest.main()
