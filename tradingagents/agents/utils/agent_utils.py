from datetime import datetime

from langchain_core.messages import HumanMessage, RemoveMessage

# Import tools from separate utility files
from tradingagents.agents.utils.core_stock_tools import get_stock_data
from tradingagents.agents.utils.technical_indicators_tools import get_indicators
from tradingagents.agents.utils.fundamental_data_tools import (
    get_fundamentals,
)
from tradingagents.agents.utils.news_data_tools import (
    get_global_news,
)
from tradingagents.dataflows.china_router import ChinaDataRouter
from tradingagents.tools.unified_news_tool import create_unified_news_tool
from tradingagents.utils.stock_utils import StockMarket, StockUtils
from tradingagents.default_config import DEFAULT_CONFIG


def get_language_instruction() -> str:
    """Return a prompt instruction for the configured output language.

    Returns empty string when English (default), so no extra tokens are used.
    Only applied to user-facing agents (analysts, portfolio manager).
    Internal debate agents stay in English for reasoning quality.
    """
    from tradingagents.dataflows.config import get_config

    lang = get_config().get("output_language", "English")
    if lang.strip().lower() == "english":
        return ""
    return f" Write your entire response in {lang}."


def build_instrument_context(ticker: str) -> str:
    """Describe the exact instrument so agents preserve exchange-qualified tickers."""
    normalized_ticker = StockUtils.normalize_symbol(ticker)
    market_info = StockUtils.get_market_info(normalized_ticker)

    context = (
        f"The instrument to analyze is `{normalized_ticker}`. "
        "Use this exact ticker in every tool call, report, and recommendation, "
        "preserving any exchange suffix (e.g. `.TO`, `.L`, `.HK`, `.T`)."
    )

    if market_info["market_name"] != "Unknown":
        context += (
            f" This instrument is listed in the {market_info['market_name']} market on the "
            f"{market_info['exchange']}, and trades in {market_info['currency_name']} "
            f"({market_info['currency_symbol']})."
        )

    return context


def create_msg_delete():
    def delete_messages(state):
        """Clear messages and add placeholder for Anthropic compatibility"""
        messages = state["messages"]

        # Remove all messages
        removal_operations = [RemoveMessage(id=m.id) for m in messages]

        # Add a minimal placeholder message
        placeholder = HumanMessage(content="Continue")

        return {"messages": removal_operations + [placeholder]}

    return delete_messages


class Toolkit:
    """统一工具包，根据市场自动选择数据源。"""

    def __init__(self, config: dict | None = None):
        self.config = config or DEFAULT_CONFIG
        self.china_router = ChinaDataRouter(provider_order=self.config.get("data_source_priority"))
        self.online = self.config.get("online_tools", True)
        self._unified_news_tool = create_unified_news_tool(self)

    def get_stock_market_data_unified(self, symbol: str, start_date: str, end_date: str) -> str:
        """Fetch unified stock market data (OHLCV) for a symbol across markets."""
        market = StockUtils.identify_stock_market(symbol)
        if market == StockMarket.CHINA_A:
            return self.china_router.get_stock_data(symbol, start_date, end_date)
        return get_stock_data.invoke({"symbol": symbol, "start_date": start_date, "end_date": end_date})

    def get_stock_fundamentals_unified(self, symbol: str, curr_date: str | None = None) -> str | dict:
        """Fetch unified fundamental financial data for a symbol across markets."""
        market = StockUtils.identify_stock_market(symbol)
        if market == StockMarket.CHINA_A:
            return self.china_router.get_fundamentals(symbol)
        if curr_date is None:
            curr_date = datetime.now().strftime("%Y-%m-%d")
        return get_fundamentals.invoke({"ticker": symbol, "curr_date": curr_date})

    def get_stock_news_unified(self, stock_code: str, max_news: int = 10, model_info: str = "") -> str:
        """Fetch unified news for a given stock code."""
        return self._unified_news_tool(stock_code, max_news, model_info)

    def get_stock_sentiment_unified(self, stock_code: str, max_news: int = 10) -> str:
        """基于新闻内容的关键词情绪统计（精简版）"""
        news_text = self.get_stock_news_unified(stock_code, max_news)
        if not news_text or "❌" in news_text:
            return "无法获取足够新闻进行情绪分析。"

        positive_keywords = [
            "上涨",
            "涨",
            "利好",
            "增长",
            "盈利",
            "突破",
            "强劲",
            "看好",
            "增持",
            "买入",
            "超预期",
            "反弹",
            "复苏",
            "扩张",
            "创新",
            "合作",
            "award",
            "beat",
            "growth",
            "profit",
            "strong",
            "bullish",
            "buy",
            "outperform",
            "upgrade",
            "partnership",
            "breakthrough",
        ]
        negative_keywords = [
            "下跌",
            "跌",
            "利空",
            "下滑",
            "亏损",
            "疲软",
            "看淡",
            "减持",
            "卖出",
            "不及预期",
            "暴跌",
            "衰退",
            "收缩",
            "裁员",
            "诉讼",
            "fine",
            "miss",
            "loss",
            "weak",
            "bearish",
            "sell",
            "underperform",
            "downgrade",
            "lawsuit",
            "investigation",
        ]

        text_lower = news_text.lower()
        pos_count = sum(1 for kw in positive_keywords if kw in text_lower)
        neg_count = sum(1 for kw in negative_keywords if kw in text_lower)
        total = pos_count + neg_count

        if total == 0:
            sentiment = "中性"
            score = 50
        else:
            score = int((pos_count / total) * 100)
            if score >= 60:
                sentiment = "偏多"
            elif score <= 40:
                sentiment = "偏空"
            else:
                sentiment = "中性"

        return (
            f"【{stock_code} 舆情情绪分析】\n"
            f"分析样本: 最近 {max_news} 条新闻\n"
            f"正面信号: {pos_count} 个\n"
            f"负面信号: {neg_count} 个\n"
            f"情绪得分: {score}/100\n"
            f"整体情绪: {sentiment}\n"
        )

    def get_indicators_unified(
        self,
        symbol: str,
        indicator: str,
        curr_date: str,
        look_back_days: int = 30,
    ) -> str:
        """Fetch unified technical indicators for a symbol."""
        return get_indicators.invoke(
            {
                "symbol": symbol,
                "indicator": indicator,
                "curr_date": curr_date,
                "look_back_days": look_back_days,
            }
        )

    def get_global_news_unified(
        self,
        curr_date: str,
        look_back_days: int = 7,
        limit: int = 5,
    ) -> str:
        """Fetch unified global macroeconomic news."""
        return get_global_news.invoke(
            {
                "curr_date": curr_date,
                "look_back_days": look_back_days,
                "limit": limit,
            }
        )
