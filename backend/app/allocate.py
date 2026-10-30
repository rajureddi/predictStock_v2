"""Budget allocation across picks: score/conviction-weighted, whole shares."""
def allocate(picks, budget):
    if not budget or budget <= 0 or not picks:
        return dict(budget_inr=budget, allocations=[], total_invested=0, leftover=(budget or 0),
                    expected_value=0, expected_profit=0)
    conv = []
    for p in picks:
        acc = (p.get("backtest") or {}).get("best_dir_acc", 50) or 50
        conv.append(max(p.get("trader_score", 50), 1) * (0.5 + acc/100.0) * (1 + max(p.get("predicted_return_pct", 0), 0)/20.0))
    total_c = sum(conv) or 1
    shares = [0]*len(picks)
    for i, p in enumerate(picks):
        target = budget * conv[i]/total_c
        shares[i] = int(target // p["current_price"]) if p["current_price"] > 0 else 0
    invested = sum(s*picks[i]["current_price"] for i, s in enumerate(shares))
    # greedy: spend leftover on highest-conviction affordable share, repeat
    order = sorted(range(len(picks)), key=lambda i: -conv[i])
    changed = True
    while changed:
        changed = False
        for i in order:
            price = picks[i]["current_price"]
            if price > 0 and invested + price <= budget:
                shares[i] += 1; invested += price; changed = True
    allocs = []
    exp_val = 0.0
    for i, p in enumerate(picks):
        inv = round(shares[i]*p["current_price"], 2); ev = round(shares[i]*p["predicted_price"], 2)
        exp_val += ev
        allocs.append(dict(symbol=p["symbol"], shares=shares[i], invested=inv, expected_value=ev,
                           expected_profit=round(ev-inv, 2)))
    invested = round(invested, 2)
    return dict(budget_inr=budget, allocations=allocs, total_invested=invested,
                leftover=round(budget-invested, 2), expected_value=round(exp_val, 2),
                expected_profit=round(exp_val-invested, 2))
