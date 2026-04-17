import questionary
from typing import List, Optional, Tuple, Dict

from rich.console import Console

from cli.models import AnalystType
from tradingagents.llm_clients.model_catalog import get_model_options
from tradingagents.utils.stock_utils import StockUtils, StockMarket

console = Console()

TICKER_INPUT_EXAMPLES = "Examples: AAPL, 600519.SH, 000001.SZ, 0700.HK"

ANALYST_ORDER = [
    ("Market Analyst", AnalystType.MARKET),
    ("Social Media Analyst", AnalystType.SOCIAL),
    ("News Analyst", AnalystType.NEWS),
    ("Fundamentals Analyst", AnalystType.FUNDAMENTALS),
]

CHINA_ANALYST_ORDER = [
    ("Market Analyst", AnalystType.MARKET),
    ("News Analyst", AnalystType.NEWS),
    ("Fundamentals Analyst", AnalystType.FUNDAMENTALS),
    ("China Market Analyst", AnalystType.CHINA_MARKET),
]

CHINA_PROVIDER_MODELS = {
    "deepseek": {
        "quick": [
            ("DeepSeek Chat (V3) - General purpose", "deepseek-chat"),
            ("DeepSeek Reasoner (R1) - Deep reasoning", "deepseek-reasoner"),
        ],
        "deep": [
            ("DeepSeek Reasoner (R1) - Deep reasoning", "deepseek-reasoner"),
            ("DeepSeek Chat (V3) - General purpose", "deepseek-chat"),
        ],
    },
    "dashscope": {
        "quick": [
            ("Qwen Turbo - Fast response", "qwen-turbo"),
            ("Qwen Plus - Balanced", "qwen-plus"),
            ("Qwen Max - Most powerful", "qwen-max"),
        ],
        "deep": [
            ("Qwen Max - Most powerful", "qwen-max"),
            ("Qwen Plus - Balanced", "qwen-plus"),
            ("Qwen Long - Long context", "qwen-long"),
        ],
    },
    "zhipu": {
        "quick": [
            ("GLM-4 Flash - Fast", "glm-4-flash"),
            ("GLM-4 - Standard", "glm-4"),
            ("GLM-4 Plus - Enhanced", "glm-4-plus"),
        ],
        "deep": [
            ("GLM-4 Plus - Enhanced", "glm-4-plus"),
            ("GLM-4 - Standard", "glm-4"),
        ],
    },
    "siliconflow": {
        "quick": [
            ("Qwen/Qwen2.5-7B-Instruct", "Qwen/Qwen2.5-7B-Instruct"),
            ("deepseek-ai/DeepSeek-V3", "deepseek-ai/DeepSeek-V3"),
        ],
        "deep": [
            ("deepseek-ai/DeepSeek-R1", "deepseek-ai/DeepSeek-R1"),
            ("Qwen/Qwen2.5-72B-Instruct", "Qwen/Qwen2.5-72B-Instruct"),
        ],
    },
    "qianfan": {
        "quick": [
            ("ERNIE 4.0 - Most capable", "ernie-4.0-8k"),
            ("ERNIE 3.5 - Balanced", "ernie-3.5-8k"),
        ],
        "deep": [
            ("ERNIE 4.0 - Most capable", "ernie-4.0-8k"),
            ("ERNIE 4.0 Turbo", "ernie-4.0-turbo-8k"),
        ],
    },
}

PROVIDER_DISPLAY_MAP = {
    "DeepSeek": ("deepseek", "https://api.deepseek.com/v1"),
    "阿里百炼 (DashScope)": (
        "dashscope",
        "https://dashscope.aliyuncs.com/compatible-mode/v1",
    ),
    "智谱AI (Zhipu)": ("zhipu", "https://open.bigmodel.cn/api/paas/v4"),
    "SiliconFlow": ("siliconflow", "https://api.siliconflow.cn/v1"),
    "百度千帆 (Qianfan)": ("qianfan", "https://qianfan.baidubce.com/v2"),
}


def get_ticker() -> str:
    """Prompt the user to enter a ticker symbol."""
    ticker = questionary.text(
        f"Enter the exact ticker symbol to analyze ({TICKER_INPUT_EXAMPLES}):",
        validate=lambda x: len(x.strip()) > 0 or "Please enter a valid ticker symbol.",
        style=questionary.Style(
            [
                ("text", "fg:green"),
                ("highlighted", "noinherit"),
            ]
        ),
    ).ask()

    if not ticker:
        console.print("\n[red]No ticker symbol provided. Exiting...[/red]")
        exit(1)

    return normalize_ticker_symbol(ticker)


def normalize_ticker_symbol(ticker: str) -> str:
    """Normalize ticker input while preserving exchange suffixes."""
    return StockUtils.normalize_symbol(ticker)


