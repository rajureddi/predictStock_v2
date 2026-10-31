# Graph Report - marketmind-pro-WINDOWS-FINAL  (2026-10-31)

## Corpus Check
- 208 files · ~540,812 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 11 file(s) not represented in the graph (top: .toml 4, (none) 2, .css 2)

## Summary
- 3721 nodes · 8219 edges · 170 communities (160 shown, 10 thin omitted)
- Extraction: 98% EXTRACTED · 2% INFERRED · 0% AMBIGUOUS · INFERRED: 169 edges (avg confidence: 0.86)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `7f475860`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- SimClock
- Market Scan Lifecycle Control
- test_pro.py
- test_v2.py
- Frontend React Application UI
- Bhavcopy Exchange Ingestion
- sectors.py
- FastAPI REST Endpoints
- Tool Orchestration
- Historical Market Datafeed
- TypeScript Compiler Configuration
- Verification Chains (by Language)
- Context Management
- The 20 Anti-Patterns
- Persona Protocol
- GRAVITAS Prompt Template
- Agent: General
- Agent: Verify
- The 7 Attack Vectors
- Model-Native Optimization Notes (Gemini tuned)
- Memory Protocol
- Agent: Plan
- Subagent Patterns
- argparse
- trader-news/news.py
- GRAVITAS -- Engineering Reliability Runtime
- Gravitas -- Verification Reference
- Gravitas -- Interruption Recovery Reference
- verify.sh
- live-browser.js
- Gravitas -- Delegation Reference
- Gravitas -- Task Contract Reference
- Agent: Explore
- Gravitas -- Model Routing Reference
- Gravitas -- Adaptive Reasoning Reference
- Gravitas -- Reconnaissance Reference
- trader-scanner/scan.py
- trader/scan.py
- coordinator.md
- run-checks.sh
- SESSION_FAILURES.md
- trader-entry/entry.py
- backtest_portfolio.py
- time_machine
- trader/timemachine.py
- trader-broker/ticket.py
- trader/ticket.py
- trader/size.py
- trader-budget/size.py
- trader-exit/exit.py
- trader/exit.py
- json
- trader-alerts/alerts.py
- trader/news.py
- trader-analyst/facts.py
- trader/facts.py
- trader/check.py
- trader-pelosi/ptr.py
- os
- datetime
- trader-risk/check.py
- AlertError
- trader-alerts
- trader-budget
- trader-pelosi
- trader-broker
- trader-risk
- trader-entry
- trader-exit
- trader-timemachine
- connectSSE
- trader-alerts/market.py
- trader-analyst
- trader-news
- trader-entry/market.py
- trader-timemachine/market.py
- Day Trader Skills — MarketMind Pro
- trader/market.py
- trader-broker/market.py
- applyEditing
- surveillance.py
- trader-scanner/market.py
- trader-news/market.py
- trader/entry.py
- resumeSession
- initPageChat
- history_replay
- simulation.py
- cmd_watch
- pipeline.py
- modern-screenshot.umd.js
- TMError
- watch_loop
- trader-scanner
- trader-timemachine/timemachine.py
- market_status
- fetch_chart
- evaluate
- to_eastern
- el
- initGlobalBar
- new-work.md
- parse_bars
- SimClock
- lib.tsx
- impeccable/SKILL.md
- updatePendingCounter
- Responsive Design
- live.md
- createLiveBrowserDomHelpers
- onboard.md
- mountSvelteComponentVariant
- bolder.md
- The Toolkit
- createLiveBrowserSessionState
- ui-backup-original/App.tsx
- actOnAgentTarget
- onAnnotDown
- animate.md
- Handle `generate`
- src/App.tsx
- Generate Report
- cmd_orb
- New visual work
- optimize.md
- SurfaceBackdrop
- Impeccable Asset Producer
- Scan mode (approach C: auto-extract, then confirm descriptive language)
- generate.md
- Visualize: Direction Comps & Asset Production
- critique.md
- Simplify the Design
- Hardening Dimensions
- urllib_request
- clarify.md
- Nielsen's 10 Heuristics
- Generate Combined Critique Report
- entry_doc
- polish.md
- quieter.md
- doctor.md
- Read
- Product
- Init flow
- Common Cognitive Load Violations
- iOS platform
- eastern_offset
- Shape
- _absorb
- orb_window
- adapt.native.md
- Android platform
- Persona-Based Design Testing
- Extract Flow
- Generate Report
- Cognitive Load Assessment
- Impeccable Finish Reviewer
- Impeccable Manual Edit Applier
- live-browser-ignores.js
- Diagnostic Scan
- $impeccable hooks
- build_universe
- interface
- Region map
- Heuristics Scoring Guide
- Impeccable Documenter
- hasTextRows

## God Nodes (most connected - your core abstractions)
1. `connectSSE()` - 34 edges
2. `setLiveState()` - 33 edges
3. `showToast()` - 33 edges
4. `resumeSession()` - 33 edges
5. `initGlobalBar()` - 30 edges
6. `el()` - 29 edges
7. `buildInsertConfigureRow()` - 28 edges
8. `handleKeyDown()` - 28 edges
9. `cleanup()` - 27 edges
10. `injectSvelteComponentsFromManifest()` - 26 edges

## Surprising Connections (you probably didn't know these)
- `The universe` --references--> `universe()`  [INFERRED]
  .agents/skills/trader-scanner/SKILL.md → backend/app/main.py
- `Step 2: Act by severity` --references--> `init()`  [INFERRED]
  .agents/skills/impeccable/reference/doctor.md → .agents/skills/impeccable/scripts/live-browser.js
- `What this owns, and what it does not` --references--> `init()`  [INFERRED]
  .agents/skills/impeccable/reference/doctor.md → .agents/skills/impeccable/scripts/live-browser.js
- `Commands` --references--> `init()`  [INFERRED]
  .agents/skills/impeccable/SKILL.md → .agents/skills/impeccable/scripts/live-browser.js
- `What it reads and writes` --references--> `universe()`  [INFERRED]
  .agents/skills/trader-scanner/SKILL.md → backend/app/main.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **End-to-End Market Screening Pipeline** — readme_stage1_screen, readme_stage2_deep_evaluation, readme_fundamentals_check, readme_news_veto [INFERRED 0.85]

