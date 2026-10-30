# Graph Report - marketmind-pro-WINDOWS-FINAL  (2026-10-30)

## Corpus Check
- 135 files · ~371,324 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 4 file(s) not represented in the graph (top: (none) 1, .css 1, .tsbuildinfo 1)

## Summary
- 2325 nodes · 4960 edges · 106 communities (98 shown, 8 thin omitted)
- Extraction: 98% EXTRACTED · 2% INFERRED · 0% AMBIGUOUS · INFERRED: 82 edges (avg confidence: 0.87)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- pipeline.py
- Market Scan Lifecycle Control
- test_pro.py
- Trader Score & Red Flag Rules
- Frontend React Application UI
- Bhavcopy Exchange Ingestion
- fundamentals.py
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
- detect_project.py
- trader-news/news.py
- GRAVITAS -- Engineering Reliability Runtime
- Gravitas -- Verification Reference
- Gravitas -- Interruption Recovery Reference
- verify.sh
- allocate
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
- cmd_watch
- trader-timemachine/timemachine.py
- trader/timemachine.py
- trader-broker/ticket.py
- trader/ticket.py
- trader/size.py
- trader-budget/size.py
- re
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
- gzip
- trader-alerts
- trader-budget
- trader-pelosi
- trader-broker
- trader-risk
- trader-entry
- trader-exit
- trader-timemachine
- detect_project.py
- trader-alerts/market.py
- trader-analyst
- trader-news
- trader-entry/market.py
- trader-timemachine/market.py
- Day Trader Skills — MarketMind Pro
- trader/market.py
- trader-broker/market.py
- trader-exit/market.py
- trader-risk/market.py
- trader-scanner/market.py
- trader-news/market.py
- trader/entry.py
- cmd_watch
- evaluate
- history_replay
- get_chart
- gzip
- simulation.py
- watch_loop
- TMError
- watch_loop
- trader-scanner
- compute
- time_machine
- fetch_chart
- SimClock
- hashlib
- eastern_offset
- SimClock
- entry_doc
- entry_doc
- eastern_offset

## God Nodes (most connected - your core abstractions)
1. `cmd_orb()` - 23 edges
2. `cmd_orb()` - 23 edges
3. `evaluate()` - 21 edges
4. `evaluate()` - 21 edges
5. `The 20 Anti-Patterns` - 21 edges
6. `build_plan()` - 20 edges
7. `build_plan()` - 20 edges
8. `time_machine()` - 19 edges
9. `time_machine()` - 19 edges
10. `check()` - 18 edges

## Surprising Connections (you probably didn't know these)
- `The universe` --references--> `universe()`  [INFERRED]
  .agents/skills/trader-scanner/SKILL.md → backend/app/main.py
- `What it reads and writes` --references--> `universe()`  [INFERRED]
  .agents/skills/trader-scanner/SKILL.md → backend/app/main.py
- `What it reads and writes` --references--> `scanned()`  [INFERRED]
  .agents/skills/trader-scanner/SKILL.md → backend/app/main.py
- `test_universe_parse_nse()` --calls--> `parse_nse()`  [EXTRACTED]
  backend/tests/test_pro.py → backend/app/universe.py
- `yahoo_url()` --calls--> `to_yahoo_symbol()`  [EXTRACTED]
  .agents/skills/trader-alerts/alerts.py → .agents/skills/trader-alerts/market.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **End-to-End Market Screening Pipeline** — readme_stage1_screen, readme_stage2_deep_evaluation, readme_fundamentals_check, readme_news_veto [INFERRED 0.85]

## Communities (106 total, 8 thin omitted)

### Community 0 - "pipeline.py"
Cohesion: 0.15
Nodes (5): finalize_with_news(), Bhavcopy Historical Data Pipeline, Stage 1 Market Screen, Stage 2 ML Deep Evaluation, Weekly Automated Market Scanner

### Community 1 - "Market Scan Lifecycle Control"
Cohesion: 0.11
Nodes (20): checkpoint_progress(), find_scan_pids(), get_status(), _log_stage(), _pid_alive(), _read_json(), scan_running(), start_scan() (+12 more)

### Community 2 - "test_pro.py"
Cohesion: 0.12
Nodes (22): add_indicators(), _adx(), _atr(), build_features(), detect_patterns(), _ema(), _fit_predict(), _rsi() (+14 more)

### Community 3 - "Trader Score & Red Flag Rules"
Cohesion: 0.16
Nodes (14): severe_red_flag(), apply_red_flag_demotion(), dedupe_by_isin(), rank_key(), run_pipeline(), _frame(), _pick(), test_dedupe_by_isin_keeps_best_listing() (+6 more)

