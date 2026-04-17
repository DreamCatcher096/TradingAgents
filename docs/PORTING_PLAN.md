# TradingAgents 中文版移植详细计划

> **目标**：将 `TradingAgents-CN` 的精华内容（去掉 MongoDB/Redis/FastAPI/Vue 后）完整移植到原版 `TradingAgents` 中，打造一个**命令行场景下最完整、最极致**的 A 股分析框架。
>
> **原则**：
> 1. 以原版为 base，CN 内容为 patch，不破坏原版架构的轻量性。
> 2. 所有新增代码必须能在纯 Python 环境中运行（`pip install` 即可，无需 Docker/数据库）。
> 3. 保留原版对美股/港股的支持，同时让 A 股成为"一等公民"。
> 4. 国产 LLM 支持与原版的 OpenAI/Anthropic/Google 支持并存。

## 当前执行状态（截至 2026-04-16）

状态标记：`[x]` 已完成，`[~]` 部分完成，`[ ]` 未开始。

| Phase | 状态 | 说明 |
|------|------|------|
| Phase 0 | `[~]` | 已补环境变量与 CN optional dependencies，目录和配置骨架未完全到位 |
| Phase 1 | `[~]` | `StockUtils`、CLI ticker 归一化、Agent 市场上下文已接入 |
| Phase 2 | `[~]` | China provider/router 骨架已落地，provider 已补入行情/估值/财务快照能力，但 router 格式化与缓存仍显著弱于 CN 版 |
| Phase 3 | `[~]` | `load_ohlcv()` 已支持 A 股分流；`ChinaDataRouter` 已增加中文技术指标格式化输出（MA/MACD/RSI/BOLL/量价统计）；文件缓存与 TTL 仍未完成 |
| Phase 4 | `[x]` | `Toolkit` 统一工具已实现（market/fundamentals/news/indicators/global_news/sentiment）；`unified_news_tool.py` 与 `get_stock_sentiment_unified` 已完成 |
| Phase 5 | `[~]` | `china_market_analyst.py`、`google_tool_handler.py` 已完成；4 个现有 Analyst 的 unified tools 接入与增强尚未开始 |
| Phase 6 | `[ ]` | `llm_adapters/` 与国产 LLM 适配层未开始 |
| Phase 7 | `[~]` | CLI 已支持 A 股 ticker 自动补全，但 A 股专属流程未接入 |
| Phase 8 | `[x]` | `default_config.py` 已扩展 `online_tools`、`data_source_priority`、quick/deep provider 分离；文件缓存 TTL 策略仍待补齐 |
| Phase 9 | `[~]` | 已新增部分单元测试，E2E 与工具调用专项测试未开始 |
| Phase 10 | `[ ]` | README、清理、最终文档收口未开始 |

**当前验证结果**：已运行 `PYTHONPATH=. pytest tests -v`，当前仓库测试结果为 `29 passed`。

## 当前与 TradingAgents-CN 的主要差距（忽略 Web/用户/可视化/容器）

### 一、数据层差距

- 当前已具备 A 股基础识别和 provider/router 骨架：`tradingagents/utils/stock_utils.py`、`tradingagents/dataflows/providers/china/*.py`、`tradingagents/dataflows/china_router.py`、`tradingagents/dataflows/stockstats_utils.py`。
- 仍缺 CN 版那种面向 CLI 的统一中国股票服务层：`TradingAgents-CN/tradingagents/dataflows/data_source_manager.py`、`stock_data_service.py`、`stock_api.py`。
- 当前 provider 接口仍较薄，仅覆盖 `get_stock_data` / `get_fundamentals` / `get_news`；缺少 `get_stock_basic_info`、`get_stock_quotes`、`get_batch_stock_quotes`、`get_valuation_data`、更完整的 `get_financial_data`。
- 当前 `ChinaDataRouter` 还没有 CN 版最关键的中文格式化能力：MA/MACD/RSI/BOLL/量价统计等可直接供 LLM 消费的高结构化中文输出。
- 当前 `stockstats_utils.load_ohlcv()` 已能对 A 股分流，但 China path 还没有文件缓存、TTL、A 股命名兼容等配套策略。

### 二、工具层与 Agent 层差距

- [x] `Toolkit` 统一工具架构已在 `agent_utils.py` 中落地，并集成 `get_stock_market_data_unified`、`get_stock_fundamentals_unified`、`get_stock_news_unified`、`get_stock_sentiment_unified`、`get_indicators_unified`、`get_global_news_unified`。
- [x] `tradingagents/tools/unified_news_tool.py` 已完成（去除了 MongoDB 依赖，适配当前 repo 的 yfinance/alpha_vantage 新闻源）。
- [x] `tradingagents/agents/analysts/china_market_analyst.py` 已完成，集成 `GoogleToolCallHandler`。
- [ ] 当前 4 个现有 analyst（fundamentals/news/market/social）尚未接入 unified tools、强制工具调用补救、计数器、防死循环等 CN 增强。
- [x] `tradingagents/agents/utils/google_tool_handler.py` 已完成，Gemini tool call 修复层已接入。

### 三、LLM / CLI / Graph 差距