def get_analysis_date() -> str:
    """Prompt the user to enter a date in YYYY-MM-DD format."""
    import re
    from datetime import datetime

    def validate_date(date_str: str) -> bool:
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
            return False
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            return True
        except ValueError:
            return False

    date = questionary.text(
        "Enter the analysis date (YYYY-MM-DD):",
        validate=lambda x: (
            validate_date(x.strip())
            or "Please enter a valid date in YYYY-MM-DD format."
        ),
        style=questionary.Style(
            [
                ("text", "fg:green"),
                ("highlighted", "noinherit"),
            ]
        ),
    ).ask()

    if not date:
        console.print("\n[red]No date provided. Exiting...[/red]")
        exit(1)

    return date.strip()


def select_analysts(ticker: str = None) -> List[AnalystType]:
    """Select analysts using an interactive checkbox."""
    analyst_order = ANALYST_ORDER

    if ticker:
        market = StockUtils.identify_stock_market(ticker)
        if market == StockMarket.CHINA_A:
            analyst_order = CHINA_ANALYST_ORDER
            console.print(
                f"[yellow]Detected A-share ticker {ticker}. "
                "Social Media Analyst unavailable (data source limitation). "
                "China Market Analyst recommended.[/yellow]"
            )

    choices = questionary.checkbox(
        "Select Your [Analysts Team]:",
        choices=[
            questionary.Choice(display, value=value) for display, value in analyst_order
        ],
        instruction="\n- Press Space to select/unselect analysts\n- Press 'a' to select/unselect all\n- Press Enter when done",
        validate=lambda x: len(x) > 0 or "You must select at least one analyst.",
        style=questionary.Style(
            [
                ("checkbox-selected", "fg:green"),
                ("selected", "fg:green noinherit"),
                ("highlighted", "noinherit"),
                ("pointer", "noinherit"),
            ]
        ),
    ).ask()

    if not choices:
        console.print("\n[red]No analysts selected. Exiting...[/red]")
        exit(1)

    return choices


def select_research_depth() -> int:
    """Select research depth using an interactive selection."""

    # Define research depth options with their corresponding values
    DEPTH_OPTIONS = [
        ("Shallow - Quick research, few debate and strategy discussion rounds", 1),
        ("Medium - Middle ground, moderate debate rounds and strategy discussion", 3),
        ("Deep - Comprehensive research, in depth debate and strategy discussion", 5),
    ]

    choice = questionary.select(
        "Select Your [Research Depth]:",
        choices=[
            questionary.Choice(display, value=value) for display, value in DEPTH_OPTIONS
        ],
        instruction="\n- Use arrow keys to navigate\n- Press Enter to select",
        style=questionary.Style(
            [
                ("selected", "fg:yellow noinherit"),
                ("highlighted", "fg:yellow noinherit"),
                ("pointer", "fg:yellow noinherit"),
            ]
        ),
    ).ask()

    if choice is None:
        console.print("\n[red]No research depth selected. Exiting...[/red]")
        exit(1)

    return choice


def _fetch_openrouter_models() -> List[Tuple[str, str]]:
    """Fetch available models from the OpenRouter API."""
    import requests

    try:
        resp = requests.get("https://openrouter.ai/api/v1/models", timeout=10)
        resp.raise_for_status()
        models = resp.json().get("data", [])
        return [(m.get("name") or m["id"], m["id"]) for m in models]
    except Exception as e:
        console.print(f"\n[yellow]Could not fetch OpenRouter models: {e}[/yellow]")
        return []


def select_openrouter_model() -> str:
    """Select an OpenRouter model from the newest available, or enter a custom ID."""
    models = _fetch_openrouter_models()

    choices = [questionary.Choice(name, value=mid) for name, mid in models[:5]]
    choices.append(questionary.Choice("Custom model ID", value="custom"))

    choice = questionary.select(
        "Select OpenRouter Model (latest available):",
        choices=choices,
        instruction="\n- Use arrow keys to navigate\n- Press Enter to select",
        style=questionary.Style(
            [
                ("selected", "fg:magenta noinherit"),
                ("highlighted", "fg:magenta noinherit"),
                ("pointer", "fg:magenta noinherit"),
            ]
        ),
    ).ask()

    if choice is None or choice == "custom":
        return (
            questionary.text(
                "Enter OpenRouter model ID (e.g. google/gemma-4-26b-a4b-it):",
                validate=lambda x: len(x.strip()) > 0 or "Please enter a model ID.",
            )
            .ask()
            .strip()
        )

    return choice


def _get_china_model_options(provider_key: str, mode: str):
    """Get model options for Chinese LLM providers."""
    return CHINA_PROVIDER_MODELS.get(provider_key, {}).get(mode, [])


