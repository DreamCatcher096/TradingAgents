import logging

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from tradingagents.agents.utils.agent_utils import (
    build_instrument_context,
    get_language_instruction,
)
from tradingagents.agents.utils.google_tool_handler import GoogleToolCallHandler

logger = logging.getLogger(__name__)


def create_fundamentals_analyst(llm, toolkit=None):
    def fundamentals_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]
        instrument_context = build_instrument_context(ticker)

        tool_call_count = state.get("fundamentals_tool_call_count", 0)

        if toolkit is not None:
            tools = [toolkit.get_stock_fundamentals_unified]
        else:
            from tradingagents.agents.utils.agent_utils import (
                get_fundamentals,
                get_balance_sheet,
                get_cashflow,
                get_income_statement,
            )

            tools = [
                get_fundamentals,
                get_balance_sheet,
                get_cashflow,
                get_income_statement,
            ]

        system_message = (
            "You are a researcher tasked with analyzing fundamental information over the past week about a company. Please write a comprehensive report of the company's fundamental information such as financial documents, company profile, basic company financials, and company financial history to gain a full view of the company's fundamental information to inform traders. Make sure to include as much detail as possible. Provide specific, actionable insights with supporting evidence to help traders make informed decisions."
            + " Make sure to append a Markdown table at the end of the report to organize key points in the report, organized and easy to read."
            + " Use the available tools to gather comprehensive company analysis and financial statements."
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
                "[Fundamentals Analyst] Detected Google model, using unified tool call handler"
            )
            analysis_prompt_template = GoogleToolCallHandler.create_analysis_prompt(
                ticker=ticker,
                company_name=ticker,
                analyst_type="fundamentals analysis",
                specific_requirements="Focus on company financial quality, valuation, and the most decision-useful fundamentals.",
            )
            report, _ = GoogleToolCallHandler.handle_google_tool_calls(
                result=result,
                llm=llm,
                tools=tools,
                state=state,
                analysis_prompt_template=analysis_prompt_template,
                analyst_name="Fundamentals Analyst",
            )
        elif len(result.tool_calls) == 0:
            report = result.content
            if toolkit is not None:
                try:
                    fallback_payload = {
                        "symbol": ticker,
                        "curr_date": current_date,
                    }
                    fallback_data = toolkit.get_stock_fundamentals_unified.invoke(
                        fallback_payload
                    )
                    tool_call_count += 1
                    report = f"{report}\n\n{fallback_data}".strip()
                except Exception as e:
                    logger.error(
                        f"[Fundamentals Analyst] Force fallback tool call failed: {e}"
                    )

        return {
            "messages": [result],
            "fundamentals_report": report,
            "fundamentals_tool_call_count": tool_call_count,
        }

    return fundamentals_analyst_node