### Community 4 - "Frontend React Application UI"
Cohesion: 0.07
Nodes (43): Frontend Single Page App Shell, dependencies, react@^18.3.1, react-dom@^18.3.1, thinking-orbs@^0.3.2, devDependencies, @types/react@^18.3.3, @types/react-dom@^18.3.0 (+35 more)

### Community 5 - "Bhavcopy Exchange Ingestion"
Cohesion: 0.14
Nodes (15): build_panels(), download_day(), download_range(), one(), existing_dates(), _fetch(), load_missing(), mark_missing() (+7 more)

### Community 6 - "fundamentals.py"
Cohesion: 0.19
Nodes (8): attach_fundamentals(), _clean_num(), fetch_fundamentals(), _fetch_one(), _load_cache(), _save_cache(), score_fundamentals(), test_fundamentals_scoring_and_flags()

### Community 7 - "FastAPI REST Endpoints"
Cohesion: 0.11
Nodes (22): The universe, What it reads and writes, BudgetIn, get_budget(), get_live_quotes(), get_simulation(), health(), history() (+14 more)

### Community 8 - "Tool Orchestration"
Cohesion: 0.06
Nodes (33): 1. Parallel by Default, 2. Tool Selection Hierarchy, 3. Never Retry Verbatim, 4. Confirm Before Destructive Actions, After implementation, After write, Always capture output, Always read before write (+25 more)

### Community 9 - "Historical Market Datafeed"
Cohesion: 0.22
Nodes (9): _clean(), download_batch(), download_one(), history_series(), local_history(), _merge(), nifty_close(), _panel_dict() (+1 more)

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

### Community 24 - "detect_project.py"
Cohesion: 0.25
Nodes (5): main(), detect_language(), run_verification(), main(), _parser()

### Community 25 - "trader-news/news.py"
Cohesion: 0.06
Nodes (33): to_yahoo_symbol(), cik_map(), collect(), collect_moves(), dedupe(), eastern_offset(), Fetcher, fingerprint() (+25 more)

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

### Community 30 - "allocate"
Cohesion: 0.25
Nodes (6): allocate(), test_allocate_no_budget(), test_allocate_whole_shares_within_budget(), Budget Position Sizing and Portfolio Allocator, Fundamentals Check and Red Flag Demotion, News Sentiment Check and Hard Veto

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
Cohesion: 0.05
Nodes (53): to_yahoo_symbol(), _absorb(), build_universe(), chart_path(), classify(), clock_label(), cmd_daily(), cmd_orb() (+45 more)

### Community 38 - "trader/scan.py"
Cohesion: 0.05
Nodes (52): _absorb(), build_universe(), chart_path(), classify(), clock_label(), cmd_daily(), cmd_orb(), confirm() (+44 more)

### Community 42 - "trader-entry/entry.py"
Cohesion: 0.16
Nodes (12): chart_path(), chart_range(), get_chart(), _load(), offline_file(), _open_url(), parse_chart(), read_text() (+4 more)

### Community 43 - "cmd_watch"
Cohesion: 0.23
Nodes (13): cmd_check(), cmd_watch(), cmd_watchlist(), EntryError, _load(), main(), _opts(), parse_hhmm() (+5 more)

### Community 44 - "trader-timemachine/timemachine.py"
Cohesion: 0.24
Nodes (9): clock12(), cmd_run(), lean(), pc(), report(), _until12(), verdict(), verdict_notes() (+1 more)

### Community 45 - "trader/timemachine.py"
Cohesion: 0.05
Nodes (44): to_yahoo_symbol(), build_pool(), cents_away(), chart_result(), chart_url(), clock12(), clock24(), cmd_chart() (+36 more)

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

### Community 50 - "re"
Cohesion: 0.08
Nodes (39): ampm(), atr_of(), build_plan(), cents(), cmd_plan(), cmd_show(), compute(), D() (+31 more)

### Community 51 - "trader/exit.py"
Cohesion: 0.08
Nodes (39): ampm(), atr_of(), build_plan(), cents(), cmd_plan(), cmd_show(), compute(), D() (+31 more)

### Community 52 - "json"
Cohesion: 0.12
Nodes (28): active(), cmd_add(), cmd_check(), cmd_clock(), cmd_list(), cmd_quote(), cmd_reset(), _dedupe() (+20 more)

### Community 53 - "trader-alerts/alerts.py"
Cohesion: 0.09
Nodes (36): active(), AlertError, cmd_add(), cmd_check(), cmd_clock(), cmd_list(), cmd_quote(), cmd_reset() (+28 more)