- 当前没有 `tradingagents/llm_adapters/` 目录，也没有 DashScope / DeepSeek / Zhipu / Qianfan / SiliconFlow / custom_openai 的适配器实现。
- 当前 `tradingagents/graph/trading_graph.py` 仍是单一 `llm_provider` 模式，没有 quick/deep provider 混搭能力。
- 当前 `graph/setup.py` 和 `graph/trading_graph.py` 仍只注册原版 4 个 analyst 和旧工具节点，没有 `china_market` 分支。
- 当前 `cli/models.py` 还没有 `CHINA_MARKET` analyst 类型。
- 当前 `cli/utils.py` 虽已支持 A 股 ticker 自动补全，但还没有 China Market Analyst 选项、A 股数据源优先级选择、国产模型菜单。
- 当前 `cli/main.py` 还没有 A 股专属主流程、运行前数据源预检、China config 注入。
- 当前也还没有 `cli/akshare_init.py`、`cli/tushare_init.py`、`cli/baostock_init.py` 这类独立诊断命令。

### 四、配置、测试与文档差距

- `tradingagents/default_config.py` 还未扩展 `online_tools`、`data_source_priority`、quick/deep provider 分离等 CN 所需配置。
- `ChinaDataRouter` 还没有 AKShare/Tushare/news 的文件缓存和 TTL 管理。
- 测试方面仅完成了：`tests/test_stock_utils.py`、`tests/test_china_router.py`，以及对 `tests/test_ticker_symbol_handling.py` 的扩展。
- 尚缺 `test_unified_news.py`、`test_google_tool_handler.py` 以及 A 股/港股/美股 CLI 端到端回归。
- README 还没有 A 股与国产 LLM 的最终说明章节。

---

## Phase 0: 环境基座与项目准备 [部分完成]

**当前状态**
- [~] `0.1` `pyproject.toml` 已加入 `cn` optional extra：`akshare`、`tushare`、`baostock`、`curl-cffi`、`pydantic-settings`；当前实现没有按原计划直接放入 base dependencies，而是保留为可选安装。
- [x] `0.2` `.env.example` 已补入 `TUSHARE_TOKEN`、`AKSHARE_ENABLED`、`BAOSTOCK_ENABLED`、`DASHSCOPE_API_KEY`、`DEEPSEEK_API_KEY`、`ZHIPU_API_KEY`、`SILICONFLOW_API_KEY`。
- [x] `0.3` 目录已通过实际文件落地：`tradingagents/dataflows/providers/china/`、`tradingagents/utils/`、`tradingagents/tools/`；`tradingagents/llm_adapters/`、`tradingagents/dataflows/technical/` 仍未建立或接入。

### 0.1 依赖更新 (`pyproject.toml`)

新增以下依赖包：

```toml
[project.dependencies]
# 原有依赖保持不变 ...

# 中国数据源
"tushare>=1.4.0",
"akshare>=1.15.0",
"baostock>=0.8.8",

# 反爬绕过（AKShare 东方财富新闻必需）
"curl-cffi>=0.10.0",

# 增强日志和工具
"pydantic-settings>=2.0.0",
```

> 注意：不引入 `pymongo`, `redis`, `fastapi`, `uvicorn`, `vue` 等任何 Web/数据库依赖。

### 0.2 环境变量模板 (`.env.example`)

在原有基础上新增中国区配置：

```bash
# ========== 中国数据源配置 ==========
TUSHARE_TOKEN=your_tushare_token_here
AKSHARE_ENABLED=true
BAOSTOCK_ENABLED=true

# ========== 国产 LLM 配置 ==========
DASHSCOPE_API_KEY=your_dashscope_key
DEEPSEEK_API_KEY=your_deepseek_key
ZHIPU_API_KEY=your_zhipu_key
SILICONFLOW_API_KEY=your_siliconflow_key
```

### 0.3 目录结构预创建

```bash
mkdir -p tradingagents/dataflows/providers/china
mkdir -p tradingagents/dataflows/technical
mkdir -p tradingagents/llm_adapters
mkdir -p tradingagents/tools
mkdir -p tradingagents/utils
```

---

## Phase 1: 股票识别与市场判断基础设施 [部分完成]

**当前状态**
- [x] `1.1` `tradingagents/utils/stock_utils.py` 已实现，支持 A 股 / 港股 / 美股识别、`600519 -> 600519.SH`、`600519.SS -> 600519.SH`、`get_full_symbol()`、市场元信息返回；并额外兼容了北京交易所代码。
- [x] `1.2` `tradingagents/agents/utils/agent_utils.py` 的 `build_instrument_context()` 已接入 `StockUtils`，能够在 prompt 中加入规范化 ticker、市场、交易所、币种信息。
- [~] `1.3` `cli/utils.py` 的 `normalize_ticker_symbol()` 已接入 `StockUtils.normalize_symbol()`；但 `TICKER_INPUT_EXAMPLES` 仍未更新为包含 A 股示例。

这是整个 A 股支持的"地基"。原版完全没有市场识别能力，必须先补全。

### 1.1 新建 `tradingagents/utils/stock_utils.py`

实现一个轻量级的 `StockUtils` 静态工具类，核心功能：

- `identify_stock_market(symbol: str) -> StockMarket`：
  - `6`, `0`, `3`, `8`, `4` 开头 6 位数字 → `CHINA_A`
  - `SH/SZ` + 6 位数字 → `CHINA_A`
  - `9` 开头 6 位数字 → 上交所 B 股（也归 `CHINA_A`）
  - 4-5 位数字 / `xxxx.HK` → `HONG_KONG`
  - 1-5 位字母 → `US`
- `get_market_info(symbol: str) -> dict`：
  - 返回 `market_name`, `exchange`, `currency_name`, `currency_symbol`, `timezone`, `is_china`, `is_hk`, `is_us`
