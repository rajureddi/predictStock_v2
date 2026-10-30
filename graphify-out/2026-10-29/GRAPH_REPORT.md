# Graph Report - marketmind-pro-WINDOWS-FINAL  (2026-10-29)

## Corpus Check
- 64 files · ~206,370 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 4 file(s) not represented in the graph (top: (none) 1, .css 1, .tsbuildinfo 1)

## Summary
- 702 nodes · 1029 edges · 42 communities (38 shown, 4 thin omitted)
- Extraction: 98% EXTRACTED · 2% INFERRED · 0% AMBIGUOUS · INFERRED: 19 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- pipeline.py
- Market Scan Lifecycle Control
- Technical Indicators & Position Sizing
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
- news.py
- GRAVITAS -- Engineering Reliability Runtime
- Gravitas -- Verification Reference
- Gravitas -- Interruption Recovery Reference
- verify.sh
- trader_score
- Gravitas -- Delegation Reference
- Gravitas -- Task Contract Reference
- Agent: Explore
- Gravitas -- Model Routing Reference
- Gravitas -- Adaptive Reasoning Reference
- Gravitas -- Reconnaissance Reference
- engine.py
- allocate.py
- coordinator.md
- run-checks.sh
- SESSION_FAILURES.md

## God Nodes (most connected - your core abstractions)
1. `The 20 Anti-Patterns` - 21 edges
2. `trader_score()` - 15 edges
3. `run_pipeline()` - 15 edges
4. `compilerOptions` - 13 edges
5. `GRAVITAS -- Engineering Reliability Runtime` - 13 edges
6. `Model-Native Optimization Notes (Gemini tuned)` - 13 edges
7. `get_status()` - 11 edges
8. `Gravitas -- Verification Reference` - 11 edges
9. `walk_forward_and_forecast()` - 10 edges
10. `load_universe()` - 10 edges

## Surprising Connections (you probably didn't know these)
- `_with_allocation()` --calls--> `allocate()`  [EXTRACTED]
  backend/app/main.py → backend/app/allocate.py
- `run_pipeline()` --calls--> `allocate()`  [EXTRACTED]
  backend/app/pipeline.py → backend/app/allocate.py
- `test_allocate_no_budget()` --calls--> `allocate()`  [EXTRACTED]
  backend/tests/test_pro.py → backend/app/allocate.py
- `test_allocate_whole_shares_within_budget()` --calls--> `allocate()`  [EXTRACTED]
  backend/tests/test_pro.py → backend/app/allocate.py
- `test_parse_nse_bhavcopy()` --calls--> `parse_nse()`  [EXTRACTED]
  backend/tests/test_v2.py → backend/app/bhavcopy.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **End-to-End Market Screening Pipeline** — readme_stage1_screen, readme_stage2_deep_evaluation, readme_fundamentals_check, readme_news_veto [INFERRED 0.85]

## Communities (42 total, 4 thin omitted)

### Community 0 - "pipeline.py"
Cohesion: 0.19
Nodes (3): Stage 1 Market Screen, Stage 2 ML Deep Evaluation, Weekly Automated Market Scanner

### Community 1 - "Market Scan Lifecycle Control"
Cohesion: 0.10
Nodes (21): scan_start(), checkpoint_progress(), find_scan_pids(), get_status(), _log_stage(), _pid_alive(), _read_json(), scan_running() (+13 more)

### Community 2 - "Technical Indicators & Position Sizing"
Cohesion: 0.21
Nodes (12): allocate(), build_features(), _fit_predict(), walk_forward_and_forecast(), target_date_for(), synth(), test_allocate_no_budget(), test_allocate_whole_shares_within_budget() (+4 more)

### Community 3 - "Trader Score & Red Flag Rules"
Cohesion: 0.20
Nodes (9): severe_red_flag(), apply_red_flag_demotion(), dedupe_by_isin(), rank_key(), _pick(), test_dedupe_by_isin_keeps_best_listing(), test_rank_key_rewards_fundamentals(), test_red_flag_demotion() (+1 more)

### Community 4 - "Frontend React Application UI"
Cohesion: 0.07
Nodes (43): Frontend Single Page App Shell, dependencies, react@^18.3.1, react-dom@^18.3.1, thinking-orbs@^0.3.2, devDependencies, @types/react@^18.3.3, @types/react-dom@^18.3.0 (+35 more)