### Community 54 - "trader/news.py"
Cohesion: 0.08
Nodes (28): cik_map(), collect(), collect_moves(), dedupe(), eastern_offset(), Fetcher, fingerprint(), _json_ready() (+20 more)

### Community 55 - "trader-analyst/facts.py"
Cohesion: 0.09
Nodes (24): analyse(), changes(), clean_title(), _date(), exhibit_name(), facts_for(), FactsError, Fetcher (+16 more)

### Community 56 - "trader/facts.py"
Cohesion: 0.08
Nodes (24): analyse(), changes(), clean_title(), _date(), exhibit_name(), facts_for(), FactsError, Fetcher (+16 more)

### Community 57 - "trader/check.py"
Cohesion: 0.08
Nodes (29): account(), business_days(), _cent(), check(), day_trades(), eastern_offset(), eastern_to_utc(), _f() (+21 more)

### Community 58 - "trader-pelosi/ptr.py"
Cohesion: 0.12
Nodes (21): _amount(), describe(), download(), _fetch_and_read(), _finish(), iso(), load_index(), load_state() (+13 more)

### Community 59 - "os"
Cohesion: 0.11
Nodes (23): _amount(), describe(), download(), _fetch_and_read(), _finish(), iso(), load_index(), load_state() (+15 more)

### Community 60 - "datetime"
Cohesion: 0.14
Nodes (12): currency_symbol(), eastern_offset(), eastern_to_utc(), get_market_timings(), is_indian_stock(), ist_to_utc(), market_to_utc(), _nth_sunday() (+4 more)

### Community 61 - "trader-risk/check.py"
Cohesion: 0.08
Nodes (29): account(), business_days(), _cent(), check(), day_trades(), eastern_offset(), eastern_to_utc(), _f() (+21 more)

### Community 62 - "gzip"
Cohesion: 0.23
Nodes (7): parse_stooq(), build_universe(), _get(), load_universe(), parse_bse(), parse_nse(), parse_stooq()

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

### Community 72 - "detect_project.py"
Cohesion: 0.39
Nodes (4): count_source_files(), detect_language(), main(), suggest_budget()

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
Cohesion: 0.13
Nodes (13): currency_symbol(), eastern_offset(), eastern_to_utc(), get_market_timings(), is_indian_stock(), ist_to_utc(), market_to_utc(), _nth_sunday() (+5 more)

### Community 78 - "Day Trader Skills — MarketMind Pro"
Cohesion: 0.33
Nodes (5): CLI usage (direct Python), Day Trader Skills — MarketMind Pro, Setup, Skills (invoke with `/trader-*`), Workflow order

### Community 79 - "trader/market.py"
Cohesion: 0.13
Nodes (13): next_open(), session(), trading_day(), currency_symbol(), eastern_offset(), eastern_to_utc(), get_market_timings(), is_indian_stock() (+5 more)

### Community 80 - "trader-broker/market.py"
Cohesion: 0.14
Nodes (12): currency_symbol(), eastern_offset(), eastern_to_utc(), get_market_timings(), is_indian_stock(), ist_to_utc(), market_to_utc(), _nth_sunday() (+4 more)

### Community 81 - "trader-exit/market.py"
Cohesion: 0.14
Nodes (12): currency_symbol(), eastern_offset(), eastern_to_utc(), get_market_timings(), is_indian_stock(), ist_to_utc(), market_to_utc(), _nth_sunday() (+4 more)

### Community 82 - "trader-risk/market.py"
Cohesion: 0.14
Nodes (12): currency_symbol(), eastern_offset(), eastern_to_utc(), get_market_timings(), is_indian_stock(), ist_to_utc(), market_to_utc(), _nth_sunday() (+4 more)

### Community 83 - "trader-scanner/market.py"
Cohesion: 0.16
Nodes (11): currency_symbol(), eastern_offset(), eastern_to_utc(), get_market_timings(), is_indian_stock(), ist_to_utc(), market_to_utc(), _nth_sunday() (+3 more)

### Community 84 - "trader-news/market.py"
Cohesion: 0.16
Nodes (11): currency_symbol(), eastern_offset(), eastern_to_utc(), get_market_timings(), is_indian_stock(), ist_to_utc(), market_to_utc(), _nth_sunday() (+3 more)

### Community 85 - "trader/entry.py"
Cohesion: 0.15
Nodes (11): ampm(), bar_line(), describe(), early_cutoff(), evaluate(), hm(), r2(), setup_name() (+3 more)

