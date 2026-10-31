"""Budget allocation across picks — ATR / stop-distance risk sizing.

Every pick risks the same rupee amount (budget × risk% × size_mult) between
entry and stop, so a tight-stop stock gets more shares and a wide-stop stock
fewer: equal risk across the portfolio instead of equal conviction-weighted
capital. Guards: no pick above 30% of investable capital; total capital
capped at budget × (1 − cash_pct) with proportional scale-down when over.
"""
MAX_PICK_PCT = 0.30
FALLBACK_STOP_PCT = 0.04  # when a pick has no usable stop


def _empty(budget, cash_pct=0.0, risk_pct=1.0):
    b = budget or 0
    return dict(budget_inr=budget, allocations=[], total_invested=0, leftover=b,
                expected_value=0, expected_profit=0, risk_inr=0, risk_pct=risk_pct,
                cash_reserve=round(b * (cash_pct or 0), 2), size_mult=1.0, investable=round(b * (1 - (cash_pct or 0)), 2))


def allocate(picks, budget, risk_pct=1.0, size_mult=1.0, cash_pct=0.0):
    """Returns the allocation dict. Existing keys (budget_inr, allocations[
    symbol, shares, invested, expected_value, expected_profit], total_invested,
    leftover, expected_value, expected_profit) are unchanged; adds risk_inr,
    risk_pct, cash_reserve, size_mult, investable and per-pick risk_inr."""
    cash_pct = min(max(float(cash_pct or 0.0), 0.0), 0.95)
    size_mult = max(float(size_mult or 1.0), 0.0)
    risk_pct = max(float(risk_pct or 1.0), 0.0)
    if not budget or budget <= 0 or not picks:
        return _empty(budget, cash_pct, risk_pct)
    investable = budget * (1.0 - cash_pct)
    risk_inr = budget * (risk_pct / 100.0) * size_mult
    per_cap = investable * MAX_PICK_PCT

    shares = [0] * len(picks)
    for i, p in enumerate(picks):
        price = float(p.get("current_price") or 0)
        if price <= 0: continue
        stop = float(p.get("stop_loss") or 0)
        per_share_risk = price - stop if 0 < stop < price else price * FALLBACK_STOP_PCT
        n = int(risk_inr // per_share_risk) if per_share_risk > 0 else 0
        n = min(n, int(per_cap // price))
        shares[i] = max(n, 0)

    def invested_total(sh): return sum(s * float(picks[i].get("current_price") or 0) for i, s in enumerate(sh))
    total = invested_total(shares)
    if total > investable and total > 0:
        f = investable / total
        shares = [int(s * f) for s in shares]
        total = invested_total(shares)
    # floor rounding can leave room for one more share of a pick that already has some:
    # top up in order of largest shortfall vs its risk target while it still fits.
    changed = True
    while changed:
        changed = False
        for i in sorted(range(len(picks)), key=lambda k: -shares[k]):
            price = float(picks[i].get("current_price") or 0)
            if shares[i] == 0 or price <= 0: continue
            stop = float(picks[i].get("stop_loss") or 0)
            psr = price - stop if 0 < stop < price else price * FALLBACK_STOP_PCT
            if (shares[i] + 1) * psr <= risk_inr and (shares[i] + 1) * price <= per_cap and total + price <= investable:
                shares[i] += 1; total += price; changed = True

    allocs, exp_val = [], 0.0
    for i, p in enumerate(picks):
        price = float(p.get("current_price") or 0)
        pred = float(p.get("predicted_price") or price)
        stop = float(p.get("stop_loss") or 0)
        inv = round(shares[i] * price, 2); ev = round(shares[i] * pred, 2)
        exp_val += ev
        psr = price - stop if 0 < stop < price else price * FALLBACK_STOP_PCT
        allocs.append(dict(symbol=p.get("symbol"), shares=shares[i], invested=inv, expected_value=ev,
                           expected_profit=round(ev - inv, 2), risk_inr=round(shares[i] * psr, 2)))
    total = round(total, 2)
    return dict(budget_inr=budget, allocations=allocs, total_invested=total,
                leftover=round(budget - total, 2), expected_value=round(exp_val, 2),
                expected_profit=round(exp_val - total, 2),
                risk_inr=round(risk_inr, 2), risk_pct=risk_pct, size_mult=size_mult,
                cash_reserve=round(budget * cash_pct, 2), investable=round(investable, 2))