- `normalize_symbol(symbol: str) -> str`：
  - `600519` → `600519.SH`
  - `000001` → `000001.SZ`
  - `600519.SS` → `600519.SH`（统一后缀）
- `get_full_symbol(symbol: str) -> str`：
  - 兼容 yfinance 格式：`600519.SS`, `000001.SZ`

> **设计约束**：该模块必须是纯函数，不依赖任何数据库/网络请求。

### 1.2 修改 `tradingagents/agents/utils/agent_utils.py`

- 在 `build_instrument_context(ticker)` 中，使用 `StockUtils` 获取市场信息，并在提示词中追加：
  - "该股票属于 A 股市场，交易所为上海证券交易所/深圳证券交易所"
  - "请使用该股票的完整代码 `{ticker}` 进行所有工具调用"

### 1.3 修改 `cli/utils.py`

- `normalize_ticker_symbol()` 中集成 `StockUtils.normalize_symbol()`
- `TICKER_INPUT_EXAMPLES` 修改为：
  ```python
  TICKER_INPUT_EXAMPLES = "Examples: AAPL, 600519.SH, 000001.SZ, 0700.HK"
  ```

---

## Phase 2: 数据层移植 — 三驾马车 (AKShare / Tushare / BaoStock) [部分完成]

**当前状态**
- [x] `2.1` `tradingagents/dataflows/providers/base_provider.py` 已新增极简 `BaseChinaDataProvider`。
- [~] `2.2` `tradingagents/dataflows/providers/china/akshare.py` 已实现同步历史行情、东方财富新闻直连、`get_stock_quotes()` / `get_batch_stock_quotes()` 与基础财务快照聚合；但 CN 版更丰富的初始化容错、基础信息增强和更细粒度 fallback 仍未补齐。
- [~] `2.3` `tradingagents/dataflows/providers/china/tushare.py` 已实现 `TUSHARE_TOKEN` 环境变量初始化、`ts.pro_bar(adj='qfq')`、股票基础信息/行情/财务快照聚合；但多源新闻轮询、情绪处理、报价批量能力和更完整的财务封装仍缺失。
- [~] `2.4` `tradingagents/dataflows/providers/china/baostock.py` 已实现历史行情路径、代码转换、估值数据、最新 K 线行情快照和最小财务数据聚合；`get_news()` 仍为空，接口丰富度仍弱于 CN 版。
- [~] `2.5` `tradingagents/dataflows/china_router.py` 已支持 provider 降级、环境开关、列名标准化、`get_stock_data_raw()` / `get_stock_data()` / `get_fundamentals()` / `get_news()`；但还没有 CN 版最重要的中文技术指标格式化输出、估值快照、股票基础信息与文件缓存代理。

### 2.1 抽象基类 `tradingagents/dataflows/providers/base_provider.py`

从 CN 版中提取一个极简的 `BaseChinaDataProvider`：

```python
class BaseChinaDataProvider(ABC):
    @abstractmethod
    def get_stock_data(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame: ...
    @abstractmethod
    def get_fundamentals(self, symbol: str) -> dict: ...
    @abstractmethod
    def get_news(self, symbol: str, limit: int = 10) -> list[dict]: ...
```

> 注意：去掉所有 `async/await`、数据库连接、Web 配置相关的抽象方法，只保留纯数据获取接口。

### 2.2 移植 AKShare 提供器

**文件**：`tradingagents/dataflows/providers/china/akshare.py`

- **保留**：
  - `AKShareProvider` 类主体
  - `_get_stock_news_direct()`（东方财富新闻 API + curl_cffi）
  - `_initialize_akshare()` 中的 requests monkey-patch（解决 headers 和延迟问题）
  - `get_historical_data()`（前复权）
  - `get_stock_quotes()` / `get_batch_stock_quotes()`（实时行情）
  - `_standardize_historical_columns()`（列名标准化为 `date/open/high/low/close/volume/amount`）
- **去除**：
  - 所有 `async/await`（改为同步接口，原版没有异步需求）
  - 所有对 `app.core.database` 的导入
  - 复杂的实时行情 `stock_bid_ask_em` 分支（保留更稳定的 `stock_zh_a_spot` 即可）
- **增强**：
  - 增加 `get_stock_data()` 接口，直接返回标准化后的 `pd.DataFrame`

### 2.3 移植 Tushare 提供器

**文件**：`tradingagents/dataflows/providers/china/tushare.py`

- **保留**：
  - `connect_sync()` 中的 Tushare 连接逻辑
  - `get_historical_data()` 使用 `ts.pro_bar(adj='qfq')`
  - `get_financial_data()` 封装 income/balancesheet/cashflow/fina_indicator
  - `get_stock_news()` 多源新闻轮询（sina/eastmoney/10jqka/cls...）
  - `_process_tushare_news()` 中的情绪分析和重要性评估
- **去除**：
  - `_get_token_from_database()` 及所有 MongoDB 导入
  - `connect()` 异步版本
  - 对 `app.core.database` 的导入
- **改造**：
  - Token 获取简化为：`os.getenv('TUSHARE_TOKEN')`
  - 所有方法改为同步（原版没有 asyncio 基础）

### 2.4 移植 BaoStock 提供器（可选）

**文件**：`tradingagents/dataflows/providers/china/baostock.py`

- 作为降级备选，保持最小可用集：
  - `get_historical_data()`（前复权）
  - `get_valuation_data()`（PE/PB）
  - `get_financial_data()`（profit/operation/growth/balance/cashflow）

### 2.5 数据源路由器 `tradingagents/dataflows/china_router.py`