### Community 86 - "cmd_watch"
Cohesion: 0.27
Nodes (11): cmd_check(), cmd_watch(), cmd_watchlist(), EntryError, main(), _opts(), parse_hhmm(), parse_now() (+3 more)

### Community 87 - "evaluate"
Cohesion: 0.16
Nodes (9): ampm(), early_cutoff(), evaluate(), hm(), next_open(), r2(), session(), trading_day() (+1 more)

### Community 88 - "history_replay"
Cohesion: 0.15
Nodes (7): cents_away(), history_replay(), opening_range(), pct(), resolve_rule(), rule_stop(), simulate()

### Community 89 - "get_chart"
Cohesion: 0.16
Nodes (9): chart_path(), chart_range(), get_chart(), offline_file(), _open_url(), parse_chart(), read_text(), yahoo_get() (+1 more)

### Community 90 - "gzip"
Cohesion: 0.18
Nodes (10): _offline_text(), AlertError, fetch(), fetch_yahoo(), _get(), get_quotes(), _offline_text(), parse_yahoo() (+2 more)

### Community 91 - "simulation.py"
Cohesion: 0.19
Nodes (5): check_orb_status(), resolve_yahoo_ticker(), simulate_daily_fallback(), simulate_pick(), enrich_latest()

### Community 92 - "watch_loop"
Cohesion: 0.21
Nodes (8): bar_line(), emit(), provider(), describe(), setup_name(), short(), to_eastern(), watch_loop()

### Community 93 - "TMError"
Cohesion: 0.24
Nodes (7): chart_result(), load_plan(), normalize_plan(), _num(), parse_clock(), TMError, to_eastern()

### Community 94 - "watch_loop"
Cohesion: 0.22
Nodes (8): emit(), provider(), eastern_offset(), eastern_to_utc(), _nth_sunday(), to_eastern(), watch_loop(), ist_to_utc()

### Community 95 - "trader-scanner"
Cohesion: 0.20
Nodes (9): Data and limits, Example: the reel, Rules, Safety, Steps, The daily scan (before the open), The opening-range breakout scan (during the session), trader-scanner (+1 more)

### Community 96 - "compute"
Cohesion: 0.22
Nodes (5): cmd_chart(), compute(), main(), read_offline(), render_chart()

### Community 97 - "time_machine"
Cohesion: 0.25
Nodes (5): build_pool(), clock24(), full_sessions(), split_sessions(), time_machine()

### Community 98 - "fetch_chart"
Cohesion: 0.29
Nodes (5): to_yahoo_symbol(), chart_url(), fetch_chart(), _get(), _sleep()

### Community 100 - "hashlib"
Cohesion: 0.31
Nodes (3): imported_plugin_names(), main(), sha256()

### Community 104 - "eastern_offset"
Cohesion: 0.33
Nodes (4): eastern_offset(), eastern_to_utc(), _nth_sunday(), parse_now()

### Community 107 - "entry_doc"
Cohesion: 0.40
Nodes (4): on_trigger(), entry_doc(), iso(), write_json()

### Community 108 - "entry_doc"
Cohesion: 0.40
Nodes (4): on_trigger(), entry_doc(), iso(), write_json()

## Knowledge Gaps
- **5 isolated node(s):** `Weekly Automated Market Scanner`, `Trader Score Rule Engine`, `Frontend Single Page App Shell`, `Backend Dependencies`, `MarketMind Pro Overview`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1023 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **8 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `prices()` connect `FastAPI REST Endpoints` to `Historical Market Datafeed`, `gzip`?**
  _High betweenness centrality (0.009) - this node is a cross-community bridge._
- **What connects `Weekly Automated Market Scanner`, `Trader Score Rule Engine`, `Frontend Single Page App Shell` to the rest of the system?**
  _5 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Market Scan Lifecycle Control` be split into smaller, more focused modules?**
  _Cohesion score 0.11494252873563218 - nodes in this community are weakly interconnected._
- **Why does `SimClock` connect `SimClock` to `trader-entry/entry.py`, `cmd_watch`?**
  _High betweenness centrality (0.009) - this node is a cross-community bridge._
- **Should `test_pro.py` be split into smaller, more focused modules?**
  _Cohesion score 0.11693548387096774 - nodes in this community are weakly interconnected._
- **Why does `parse_bse()` connect `Bhavcopy Exchange Ingestion` to `Historical Market Datafeed`, `gzip`?**
  _High betweenness centrality (0.008) - this node is a cross-community bridge._
- **Should `Frontend React Application UI` be split into smaller, more focused modules?**
  _Cohesion score 0.0726950354609929 - nodes in this community are weakly interconnected._