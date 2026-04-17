# TradingAgents CN Port Phase 0-3 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add the first A-share foundation slice so `600519`/`000001` can be normalized, described correctly in prompts, and routed toward China-specific OHLCV loading without breaking existing US/HK paths.

**Architecture:** Keep the current TradingAgents layout intact and add the CN port as small, isolated modules. Build the market-recognition layer first, then connect it into CLI and agent prompts, then add a lightweight China provider/router abstraction that `stockstats_utils` can call for A-share symbols while non-China symbols continue to use yfinance unchanged.

**Tech Stack:** Python, unittest/pytest-compatible tests, pandas, yfinance, optional AKShare/Tushare/BaoStock integrations.

---

### Task 1: Add market recognition foundation

**Files:**
- Create: `tradingagents/utils/__init__.py`
- Create: `tradingagents/utils/stock_utils.py`
- Modify: `pyproject.toml`
- Modify: `.env.example`
- Test: `tests/test_stock_utils.py`

**Step 1: Write the failing test**

Add tests for:
- `StockUtils.identify_stock_market("600519") == StockMarket.CHINA_A`
- `StockUtils.identify_stock_market("000001.SZ") == StockMarket.CHINA_A`
- `StockUtils.identify_stock_market("0700.HK") == StockMarket.HONG_KONG`
- `StockUtils.identify_stock_market("AAPL") == StockMarket.US`
- `StockUtils.normalize_symbol("600519") == "600519.SH"`
- `StockUtils.normalize_symbol("600519.SS") == "600519.SH"`
- `StockUtils.normalize_symbol("000001") == "000001.SZ"`
- `StockUtils.get_market_info("600519")` returns Shanghai / RMB metadata.

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_stock_utils.py -v`
Expected: FAIL because `tradingagents.utils.stock_utils` does not exist yet.

**Step 3: Write minimal implementation**

Implement `StockMarket` and `StockUtils` with pure helper methods only. Update `pyproject.toml` and `.env.example` with the planned China data source and domestic LLM environment entries, but do not add any runtime dependency on web/database stacks.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_stock_utils.py -v`
Expected: PASS.

### Task 2: Connect ticker normalization into CLI and agent prompts

**Files:**
- Modify: `cli/utils.py`
- Modify: `tradingagents/agents/utils/agent_utils.py`
- Modify: `tests/test_ticker_symbol_handling.py`

**Step 1: Write the failing test**

Add tests for:
- `normalize_ticker_symbol(" 600519 ") == "600519.SH"`
- `normalize_ticker_symbol("600519.ss") == "600519.SH"`
- `normalize_ticker_symbol("000001") == "000001.SZ"`
- `build_instrument_context("600519.SH")` includes market, exchange, and exact ticker guidance.

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_ticker_symbol_handling.py -v`
Expected: FAIL because current normalization only uppercases and current prompt context lacks market metadata.

**Step 3: Write minimal implementation**

Route CLI normalization through `StockUtils.normalize_symbol()` and enrich `build_instrument_context()` with `StockUtils.get_market_info()` output while preserving current non-China behavior.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_ticker_symbol_handling.py -v`
Expected: PASS.

### Task 3: Add China data provider/router scaffolding and A-share OHLCV routing

**Files:**
- Create: `tradingagents/dataflows/providers/__init__.py`
- Create: `tradingagents/dataflows/providers/base_provider.py`
- Create: `tradingagents/dataflows/providers/china/__init__.py`
- Create: `tradingagents/dataflows/providers/china/akshare.py`
- Create: `tradingagents/dataflows/providers/china/tushare.py`
- Create: `tradingagents/dataflows/providers/china/baostock.py`
- Create: `tradingagents/dataflows/china_router.py`
- Modify: `tradingagents/dataflows/stockstats_utils.py`
- Test: `tests/test_china_router.py`

**Step 1: Write the failing test**

Add tests for:
- `ChinaDataRouter._standardize_historical_columns()` maps Chinese OHLCV columns to `Date/Open/High/Low/Close/Volume/Amount`
- `load_ohlcv("600519.SH", "2025-04-15")` uses `ChinaDataRouter.get_stock_data_raw()`
- `load_ohlcv("AAPL", "2025-04-15")` keeps using the yfinance path

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_china_router.py -v`
Expected: FAIL because router/provider modules do not exist and `load_ohlcv()` does not branch by market.

**Step 3: Write minimal implementation**

Create a lightweight provider abstraction with optional dependency detection. Implement the first router version with provider registration, column normalization, and a raw DataFrame path for `stockstats_utils`. Keep provider imports lazy so tests do not require AKShare/Tushare/BaoStock to be installed.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_china_router.py -v`
Expected: PASS.

### Task 4: Run targeted regression checks for the first slice

**Files:**
- Test only.

**Step 1: Run the focused suite**

Run: `pytest tests/test_stock_utils.py tests/test_ticker_symbol_handling.py tests/test_china_router.py -v`

**Step 2: Run existing regression coverage that touches changed areas**

Run: `pytest tests/test_google_api_key.py tests/test_model_validation.py -v`

**Step 3: Fix any regressions**

Only if the suite shows issues caused by the new work.
