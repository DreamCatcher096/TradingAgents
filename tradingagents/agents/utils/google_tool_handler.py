#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Google模型工具调用统一处理器

解决Google模型在工具调用时result.content为空的问题，
提供统一的工具调用处理逻辑供所有分析师使用。
"""

import logging
import time
import traceback
import uuid
from typing import Any, Dict, List, Optional, Tuple

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

logger = logging.getLogger(__name__)


class GoogleToolCallHandler:
    """Google模型工具调用统一处理器"""

    @staticmethod
    def is_google_model(llm) -> bool:
        """检查是否为Google模型"""
        return (
            "Google" in llm.__class__.__name__
            or "ChatGoogleOpenAI" in llm.__class__.__name__
        )

    @staticmethod
    def handle_google_tool_calls(
        result: AIMessage,
        llm: Any,
        tools: List[Any],
        state: Dict[str, Any],
        analysis_prompt_template: str,
        analyst_name: str = "分析师",
    ) -> Tuple[str, List[Any]]:
        """
        统一处理Google模型的工具调用
        """
        logger.info(f"[{analyst_name}] 开始Google工具调用处理...")

        if not GoogleToolCallHandler.is_google_model(llm):
            logger.warning(f"[{analyst_name}] 非Google模型，跳过特殊处理")
            return result.content, [result]

        logger.info(f"[{analyst_name}] 确认为Google模型")

        if not hasattr(result, "content"):
            logger.error(f"[{analyst_name}] Google模型API调用失败，无返回内容")
            return "Google模型API调用失败", []

        if not hasattr(result, "tool_calls"):
            logger.warning(f"[{analyst_name}] 结果对象没有tool_calls属性")
            return result.content, [result]

        if not result.tool_calls:
            logger.info(f"[{analyst_name}] Google模型未调用工具")
            content = result.content
            is_analysis_report = False
            analysis_keywords = [
                "分析",
                "报告",
                "总结",
                "评估",
                "建议",
                "风险",
                "趋势",
                "市场",
                "股票",
                "投资",
            ]
            if content and len(content) > 200:
                keyword_count = sum(
                    1 for keyword in analysis_keywords if keyword in content
                )
                is_analysis_report = keyword_count >= 3
                if is_analysis_report:
                    logger.info(f"[{analyst_name}] Google模型直接返回了分析报告")
                    return content, [result]
            return result.content, [result]

        logger.info(
            f"[{analyst_name}] Google模型调用了 {len(result.tool_calls)} 个工具"
        )

        try:
            tool_messages = []
            tool_results = []
            executed_tools = set()

            valid_tool_calls = []
            for i, tool_call in enumerate(result.tool_calls):
                if GoogleToolCallHandler._validate_tool_call(
                    tool_call, i, analyst_name
                ):
                    valid_tool_calls.append(tool_call)
                else:
                    fixed_tool_call = GoogleToolCallHandler._fix_tool_call(
                        tool_call, i, analyst_name
                    )
                    if fixed_tool_call:
                        valid_tool_calls.append(fixed_tool_call)

            for i, tool_call in enumerate(valid_tool_calls):
                tool_name = tool_call.get("name")
                tool_args = tool_call.get("args", {})
                tool_id = tool_call.get("id")

                tool_signature = f"{tool_name}_{hash(str(tool_args))}"
                if tool_signature in executed_tools:
                    logger.warning(f"[{analyst_name}] 跳过重复工具调用: {tool_name}")
                    continue
                executed_tools.add(tool_signature)

                logger.info(
                    f"[{analyst_name}] 执行工具 {i + 1}/{len(valid_tool_calls)}: {tool_name}"
                )

                tool_result = None
                available_tools = []

                for tool in tools:
                    current_tool_name = GoogleToolCallHandler._get_tool_name(tool)
                    available_tools.append(current_tool_name)

                    if current_tool_name == tool_name:
                        try:
                            if hasattr(tool, "invoke"):
                                tool_result = tool.invoke(tool_args)
                            elif callable(tool):
                                tool_result = tool(**tool_args)
                            else:
                                tool_result = f"工具类型不支持: {type(tool)}"
                            break
                        except Exception as tool_error:
                            logger.error(f"[{analyst_name}] 工具执行失败: {tool_error}")
                            tool_result = f"工具执行失败: {str(tool_error)}"

                if tool_result is None:
                    tool_result = f"未找到工具: {tool_name}"
                    logger.warning(f"[{analyst_name}] 未找到工具: {tool_name}")

                tool_message = ToolMessage(
                    content=str(tool_result), tool_call_id=tool_id
                )
                tool_messages.append(tool_message)
                tool_results.append(tool_result)

            logger.info(f"[{analyst_name}] 工具调用完成，成功: {len(tool_results)}")

            safe_messages = []
            if "messages" in state and state["messages"]:
                for msg in state["messages"]:
                    if isinstance(msg, HumanMessage):
                        safe_messages.append(msg)
                        break

            if hasattr(result, "content"):
                safe_messages.append(result)

            safe_messages.extend(tool_messages)
            safe_messages.append(HumanMessage(content=analysis_prompt_template))

            if not safe_messages:
                tool_summary = "\n\n".join(
                    [f"工具结果 {i + 1}:\n{str(r)}" for i, r in enumerate(tool_results)]
                )
                report = f"{analyst_name}工具调用完成，获得以下数据：\n\n{tool_summary}"
                return report, [result] + tool_messages

            try:
                final_result = llm.invoke(safe_messages)
                if hasattr(final_result, "content") and final_result.content:
                    report = final_result.content
                    logger.info(f"[{analyst_name}] Google模型最终分析报告生成成功")
                    all_messages = [result] + tool_messages + [final_result]
                    return report, all_messages
                else:
                    tool_summary = "\n\n".join(
                        [
                            f"工具结果 {i + 1}:\n{str(r)}"
                            for i, r in enumerate(tool_results)
                        ]
                    )
                    report = (
                        f"{analyst_name}工具调用完成，获得以下数据：\n\n{tool_summary}"
                    )
                    return report, [result] + tool_messages
            except Exception as final_error:
                logger.error(f"[{analyst_name}] 最终分析报告生成失败: {final_error}")
                tool_summary = "\n\n".join(
                    [f"工具结果 {i + 1}:\n{str(r)}" for i, r in enumerate(tool_results)]
                )
                report = f"{analyst_name}工具调用完成，获得以下数据：\n\n{tool_summary}"
                return report, [result] + tool_messages

        except Exception as e:
            logger.error(f"[{analyst_name}] Google模型工具调用处理失败: {e}")
            tool_names = [tc.get("name", "unknown") for tc in result.tool_calls]
            report = f"{analyst_name}调用了工具 {tool_names} 但处理失败: {str(e)}"
            return report, [result]

    @staticmethod
    def _get_tool_name(tool):
        """获取工具名称"""
        if hasattr(tool, "name"):
            return tool.name
        elif hasattr(tool, "__name__"):
            return tool.__name__
        else:
            return str(tool)

    @staticmethod
    def _validate_tool_call(tool_call, index, analyst_name):
        """验证工具调用格式"""
        try:
            if not isinstance(tool_call, dict):
                logger.warning(
                    f"[{analyst_name}] 工具调用 {index} 不是字典格式: {type(tool_call)}"
                )
                return False

            required_fields = ["name", "args", "id"]
            for field in required_fields:
                if field not in tool_call:
                    logger.warning(
                        f"[{analyst_name}] 工具调用 {index} 缺少字段 '{field}': {tool_call}"
                    )
                    return False

            tool_name = tool_call.get("name")
            if not isinstance(tool_name, str) or not tool_name.strip():
                logger.warning(
                    f"[{analyst_name}] 工具调用 {index} 工具名称无效: {tool_name}"
                )
                return False

            tool_args = tool_call.get("args")
            if not isinstance(tool_args, dict):
                logger.warning(
                    f"[{analyst_name}] 工具调用 {index} 参数不是字典格式: {type(tool_args)}"
                )
                return False

            tool_id = tool_call.get("id")
            if not isinstance(tool_id, str) or not tool_id.strip():
                logger.warning(f"[{analyst_name}] 工具调用 {index} ID无效: {tool_id}")
                return False

            return True
        except Exception as e:
            logger.error(f"[{analyst_name}] 工具调用 {index} 验证异常: {e}")
            return False

    @staticmethod
    def _fix_tool_call(tool_call, index, analyst_name):
        """尝试修复工具调用格式"""
        try:
            if not isinstance(tool_call, dict):
                return None

            fixed_tool_call = tool_call.copy()

            if "name" not in fixed_tool_call or not isinstance(
                fixed_tool_call["name"], str
            ):
                if "function" in fixed_tool_call and isinstance(
                    fixed_tool_call["function"], dict
                ):
                    function_data = fixed_tool_call["function"]
                    if "name" in function_data:
                        fixed_tool_call["name"] = function_data["name"]
                        if "arguments" in function_data:
                            import json

                            try:
                                if isinstance(function_data["arguments"], str):
                                    fixed_tool_call["args"] = json.loads(
                                        function_data["arguments"]
                                    )
                                else:
                                    fixed_tool_call["args"] = function_data["arguments"]
                            except json.JSONDecodeError:
                                fixed_tool_call["args"] = {}
                else:
                    return None

            if "args" not in fixed_tool_call:
                fixed_tool_call["args"] = {}
            elif not isinstance(fixed_tool_call["args"], dict):
                import json

                try:
                    if isinstance(fixed_tool_call["args"], str):
                        fixed_tool_call["args"] = json.loads(fixed_tool_call["args"])
                    else:
                        fixed_tool_call["args"] = {}
                except:
                    fixed_tool_call["args"] = {}

            if "id" not in fixed_tool_call or not isinstance(
                fixed_tool_call["id"], str
            ):
                fixed_tool_call["id"] = f"call_{uuid.uuid4().hex[:8]}"

            if GoogleToolCallHandler._validate_tool_call(
                fixed_tool_call, index, analyst_name
            ):
                return fixed_tool_call
            else:
                return None
        except Exception as e:
            logger.error(f"[{analyst_name}] 工具调用 {index} 修复异常: {e}")
            return None

    @staticmethod
    def handle_simple_google_response(
        result: AIMessage, llm: Any, analyst_name: str = "分析师"
    ) -> str:
        """处理简单的Google模型响应（无工具调用）"""
        if not GoogleToolCallHandler.is_google_model(llm):
            return result.content

        if len(result.content) > 15000:
            return result.content[:10000] + "\n\n[注：内容已截断以确保可读性]"
        return result.content

    @staticmethod
    def generate_final_analysis_report(llm, messages: List, analyst_name: str) -> str:
        """生成最终分析报告"""
        if not GoogleToolCallHandler.is_google_model(llm):
            return ""

        max_retries = 3
        retry_delay = 2

        for attempt in range(max_retries):
            try:
                if attempt == 0:
                    analysis_prompt = f"""
                    基于以上工具调用的结果，请为{analyst_name}生成一份详细的分析报告。
                    要求：综合分析所有工具返回的数据，提供清晰的投资建议和风险评估。
                    """
                elif attempt == 1:
                    analysis_prompt = f"""
                    请简要分析{analyst_name}的工具调用结果并提供投资建议。
                    要求：简洁明了，包含关键数据和建议。
                    """
                else:
                    analysis_prompt = f"""
                    请为{analyst_name}提供一个简短的分析总结。
                    """

                optimized_messages = GoogleToolCallHandler._optimize_message_sequence(
                    messages, analysis_prompt
                )
                result = llm.invoke(optimized_messages)

                if (
                    hasattr(result, "content")
                    and result.content
                    and len(result.content.strip()) > 0
                ):
                    return result.content
                elif attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                else:
                    return GoogleToolCallHandler._generate_fallback_report(
                        messages, analyst_name
                    )
            except Exception as e:
                logger.error(
                    f"[{analyst_name}] LLM调用异常 (尝试 {attempt + 1}/{max_retries}): {e}"
                )
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                else:
                    return GoogleToolCallHandler._generate_fallback_report(
                        messages, analyst_name
                    )

        return GoogleToolCallHandler._generate_fallback_report(messages, analyst_name)

    @staticmethod
    def _optimize_message_sequence(messages: List, analysis_prompt: str) -> List:
        """优化消息序列，确保在合理长度内"""
        total_length = sum(
            len(str(msg.content)) for msg in messages if hasattr(msg, "content")
        )
        total_length += len(analysis_prompt)

        if total_length <= 50000:
            return messages + [HumanMessage(content=analysis_prompt)]

        optimized_messages = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                optimized_messages = [msg]
                break

        for msg in messages:
            if isinstance(msg, (AIMessage, ToolMessage)):
                if hasattr(msg, "content") and len(str(msg.content)) > 5000:
                    truncated_content = (
                        str(msg.content)[:5000] + "\n\n[注：数据已截断以确保处理效率]"
                    )
                    if isinstance(msg, AIMessage):
                        optimized_msg = AIMessage(content=truncated_content)
                    else:
                        optimized_msg = ToolMessage(
                            content=truncated_content,
                            tool_call_id=getattr(msg, "tool_call_id", "unknown"),
                        )
                    optimized_messages.append(optimized_msg)
                else:
                    optimized_messages.append(msg)

        optimized_messages.append(HumanMessage(content=analysis_prompt))
        return optimized_messages

    @staticmethod
    def _generate_fallback_report(messages: List, analyst_name: str) -> str:
        """生成降级报告"""
        tool_results = []
        for msg in messages:
            if isinstance(msg, ToolMessage) and hasattr(msg, "content"):
                content = str(msg.content)
                if len(content) > 1000:
                    content = content[:1000] + "\n\n[注：数据已截断]"
                tool_results.append(content)

        if tool_results:
            tool_summary = "\n\n".join(
                [
                    f"工具结果 {i + 1}:\n{result}"
                    for i, result in enumerate(tool_results)
                ]
            )
            report = f"{analyst_name}工具调用完成，获得以下数据：\n\n{tool_summary}\n\n注：由于模型响应异常，此为基于工具数据的简化报告。"
        else:
            report = f"{analyst_name}分析完成，但未能获取到有效的工具数据。建议检查数据源或重新尝试分析。"
        return report

    @staticmethod
    def create_analysis_prompt(
        ticker: str,
        company_name: str,
        analyst_type: str,
        specific_requirements: str = "",
    ) -> str:
        """创建标准的分析提示词"""
        base_prompt = f"""现在请基于上述工具获取的数据，生成详细的{analyst_type}报告。

**股票信息：**
- 公司名称：{company_name}
- 股票代码：{ticker}

**分析要求：**
1. 报告必须基于工具返回的真实数据进行分析
2. 包含具体的数值和专业分析
3. 提供明确的投资建议和风险提示
4. 报告长度不少于800字
5. 使用中文撰写
6. 确保在分析中正确使用公司名称"{company_name}"和股票代码"{ticker}"

{specific_requirements}

请生成专业、详细的{analyst_type}报告。"""
        return base_prompt