**新建文件**，替代 CN 版重达 2400 行的 `data_source_manager.py`。核心职责是：**多源降级 + 数据格式化**。

```python
class ChinaDataRouter:
    def __init__(self):
        self.providers = []
        # 自动检测可用提供器
        if AKShareProvider().connected:
            self.providers.append(AKShareProvider())
        if TushareProvider().is_available():
            self.providers.append(TushareProvider())
        if BaoStockProvider().connected:
            self.providers.append(BaoStockProvider())

    def get_stock_data(self, symbol, start, end) -> str:
        for provider in self.providers:
            df = provider.get_stock_data(symbol, start, end)
            if df is not None and not df.empty:
                return self._format_stock_data_response(df, symbol, start, end)
        return f"❌ 无法获取 {symbol} 的历史数据"

    def get_fundamentals(self, symbol) -> str:
        # Tushare 优先（基本面最强），然后 AKShare
        for provider in self.providers:
            data = provider.get_fundamentals(symbol)
            if data:
                return self._format_fundamentals_response(data, symbol)
        return f"❌ 无法获取 {symbol} 的基本面数据"

    def get_news(self, symbol, limit=10) -> list[dict]:
        for provider in self.providers:
            news = provider.get_news(symbol, limit)
            if news:
                return news
        return []
```

**关键技术指标格式化**（从 CN 版 `data_source_manager.py` 中提取精华）：

`_format_stock_data_response(df, symbol, start, end) -> str` 必须包含：
- 移动平均线：MA5/MA10/MA20/MA60，并标注价格在均线上方/下方（↑↓）
- MACD：DIF/DEA/MACD，检测金叉/死叉
- RSI(6,12,24)：同花顺风格，超买超卖标注
- 布林带：上轨/中轨/下轨，价格位置百分比
- 最高价/最低价/平均价/成交量统计
- 全部用中文输出，货币符号用 ¥

> **约束**：该路由器只处理中国市场数据，美股/港股仍走原版 yfinance/alpha_vantage 路径。

---

## Phase 3: 技术指标层改造 [部分完成]

**当前状态**
- [~] `3.1` `tradingagents/dataflows/stockstats_utils.py` 的 `load_ohlcv()` 已新增 `vendor` 参数，并在 A 股场景下改走 `ChinaDataRouter`，美股/港股继续保留 yfinance 路径；但 China path 还没有接入文件缓存、A 股缓存命名兼容、interface 层统一透传。
- [x] `3.2` `ChinaDataRouter._standardize_historical_columns()` 已实现中英文字段映射，可为 `stockstats` 下游提供标准 `Date/Open/High/Low/Close/Volume/Amount` 列。
- [x] `3.3` `ChinaDataRouter._format_stock_data_response()` 已新增中文技术指标格式化输出（MA5/MA10/MA20/MA60、MACD 金叉/死叉、RSI(6/12/24)、布林带、最高价/最低价/平均价/成交量统计，货币符号 ¥）。

### 3.1 重构 `tradingagents/dataflows/stockstats_utils.py`

原版 `load_ohlcv()` 硬编码了 `yf.download()`，必须抽象化：

```python
def load_ohlcv(symbol: str, curr_date: str, vendor: str = None) -> pd.DataFrame:
    """
    根据配置的 vendor 加载 OHLCV 数据。
    如果是 A 股，优先使用 ChinaDataRouter；否则使用 yfinance。
    """
    market = StockUtils.identify_stock_market(symbol)
    if market == StockMarket.CHINA_A:
        # 使用 AKShare 获取数据（缓存到 data_cache_dir）
        router = ChinaDataRouter()
        df = router.get_stock_data_raw(symbol, start_date="5_years_ago", end_date=curr_date)
        return df
    else:
        # 原版 yfinance 逻辑
        ...
```

- 增加 `vendor` 参数的透传
- 缓存文件命名兼容 A 股：`600519-SS-data-2015-01-01-2025-04-15.csv`

### 3.2 兼容 `stockstats` 的列名映射

AKShare 返回的列名是中文（开盘/收盘/最高/最低/成交量），需要在做 `wrap(data)` 之前映射为英文：`open/high/low/close/volume`。

在 `ChinaDataRouter` 的 `_standardize_historical_columns()` 中完成映射，确保下游 `stockstats` 可以直接使用。

---

## Phase 4: 工具层重构 — Toolkit 与统一工具 [部分完成]

**当前状态**
- [x] `4.1` `tradingagents/agents/utils/agent_utils.py` 已新增 `Toolkit` 类，统一封装了 `get_stock_market_data_unified`、`get_stock_fundamentals_unified`、`get_stock_news_unified`、`get_indicators_unified`、`get_global_news_unified`。
- [x] `4.2` `tradingagents/tools/unified_news_tool.py` 已实现（去除 MongoDB 依赖）。
- [x] `4.3` `Toolkit` 已新增 `get_stock_sentiment_unified` 精简版（基于关键词情绪统计）。

### 4.1 `Toolkit` 类的引入

**修改** `tradingagents/agents/utils/agent_utils.py`：

将原版分散的 `get_stock_data`, `get_indicators`, `get_fundamentals`, `get_news`... 封装进一个 `Toolkit` 类。这是 CN 版的关键架构改进，让 `TradingAgentsGraph` 和 Analyst 都通过 `toolkit` 访问工具，而不是直接 import 函数。