def select_shallow_thinking_agent(provider) -> str:
    """Select shallow thinking llm engine using an interactive selection."""

    if provider.lower() == "openrouter":
        return select_openrouter_model()

    china_options = _get_china_model_options(provider.lower(), "quick")
    if china_options:
        choice = questionary.select(
            "Select Your [Quick-Thinking LLM Engine]:",
            choices=[
                questionary.Choice(display, value=value)
                for display, value in china_options
            ],
            instruction="\n- Use arrow keys to navigate\n- Press Enter to select",
            style=questionary.Style(
                [
                    ("selected", "fg:magenta noinherit"),
                    ("highlighted", "fg:magenta noinherit"),
                    ("pointer", "fg:magenta noinherit"),
                ]
            ),
        ).ask()

        if choice is None:
            console.print(
                "\n[red]No shallow thinking llm engine selected. Exiting...[/red]"
            )
            exit(1)

        return choice

    choice = questionary.select(
        "Select Your [Quick-Thinking LLM Engine]:",
        choices=[
            questionary.Choice(display, value=value)
            for display, value in get_model_options(provider, "quick")
        ],
        instruction="\n- Use arrow keys to navigate\n- Press Enter to select",
        style=questionary.Style(
            [
                ("selected", "fg:magenta noinherit"),
                ("highlighted", "fg:magenta noinherit"),
                ("pointer", "fg:magenta noinherit"),
            ]
        ),
    ).ask()

    if choice is None:
        console.print(
            "\n[red]No shallow thinking llm engine selected. Exiting...[/red]"
        )
        exit(1)

    return choice


def select_deep_thinking_agent(provider) -> str:
    """Select deep thinking llm engine using an interactive selection."""

    if provider.lower() == "openrouter":
        return select_openrouter_model()

    china_options = _get_china_model_options(provider.lower(), "deep")
    if china_options:
        choice = questionary.select(
            "Select Your [Deep-Thinking LLM Engine]:",
            choices=[
                questionary.Choice(display, value=value)
                for display, value in china_options
            ],
            instruction="\n- Use arrow keys to navigate\n- Press Enter to select",
            style=questionary.Style(
                [
                    ("selected", "fg:magenta noinherit"),
                    ("highlighted", "fg:magenta noinherit"),
                    ("pointer", "fg:magenta noinherit"),
                ]
            ),
        ).ask()

        if choice is None:
            console.print(
                "\n[red]No deep thinking llm engine selected. Exiting...[/red]"
            )
            exit(1)

        return choice

    choice = questionary.select(
        "Select Your [Deep-Thinking LLM Engine]:",
        choices=[
            questionary.Choice(display, value=value)
            for display, value in get_model_options(provider, "deep")
        ],
        instruction="\n- Use arrow keys to navigate\n- Press Enter to select",
        style=questionary.Style(
            [
                ("selected", "fg:magenta noinherit"),
                ("highlighted", "fg:magenta noinherit"),
                ("pointer", "fg:magenta noinherit"),
            ]
        ),
    ).ask()

    if choice is None:
        console.print("\n[red]No deep thinking llm engine selected. Exiting...[/red]")
        exit(1)

    return choice


def select_llm_provider() -> tuple[str, str | None]:
    """Select the LLM provider and its API endpoint."""
    BASE_URLS = [
        ("OpenAI", "https://api.openai.com/v1"),
        ("Google", None),
        ("Anthropic", "https://api.anthropic.com/"),
        ("xAI", "https://api.x.ai/v1"),
        ("Openrouter", "https://openrouter.ai/api/v1"),
        ("Ollama", "http://localhost:11434/v1"),
        ("DeepSeek", "https://api.deepseek.com/v1"),
        (
            "\u963f\u91cc\u767e\u70bc (DashScope)",
            "https://dashscope.aliyuncs.com/compatible-mode/v1",
        ),
        ("\u667a\u8c31AI (Zhipu)", "https://open.bigmodel.cn/api/paas/v4"),
        ("SiliconFlow", "https://api.siliconflow.cn/v1"),
        ("\u767e\u5ea6\u5343\u5e06 (Qianfan)", "https://qianfan.baidubce.com/v2"),
    ]

    choice = questionary.select(
        "Select your LLM Provider:",
        choices=[
            questionary.Choice(display, value=(display, value))
            for display, value in BASE_URLS
        ],
        instruction="\n- Use arrow keys to navigate\n- Press Enter to select",
        style=questionary.Style(
            [
                ("selected", "fg:magenta noinherit"),
                ("highlighted", "fg:magenta noinherit"),
                ("pointer", "fg:magenta noinherit"),
            ]
        ),
    ).ask()

    if choice is None:
        console.print("\n[red]no OpenAI backend selected. Exiting...[/red]")
        exit(1)

    display_name, url = choice
    print(f"You selected: {display_name}\tURL: {url}")

    return display_name, url