## Communities (170 total, 10 thin omitted)

### Community 1 - "Market Scan Lifecycle Control"
Cohesion: 0.11
Nodes (21): scan_status(), checkpoint_progress(), find_scan_pids(), get_status(), _log_stage(), _pid_alive(), _read_json(), scan_running() (+13 more)

### Community 2 - "test_pro.py"
Cohesion: 0.12
Nodes (22): add_indicators(), _adx(), _atr(), build_features(), detect_patterns(), _ema(), _fit_predict(), _rsi() (+14 more)

### Community 3 - "test_v2.py"
Cohesion: 0.11
Nodes (20): attach_fundamentals(), _clean_num(), fetch_fundamentals(), _fetch_one(), _load_cache(), _save_cache(), score_fundamentals(), severe_red_flag() (+12 more)

### Community 4 - "Frontend React Application UI"
Cohesion: 0.08
Nodes (33): dependencies, @fontsource-variable/geist@^5.3.0, @fontsource-variable/geist-mono@^5.3.0, @phosphor-icons/react@^2.1.10, react@^18.3.1, react-dom@^18.3.1, thinking-orbs@^0.3.2, devDependencies (+25 more)

### Community 5 - "Bhavcopy Exchange Ingestion"
Cohesion: 0.10
Nodes (21): build_panels(), download_day(), download_range(), one(), existing_dates(), _fetch(), load_missing(), mark_missing() (+13 more)

### Community 6 - "sectors.py"
Cohesion: 0.23
Nodes (6): apply_sector_cap(), attach_sectors(), _fetch_one(), fetch_sectors(), _load(), _save()

### Community 7 - "FastAPI REST Endpoints"
Cohesion: 0.09
Nodes (26): The universe, What it reads and writes, local_history(), backtest_summary(), BudgetIn, get_budget(), get_live_quotes(), get_simulation() (+18 more)

### Community 8 - "Tool Orchestration"
Cohesion: 0.06
Nodes (33): 1. Parallel by Default, 2. Tool Selection Hierarchy, 3. Never Retry Verbatim, 4. Confirm Before Destructive Actions, After implementation, After write, Always capture output, Always read before write (+25 more)

### Community 9 - "Historical Market Datafeed"
Cohesion: 0.20
Nodes (11): _clean(), download_batch(), download_one(), history_series(), _merge(), nifty_close(), _panel_dict(), _yahoo_batch() (+3 more)

### Community 10 - "TypeScript Compiler Configuration"
Cohesion: 0.13
Nodes (14): compilerOptions, allowImportingTsExtensions, isolatedModules, jsx, lib, module, moduleResolution, noEmit (+6 more)

### Community 12 - "Verification Chains (by Language)"
Cohesion: 0.07
Nodes (27): Baseline (before implementation), C#, Edge Case Matrix, Evidence Format (cite verbatim), Evidence Requirements, Go, Issuing VERDICT: FAIL, Issuing VERDICT: PASS (+19 more)

### Community 13 - "Context Management"
Cohesion: 0.08
Nodes (25): Context Budgeting, Context Hygiene Rules, Context Management, Context Structure (by Task Size), Cross-session continuity, Don't pass:, Large task (full codebase, 200K–1M tokens), Long Session Management (+17 more)

### Community 14 - "The 20 Anti-Patterns"
Cohesion: 0.08
Nodes (23): 10. Preamble Padding, 11. Over-scoping, 12. Quiet Workarounds, 13. Scope Narrowing Without Disclosure, 14. Post-hoc Rationalization, 15. False Precision, 16. Context Window Gaslighting, 17. Tool Trust Abuse (+15 more)

### Community 15 - "Persona Protocol"
Cohesion: 0.08
Nodes (23): After Tool Calls, Always open with:, Autonomous Operation Voice, Core Voice, Disagreement Protocol, Do, Don't, Examples (+15 more)

### Community 16 - "GRAVITAS Prompt Template"
Cohesion: 0.09
Nodes (21): Assembling the Full Prompt, Bug Fix, Example: Bug Fix Task, Explore Dispatch, Feature Addition, For a conditional subagent, For Long Sessions (after context compression), GRAVITAS Prompt Template (+13 more)

### Community 17 - "Agent: General"
Cohesion: 0.10
Nodes (20): Agent: General, Always run the full chain for the language, Before Writing Any Code, Cite verbatim, Code Standards, Compare to baseline, Don't over-engineer, Execution Protocol (+12 more)

### Community 18 - "Agent: Verify"
Cohesion: 0.10
Nodes (20): 1. Coverage check, 2. Test quality check, 3. Security spot-check (if auth/input/db code changed), Adversarial Test Review, Agent: Verify, Edge Case Matrix, Escalation, Full Verification Chain (+12 more)

### Community 19 - "The 7 Attack Vectors"
Cohesion: 0.10
Nodes (19): Adversarial Critique Protocol, Auth Middleware Order, Common Failure Patterns (Historical), Critique Output Format, Critique Thresholds, DB Migration Without Transaction, Import Style Breaks Tree Shaking, Test Assertion Mismatch (+11 more)

### Community 20 - "Model-Native Optimization Notes (Gemini tuned)"
Cohesion: 0.12
Nodes (16): 10. Integration with GRAVITAS Tiers, 11. Portability Notes (tuned on Gemini, re-validate elsewhere), 12. Anti-patterns for Gemini, 1. Adaptive Reasoning, 2. Outcome-First Prompting, 3. Few-Shot Examples — Gemini's Strongest Lever, 4. Markdown Structure Over XML, 5. Context Window — Large, But Use Wisely (+8 more)

### Community 21 - "Memory Protocol"
Cohesion: 0.12
Nodes (16): Before saving, Cross-Session Continuity Pattern, Don't save, `feedback` — What the user has corrected, Layer 1 — Session Memory (in-session, ephemeral), Layer 2 — Project Memory (cross-session, persistent), Memory Index — GRAVITAS_MEMORY.md, Memory Lifecycle (+8 more)

### Community 22 - "Agent: Plan"
Cohesion: 0.12
Nodes (15): Agent: Plan, Calibrated Reasoning Phase, Complexity Heuristics, Plan Agent Rules, Plan Templates, Planning Process, Step 1 — Absorb Everything Explore Found, Step 2 — Extended Research (for Tier 1+) (+7 more)

