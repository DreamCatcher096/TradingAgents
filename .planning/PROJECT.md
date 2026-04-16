# TradingAgents A-Share Port

## What This Is

This repository is the upstream `TradingAgents` codebase with an in-progress brownfield port of the CLI-focused, pure-Python parts of `TradingAgents-CN`. The goal is to keep the original multi-market architecture lightweight while making A-shares and Chinese LLM providers first-class citizens in the terminal workflow.

## Core Value

Ship a pure-Python `TradingAgents` codebase that preserves the existing US/HK experience while delivering a complete, production-usable A-share analysis path in the CLI.

## Requirements

### Validated

- [x] Base TradingAgents analyst graph, CLI workflow, and multi-provider LLM support remain intact in the upstream project.
- [x] Initial A-share groundwork already exists: ticker normalization, China providers/router scaffolding, Toolkit unified tools, and the China market analyst.

### Active

- [ ] Close the remaining China data-layer gaps from `docs/PORTING_PLAN.md`, especially richer provider coverage and file-cache/TTL support.
- [ ] Finish agent, graph, and CLI integration so A-share flows work end to end without regressing US/HK behavior.
- [ ] Add domestic LLM adapters, targeted tests, and final documentation for the port.

### Out of Scope

- Web, database, and service-layer code from `TradingAgents-CN` (`MongoDB`, `Redis`, `FastAPI`, `Vue`) — explicitly excluded to keep this repo installable with `pip install` only.
- Replacing the upstream architecture wholesale — the upstream repo stays the base and CN behavior is layered in as targeted patches.

## Context

- Canonical porting plan: `docs/PORTING_PLAN.md`
- Reference implementation: `~/projects/TradingAgents-CN`
- Latest recorded status in the porting plan shows Phases 4 and 8 complete, Phases 0/1/2/3/5/7/9 partially complete, and Phases 6/10 not started.
- The current working tree already contains substantial uncommitted porting changes; new work must avoid disturbing unrelated edits.

## Constraints

- **Tech stack**: Pure Python only — new functionality must run without Docker, databases, or background services.
- **Compatibility**: US and HK flows must keep working while A-shares become a first-class market.
- **Architecture**: Prefer small, upstream-friendly patches instead of a heavy CN-style service rewrite.
- **Reference source**: `TradingAgents-CN` is a patch source, not the target architecture.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Use upstream `TradingAgents` as the permanent base | Keeps the port maintainable and minimizes divergence from upstream updates | ✓ Good |
| Keep all CN additions pure-Python and optional where possible | Matches the repo's installation model and avoids web/database dependencies | ✓ Good |
| Preserve US/HK behavior while adding A-share support | The port is an expansion, not a market-specific fork | ✓ Good |
| Use `docs/PORTING_PLAN.md` as the current brownfield execution source | Existing work is already tracked there and can seed GSD state | ✓ Good |

---
*Last updated: 2026-04-16 after bootstrapping GSD state from `docs/PORTING_PLAN.md`*
