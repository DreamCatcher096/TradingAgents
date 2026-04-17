#!/usr/bin/env python3
"""
统一新闻分析工具
整合A股、港股、美股等不同市场的新闻获取逻辑到一个工具函数中
"""

import logging
from datetime import datetime, timedelta

from tradingagents.agents.utils.news_data_tools import get_news, get_global_news
from tradingagents.utils.stock_utils import StockMarket, StockUtils

logger = logging.getLogger(__name__)


class UnifiedNewsAnalyzer:
    """统一新闻分析器，整合所有新闻获取逻辑"""

    def __init__(self, toolkit):
        """初始化统一新闻分析器

        Args:
            toolkit: 包含各种新闻获取工具的工具包
        """
        self.toolkit = toolkit

    def get_stock_news_unified(
        self, stock_code: str, max_news: int = 10, model_info: str = ""
    ) -> str:
        """
        统一新闻获取接口
        根据股票代码自动识别股票类型并获取相应新闻
        """
        logger.info(f"[统一新闻工具] 开始获取 {stock_code} 的新闻")

        market = StockUtils.identify_stock_market(stock_code)

        if market == StockMarket.CHINA_A:
            result = self._get_a_share_news(stock_code, max_news, model_info)
        elif market == StockMarket.HONG_KONG:
            result = self._get_hk_share_news(stock_code, max_news, model_info)
        elif market == StockMarket.US:
            result = self._get_us_share_news(stock_code, max_news, model_info)
        else:
            # 默认按美股逻辑处理
            result = self._get_us_share_news(stock_code, max_news, model_info)

        logger.info(f"[统一新闻工具] 新闻获取完成，结果长度: {len(result)} 字符")

        if not result or len(result.strip()) < 50:
            logger.warning(f"[统一新闻工具] 返回结果异常短或为空！")

        return result

    def _get_a_share_news(
        self, stock_code: str, max_news: int, model_info: str = ""
    ) -> str:
        """获取A股新闻"""
        logger.info(f"[统一新闻工具] 获取A股 {stock_code} 新闻")

        curr_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

        # 优先级1: ChinaDataRouter (AKShare东方财富等)
        try:
            news_items = self.toolkit.china_router.get_news(stock_code, limit=max_news)
            if news_items:
                formatted = self._format_news_items(news_items, stock_code)
                logger.info(
                    f"[统一新闻工具] AKShare/ChinaRouter新闻获取成功: {len(formatted)} 字符"
                )
                return self._format_news_result(
                    formatted, "AKShare/东方财富", model_info
                )
        except Exception as e:
            logger.warning(f"[统一新闻工具] ChinaRouter新闻获取失败: {e}")

        # 优先级2: 原版新闻工具 (通过yfinance/alpha_vantage)
        try:
            result = get_news.invoke(
                {"ticker": stock_code, "start_date": start_date, "end_date": curr_date}
            )
            if result and len(result.strip()) > 50:
                logger.info(f"[统一新闻工具] 通用新闻工具获取成功: {len(result)} 字符")
                return self._format_news_result(result, "通用新闻源", model_info)
        except Exception as e:
            logger.warning(f"[统一新闻工具] 通用新闻工具获取失败: {e}")

        # 优先级3: 全球新闻
        try:
            result = get_global_news.invoke(
                {
                    "curr_date": curr_date,
                    "look_back_days": 7,
                    "limit": min(max_news, 10),
                }
            )
            if result and len(result.strip()) > 50:
                logger.info(f"[统一新闻工具] 全球新闻获取成功: {len(result)} 字符")
                return self._format_news_result(result, "全球新闻", model_info)
        except Exception as e:
            logger.warning(f"[统一新闻工具] 全球新闻获取失败: {e}")

        return "❌ 无法获取A股新闻数据，所有新闻源均不可用"

    def _get_hk_share_news(
        self, stock_code: str, max_news: int, model_info: str = ""
    ) -> str:
        """获取港股新闻"""
        logger.info(f"[统一新闻工具] 获取港股 {stock_code} 新闻")

        curr_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

        # 优先级1: 通用新闻工具
        try:
            result = get_news.invoke(
                {"ticker": stock_code, "start_date": start_date, "end_date": curr_date}
            )
            if result and len(result.strip()) > 50:
                logger.info(f"[统一新闻工具] 港股通用新闻获取成功: {len(result)} 字符")
                return self._format_news_result(result, "通用新闻源", model_info)
        except Exception as e:
            logger.warning(f"[统一新闻工具] 港股通用新闻获取失败: {e}")

        # 优先级2: 全球新闻
        try:
            result = get_global_news.invoke(
                {
                    "curr_date": curr_date,
                    "look_back_days": 7,
                    "limit": min(max_news, 10),
                }
            )
            if result and len(result.strip()) > 50:
                logger.info(f"[统一新闻工具] 港股全球新闻获取成功: {len(result)} 字符")
                return self._format_news_result(result, "全球新闻", model_info)
        except Exception as e:
            logger.warning(f"[统一新闻工具] 港股全球新闻获取失败: {e}")

        # 优先级3: 尝试AKShare (部分港股有覆盖)
        try:
            news_items = self.toolkit.china_router.get_news(stock_code, limit=max_news)
            if news_items:
                formatted = self._format_news_items(news_items, stock_code)
                logger.info(
                    f"[统一新闻工具] 港股AKShare新闻获取成功: {len(formatted)} 字符"
                )
                return self._format_news_result(formatted, "AKShare", model_info)
        except Exception as e:
            logger.warning(f"[统一新闻工具] 港股AKShare新闻获取失败: {e}")

        return "❌ 无法获取港股新闻数据，所有新闻源均不可用"

    def _get_us_share_news(
        self, stock_code: str, max_news: int, model_info: str = ""
    ) -> str:
        """获取美股新闻"""
        logger.info(f"[统一新闻工具] 获取美股 {stock_code} 新闻")

        curr_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

        # 优先级1: 通用新闻工具
        try:
            result = get_news.invoke(
                {"ticker": stock_code, "start_date": start_date, "end_date": curr_date}
            )
            if result and len(result.strip()) > 50:
                logger.info(f"[统一新闻工具] 美股通用新闻获取成功: {len(result)} 字符")
                return self._format_news_result(result, "通用新闻源", model_info)
        except Exception as e:
            logger.warning(f"[统一新闻工具] 美股通用新闻获取失败: {e}")

        # 优先级2: 全球新闻
        try:
            result = get_global_news.invoke(
                {
                    "curr_date": curr_date,
                    "look_back_days": 7,
                    "limit": min(max_news, 10),
                }
            )
            if result and len(result.strip()) > 50:
                logger.info(f"[统一新闻工具] 美股全球新闻获取成功: {len(result)} 字符")
                return self._format_news_result(result, "全球新闻", model_info)
        except Exception as e:
            logger.warning(f"[统一新闻工具] 美股全球新闻获取失败: {e}")

        return "❌ 无法获取美股新闻数据，所有新闻源均不可用"

    def _format_news_items(self, news_items: list, stock_code: str) -> str:
        """将AKShare返回的新闻列表格式化为字符串"""
        if not news_items:
            return ""

        lines = [f"# {stock_code} 最新新闻\n"]
        for i, news in enumerate(news_items, 1):
            title = news.get("title", "无标题") if isinstance(news, dict) else str(news)
            content = news.get("content", "") if isinstance(news, dict) else ""
            source = (
                news.get("source", "未知来源") if isinstance(news, dict) else "未知来源"
            )
            publish_time = (
                news.get("publish_time", "") if isinstance(news, dict) else ""
            )

            lines.append(f"## {i}. {title}")
            if source or publish_time:
                lines.append(f"**来源**: {source} | **时间**: {publish_time}")
            if content:
                preview = content[:300] + "..." if len(content) > 300 else content
                lines.append(f"{preview}")
            lines.append("")

        return "\n".join(lines)

    def _format_news_result(
        self, news_content: str, source: str, model_info: str = ""
    ) -> str:
        """格式化新闻结果"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        is_google_model = any(
            keyword in model_info.lower() for keyword in ["google", "gemini", "gemma"]
        )
        original_length = len(news_content)
        google_control_applied = False

        # 对Google模型进行特殊的长度控制
        if is_google_model and len(news_content) > 5000:
            logger.warning(
                f"[统一新闻工具] 检测到Google模型，新闻内容过长({len(news_content)}字符)，进行长度控制..."
            )

            lines = news_content.split("\n")
            important_lines = []
            char_count = 0
            target_length = 3000

            important_keywords = [
                "股票",
                "公司",
                "财报",
                "业绩",
                "涨跌",
                "价格",
                "市值",
                "营收",
                "利润",
                "增长",
                "下跌",
                "上涨",
                "盈利",
                "亏损",
                "投资",
                "分析",
                "预期",
                "公告",
            ]

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                is_important = any(keyword in line for keyword in important_keywords)

                if is_important and char_count + len(line) < target_length:
                    important_lines.append(line)
                    char_count += len(line)
                elif not is_important and char_count + len(line) < target_length * 0.7:
                    important_lines.append(line)
                    char_count += len(line)

                if char_count >= target_length:
                    break

            if important_lines:
                processed_content = "\n".join(important_lines)
                if len(processed_content) > target_length:
                    processed_content = (
                        processed_content[:target_length] + "...(内容已智能截断)"
                    )
                news_content = processed_content
                google_control_applied = True
                logger.info(
                    f"[统一新闻工具] Google模型智能长度控制完成，从{original_length}字符压缩至{len(news_content)}字符"
                )
            else:
                news_content = news_content[:target_length] + "...(内容已强制截断)"
                google_control_applied = True
                logger.info(f"[统一新闻工具] Google模型强制截断至{target_length}字符")

        base_format_length = 300
        if is_google_model and (len(news_content) + base_format_length) > 4000:
            max_content_length = 3500
            if len(news_content) > max_content_length:
                news_content = news_content[:max_content_length] + "...(已优化长度)"
                google_control_applied = True
                logger.info(
                    f"[统一新闻工具] Google模型最终长度优化，内容长度: {len(news_content)}字符"
                )

        formatted_result = f"""