### Community 23 - "Subagent Patterns"
Cohesion: 0.12
Nodes (15): Agent Communication Rules, Anti-Patterns, Core Decision: Spawn or Act Directly?, Dispatching an Agent, Example Dispatch: Explore, Example Dispatch: General, Example Dispatch: Verify, Pattern 1: Sequential Pipeline (+7 more)

### Community 24 - "argparse"
Cohesion: 0.19
Nodes (7): count_source_files(), detect_language(), main(), suggest_budget(), main(), detect_language(), run_verification()

### Community 25 - "trader-news/news.py"
Cohesion: 0.08
Nodes (28): cik_map(), collect(), collect_moves(), dedupe(), eastern_offset(), Fetcher, fingerprint(), _json_ready() (+20 more)

### Community 26 - "GRAVITAS -- Engineering Reliability Runtime"
Cohesion: 0.14
Nodes (13): DECISION RECORDS, DEEP REFERENCES, DELEGATION, EFFORT PROFILES, Evidence, GRAVITAS -- Engineering Reliability Runtime, MODES, OUTPUT FORMAT (+5 more)

### Community 27 - "Gravitas -- Verification Reference"
Cohesion: 0.17
Nodes (11): Adversarial Edge Cases (strict/security work), Completion Gating, Evidence Requirements by Claim, Gravitas -- Verification Reference, Regression Baseline, Reproduction-First Debugging, Requirement-Evidence States, Scope-Appropriate Verification (+3 more)

### Community 28 - "Gravitas -- Interruption Recovery Reference"
Cohesion: 0.18
Nodes (10): Anchor Upgrade (Backfill), Circuit Breaker, Evidence Ledger: .gravitas/sessions/<task-id>/evidence.jsonl, Failure Log: .gravitas/sessions/<task-id>/failures.jsonl, Gravitas -- Interruption Recovery Reference, Recovery Protocol, State File: .gravitas/sessions/<task-id>/state.json, The Problem (+2 more)

### Community 29 - "verify.sh"
Cohesion: 0.58
Nodes (10): log_fail(), log_info(), log_pass(), log_warn(), verify.sh script, detect_language(), verify_go(), verify_python() (+2 more)

### Community 30 - "live-browser.js"
Cohesion: 0.03
Nodes (123): applyGlobalBarLabelState(), applyLiveBarPreference(), applyPlaceholderSizingStyles(), averageRgb01(), bindEditBadgeProxy(), bufferToBase64(), buildCollapsible(), buildColorModels() (+115 more)

### Community 31 - "Gravitas -- Delegation Reference"
Cohesion: 0.20
Nodes (9): Budget Profiles and Delegation, Gravitas -- Delegation Reference, Impact Auditor, Investigator, Simple Task Rule, Spawn Decision Record, The Principle, Three Conditional Roles (+1 more)

### Community 32 - "Gravitas -- Task Contract Reference"
Cohesion: 0.20
Nodes (9): Acceptance Criteria, Action Lock, Allowed Write Scope, Gravitas -- Task Contract Reference, Interruption Recovery, Modes, Policy Dimensions, Schema (+1 more)

### Community 33 - "Agent: Explore"
Cohesion: 0.22
Nodes (8): Agent: Explore, Exploration Depth by Tier, Explore Rules, MANDATORY: Full Codebase Map Phase, Phase 2 — Target Deep Dive (parallel batch), Phase 3 — Dependency and Impact Analysis (parallel batch), Phase 4 — Critical Analysis, What to Report

### Community 34 - "Gravitas -- Model Routing Reference"
Cohesion: 0.25
Nodes (7): Available Models in Antigravity (example snapshot, September 2026 -- verify), Conceptual Routing Policy, Gravitas -- Model Routing Reference, GravitasBench Will Measure This, Quota-Aware Routing, The Principle, When Native Antigravity Features Are Better

### Community 35 - "Gravitas -- Adaptive Reasoning Reference"
Cohesion: 0.25
Nodes (7): Gravitas -- Adaptive Reasoning Reference, Reasoning by Scenario, Reasoning Depth Formula, Red Flags for Over-Reasoning, Red Flags for Under-Reasoning, Selective CoT, The Core Principle

### Community 36 - "Gravitas -- Reconnaissance Reference"
Cohesion: 0.25
Nodes (7): Dependency-Directed Recon, Extended Recon (unfamiliar codebase or high fan-out), Gravitas -- Reconnaissance Reference, Recon Completeness Check, Recon Principle, Standard Recon (Tier 1 tasks), What Not to Do

### Community 37 - "trader-scanner/scan.py"
Cohesion: 0.16
Nodes (15): chart_path(), cmd_daily(), fetch_spark(), find_setups(), load_offline(), money(), _n(), progress() (+7 more)

### Community 38 - "trader/scan.py"
Cohesion: 0.05
Nodes (52): _absorb(), build_universe(), chart_path(), classify(), clock_label(), cmd_daily(), cmd_orb(), confirm() (+44 more)

### Community 42 - "trader-entry/entry.py"
Cohesion: 0.16
Nodes (12): chart_path(), chart_range(), get_chart(), _load(), offline_file(), _open_url(), parse_chart(), read_text() (+4 more)

### Community 43 - "backtest_portfolio.py"
Cohesion: 0.08
Nodes (22): compute_trade_stats(), _f(), max_consecutive_losses(), portfolio_metrics(), r_multiple(), regime_on(), regime_series(), simulate_exit() (+14 more)

### Community 44 - "time_machine"
Cohesion: 0.14
Nodes (11): build_pool(), chart_result(), clock12(), clock24(), full_sessions(), lean(), split_sessions(), time_machine() (+3 more)

### Community 45 - "trader/timemachine.py"
Cohesion: 0.06
Nodes (39): to_yahoo_symbol(), build_pool(), cents_away(), chart_result(), chart_url(), clock12(), clock24(), cmd_chart() (+31 more)

### Community 46 - "trader-broker/ticket.py"
Cohesion: 0.09
Nodes (44): amount_numbers(), apply_fill(), _clock(), cmd_approve(), cmd_decline(), cmd_fill(), cmd_flatten(), cmd_log() (+36 more)

