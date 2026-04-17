import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from tradingagents.tools.unified_news_tool import UnifiedNewsAnalyzer


class UnifiedNewsTests(unittest.TestCase):
    def test_a_share_returns_chinese_news_when_router_has_items(self):
        """A股通过 ChinaDataRouter 获取新闻，返回包含中文新闻的字符串"""
        mock_news = [
            {
                "title": "贵州茅台业绩超预期",
                "content": "贵州茅台发布最新财报，营收增长20%...",
                "source": "东方财富",
                "publish_time": "2025-04-15 10:00",
            },
            {
                "title": "白酒行业景气度回升",
                "content": "多家券商上调白酒板块评级...",
                "source": "新浪财经",
                "publish_time": "2025-04-15 09:30",
            },
        ]
        router = SimpleNamespace(get_news=lambda symbol, limit: mock_news)
        toolkit = SimpleNamespace(china_router=router)
        analyzer = UnifiedNewsAnalyzer(toolkit)

        result = analyzer.get_stock_news_unified("600519.SH", max_news=10)

        self.assertIn("贵州茅台业绩超预期", result)
        self.assertIn("东方财富", result)
        self.assertIn("600519.SH 最新新闻", result)
        self.assertIn("=== 新闻数据来源: AKShare/东方财富 ===", result)
        self.assertTrue(len(result) > 100)

    @patch("tradingagents.tools.unified_news_tool.get_news")
    @patch("tradingagents.tools.unified_news_tool.get_global_news")
    def test_us_stock_falls_back_to_general_news_source(
        self, mock_get_global, mock_get_news
    ):
        """美股在通用新闻源可用时返回英文/通用新闻内容"""
        mock_get_news.invoke = MagicMock(
            return_value="Apple announced record iPhone sales this quarter, exceeding all analyst expectations by a significant margin."
        )
        mock_get_global.invoke = MagicMock(return_value="")
        toolkit = SimpleNamespace(china_router=SimpleNamespace())
        analyzer = UnifiedNewsAnalyzer(toolkit)

        result = analyzer.get_stock_news_unified("AAPL", max_news=10)

        self.assertIn("Apple announced record iPhone sales", result)
        self.assertIn("=== 新闻数据来源: 通用新闻源 ===", result)

    def test_empty_router_falls_back_gracefully(self):
        """当所有新闻源都不可用时返回错误提示"""
        router = SimpleNamespace(get_news=lambda symbol, limit: [])
        toolkit = SimpleNamespace(china_router=router)
        analyzer = UnifiedNewsAnalyzer(toolkit)

        with (
            patch("tradingagents.tools.unified_news_tool.get_news") as mock_get_news,
            patch(
                "tradingagents.tools.unified_news_tool.get_global_news"
            ) as mock_get_global,
        ):
            mock_get_news.invoke = MagicMock(return_value="")
            mock_get_global.invoke = MagicMock(return_value="")

            result = analyzer.get_stock_news_unified("600519.SH", max_news=10)

        self.assertIn("无法获取A股新闻数据", result)


if __name__ == "__main__":
    unittest.main()