=== 新闻数据来源: {source} ===
获取时间: {timestamp}
数据长度: {len(news_content)} 字符
{f"模型类型: {model_info}" if model_info else ""}
{f"Google模型长度控制已应用 (原长度: {original_length} 字符)" if google_control_applied else ""}

=== 新闻内容 ===
{news_content}

=== 数据状态 ===
状态: 成功获取
来源: {source}
时间戳: {timestamp}
"""
        return formatted_result.strip()


def create_unified_news_tool(toolkit):
    """创建统一新闻工具函数"""
    analyzer = UnifiedNewsAnalyzer(toolkit)

    def get_stock_news_unified(
        stock_code: str, max_news: int = 100, model_info: str = ""
    ):
        """
        统一新闻获取工具

        Args:
            stock_code (str): 股票代码 (支持A股如600519.SH、港股如0700.HK、美股如AAPL)
            max_news (int): 最大新闻数量，默认100
            model_info (str): 当前使用的模型信息，用于特殊处理

        Returns:
            str: 格式化的新闻内容
        """
        if not stock_code:
            return "❌ 错误: 未提供股票代码"

        return analyzer.get_stock_news_unified(stock_code, max_news, model_info)

    get_stock_news_unified.name = "get_stock_news_unified"
    get_stock_news_unified.description = """
统一新闻获取工具 - 根据股票代码自动获取相应市场的新闻

功能:
- 自动识别股票类型（A股/港股/美股）
- A股: 优先AKShare/东方财富 -> 通用新闻源 -> 全球新闻
- 港股: 优先通用新闻源 -> 全球新闻 -> AKShare
- 美股: 优先通用新闻源 -> 全球新闻
- 返回格式化的新闻内容
- 支持Google模型的特殊长度控制
"""

    return get_stock_news_unified