### Community 47 - "trader/ticket.py"
Cohesion: 0.09
Nodes (44): amount_numbers(), apply_fill(), _clock(), cmd_approve(), cmd_decline(), cmd_fill(), cmd_flatten(), cmd_log() (+36 more)

### Community 48 - "trader/size.py"
Cohesion: 0.07
Nodes (35): allocate(), bracket_order(), eastern_offset(), eastern_to_utc(), _f(), fresh_price(), load_config(), load_prices() (+27 more)

### Community 49 - "trader-budget/size.py"
Cohesion: 0.07
Nodes (35): allocate(), bracket_order(), eastern_offset(), eastern_to_utc(), _f(), fresh_price(), load_config(), load_prices() (+27 more)

### Community 50 - "trader-exit/exit.py"
Cohesion: 0.05
Nodes (51): ampm(), atr_of(), build_plan(), cents(), cmd_plan(), cmd_show(), compute(), D() (+43 more)

### Community 51 - "trader/exit.py"
Cohesion: 0.08
Nodes (39): ampm(), atr_of(), build_plan(), cents(), cmd_plan(), cmd_show(), compute(), D() (+31 more)

### Community 52 - "json"
Cohesion: 0.12
Nodes (28): active(), cmd_add(), cmd_check(), cmd_clock(), cmd_list(), cmd_quote(), cmd_reset(), _dedupe() (+20 more)

### Community 53 - "trader-alerts/alerts.py"
Cohesion: 0.11
Nodes (31): active(), AlertError, cmd_add(), cmd_check(), cmd_clock(), cmd_list(), cmd_quote(), cmd_reset() (+23 more)

### Community 54 - "trader/news.py"
Cohesion: 0.08
Nodes (28): cik_map(), collect(), collect_moves(), dedupe(), eastern_offset(), Fetcher, fingerprint(), _json_ready() (+20 more)

### Community 55 - "trader-analyst/facts.py"
Cohesion: 0.09
Nodes (24): analyse(), changes(), clean_title(), _date(), exhibit_name(), facts_for(), FactsError, Fetcher (+16 more)

### Community 56 - "trader/facts.py"
Cohesion: 0.09
Nodes (24): analyse(), changes(), clean_title(), _date(), exhibit_name(), facts_for(), FactsError, Fetcher (+16 more)

### Community 57 - "trader/check.py"
Cohesion: 0.07
Nodes (32): imported_plugin_names(), main(), sha256(), account(), business_days(), _cent(), check(), day_trades() (+24 more)

### Community 58 - "trader-pelosi/ptr.py"
Cohesion: 0.11
Nodes (23): _amount(), describe(), download(), _fetch_and_read(), _finish(), iso(), load_index(), load_state() (+15 more)

### Community 59 - "os"
Cohesion: 0.10
Nodes (23): _amount(), describe(), download(), _fetch_and_read(), _finish(), iso(), load_index(), load_state() (+15 more)

### Community 60 - "datetime"
Cohesion: 0.14
Nodes (12): currency_symbol(), eastern_offset(), eastern_to_utc(), get_market_timings(), is_indian_stock(), ist_to_utc(), market_to_utc(), _nth_sunday() (+4 more)

### Community 61 - "trader-risk/check.py"
Cohesion: 0.05
Nodes (41): account(), business_days(), _cent(), check(), day_trades(), eastern_offset(), eastern_to_utc(), _f() (+33 more)

### Community 62 - "AlertError"
Cohesion: 0.17
Nodes (10): AlertError, fetch(), fetch_yahoo(), _get(), get_quotes(), _offline_text(), parse_stooq(), parse_yahoo() (+2 more)

### Community 63 - "trader-alerts"
Cohesion: 0.18
Nodes (10): Example: the reel, Quotes, Rule types, Rules, Safety, Steps, The NYSE clock, trader-alerts (+2 more)

### Community 64 - "trader-budget"
Cohesion: 0.18
Nodes (10): Example: the reel, Rules, Safety, Step 1: set the rules once, Step 2: size the trade, Step 3: show the user, trader-budget, Weights mode (kept from v1) (+2 more)

### Community 65 - "trader-pelosi"
Cohesion: 0.18
Nodes (10): Example: a real alert, Safety, Step 1: what has been filed, Step 2: watch for new ones, Step 3: read a report, The rules, The Senate: the manual route, trader-pelosi (+2 more)

