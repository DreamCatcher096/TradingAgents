from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
import logging

from tradingagents.utils.stock_utils import StockUtils
from tradingagents.agents.utils.google_tool_handler import GoogleToolCallHandler

logger = logging.getLogger(__name__)


def _get_company_name_for_china_market(ticker: str, market_info: dict) -> str:
    """为中国市场分析师获取公司名称"""
    try:
        if market_info.get("is_china"):
            # 尝试从各个provider获取股票基础信息
            from tradingagents.dataflows.china_router import ChinaDataRouter

            router = ChinaDataRouter()
            for provider in router.providers:
                try:
                    if hasattr(provider, "get_stock_basic_info"):
                        info = provider.get_stock_basic_info(ticker)
                        if info and info.get("name"):
                            return info["name"]
                except Exception:
                    continue
            # 降级：返回代码本身
            return ticker
        elif market_info.get("is_hk"):
            return ticker
        elif market_info.get("is_us"):
            us_stock_names = {
                "AAPL": "苹果公司",
                "TSLA": "特斯拉",
                "NVDA": "英伟达",
                "MSFT": "微软",
                "GOOGL": "谷歌",
                "AMZN": "亚马逊",
                "META": "Meta",
                "NFLX": "奈飞",
            }
            return us_stock_names.get(ticker.upper(), f"美股{ticker}")
        else:
            return ticker
    except Exception as e:
        logger.error(f"[中国市场分析师] 获取公司名称失败: {e}")
        return ticker


def create_china_market_analyst(llm, toolkit):
    """创建中国市场分析师"""

    def china_market_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]

        market_info = StockUtils.get_market_info(ticker)
        company_name = _get_company_name_for_china_market(ticker, market_info)
        logger.info(f"[中国市场分析师] 公司名称: {company_name}")

        tools = [
            toolkit.get_stock_market_data_unified,
            toolkit.get_indicators_unified,
        ]

        system_message = (
            "您是一位专业的中国股市分析师，专门分析A股、港股等中国资本市场。"
            "您具备深厚的中国股市知识和丰富的本土投资经验。\n\n"
            "您的专业领域包括：\n"
            "1. A股市场分析: 深度理解A股的独特性，包括涨跌停制度、T+1交易、融资融券等\n"
            "2. 中国经济政策: 熟悉货币政策、财政政策对股市的影响机制\n"
            "3. 行业板块轮动: 掌握中国特色的板块轮动规律和热点切换\n"
            "4. 监管环境: 了解证监会政策、退市制度、注册制等监管变化\n"
            "5. 市场情绪: 理解中国投资者的行为特征和情绪波动\n\n"
            "分析重点：\n"
            "- 技术面分析: 使用提供的指标数据进行精确的技术指标分析\n"
            "- 基本面分析: 结合中国会计准则和财报特点进行分析\n"
            "- 政策面分析: 评估政策变化对个股和板块的影响\n"
            "- 资金面分析: 分析资金流向和市场情绪\n"
            "- 市场风格: 判断当前是成长风格还是价值风格占优\n\n"
            "中国股市特色考虑：\n"
            "- 涨跌停板限制对交易策略的影响\n"
            "- ST股票的特殊风险和机会\n"
            "- 科创板、创业板的差异化分析\n"
            "- 国企改革、混改等主题投资机会\n"
            "- 地缘政治对中概股的影响\n\n"
            "请基于提供的数据接口和技术指标，结合中国股市的特殊性，撰写专业的中文分析报告。"
            "确保在报告末尾附上Markdown表格总结关键发现和投资建议。"
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "您是一位专业的AI助手，与其他分析师协作进行股票分析。"
                    " 使用提供的工具获取和分析数据。"
                    " 如果您无法完全回答，没关系；其他分析师会补充您的分析。"
                    " 专注于您的专业领域，提供高质量的分析见解。"
                    " 您可以访问以下工具：{tool_names}。\n{system_message}"
                    "当前分析日期：{current_date}，分析标的：{ticker}。请用中文撰写所有分析内容。",
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        prompt = prompt.partial(system_message=system_message)
        tool_names = []
        for tool in tools:
            if hasattr(tool, "name"):
                tool_names.append(tool.name)
            elif hasattr(tool, "__name__"):
                tool_names.append(tool.__name__)
            else:
                tool_names.append(str(tool))

        prompt = prompt.partial(tool_names=", ".join(tool_names))
        prompt = prompt.partial(current_date=current_date)
        prompt = prompt.partial(ticker=ticker)

        chain = prompt | llm.bind_tools(tools)
        result = chain.invoke(state["messages"])

        report = ""

        if GoogleToolCallHandler.is_google_model(llm):
            logger.info("[中国市场分析师] 检测到Google模型，使用统一工具调用处理器")
            analysis_prompt_template = GoogleToolCallHandler.create_analysis_prompt(
                ticker=ticker,
                company_name=company_name,
                analyst_type="中国市场分析",
                specific_requirements="重点关注中国A股市场特点、政策影响、行业发展趋势等。",
            )
            report, messages = GoogleToolCallHandler.handle_google_tool_calls(
                result=result,
                llm=llm,
                tools=tools,
                state=state,
                analysis_prompt_template=analysis_prompt_template,
                analyst_name="中国市场分析师",
            )
        else:
            if len(result.tool_calls) == 0:
                report = result.content

        return {
            "messages": [result],
            "china_market_report": report,
            "sender": "ChinaMarketAnalyst",
        }

    return china_market_analyst_node