def ask_openai_reasoning_effort() -> str:
    """Ask for OpenAI reasoning effort level."""
    choices = [
        questionary.Choice("Medium (Default)", "medium"),
        questionary.Choice("High (More thorough)", "high"),
        questionary.Choice("Low (Faster)", "low"),
    ]
    return questionary.select(
        "Select Reasoning Effort:",
        choices=choices,
        style=questionary.Style(
            [
                ("selected", "fg:cyan noinherit"),
                ("highlighted", "fg:cyan noinherit"),
                ("pointer", "fg:cyan noinherit"),
            ]
        ),
    ).ask()


def ask_anthropic_effort() -> str | None:
    """Ask for Anthropic effort level.

    Controls token usage and response thoroughness on Claude 4.5+ and 4.6 models.
    """
    return questionary.select(
        "Select Effort Level:",
        choices=[
            questionary.Choice("High (recommended)", "high"),
            questionary.Choice("Medium (balanced)", "medium"),
            questionary.Choice("Low (faster, cheaper)", "low"),
        ],
        style=questionary.Style(
            [
                ("selected", "fg:cyan noinherit"),
                ("highlighted", "fg:cyan noinherit"),
                ("pointer", "fg:cyan noinherit"),
            ]
        ),
    ).ask()


def ask_gemini_thinking_config() -> str | None:
    """Ask for Gemini thinking configuration.

    Returns thinking_level: "high" or "minimal".
    Client maps to appropriate API param based on model series.
    """
    return questionary.select(
        "Select Thinking Mode:",
        choices=[
            questionary.Choice("Enable Thinking (recommended)", "high"),
            questionary.Choice("Minimal/Disable Thinking", "minimal"),
        ],
        style=questionary.Style(
            [
                ("selected", "fg:green noinherit"),
                ("highlighted", "fg:green noinherit"),
                ("pointer", "fg:green noinherit"),
            ]
        ),
    ).ask()


def ask_output_language() -> str:
    """Ask for report output language."""
    choice = questionary.select(
        "Select Output Language:",
        choices=[
            questionary.Choice("English (default)", "English"),
            questionary.Choice("Chinese (中文)", "Chinese"),
            questionary.Choice("Japanese (日本語)", "Japanese"),
            questionary.Choice("Korean (한국어)", "Korean"),
            questionary.Choice("Hindi (हिन्दी)", "Hindi"),
            questionary.Choice("Spanish (Español)", "Spanish"),
            questionary.Choice("Portuguese (Português)", "Portuguese"),
            questionary.Choice("French (Français)", "French"),
            questionary.Choice("German (Deutsch)", "German"),
            questionary.Choice("Arabic (العربية)", "Arabic"),
            questionary.Choice("Russian (Русский)", "Russian"),
            questionary.Choice("Custom language", "custom"),
        ],
        style=questionary.Style(
            [
                ("selected", "fg:yellow noinherit"),
                ("highlighted", "fg:yellow noinherit"),
                ("pointer", "fg:yellow noinherit"),
            ]
        ),
    ).ask()

    if choice == "custom":
        return (
            questionary.text(
                "Enter language name (e.g. Turkish, Vietnamese, Thai, Indonesian):",
                validate=lambda x: (
                    len(x.strip()) > 0 or "Please enter a language name."
                ),
            )
            .ask()
            .strip()
        )

    return choice


def select_market() -> str:
    """Let user select which stock market to analyze."""
    MARKET_OPTIONS = [
        ("\u7f8e\u80a1 (US Market)", "us"),
        ("A\u80a1 (China A-Share Market)", "china_a"),
        ("\u6e2f\u80a1 (Hong Kong Market)", "hong_kong"),
    ]

    choice = questionary.select(
        "Select Your [Stock Market]:",
        choices=[
            questionary.Choice(display, value=value)
            for display, value in MARKET_OPTIONS
        ],
        instruction="\n- Use arrow keys to navigate\n- Press Enter to select",
        style=questionary.Style(
            [
                ("selected", "fg:yellow noinherit"),
                ("highlighted", "fg:yellow noinherit"),
                ("pointer", "fg:yellow noinherit"),
            ]
        ),
    ).ask()

    if choice is None:
        console.print("\n[red]No market selected. Exiting...[/red]")
        exit(1)

    return choice


def resolve_provider_key(display_name: str) -> str:
    """Resolve LLM provider display name to internal key for config."""
    display_lower = display_name.lower()
    if display_lower in (
        "openai",
        "google",
        "anthropic",
        "xai",
        "openrouter",
        "ollama",
    ):
        return display_lower
    for cn_display, (key, _) in PROVIDER_DISPLAY_MAP.items():
        if cn_display.lower() == display_lower or key == display_lower:
            return key
    return display_lower
