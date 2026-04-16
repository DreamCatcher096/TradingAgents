# Roadmap

Source of truth: `docs/PORTING_PLAN.md` (status snapshot dated 2026-04-16)

## Goal

Port the CLI-relevant, pure-Python functionality from `TradingAgents-CN` into `TradingAgents` without breaking the upstream architecture or existing US/HK workflows.

## Phase Summary

| Phase | Status | Goal |
|------|--------|------|
| 0 | In progress | Finish the CN dependency, environment, and directory scaffolding without introducing web or database runtime requirements. |
| 1 | In progress | Complete market identification and CLI ticker UX so A-share symbols flow cleanly through prompts and tools. |
| 2 | In progress | Close the remaining China provider/router gaps for richer quotes, valuations, fundamentals, and structured data routing. |
| 3 | In progress | Finish A-share technical-indicator plumbing, cache compatibility, and file-cache support in the OHLCV path. |
| 4 | Complete | Land the Toolkit-based unified tool architecture for market, fundamentals, news, sentiment, and indicators. |
| 5 | In progress | Wire the remaining analysts and graph setup onto unified tools and the China market analyst path. |
| 6 | Not started | Add `llm_adapters/` and domestic-provider support without removing the upstream LLM clients. |
| 7 | In progress | Complete CLI support for A-share-specific analyst selection, data-source setup, and market-aware runtime behavior. |
| 8 | Complete | Extend default config for online tools and provider priority; follow-up cache TTL work remains in the data layer. |
| 9 | In progress | Add missing unit, tool-call, and CLI regression coverage for the ported behavior. |
| 10 | Not started | Update README and perform final cleanup/linting for the completed port. |

## Phase Details

### Phase 0: 环境基座与项目准备
Status: In progress
Goal: Keep all China-specific dependencies and scaffolding lightweight and installable in a pure-Python environment.
Success criteria:
1. Environment variables cover China data sources and domestic LLM providers.
2. Required scaffolding for China-specific modules exists where the remaining implementation needs it.
3. No MongoDB, Redis, FastAPI, or Vue dependencies are introduced.

### Phase 1: 股票识别与市场判断基础设施
Status: In progress
Goal: Normalize ticker handling and market metadata so A-share symbols behave consistently in the CLI and agent prompts.
Success criteria:
1. A-share, HK, and US symbols are identified and normalized correctly.
2. CLI examples and ticker entry flows reflect A-share support.
3. Agent prompts consistently receive normalized market context.

### Phase 2: 数据层移植 — 三驾马车
Status: In progress
Goal: Make AKShare, Tushare, and BaoStock routing rich enough to cover the CN data use cases that matter in the CLI.
Success criteria:
1. China providers expose usable historical, quote, valuation, and fundamentals APIs.
2. Router fallback order is reliable and formats output for CLI/LLM consumption.
3. Missing provider and router capabilities called out in `docs/PORTING_PLAN.md` are closed or intentionally deferred.

### Phase 3: 技术指标层改造
Status: In progress
Goal: Ensure the A-share OHLCV path supports technical analysis, cache compatibility, and structured Chinese formatting.
Success criteria:
1. `load_ohlcv()` routes A-share requests through China data flows without regressing other markets.
2. Technical-indicator consumers receive stockstats-compatible data.
3. File-cache and TTL behavior for China OHLCV/news/fundamentals is implemented or clearly tracked.

### Phase 4: 工具层重构 — Toolkit 与统一工具
Status: Complete
Goal: Route analyst tools through the shared Toolkit and unified news/sentiment helpers.
Success criteria:
1. Unified market, fundamentals, news, sentiment, and indicator entry points exist.
2. The toolkit mediates market-aware tool routing.
3. Unified news logic works without MongoDB.

### Phase 5: Agent 层增强
Status: In progress
Goal: Finish analyst- and graph-level integration so all relevant analysts can use the unified tool layer safely.
Success criteria:
1. Existing analysts use unified tools and fallback behavior where required.
2. Gemini/Google tool-call compatibility remains intact.
3. Graph setup can register and route the China market analyst path.

### Phase 6: LLM 适配层
Status: Not started
Goal: Add domestic-provider adapters and mixed quick/deep provider support.
Success criteria:
1. `tradingagents/llm_adapters/` exists with the planned adapters.
2. `TradingAgentsGraph` can create LLMs for the new providers.
3. CLI model selection exposes the new provider/model choices.

### Phase 7: CLI 层完整适配
Status: In progress
Goal: Make the CLI fully market-aware for A-share analysis and setup flows.
Success criteria:
1. China market analyst selection exists in the CLI models and prompts.
2. A-share-specific data-source selection and init helpers are available.
3. CLI runtime injects the right China config when the ticker is an A-share.

### Phase 8: 配置与缓存策略
Status: Complete
Goal: Extend base configuration for the port while leaving cache/TTL implementation to follow-up work.
Success criteria:
1. Config exposes online tools and China data-source priority.
2. Quick and deep model provider separation is configurable.
3. Output language can be overridden for A-share flows.

### Phase 9: 测试验证矩阵
Status: In progress
Goal: Close the missing unit, tool-call, and end-to-end regression tests for the port.
Success criteria:
1. Missing tests for unified news and Google tool handling are added.
2. CLI regression scenarios for A-share, HK, and US flows are executable.
3. Acceptance criteria in `docs/PORTING_PLAN.md` are either verified or explicitly tracked as pending.

### Phase 10: 文档与清理
Status: Not started
Goal: Document the completed A-share and domestic-LLM support and clean up porting leftovers.
Success criteria:
1. README documents A-share support, domestic LLMs, and environment setup.
2. Temporary migration leftovers and stale imports are removed.
3. Lint and sanity checks pass for the cleaned-up codebase.