### Community 5 - "Bhavcopy Exchange Ingestion"
Cohesion: 0.09
Nodes (21): build_panels(), download_day(), download_range(), one(), existing_dates(), _fetch(), load_missing(), mark_missing() (+13 more)

### Community 6 - "fundamentals.py"
Cohesion: 0.23
Nodes (8): attach_fundamentals(), _clean_num(), fetch_fundamentals(), _fetch_one(), _load_cache(), _save_cache(), score_fundamentals(), test_fundamentals_scoring_and_flags()

### Community 7 - "FastAPI REST Endpoints"
Cohesion: 0.10
Nodes (22): imported_plugin_names(), main(), sha256(), BudgetIn, get_budget(), get_live_quotes(), health(), history() (+14 more)

### Community 8 - "Tool Orchestration"
Cohesion: 0.06
Nodes (33): 1. Parallel by Default, 2. Tool Selection Hierarchy, 3. Never Retry Verbatim, 4. Confirm Before Destructive Actions, After implementation, After write, Always capture output, Always read before write (+25 more)

### Community 9 - "Historical Market Datafeed"
Cohesion: 0.17
Nodes (12): _clean(), download_batch(), download_one(), history_series(), local_history(), _merge(), nifty_close(), _panel_dict() (+4 more)

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
Cohesion: 0.18
Nodes (7): count_source_files(), detect_language(), main(), suggest_budget(), main(), detect_language(), run_verification()

### Community 25 - "news.py"
Cohesion: 0.15
Nodes (5): analyse_headlines(), fetch_news(), get_news(), finalize_with_news(), test_news_veto_and_sentiment()

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

### Community 30 - "trader_score"
Cohesion: 0.22
Nodes (8): detect_patterns(), swing_levels(), trader_score(), test_patterns_engulfing(), _frame(), test_delivery_absent_is_noop(), test_delivery_high_adds_score_and_reason(), test_delivery_low_on_big_up_day_penalised()

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

### Community 37 - "engine.py"
Cohesion: 0.39
Nodes (6): add_indicators(), _adx(), _atr(), _ema(), _rsi(), Trader Score Rule Engine

### Community 38 - "allocate.py"
Cohesion: 0.40
Nodes (3): Budget Position Sizing and Portfolio Allocator, Fundamentals Check and Red Flag Demotion, News Sentiment Check and Hard Veto

## Knowledge Gaps
- **5 isolated node(s):** `Weekly Automated Market Scanner`, `Trader Score Rule Engine`, `Frontend Single Page App Shell`, `Backend Dependencies`, `MarketMind Pro Overview`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 403 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **4 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `trader_score()` connect `trader_score` to `pipeline.py`, `Technical Indicators & Position Sizing`, `Trader Score & Red Flag Rules`, `engine.py`, `Historical Market Datafeed`?**
  _High betweenness centrality (0.004) - this node is a cross-community bridge._
- **What connects `Weekly Automated Market Scanner`, `Trader Score Rule Engine`, `Frontend Single Page App Shell` to the rest of the system?**
  _5 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Market Scan Lifecycle Control` be split into smaller, more focused modules?**
  _Cohesion score 0.10483870967741936 - nodes in this community are weakly interconnected._
- **Why does `run_pipeline()` connect `Historical Market Datafeed` to `pipeline.py`, `Technical Indicators & Position Sizing`, `Trader Score & Red Flag Rules`, `Bhavcopy Exchange Ingestion`, `fundamentals.py`, `FastAPI REST Endpoints`, `news.py`?**
  _High betweenness centrality (0.003) - this node is a cross-community bridge._
- **Should `Frontend React Application UI` be split into smaller, more focused modules?**
  _Cohesion score 0.0726950354609929 - nodes in this community are weakly interconnected._
- **Why does `walk_forward_and_forecast()` connect `Technical Indicators & Position Sizing` to `pipeline.py`, `Historical Market Datafeed`, `engine.py`?**
  _High betweenness centrality (0.002) - this node is a cross-community bridge._
- **Should `Bhavcopy Exchange Ingestion` be split into smaller, more focused modules?**
  _Cohesion score 0.0945945945945946 - nodes in this community are weakly interconnected._