```python
class Toolkit:
    def __init__(self, config: dict = None):
        self.config = config or DEFAULT_CONFIG
        self.china_router = ChinaDataRouter()
        self.online = self.config.get("online_tools", True)

    # ========== 统一市场数据工具 ==========
    def get_stock_market_data_unified(self, symbol, start_date, end_date) -> str:
        market = StockUtils.identify_stock_market(symbol)
        if market == StockMarket.CHINA_A:
            return self.china_router.get_stock_data(symbol, start_date, end_date)
        elif self.online:
            return get_YFin_data_online(symbol, start_date, end_date)
        else:
            return get_YFin_data(symbol, start_date, end_date)

    # ========== 统一基本面工具 ==========
    def get_stock_fundamentals_unified(self, symbol, curr_date=None) -> str:
        market = StockUtils.identify_stock_market(symbol)
        if market == StockMarket.CHINA_A:
            return self.china_router.get_fundamentals(symbol)
        else:
            # 美股：走原版 fundamental_data_tools
            return get_fundamentals(symbol, curr_date)

    # ========== 统一新闻工具 ==========
    def get_stock_news_unified(self, stock_code, max_news=10, model_info="") -> str:
        # 调用 Phase 4.2 中的 UnifiedNewsAnalyzer
        analyzer = UnifiedNewsAnalyzer(self)
        return analyzer.get_stock_news_unified(stock_code, max_news, model_info)

    # ========== 原有工具的保留 ==========
    def get_YFin_data_online(self, symbol, start_date, end_date): ...
    def get_indicators(self, symbol, indicator, curr_date, look_back_days): ...
    # ... 其他原版工具
```

### 4.2 统一新闻工具 `tradingagents/tools/unified_news_tool.py`

从 CN 版完整移植，但需要**去除 MongoDB 依赖**：

- **A 股路径**：
  1. 优先 `AKShareProvider.get_news()`（东方财富实时新闻）
  2. 失败则 `get_google_news(query=f"{stock_code} 股票 新闻")`
  3. 失败则 `get_stock_news_openai()`（OpenAI Web Search）
- **港股路径**：Google 新闻 → OpenAI → AKShare（部分港股有东方财富覆盖）
- **美股路径**：OpenAI → Google 英文 → yfinance news
- **Google 模型截断**：保留 3000~4000 字符的智能截断逻辑
- **去除**：`_get_news_from_database()`, `_sync_news_from_akshare()` 等 MongoDB 相关代码

### 4.3 统一情绪工具（精简版）

对于 `social_media_analyst`，CN 版的 `get_stock_sentiment_unified` 可以简化为：
- A 股：基于 `unified_news_tool` 获取的新闻，做简单的关键词情绪统计（positive/negative/neutral）
- 美股/港股：走原版 `get_news` 逻辑

不需要引入复杂的爬虫或微博 API。

---

## Phase 5: Agent 层增强 [部分完成]

**当前状态**
- [x] `5.1` `tradingagents/agents/analysts/china_market_analyst.py` 已创建并集成 `GoogleToolCallHandler`。
- [ ] `5.2` 当前 `fundamentals_analyst.py` / `news_analyst.py` / `market_analyst.py` / `social_media_analyst.py` 尚未接入 unified tools、强制工具调用补救、计数器、防死循环等 CN 增强。
- [x] `5.3` `tradingagents/agents/utils/google_tool_handler.py` 已完成。
- [ ] `5.4` `tradingagents/graph/setup.py` 仍只注册原版 4 个 analyst，没有 `china_market` 节点。
- [ ] `5.5` `tradingagents/graph/trading_graph.py` 仍基于旧工具函数构建 `ToolNode`，没有 `Toolkit` 驱动的统一工具节点。

### 5.1 新增中国市场分析师

**文件**：`tradingagents/agents/analysts/china_market_analyst.py`

从 CN 版完整移植 `create_china_market_analyst(llm, toolkit)`：
- Prompt 中注入 A 股规则（T+1、涨跌停、ST、科创/创业板差异）
- 工具绑定 `toolkit.get_stock_market_data_unified`
- 集成 `GoogleToolCallHandler`

### 5.2 增强所有现有 Analyst

对以下 4 个 Analyst 进行增强（以 `fundamentals_analyst.py` 为标杆）：

#### `fundamentals_analyst.py`
- 绑定 `toolkit.get_stock_fundamentals_unified`
- 增加 `_get_company_name_for_fundamentals()`，A 股自动解析中文名
- 增加 **强制工具调用机制**：如果 LLM 未调用工具，后端直接 `toolkit.get_stock_fundamentals_unified.invoke()` 获取数据，再生成报告
- 增加 `fundamentals_tool_call_count` 防止死循环
- 集成 `GoogleToolCallHandler`

#### `news_analyst.py`
- 绑定 `toolkit.get_stock_news_unified`
- 增加 `news_tool_call_count` 防止死循环
- 增加强制新闻获取补救机制
- 集成 `GoogleToolCallHandler`

#### `market_analyst.py`
- 在 Prompt 中增加中国市场技术指标说明
- 对于 A 股，优先调用 `toolkit.get_stock_market_data_unified`
- 集成 `GoogleToolCallHandler`

#### `social_media_analyst.py`
- 绑定 `toolkit.get_stock_sentiment_unified`
- 适配中文舆情分析 Prompt

### 5.3 Google 工具调用处理器

**文件**：`tradingagents/agents/utils/google_tool_handler.py`

从 CN 版**原样移植**。这个模块完全独立，不依赖 MongoDB/FastAPI，是纯粹的 LangChain 兼容层。

### 5.4 `graph/setup.py` 注册新 Agent

