import unittest
from unittest.mock import Mock

import pandas as pd

from tradingagents.dataflows.providers.china.akshare import AKShareProvider
from tradingagents.dataflows.providers.china.baostock import BaoStockProvider
from tradingagents.dataflows.providers.china.tushare import TushareProvider


class _FakeBaoResult:
    def __init__(self, fields, rows):
        self.error_code = "0"
        self.error_msg = ""
        self.fields = fields
        self._rows = rows
        self._index = -1

    def next(self):
        self._index += 1
        return self._index < len(self._rows)

    def get_row_data(self):
        return self._rows[self._index]


class ChinaProviderTests(unittest.TestCase):
    def test_akshare_batch_quotes_extract_requested_symbols(self):
        provider = AKShareProvider()
        provider.connected = True
        provider.ak = Mock()
        provider.ak.stock_zh_a_spot.return_value = pd.DataFrame(
            [
                {
                    "代码": "600519",
                    "名称": "贵州茅台",
                    "最新价": 1500.5,
                    "涨跌额": 12.3,
                    "涨跌幅": 0.82,
                    "成交量": 1000,
                    "成交额": 2000,
                    "今开": 1490.0,
                    "最高": 1510.0,
                    "最低": 1488.0,
                    "昨收": 1488.2,
                    "换手率": 0.3,
                    "量比": 1.1,
                    "市盈率-动态": 22.5,
                    "市净率": 8.2,
                    "总市值": 1880000000000,
                    "流通市值": 1880000000000,
                },
                {
                    "代码": "000001",
                    "名称": "平安银行",
                    "最新价": 10.5,
                    "涨跌额": 0.1,
                    "涨跌幅": 0.96,
                    "成交量": 3000,
                    "成交额": 4000,
                    "今开": 10.4,
                    "最高": 10.6,
                    "最低": 10.2,
                    "昨收": 10.4,
                },
            ]
        )

        quotes = provider.get_batch_stock_quotes(["600519.SH", "000001.SZ"])

        self.assertEqual(set(quotes.keys()), {"600519.SH", "000001.SZ"})
        self.assertEqual(quotes["600519.SH"]["name"], "贵州茅台")
        self.assertAlmostEqual(quotes["600519.SH"]["price"], 1500.5)
        self.assertAlmostEqual(quotes["600519.SH"]["total_mv"], 18800.0)

    def test_akshare_fundamentals_include_quote_and_financial_sets(self):
        provider = AKShareProvider()
        provider.connected = True
        provider.ak = Mock()
        provider.ak.stock_individual_info_em.return_value = pd.DataFrame(
            [["股票简称", "贵州茅台"], ["行业", "白酒"]]
        )
        provider.ak.stock_zh_a_spot.return_value = pd.DataFrame(
            [
                {
                    "代码": "600519",
                    "名称": "贵州茅台",
                    "最新价": 1500.5,
                    "涨跌额": 12.3,
                    "涨跌幅": 0.82,
                    "成交量": 1000,
                    "成交额": 2000,
                    "今开": 1490.0,
                    "最高": 1510.0,
                    "最低": 1488.0,
                    "昨收": 1488.2,
                }
            ]
        )
        provider.ak.stock_financial_abstract.return_value = pd.DataFrame(
            [{"报告期": "2024Q4", "净资产收益率": 32.1}]
        )
        provider.ak.stock_balance_sheet_by_report_em.return_value = pd.DataFrame(
            [{"报告期": "2024Q4", "资产总计": 200.0}]
        )
        provider.ak.stock_profit_sheet_by_report_em.return_value = pd.DataFrame(
            [{"报告期": "2024Q4", "营业总收入": 100.0}]
        )
        provider.ak.stock_cash_flow_sheet_by_report_em.return_value = pd.DataFrame(
            [{"报告期": "2024Q4", "经营活动现金流量净额": 50.0}]
        )

        fundamentals = provider.get_fundamentals("600519.SH")

        self.assertEqual(fundamentals["basic_info"]["股票简称"], "贵州茅台")
        self.assertAlmostEqual(fundamentals["quote"]["price"], 1500.5)
        self.assertEqual(
            fundamentals["financial_data"]["main_indicators"][0]["净资产收益率"],
            32.1,
        )

    def test_tushare_fundamentals_include_quote_and_financial_sets(self):
        provider = TushareProvider()
        provider.connected = True
        provider.api = Mock()
        provider.ts = Mock()
        provider.api.stock_basic.return_value = pd.DataFrame(
            [
                {
                    "ts_code": "600519.SH",
                    "symbol": "600519",
                    "name": "贵州茅台",
                    "area": "贵州",
                    "industry": "白酒",
                    "market": "主板",
                    "exchange": "SSE",
                    "list_date": "20010827",
                }
            ]
        )
        provider.api.daily.return_value = pd.DataFrame(
            [
                {
                    "ts_code": "600519.SH",
                    "trade_date": "20250415",
                    "open": 1490.0,
                    "high": 1510.0,
                    "low": 1488.0,
                    "close": 1500.5,
                    "pre_close": 1488.2,
                    "change": 12.3,
                    "pct_chg": 0.82,
                    "vol": 1000,
                    "amount": 2000,
                }
            ]
        )
        provider.api.daily_basic.return_value = pd.DataFrame(
            [{"ts_code": "600519.SH", "trade_date": "20250415", "pe_ttm": 24.6}]
        )
        provider.api.income.return_value = pd.DataFrame(
            [{"ts_code": "600519.SH", "revenue": 100.0}]
        )
        provider.api.balancesheet.return_value = pd.DataFrame(
            [{"ts_code": "600519.SH", "total_assets": 200.0}]
        )
        provider.api.cashflow.return_value = pd.DataFrame(
            [{"ts_code": "600519.SH", "net_cash_flows_oper_act": 50.0}]
        )
        provider.api.fina_indicator.return_value = pd.DataFrame(
            [{"ts_code": "600519.SH", "roe": 32.1}]
        )

        fundamentals = provider.get_fundamentals("600519.SH")

        self.assertEqual(fundamentals["basic_info"]["name"], "贵州茅台")
        self.assertAlmostEqual(fundamentals["quote"]["close"], 1500.5)
        self.assertAlmostEqual(fundamentals["daily_basic"]["pe_ttm"], 24.6)
        self.assertEqual(
            fundamentals["financial_data"]["income_statement"][0]["revenue"],
            100.0,
        )

    def test_tushare_fundamentals_do_not_fail_when_daily_basic_is_unavailable(self):
        provider = TushareProvider()
        provider.connected = True
        provider.api = Mock()
        provider.ts = Mock()
        provider.api.stock_basic.return_value = pd.DataFrame(
            [{"ts_code": "600519.SH", "name": "贵州茅台"}]
        )
        provider.api.daily.return_value = pd.DataFrame(
            [{"ts_code": "600519.SH", "close": 1500.5, "trade_date": "20250415"}]
        )
        provider.api.daily_basic.side_effect = RuntimeError("daily_basic unavailable")
        provider.api.income.return_value = pd.DataFrame(
            [{"ts_code": "600519.SH", "revenue": 100.0}]
        )
        provider.api.balancesheet.return_value = pd.DataFrame()
        provider.api.cashflow.return_value = pd.DataFrame()
        provider.api.fina_indicator.return_value = pd.DataFrame()

        fundamentals = provider.get_fundamentals("600519.SH")

        self.assertEqual(fundamentals["basic_info"]["name"], "贵州茅台")
        self.assertAlmostEqual(fundamentals["quote"]["close"], 1500.5)
        self.assertNotIn("daily_basic", fundamentals)

    def test_tushare_quote_normalizes_plain_a_share_symbol(self):
        provider = TushareProvider()
        provider.connected = True
        provider.api = Mock()
        provider.api.daily.return_value = pd.DataFrame(
            [{"ts_code": "600519.SH", "close": 1500.5, "trade_date": "20250415"}]
        )

        quote = provider.get_stock_quotes("600519")

        self.assertEqual(quote["symbol"], "600519.SH")

    def test_baostock_fundamentals_merge_quote_valuation_and_financials(self):
        provider = BaoStockProvider()
        provider.connected = True
        provider.bs = Mock()
        provider.bs.login.side_effect = lambda: Mock(error_code="0", error_msg="")
        provider.bs.query_history_k_data_plus.side_effect = [
            _FakeBaoResult(
                [
                    "date",
                    "code",
                    "open",
                    "high",
                    "low",
                    "close",
                    "preclose",
                    "volume",
                    "amount",
                    "pctChg",
                ],
                [
                    [
                        "2025-04-15",
                        "sh.600519",
                        "1490",
                        "1510",
                        "1488",
                        "1500.5",
                        "1488.2",
                        "1000",
                        "2000",
                        "0.82",
                    ]
                ],
            ),
            _FakeBaoResult(
                ["date", "code", "close", "peTTM", "pbMRQ", "psTTM", "pcfNcfTTM"],
                [["2025-04-15", "sh.600519", "1500.5", "22.5", "8.2", "10.1", "11.2"]],
            ),
        ]
        provider.bs.query_profit_data.return_value = _FakeBaoResult(
            ["code", "pubDate", "roeAvg"], [["sh.600519", "2025-03-31", "20.5"]]
        )
        provider.bs.query_operation_data.return_value = _FakeBaoResult(
            ["code", "pubDate", "NRTurnRatio"], [["sh.600519", "2025-03-31", "1.2"]]
        )
        provider.bs.query_growth_data.return_value = _FakeBaoResult(
            ["code", "pubDate", "YOYEquity"], [["sh.600519", "2025-03-31", "12.1"]]
        )
        provider.bs.query_balance_data.return_value = _FakeBaoResult(
            ["code", "pubDate", "currentRatio"], [["sh.600519", "2025-03-31", "2.1"]]
        )
        provider.bs.query_cash_flow_data.return_value = _FakeBaoResult(
            ["code", "pubDate", "CAToAsset"], [["sh.600519", "2025-03-31", "0.4"]]
        )

        fundamentals = provider.get_fundamentals("600519.SH")

        self.assertAlmostEqual(fundamentals["quote"]["close"], 1500.5)
        self.assertAlmostEqual(fundamentals["valuation"]["pe_ttm"], 22.5)
        self.assertIn("profit_data", fundamentals["financial_data"])

    def test_baostock_financial_data_falls_back_to_previous_quarter(self):
        provider = BaoStockProvider()
        provider.connected = True
        provider.bs = Mock()
        provider.bs.login.side_effect = lambda: Mock(error_code="0", error_msg="")
        provider.bs.query_profit_data.side_effect = [
            _FakeBaoResult(["code", "pubDate", "roeAvg"], []),
            _FakeBaoResult(
                ["code", "pubDate", "roeAvg"], [["sh.600519", "2025-03-31", "20.5"]]
            ),
        ]
        provider.bs.query_operation_data.return_value = _FakeBaoResult(
            ["code", "pubDate", "NRTurnRatio"], []
        )
        provider.bs.query_growth_data.return_value = _FakeBaoResult(
            ["code", "pubDate", "YOYEquity"], []
        )
        provider.bs.query_balance_data.return_value = _FakeBaoResult(
            ["code", "pubDate", "currentRatio"], []
        )
        provider.bs.query_cash_flow_data.return_value = _FakeBaoResult(
            ["code", "pubDate", "CAToAsset"], []
        )

        financial_data = provider.get_financial_data("600519.SH", year=2025, quarter=2)

        self.assertEqual(financial_data["profit_data"]["pubDate"], "2025-03-31")


if __name__ == "__main__":
    unittest.main()
