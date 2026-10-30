# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users
Indian retail traders and investors who check a short list of weekly swing-trade candidates (NSE + BSE) once a week, usually on Monday, decide what to buy within a personal budget, and come back during the week to track how past picks performed.

## Product Purpose
MarketMind Pro screens the entire Indian market (~7,987 NSE + BSE listings) every week, reads each stock the way an experienced trader would, predicts the price 7 calendar days ahead, and publishes only 5-7 picks that pass a quality gate, a fundamentals check, a news veto and a Monte Carlo simulation. Success: the visitor understands each pick, why it was chosen, its risk, and how many shares fit their budget, without reading a manual.

## Positioning
No black box and no promised accuracy: every pick must beat a naive baseline in a walk-forward backtest on its own history, accuracy shown is measured, and excluded stocks are listed openly with the reason.

## Operating Context
Local web app (Vite + React on port 5174) talking to a FastAPI backend on port 8001 through `/api/*`. The weekly scan can be started from the website and takes 30-60 minutes; the page polls scan status every 4 seconds. A standalone cinematic 3D film page (`public/marketmind-3d.html`) and a rendered MP4 already exist.

## Capabilities and Constraints
- Tabs: This Week's Picks, All Scanned Stocks, Past Weeks, 3D Prediction Space.
- API endpoints (frontend must not change them): `/api/picks/latest`, `/api/screen/budget` (GET/POST), `/api/scanned`, `/api/history`, `/api/scan/status`, `/api/scan/start` (POST), `/api/prices/{symbol}`.
- Backend, API contracts and data flow are out of scope for UI work.
- All loading states use the `thinking-orbs` ThinkingOrb (no plain spinners).

## Brand Commitments
- Name: MarketMind Pro.
- Visual world pinned by the owner (2026-10-30): the Prompt-Motion 3D architecture gallery (prompt-motion.com): light plaster ground, dark anodized cards, single orange accent, Geist type, cinematic camera. The app itself is rendered as a 3D space with picks as physical cards and data panels on demand.

## Evidence on Hand
Real data comes only from the API. No testimonials, customers, or accuracy claims beyond the measured backtest numbers may be invented.

## Product Principles
1. Show the measured evidence behind every prediction; never imply guarantees.
2. Exclusions are as visible as picks.
3. The 3D space must never hide data: every card, column and block has a readable DOM equivalent.
4. Analysis software, not investment advice.
