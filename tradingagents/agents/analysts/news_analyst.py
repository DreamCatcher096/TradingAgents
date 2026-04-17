import logging

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from tradingagents.agents.utils.agent_utils import (
    build_instrument_context,
    get_language_instruction,
)
from tradingagents.agents.utils.google_tool_handler import GoogleToolCallHandler

logger = logging.getLogger(__name__)


def create_news_analyst(llm, toolkit=None):
    def news_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]
        instrument_context = build_instrument_context(ticker)

        tool_call_count = state.get("news_tool_call_count", 0)
        max_tool_calls = 3

        if toolkit is not None:
            tools = [toolkit.get_stock_news_unified]
        else:
            from tradingagents.agents.utils.agent_utils import (
                get_news,
                get_global_news,
            )

            tools = [get_news, get_global_news]

        system_message = (
            "You are a news researcher tasked with analyzing recent news and trends over the past week. Please write a comprehensive report of the current state of the world that is relevant for trading and macroeconomics. Use the available tools to search for company-specific news and broader macroeconomic news. Provide specific, actionable insights with supporting evidence to help traders make informed decisions."
            + """ Make sure to append a Markdown table at the end of the report to organize key points in the report, organized and easy to read."""
            + get_language_instruction()
        )

        tool_names = []
        for tool in tools:
            if hasattr(tool, "name"):
                tool_names.append(tool.name)
            elif hasattr(tool, "__name__"):
                tool_names.append(tool.__name__)
            else:
                tool_names.append(str(tool))

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a helpful AI assistant, collaborating with other assistants."
                    " Use the provided tools to progress towards answering the question."
                    " If you are unable to fully answer, that's OK; another assistant with different tools"
                    " will help where you left off. Execute what you can to make progress."
                    " If you or any other assistant has the FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** or deliverable,"
                    " prefix your response with FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** so the team knows to stop."
                    " You have access to the following tools: {tool_names}.\n{system_message}"
                    "For your reference, the current date is {current_date}. {instrument_context}",
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        prompt = prompt.partial(system_message=system_message)
        prompt = prompt.partial(tool_names=", ".join(tool_names))
        prompt = prompt.partial(current_date=current_date)
        prompt = prompt.partial(instrument_context=instrument_context)

        chain = prompt | llm.bind_tools(tools)
        result = chain.invoke(state["messages"])

        tool_call_count += (
            len(result.tool_calls) if hasattr(result, "tool_calls") else 0
        )

        report = ""

        if hasattr(
            GoogleToolCallHandler, "is_google_model"
        ) and GoogleToolCallHandler.is_google_model(llm):
            logger.info(
                "[News Analyst] Detected Google model, using unified tool call handler"
            )
            analysis_prompt_template = GoogleToolCallHandler.create_analysis_prompt(
                ticker=ticker,
                company_name=ticker,
                analyst_type="news analysis",
                specific_requirements="Focus on news events impact on stock price, market sentiment changes, and policy implications.",
            )
            report, _ = GoogleToolCallHandler.handle_google_tool_calls(
                result=result,
                llm=llm,
                tools=tools,
                state=state,
                analysis_prompt_template=analysis_prompt_template,
                analyst_name="News Analyst",
            )
        elif len(result.tool_calls) == 0:
            report = result.content
            if toolkit is not None:
                try:
                    fallback_data = toolkit.get_stock_news_unified.invoke(
                        {"stock_code": ticker, "max_news": 10}
                    )
                    tool_call_count += 1
                    report = f"{report}\n\n{fallback_data}".strip()
                except Exception as e:
                    logger.error(f"[News Analyst] Force fallback tool call failed: {e}")

        return {
            "messages": [result],
            "news_report": report,
            "news_tool_call_count": tool_call_count,
        }

    return news_analyst_node