在 `GraphSetup.setup_graph()` 中：
- 保留原版 4 个 Analyst 的注册逻辑
- **新增可选注册**：如果 `selected_analysts` 包含 `"china_market"`，则注册 `China Market Analyst` 节点
- ToolNode 中增加 `china_market` 分支

### 5.5 `graph/trading_graph.py` 适配

- 将 `_create_tool_nodes()` 中的工具列表替换为 `Toolkit` 提供的统一工具
- `ToolNode` 构造方式：
  ```python
  toolkit = Toolkit(config=self.config)
  self.tool_nodes = {
      "market": ToolNode([toolkit.get_stock_market_data_unified, toolkit.get_indicators]),
      "news": ToolNode([toolkit.get_stock_news_unified, toolkit.get_global_news_openai]),
      "fundamentals": ToolNode([toolkit.get_stock_fundamentals_unified]),
      "social": ToolNode([toolkit.get_stock_sentiment_unified]),
      "china_market": ToolNode([toolkit.get_stock_market_data_unified]),
  }
  ```

---

## Phase 6: LLM 适配层 — 替换 `llm_clients/` [未开始]

**当前状态**
- [ ] `6.1` 当前仓库没有 `tradingagents/llm_adapters/` 目录。
- [ ] `6.2` `dashscope_openai_adapter.py`、`deepseek_adapter.py`、`google_openai_adapter.py`、`openai_compatible_base.py` 均未移植。
- [ ] `6.3` `tradingagents/graph/trading_graph.py` 仍只支持原版 provider 路径，没有 `dashscope` / `deepseek` / `zhipu` / `siliconflow` / `qianfan` / `custom_openai` 分支，也没有 quick/deep 混合 provider 支持。
- [ ] `6.4` `cli/utils.py` 尚未加入国产 LLM 选项与对应模型菜单。
- [~] 附注：当前仅对 `tradingagents/llm_clients/__init__.py` 和 `google_client.py` 做了轻量兼容性调整（懒加载 / 可选导入），这不是本 Phase 的正式移植内容。

### 6.1 目录替换策略

原版 `tradingagents/llm_clients/` 只支持 OpenAI/Anthropic/Google/xAI/OpenRouter/Ollama。

**最经济的做法**：不删除 `llm_clients/`，而是在 `tradingagents/` 下**新建** `llm_adapters/`，然后在 `trading_graph.py` 中让 `create_llm_by_provider()` 优先使用新适配器。

### 6.2 需要移植的适配器文件

从 CN 版复制到 `tradingagents/llm_adapters/`：
- `dashscope_openai_adapter.py` — 阿里百炼
- `deepseek_adapter.py` — DeepSeek（带 token 统计）
- `google_openai_adapter.py` — Gemini OpenAI 兼容
- `openai_compatible_base.py` — 智谱/千帆/SiliconFlow/自定义端点

### 6.3 `trading_graph.py` 中的 `create_llm_by_provider()`

在 `TradingAgentsGraph.__init__()` 中：
- 保留原版对 `openai`, `anthropic`, `google`, `ollama` 的处理逻辑
- **新增分支**：`dashscope`, `deepseek`, `zhipu`, `siliconflow`, `qianfan`, `custom_openai`
- 混合模式支持：快速模型和深度模型可以来自不同厂家（如 quick=deepseek, deep=claude）

### 6.4 CLI 模型选择增强

**修改** `cli/utils.py`：
- `select_llm_provider()` 中增加国产 LLM 选项：
  - 阿里百炼 (DashScope)
  - DeepSeek
  - 智谱 AI (Zhipu)
  - 百度千帆 (Qianfan)
  - SiliconFlow
- 当选择国产 LLM 时，自动读取对应环境变量作为 API Key
- `select_shallow_thinking_agent()` / `select_deep_thinking_agent()` 中增加国产模型列表：
  - DeepSeek: `deepseek-chat`, `deepseek-reasoner`
  - DashScope: `qwen-max`, `qwen-plus`, `qwen-turbo`
  - Zhipu: `glm-4`, `glm-4-flash`

---

## Phase 7: CLI 层完整适配 [部分完成]

**当前状态**
- [ ] `7.1` `cli/models.py` 还没有 `CHINA_MARKET`。
- [~] `7.2` `cli/utils.py` 已具备 A 股 ticker 自动补全能力，但仍缺 China Market Analyst 选项、A 股数据源选择交互、更新后的输入示例。
- [ ] `7.3` `cli/akshare_init.py`、`cli/tushare_init.py`、`cli/baostock_init.py` 尚未创建。
- [ ] `7.4` `cli/main.py` 还没有基于市场自动注入 A 股配置、默认启用 China analyst、预检数据源的主流程。

### 7.1 Analyst 类型扩展 (`cli/models.py`)

```python
class AnalystType(str, Enum):
    MARKET = "market"
    SOCIAL = "social"
    NEWS = "news"
    FUNDAMENTALS = "fundamentals"
    CHINA_MARKET = "china_market"  # [新增]
```

### 7.2 CLI 交互增强 (`cli/utils.py`)

- `select_analysts()` 中增加 "China Market Analyst" 选项
- `get_ticker()` 增加 A 股代码实时校验：
  - 如果用户输入 `600519`（不带后缀），自动补全为 `600519.SH`
  - 如果用户输入 `000001.SZ`，保留原样
- 增加 `ask_data_source()` 可选交互：让用户选择 A 股数据源优先级（AKShare / Tushare / Auto）