### Community 66 - "trader-broker"
Cohesion: 0.20
Nodes (9): Example: the reel, Safety, Setup A: Alpaca (official MCP server, Claude Desktop), Setup B: Interactive Brokers (connector in Claude's directory), Steps: the entry, Steps: while it is open, and out by the close, trader-broker, What it never does (+1 more)

### Community 67 - "trader-risk"
Cohesion: 0.20
Nodes (9): Entries and exits, Example: the reel, Rules, Safety, Steps, The checks, trader-risk, What it never does (+1 more)

### Community 68 - "trader-entry"
Cohesion: 0.22
Nodes (8): Example: the reel, Rules, Safety, Steps, The rule, trader-entry, What it never does, What it reads and writes

### Community 69 - "trader-exit"
Cohesion: 0.22
Nodes (8): Example: the reel, Rules, Safety, Steps, Stops and targets, trader-exit, What it never does, What it reads and writes

### Community 70 - "trader-timemachine"
Cohesion: 0.22
Nodes (8): Example: the reel, How it works, Rules, Safety, Steps, trader-timemachine, What it never does, What it reads and writes

### Community 72 - "connectSSE"
Cohesion: 0.07
Nodes (86): abandonForeignSession(), abandonSupersededGo(), abortSvelteComponentInjection(), beginNewLiveConfiguration(), cancelEditing(), cancelEditingToPicking(), cancelInsertConfigure(), cleanup() (+78 more)

### Community 73 - "trader-alerts/market.py"
Cohesion: 0.14
Nodes (12): currency_symbol(), eastern_offset(), eastern_to_utc(), get_market_timings(), is_indian_stock(), ist_to_utc(), market_to_utc(), _nth_sunday() (+4 more)

### Community 74 - "trader-analyst"
Cohesion: 0.25
Nodes (7): Example: the reel's stock, Safety, Steps, The rules, trader-analyst, What it never does, What it reads and writes

### Community 75 - "trader-news"
Cohesion: 0.25
Nodes (7): Example: the reel, Safety, Steps, The rules, trader-news, What it never does, What it reads and writes

### Community 76 - "trader-entry/market.py"
Cohesion: 0.13
Nodes (13): eastern_to_utc(), currency_symbol(), eastern_offset(), eastern_to_utc(), get_market_timings(), is_indian_stock(), ist_to_utc(), market_to_utc() (+5 more)

### Community 77 - "trader-timemachine/market.py"
Cohesion: 0.16
Nodes (11): currency_symbol(), eastern_offset(), eastern_to_utc(), get_market_timings(), is_indian_stock(), ist_to_utc(), market_to_utc(), _nth_sunday() (+3 more)

### Community 78 - "Day Trader Skills — MarketMind Pro"
Cohesion: 0.33
Nodes (5): CLI usage (direct Python), Day Trader Skills — MarketMind Pro, Setup, Skills (invoke with `/trader-*`), Workflow order

### Community 79 - "trader/market.py"
Cohesion: 0.10
Nodes (22): eastern_offset(), eastern_to_utc(), next_open(), _nth_sunday(), session(), trading_day(), currency_symbol(), eastern_offset() (+14 more)

### Community 80 - "trader-broker/market.py"
Cohesion: 0.14
Nodes (12): currency_symbol(), eastern_offset(), eastern_to_utc(), get_market_timings(), is_indian_stock(), ist_to_utc(), market_to_utc(), _nth_sunday() (+4 more)

### Community 81 - "applyEditing"
Cohesion: 0.06
Nodes (45): addManualContextText(), applyEditing(), buildLocatorForLeaf(), canRestoreManualEditElement(), collectEditableTextRows(), visit(), collectManualContextPieces(), walk() (+37 more)

### Community 82 - "surveillance.py"
Cohesion: 0.12
Nodes (14): apply_earnings_filter(), apply_surveillance_veto(), _calendar_dates(), earnings_in_window(), extract_symbols(), walk(), _fetch_calendar(), fetch_earnings_dates() (+6 more)

### Community 83 - "trader-scanner/market.py"
Cohesion: 0.14
Nodes (12): currency_symbol(), eastern_offset(), eastern_to_utc(), get_market_timings(), is_indian_stock(), ist_to_utc(), market_to_utc(), _nth_sunday() (+4 more)

### Community 84 - "trader-news/market.py"
Cohesion: 0.14
Nodes (12): currency_symbol(), eastern_offset(), eastern_to_utc(), get_market_timings(), is_indian_stock(), ist_to_utc(), market_to_utc(), _nth_sunday() (+4 more)

### Community 85 - "trader/entry.py"
Cohesion: 0.08
Nodes (41): ampm(), bar_line(), chart_path(), chart_range(), cmd_check(), cmd_watch(), emit(), on_trigger() (+33 more)

### Community 86 - "resumeSession"
Cohesion: 0.06
Nodes (65): applyParamDefaults(), applyParamValue(), applySavedParamValues(), applySavedSessionMeta(), buildParamsPanel(), checkpointPayload(), clampVariantIndex(), clearHandled() (+57 more)

### Community 87 - "initPageChat"
Cohesion: 0.07
Nodes (55): armPageChatForTyping(), attachSteerFocusDebug(), attachSteerFocusGuard(), buildSteerProcessingDots(), buildSteerQueueHint(), clearSteerAwaitTimer(), clearSteerFocusRecoverTimer(), collapsePageChat() (+47 more)

### Community 88 - "history_replay"
Cohesion: 0.25
Nodes (5): cents_away(), history_replay(), opening_range(), resolve_rule(), rule_stop()

### Community 89 - "simulation.py"
Cohesion: 0.18
Nodes (6): check_orb_status(), resolve_yahoo_ticker(), simulate_daily_fallback(), simulate_pick(), _verdict_from_payoff(), enrich_latest()

### Community 90 - "cmd_watch"
Cohesion: 0.27
Nodes (11): cmd_check(), cmd_watch(), cmd_watchlist(), EntryError, main(), _opts(), parse_hhmm(), parse_now() (+3 more)

### Community 91 - "pipeline.py"
Cohesion: 0.09
Nodes (12): allocate(), _empty(), finalize_with_news(), test_allocate_no_budget(), test_allocate_whole_shares_within_budget(), Bhavcopy Historical Data Pipeline, Budget Position Sizing and Portfolio Allocator, Fundamentals Check and Red Flag Demotion (+4 more)

### Community 92 - "modern-screenshot.umd.js"
Cohesion: 0.09
Nodes (55): ae(), be(), bt(), Ce(), s(), Ct(), de(), dt() (+47 more)

### Community 93 - "TMError"
Cohesion: 0.18
Nodes (9): compute(), eastern_to_utc(), load_plan(), normalize_plan(), _num(), parse_clock(), parse_now(), read_offline() (+1 more)

### Community 94 - "watch_loop"
Cohesion: 0.21
Nodes (8): bar_line(), emit(), provider(), describe(), setup_name(), short(), to_eastern(), watch_loop()

### Community 95 - "trader-scanner"
Cohesion: 0.20
Nodes (9): Data and limits, Example: the reel, Rules, Safety, Steps, The daily scan (before the open), The opening-range breakout scan (during the session), trader-scanner (+1 more)

### Community 96 - "trader-timemachine/timemachine.py"
Cohesion: 0.17
Nodes (9): cmd_chart(), cmd_run(), main(), pc(), pct(), render_chart(), report(), simulate() (+1 more)

### Community 97 - "market_status"
Cohesion: 0.20
Nodes (7): eastern_offset(), market_status(), _nth_sunday(), _rang_today(), session(), to_eastern(), trading_day()

### Community 98 - "fetch_chart"
Cohesion: 0.29
Nodes (5): to_yahoo_symbol(), chart_url(), fetch_chart(), _get(), _sleep()

### Community 99 - "evaluate"
Cohesion: 0.16
Nodes (9): ampm(), early_cutoff(), evaluate(), hm(), next_open(), r2(), session(), trading_day() (+1 more)

### Community 100 - "to_eastern"
Cohesion: 0.29
Nodes (5): daily_closes(), eastern_offset(), _nth_sunday(), to_eastern(), ts_to_eastern()

### Community 101 - "el"
Cohesion: 0.07
Nodes (55): actionLabel(), applyConfigureBarChrome(), bindConfigureCountPillTooltip(), bindConfigureInlineControlHover(), bindConfigureModifierPillHover(), buildConfigureActionControl(), buildConfigureCountControl(), buildConfigureRow() (+47 more)

### Community 102 - "initGlobalBar"
Cohesion: 0.07
Nodes (48): agentHasWorkInFlight(), agentStatusText(), barPaletteForTheme(), brandMarkSvg(), buildDesignHeader(), cursorForInsertAxis(), designPanelCss(), detectPageTheme() (+40 more)

### Community 103 - "new-work.md"
Cohesion: 0.08
Nodes (21): Recommended Actions, Craft (deprecated alias), Apply, Live-mode signature params, Set the spatial thesis, Two isolated assessments, Verify, Visitor mode (+13 more)

### Community 104 - "parse_bars"
Cohesion: 0.29
Nodes (5): eastern_offset(), _nth_sunday(), parse_bars(), to_eastern(), utc_of()

### Community 106 - "lib.tsx"
Cohesion: 0.18
Nodes (26): C, chartCache, crores(), fetchSeries(), flagClass(), Fundamentals(), Holding, inr() (+18 more)

### Community 107 - "impeccable/SKILL.md"
Cohesion: 0.09
Nodes (19): Craft floor, Refuse, Verify, Color, Components, Layout, Motion, Operate mode depth (and Read notes) (+11 more)

### Community 108 - "updatePendingCounter"
Cohesion: 0.17
Nodes (26): clearStoredManualApplyState(), dismissToast(), fetchPendingCount(), handleManualEditActivity(), hidePendingApplyDock(), manualApplyLoadingText(), manualApplyStateKey(), manualEditEventForCurrentPage() (+18 more)

### Community 109 - "Responsive Design"
Cohesion: 0.08
Nodes (25): Assess Adaptation Challenge, Breakpoints: Content-Driven, Content Adaptation, Desktop Adaptation (Mobile → Desktop), Detect Input Method, Not Just Screen Size, Email Adaptation (Web → Email), Implement Adaptations, Layout Adaptation Patterns (+17 more)

### Community 110 - "live.md"
Cohesion: 0.08
Nodes (22): Apply at system scale, Audit before choosing, Choose a strategy, Contrast and perception, Live-mode signature params, Verify, Visitor mode, Cleanup (+14 more)

### Community 111 - "createLiveBrowserDomHelpers"
Cohesion: 0.16
Nodes (15): createLiveBrowserDomHelpers(), activeElementDeep(), cloneWithoutChrome(), copyTextViaSelection(), cssId(), liveUiRoot(), makeFrozenAnchor(), raiseHitModal() (+7 more)

### Community 112 - "onboard.md"
Cohesion: 0.09
Nodes (22): Assess Onboarding Needs, Context Over Ceremony, Contextual Help, Design Onboarding Experiences, Documentation & Help, Empty State Design, Feature Discovery & Adoption, Guided Tours & Walkthroughs (+14 more)

### Community 113 - "mountSvelteComponentVariant"
Cohesion: 0.12
Nodes (25): acceptedDomAlreadyClean(), applyOriginalAttrsToSvelteAnchor(), clearHandledWrapperReloadStamp(), commitAcceptedSvelteComponentToDom(), componentModuleCandidates(), deferredRecoverySuperseded(), describeMountFailure(), detectDevServerBase() (+17 more)

### Community 114 - "bolder.md"
Cohesion: 0.33
Nodes (5): Before you finish, Scope is sovereign, The amplification, The skeleton test, Why it reads flat

### Community 115 - "The Toolkit"
Cohesion: 0.10
Nodes (20): Animate complex properties, Assess What "Extraordinary" Means Here, For data-heavy interfaces, For functional UI, For performance-critical UI, For visual/marketing surfaces, Implement with Discipline, Interact with the device (+12 more)

### Community 116 - "createLiveBrowserSessionState"
Cohesion: 0.19
Nodes (17): createLiveBrowserSessionState(), clearHandled(), clearScrollY(), clearSession(), isHandled(), loadSession(), markHandled(), nextCheckpointRevision() (+9 more)

### Community 117 - "ui-backup-original/App.tsx"
Cohesion: 0.24
Nodes (16): App(), chartCache, crores(), fetchSeries(), flagClass(), Fundamentals(), inr(), NewsPanel() (+8 more)

### Community 118 - "actOnAgentTarget"
Cohesion: 0.14
Nodes (27): actOnAgentTarget(), agentTargetBusyReason(), agentTargetOverlayGone(), agentTargetTaken(), buildPlaceholderResizeHandles(), claimAgentTarget(), claimAndActOnAgentTarget(), cursorForPlaceholderEdge() (+19 more)

### Community 119 - "onAnnotDown"
Cohesion: 0.12
Nodes (28): applyPlaceholderDimensions(), beginEditPin(), buildAnnotationsForCapture(), buildInsertPlaceholderSnapshotFromDom(), buildPickedAnchorSnapshot(), buildPinElement(), cancelEditingPin(), captureAndEmit() (+20 more)

### Community 120 - "animate.md"
Cohesion: 0.12
Nodes (14): Accessibility and control, Choose material by meaning, Find the job, Implement to the runtime, Set the motion thesis, Timing and easing, Verify, Visitor mode (+6 more)

### Community 121 - "Handle `generate`"
Cohesion: 0.12
Nodes (16): 1. Read the screenshot (if present), 2. Wrap the element, 3. Load the action's reference, 4. Plan three variants: identity first, then mode, then axes, 5. Apply the freeform prompt (if present), 6. Deliver variants, 7. Parameters (composition-sized, 0-4 per variant), 8. Signal done (+8 more)

### Community 122 - "src/App.tsx"
Cohesion: 0.23
Nodes (12): Frontend Single Page App Shell, AccMeter(), App(), Backdrop, MiniSpark(), PctBar(), SortKey, applyPalette() (+4 more)

### Community 123 - "Generate Report"
Cohesion: 0.13
Nodes (14): 1. Accessibility (A11y), 2. Performance, 3. Theming, 4. Responsive Design, 5. Implementation Integrity (CRITICAL), Audit Health Score, Detailed Findings by Severity, Diagnostic Scan (+6 more)

### Community 124 - "cmd_orb"
Cohesion: 0.27
Nodes (9): cmd_orb(), eastern_to_utc(), _p(), parse_hhmm(), parse_now(), read_config(), read_symbols(), ScanError (+1 more)

### Community 125 - "New visual work"
Cohesion: 0.14
Nodes (14): 1. Decide what is already true, 2. Ask what will change the work, 3. Choose the right amount of invention, 4. Commit the world, 5. Record the decision, 6. Build with full commitment, 7. Inspect and finish, Both paths (+6 more)

### Community 126 - "optimize.md"
Cohesion: 0.14
Nodes (13): Animation Performance, Assess Performance Issues, Core Web Vitals Optimization, Cumulative Layout Shift (CLS < 0.1), Interaction to Next Paint (INP < 200ms), Largest Contentful Paint (LCP < 2.5s), Loading Performance, Network Optimization (+5 more)

### Community 127 - "SurfaceBackdrop"
Cohesion: 0.21
Nodes (4): three@^0.187.0, Backdrop(), SurfaceBackdrop, three

### Community 128 - "Impeccable Asset Producer"
Cohesion: 0.15
Nodes (11): Act on the receipt, Assemble and review, Plan and asset review, Plan, capture, serve, Core Rule, Decision Comps, Impeccable Asset Producer, Input Contract (+3 more)

### Community 129 - "Scan mode (approach C: auto-extract, then confirm descriptive language)"
Cohesion: 0.08
Nodes (23): Component translation rules, Narrative mapping, Pitfalls, Scan mode (approach C: auto-extract, then confirm descriptive language), Schema, Seed mode, Step 1: Find the design assets, Step 1: Route through new-work's workshop (+15 more)

### Community 130 - "generate.md"
Cohesion: 0.15
Nodes (11): Step 1: Parse the request, Step 2: Reuse the page, then start, Step 3: Generate, Step 4: Accept and close, append-arrays, append-string, Config drift, Consent prompt (use this phrasing) (+3 more)

### Community 131 - "Visualize: Direction Comps & Asset Production"
Cohesion: 0.33
Nodes (5): After approval: the comp becomes a spec, Generate three compositional options, One approval point, Plates and provenance, Visualize: Direction Comps & Asset Production

### Community 132 - "critique.md"
Cohesion: 0.17
Nodes (11): Action Summary, Ask the User, Assessment A: Design Review, Assessment B: Detector + Browser Evidence, Assessment Orchestration, Deliver the Report, Hard Invariants, Persist the Snapshot (+3 more)

### Community 133 - "Simplify the Design"
Cohesion: 0.17
Nodes (11): Assess Current State, Code Simplification, Content Simplification, Document Removed Complexity, Information Architecture, Interaction Simplification, Layout Simplification, Plan Simplification (+3 more)

### Community 134 - "Hardening Dimensions"
Cohesion: 0.17
Nodes (11): Accessibility Resilience, Assess Hardening Needs, Edge Cases & Boundary Conditions, Error Handling, Hardening Dimensions, Input Validation & Sanitization, Internationalization (i18n), Performance Resilience (+3 more)

### Community 135 - "urllib_request"
Cohesion: 0.20
Nodes (4): analyse_headlines(), fetch_news(), get_news(), test_news_veto_and_sentiment()

### Community 136 - "clarify.md"
Cohesion: 0.18
Nodes (10): Actions and navigation, Audit the language, Errors and permissions, Forms, Help and instructional text, Loading, empty, and success states, Rewrite by function, Set the message hierarchy (+2 more)

### Community 137 - "Nielsen's 10 Heuristics"
Cohesion: 0.18
Nodes (11): 10. Help and Documentation, 1. Visibility of System Status, 2. Match Between System and Real World, 3. User Control and Freedom, 4. Consistency and Standards, 5. Error Prevention, 6. Recognition Rather Than Recall, 7. Flexibility and Efficiency of Use (+3 more)

### Community 138 - "Generate Combined Critique Report"
Cohesion: 0.18
Nodes (11): Design Health Score, Design Specificity Verdict, Generate Combined Critique Report, Minor Observations, Overall Impression, Persona Red Flags, Priority Issues, Questions to Consider (+3 more)

### Community 139 - "entry_doc"
Cohesion: 0.40
Nodes (4): on_trigger(), entry_doc(), iso(), write_json()

### Community 140 - "polish.md"
Cohesion: 0.18
Nodes (10): 1. Establish the system, 2. Gather the evidence, 3. Triage, 4. Polish the whole path, 5. Verify and finish, Color, imagery, and icons, Content and code, Flow and hierarchy (+2 more)

### Community 141 - "quieter.md"
Cohesion: 0.18
Nodes (10): Assess Current State, Color Refinement, Composition Refinement, Motion Reduction, Plan Refinement, Refine the Design, Simplification, Verify Quality (+2 more)

### Community 143 - "doctor.md"
Cohesion: 0.25
Nodes (7): Monorepo notes, Opting out of the boot check, Step 1: Run the pass, Step 2: Act by severity, Step 3: Deprecated fields are binding, Step 4: Do not overclaim on truth drift, What this owns, and what it does not

### Community 144 - "Read"
Cohesion: 0.50
Nodes (3): Comps, Directions, Read

### Community 145 - "Product"
Cohesion: 0.18
Nodes (10): Brand Commitments, Capabilities and Constraints, Evidence on Hand, Operating Context, Platform, Positioning, Product, Product Principles (+2 more)

### Community 146 - "Init flow"
Cohesion: 0.20
Nodes (10): Completion gate, Init flow, Step 1: Load current state, Step 2: Explore the project, Step 3: Interview for product truth, Step 4: Write PRODUCT.md, Step 5: Record workflow defaults, Step 6: Wrap up or resume (+2 more)

### Community 147 - "Common Cognitive Load Violations"
Cohesion: 0.22
Nodes (9): 1. The Wall of Options, 2. The Memory Bridge, 3. The Hidden Navigation, 4. The Jargon Barrier, 5. The Visual Noise Floor, 6. The Inconsistent Pattern, 7. The Multi-Task Demand, 8. The Context Switch (+1 more)

### Community 148 - "iOS platform"
Cohesion: 0.22
Nodes (9): Color & materials, Components & controls, iOS platform, Layout & structure, Motion, The iOS slop test, Touch targets, Typography (+1 more)

### Community 150 - "Shape"
Cohesion: 0.22
Nodes (8): Cadence, Confirm and stop, Phase 1: Discovery interview, Phase 2: Resolve the design direction, Phase 3: Write the brief, Round 1: purpose, people, and outcome, Round 2: material, behavior, and boundaries, Shape

### Community 151 - "_absorb"
Cohesion: 0.22
Nodes (5): _absorb(), confirm(), parse_chart(), parse_spark(), series_from_result()

### Community 152 - "orb_window"
Cohesion: 0.12
Nodes (11): clock_label(), day_label(), orb_candidate(), orb_hit(), orb_window(), scan_orb(), session(), session_bars() (+3 more)

### Community 153 - "adapt.native.md"
Cohesion: 0.25
Nodes (7): Adaptation Strategies, Assess Adaptation Challenge, Implement & Verify, Orientation & foldables, Phone → Tablet (iPad / large screens), Platform → platform (iOS ↔ Android), Web → native (porting a website or web app)

### Community 154 - "Android platform"
Cohesion: 0.25
Nodes (8): Android platform, Color & theming, Components & motion, Layout & structure, The Android slop test, Touch targets, Typography, Verifying the build

### Community 155 - "Persona-Based Design Testing"
Cohesion: 0.25
Nodes (8): 1. Impatient Power User: "Alex", 2. Confused First-Timer: "Jordan", 3. Accessibility-Dependent User: "Sam", 4. Deliberate Stress Tester: "Riley", 5. Distracted Mobile User: "Casey", Persona-Based Design Testing, Project-Specific Personas, Selecting Personas

### Community 156 - "Extract Flow"
Cohesion: 0.25
Nodes (7): Extract Flow, Step 1: Discover the Design System, Step 2: Identify Patterns, Step 3: Plan Extraction, Step 4: Extract & Enrich, Step 5: Migrate, Step 6: Document

### Community 158 - "Generate Report"
Cohesion: 0.29
Nodes (7): Audit Health Score, Detailed Findings by Severity, Executive Summary, Generate Report, Patterns & Systemic Issues, Platform Conformance Verdict, Positive Findings

### Community 159 - "Cognitive Load Assessment"
Cohesion: 0.29
Nodes (7): Cognitive Load Assessment, Cognitive Load Checklist, Extraneous Load: Bad Design, Germane Load: Learning Effort, Intrinsic Load: The Task Itself, The Working Memory Rule, Three Types of Cognitive Load

### Community 160 - "Impeccable Finish Reviewer"
Cohesion: 0.29
Nodes (6): Checks, in order, Disposition, Impeccable Finish Reviewer, Input Contract, Output Contract, Verdict Pass

### Community 161 - "Impeccable Manual Edit Applier"
Cohesion: 0.29
Nodes (6): Checks, Entry Atomicity, Impeccable Manual Edit Applier, Input Contract, Output Contract, Workflow

### Community 162 - "live-browser-ignores.js"
Cohesion: 0.52
Nodes (6): globToRegex(), matchesScope(), normalizeIgnoreRule(), normalizeIgnoreValue(), pageCandidates(), resolveDetectIgnores()

### Community 163 - "Diagnostic Scan"
Cohesion: 0.33
Nodes (6): 1. Accessibility (VoiceOver / TalkBack), 2. Performance, 3. Appearance & Theming, 4. Platform Conformance (CRITICAL), 5. Adaptivity, Diagnostic Scan

### Community 164 - "$impeccable hooks"
Cohesion: 0.33
Nodes (6): Constraints, Failure modes, Flow, $impeccable hooks, Routing, Triage findings

### Community 165 - "build_universe"
Cohesion: 0.17
Nodes (7): build_universe(), classify(), cmd_universe(), http_get(), main(), parse_symdir(), yahoo_get()

### Community 166 - "interface"
Cohesion: 0.40
Nodes (4): interface, default_prompt, display_name, short_description

### Community 167 - "Region map"
Cohesion: 0.40
Nodes (4): Containment, Painted material, Region map, What varies independently

### Community 168 - "Heuristics Scoring Guide"
Cohesion: 0.50
Nodes (4): Heuristics Scoring Guide, Issue Severity (P0–P3), Reference Material, Score Summary

### Community 170 - "Impeccable Documenter"
Cohesion: 0.40
Nodes (4): Impeccable Documenter, Input Contract, Output Contract, Workflow

## Knowledge Gaps
- **5 isolated node(s):** `Frontend Single Page App Shell`, `Trader Score Rule Engine`, `Backend Dependencies`, `MarketMind Pro Overview`, `Weekly Automated Market Scanner`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1498 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **10 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `init()` connect `initGlobalBar` to `generate.md`, `connectSSE`, `impeccable/SKILL.md`, `updatePendingCounter`, `doctor.md`, `Init flow`, `onAnnotDown`, `resumeSession`, `initPageChat`, `live-browser.js`?**
  _High betweenness centrality (0.052) - this node is a cross-community bridge._
- **What connects `Frontend Single Page App Shell`, `Trader Score Rule Engine`, `Backend Dependencies` to the rest of the system?**
  _5 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Market Scan Lifecycle Control` be split into smaller, more focused modules?**
  _Cohesion score 0.10967741935483871 - nodes in this community are weakly interconnected._
- **Why does `Commands` connect `impeccable/SKILL.md` to `initGlobalBar`?**
  _High betweenness centrality (0.020) - this node is a cross-community bridge._
- **Should `test_pro.py` be split into smaller, more focused modules?**
  _Cohesion score 0.11895161290322581 - nodes in this community are weakly interconnected._
- **Why does `apply_red_flag_demotion()` connect `test_v2.py` to `Historical Market Datafeed`, `pipeline.py`?**
  _High betweenness centrality (0.006) - this node is a cross-community bridge._
- **Should `test_v2.py` be split into smaller, more focused modules?**
  _Cohesion score 0.10804597701149425 - nodes in this community are weakly interconnected._