### 7.3 数据源初始化命令（新增 CLI 子命令）

在 `cli/` 下新增三个轻量级初始化脚本：
- `cli/akshare_init.py`：验证 AKShare 连接，打印可用接口列表
- `cli/tushare_init.py`：验证 Tushare Token 有效性
- `cli/baostock_init.py`：验证 BaoStock 登录

这些不作为主 CLI 必经流程，而是作为 `python -m cli.akshare_init` 的独立诊断工具。

### 7.4 主流程 `cli/main.py`

- 在 `run_analysis()` 中，根据用户选择的 `ticker` 自动判断市场：
  - 如果是 A 股，默认启用 `china_market` analyst（如果用户选了它）
  - 在 `config` 中注入 `online_tools=true` 和 `data_source_priority`
- 输出报告保存路径保持原版的 `results/{ticker}/{date}/` 结构

---

## Phase 8: 配置与缓存策略（轻量版） [部分完成]

**当前状态**
- [x] `8.1` `tradingagents/default_config.py` 已加入 `online_tools`、`data_source_priority`、`quick_think_llm_provider`/`deep_think_llm_provider` 扩展；`output_language` 保持 English 默认（CLI 在 A 股流程中可覆盖为 Chinese）。
- [ ] `8.2` 当前没有 AKShare/Tushare/news 的文件缓存路径约定与 TTL 管理，`ChinaDataRouter` 也尚未代理缓存读写。

### 8.1 `tradingagents/default_config.py` 扩展

```python
DEFAULT_CONFIG = {
    # ... 原有配置 ...
    "online_tools": True,
    "data_source_priority": ["akshare", "tushare", "baostock"],
    "output_language": "Chinese",
    "llm_provider": "openai",  # 也可以是 "deepseek", "dashscope" 等
}
```

### 8.2 文件缓存策略

不使用 MongoDB/Redis，只使用**文件缓存**：

- **AKShare 缓存**：
  - 路径：`{data_cache_dir}/akshare/{symbol}/{start}_{end}.csv`
  - 缓存 TTL：日线数据 1 天，实时行情 5 分钟
- **Tushare 缓存**：
  - 路径：`{data_cache_dir}/tushare/{symbol}/{start}_{end}.csv`
  - 缓存 TTL：财务数据 1 天（因为财报不频繁更新）
- **新闻缓存**：
  - 路径：`{data_cache_dir}/news/{symbol}/{date}.json`
  - 缓存 TTL：2 小时

缓存读写由 `ChinaDataRouter` 统一代理，对各 Provider 透明。

---

## Phase 9: 测试验证矩阵 [部分完成]

**当前状态**
- [~] `9.1` 已新增 `tests/test_stock_utils.py`、`tests/test_china_router.py`、`tests/test_china_providers.py`，并扩展 `tests/test_ticker_symbol_handling.py`；当前还缺 `test_unified_news.py`、`test_google_tool_handler.py`、联网 provider 集成测试。
- [ ] `9.2` 计划中的 CLI 端到端测试尚未执行。
- [ ] `9.3` 验收标准大多尚未满足或尚未验证。

### 9.1 单元测试

新增以下测试文件到 `tests/`：

| 测试文件 | 验证内容 | 当前状态 |
|---------|---------|---------|
| `test_stock_utils.py` | `600519`→SH, `000001`→SZ, `AAPL`→US, `0700.HK`→HK | `[x]` 已完成 |
| `test_china_router.py` | China router 的 provider 开关、路由行为、列名标准化 | `[~]` 已完成单元测试；尚未做真实 provider 联网集成验证 |
| `test_china_router_format.py` | 中文技术指标格式化（MA/MACD/RSI/BOLL/量价统计） | `[x]` 已完成单元测试 |
| `test_china_providers.py` | AKShare/Tushare/BaoStock 的行情/估值/财务快照聚合 | `[x]` 已完成单元测试 |
| `test_toolkit.py` | Toolkit 统一工具路由（A 股/美股市场/基本面/新闻） | `[x]` 已完成单元测试 |
| `test_unified_news.py` | `UnifiedNewsAnalyzer` 对 A 股返回包含中文新闻的字符串 | `[ ]` 未开始 |
| `test_google_tool_handler.py` | 模拟 Gemini 的 `tool_calls` 格式，验证能正确生成报告 | `[ ]` 未开始 |

### 9.2 端到端测试

在本地环境运行以下 CLI 命令，确保全部通过：

```bash
# 1. A 股 + 国产 LLM (DeepSeek)
python -m cli.main
# 输入: 600519.SH, 2025-04-15, 选择 China Market + Fundamentals + News, DeepSeek

# 2. A 股 + OpenAI
python -m cli.main
# 输入: 000001.SZ, 2025-04-15, 选择全部 Analyst, OpenAI

# 3. 美股回归测试（确保原版功能未破坏）
python -m cli.main
# 输入: NVDA, 2026-01-15, 选择 Market + Fundamentals + News, OpenAI

# 4. 港股测试
python -m cli.main
# 输入: 0700.HK, 2025-04-15, 选择 News + Fundamentals, OpenAI
```

### 9.3 验收标准

- [ ] `600519.SH` 分析能在 3 分钟内完成（含数据获取 + LLM 推理）
- [ ] 所有 Analyst 报告均为中文（当 `output_language=Chinese` 时）
- [ ] Market Analyst 报告中包含 MA/MACD/RSI/BOLL 等中文技术指标
- [ ] News Analyst 报告中包含东方财富或 Tushare 来源的最新新闻
- [ ] Fundamentals Analyst 报告中包含 PE/PB/ROE 等估值数据
- [ ] 使用 DeepSeek/DashScope/Zhipu 时，工具调用不报错
- [ ] 使用 Gemini 时，不会因工具调用格式问题而崩溃
- [ ] 美股 `NVDA` 的分析结果与原版一致（回归测试）

---

## Phase 10: 文档与清理 [未开始]

**当前状态**
- [ ] `10.1` README 尚未加入 A 股与国产 LLM 说明章节。
- [ ] `10.2` 还没有执行面向整个仓库的移植清理与 lint 收口。

### 10.1 README 更新

在 `README.md` 中新增 "A 股与国产 LLM 支持" 章节，包含：
- 支持的 A 股数据源（AKShare / Tushare / BaoStock）
- 支持的国产 LLM（DeepSeek / 阿里百炼 / 智谱 / 千帆 / SiliconFlow）
- A 股代码输入示例（`600519.SH`, `000001.SZ`）
- 环境变量配置说明

### 10.2 代码清理

- 删除 CN 版移植过程中产生的临时文件
- 确保没有遗留的 `from app.core.database import ...` 或 MongoDB 相关导入
- 运行 `ruff check tradingagents/` 或 `flake8`，确保无语法错误

---

## 附录：移植后文件变更清单（含当前完成情况）

### 新增文件（~18 个）

```
tradingagents/
├── agents/
│   ├── analysts/china_market_analyst.py   # [已完成]
│   └── utils/google_tool_handler.py       # [已完成]
├── dataflows/
│   ├── china_router.py                    # [已完成]
│   └── providers/
│       ├── __init__.py                    # [已完成]
│       ├── base_provider.py               # [已完成]
│       └── china/
│           ├── __init__.py                # [已完成]
│           ├── akshare.py                 # [部分完成]
│           ├── tushare.py                 # [部分完成]
│           └── baostock.py                # [部分完成]
├── llm_adapters/                          # [未开始]
│   ├── __init__.py
│   ├── dashscope_openai_adapter.py
│   ├── deepseek_adapter.py
│   ├── google_openai_adapter.py
│   └── openai_compatible_base.py
├── tools/                                 # [已完成]
│   ├── __init__.py
│   └── unified_news_tool.py
├── utils/
│   ├── __init__.py                        # [已完成]
│   └── stock_utils.py                     # [已完成]
└── tests/
    ├── test_stock_utils.py                # [已完成]
    ├── test_china_router.py               # [已完成，当前为单元测试]
    ├── test_china_router_format.py        # [已完成，当前为单元测试]
    ├── test_china_providers.py            # [已完成，当前为单元测试]
    ├── test_toolkit.py                    # [已完成，当前为单元测试]
    ├── test_unified_news.py               # [未开始]
    └── test_google_tool_handler.py        # [未开始]
```

### 修改文件（~10 个）

```
tradingagents/
├── agents/
│   ├── analysts/
│   │   ├── fundamentals_analyst.py        # [未开始]
│   │   ├── market_analyst.py              # [未开始]
│   │   ├── news_analyst.py                # [未开始]
│   │   └── social_media_analyst.py        # [未开始]
│   └── utils/agent_utils.py               # [已完成 Toolkit 与统一工具集成；Analyst 接入待完成]
├── dataflows/
│   ├── china_router.py                    # [部分完成：已新增格式化输出，缓存/TTL 未完成]
│   ├── interface.py                       # [未开始]
│   └── stockstats_utils.py                # [部分完成]
├── graph/
│   ├── setup.py                           # [未开始]
│   └── trading_graph.py                   # [未开始]
├── default_config.py                      # [已完成配置扩展；缓存策略未完成]
└── llm_clients/
    └── (保留但优先级降低，被 llm_adapters 补充)  # [未开始]

cli/
├── main.py                                # [未开始]
├── models.py                              # [未开始]
└── utils.py                               # [部分完成]

pyproject.toml                             # [部分完成]
.env.example                               # [已完成]
tests/test_ticker_symbol_handling.py       # [已完成，辅助回归]
```

---

## 执行建议：分 3 个迭代推进

### 迭代 1：数据先行（Week 1）
- Phase 0 ~ Phase 3
- 目标：命令行输入 `600519.SH` 能拿到正确的 OHLCV、基本面、新闻数据
- 当前进度：已完成 ticker 识别、A 股路由骨架和部分 provider；距离"稳定拿到正确的 OHLCV、基本面、新闻数据"仍差 router 格式化、provider 丰富能力、统一接口层。

### 迭代 2：Agent 与 LLM（Week 2）
- Phase 4 ~ Phase 6
- 目标：所有 Analyst 能正确使用中国数据源，国产 LLM 能正常对话和调用工具
- 当前进度：Toolkit 与统一工具已完成，`china_market_analyst.py` 和 `google_tool_handler.py` 已落地；剩余 4 个现有 Analyst 的增强、Graph 注册、`llm_adapters/` 尚未开始。

### 迭代 3：打磨与测试（Week 3）
- Phase 7 ~ Phase 10
- 目标：CLI 体验完整、回归测试通过、文档更新完毕
- 当前进度：仅有 CLI ticker 自动补全和部分单元测试提前落地，整体仍未开始。

---

*本计划为"最经济但最完整"的移植方案。如果希望进一步压缩范围，可以优先执行标有 ★★★★★ 的模块（见 `CN_INVENTORY.md`），但建议至少完成迭代 1 和迭代 2 的核心内容。*
