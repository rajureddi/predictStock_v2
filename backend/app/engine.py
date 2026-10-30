"""Trader-style technical analysis engine: indicators, candlestick patterns,
scoring, ML walk-forward backtest + forecast. Pure pandas/numpy/sklearn."""
import numpy as np, pandas as pd

HORIZON = 5  # trading days ~= 7 calendar days

# ---------- indicators ----------
def _ema(s, n): return s.ewm(span=n, adjust=False).mean()
def _rsi(c, n=14):
    d = c.diff(); up = d.clip(lower=0).ewm(alpha=1/n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1/n, adjust=False).mean()
    rs = up / dn.replace(0, np.nan)
    return 100 - 100/(1+rs)
def _atr(df, n=14):
    h,l,c = df['High'], df['Low'], df['Close']
    tr = pd.concat([h-l, (h-c.shift()).abs(), (l-c.shift()).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1/n, adjust=False).mean()
def _adx(df, n=14):
    h,l,c = df['High'], df['Low'], df['Close']
    up = h.diff(); dn = -l.diff()
    pdm = np.where((up>dn)&(up>0), up, 0.0); ndm = np.where((dn>up)&(dn>0), dn, 0.0)
    tr = pd.concat([h-l, (h-c.shift()).abs(), (l-c.shift()).abs()], axis=1).max(axis=1)
    atr = pd.Series(tr, index=df.index).ewm(alpha=1/n, adjust=False).mean()
    pdi = 100*pd.Series(pdm, index=df.index).ewm(alpha=1/n, adjust=False).mean()/atr
    ndi = 100*pd.Series(ndm, index=df.index).ewm(alpha=1/n, adjust=False).mean()/atr
    dx = 100*(pdi-ndi).abs()/(pdi+ndi).replace(0,np.nan)
    return dx.ewm(alpha=1/n, adjust=False).mean(), pdi, ndi

def add_indicators(df):
    df = df.copy()
    c, v = df['Close'], df['Volume']
    for n in (9,21,50,200): df[f'EMA{n}'] = _ema(c,n)
    df['SMA50'] = c.rolling(50).mean(); df['SMA200'] = c.rolling(200).mean()
    df['RSI'] = _rsi(c)
    macd = _ema(c,12)-_ema(c,26); df['MACD']=macd; df['MACD_SIG']=_ema(macd,9); df['MACD_HIST']=macd-df['MACD_SIG']
    ll = df['Low'].rolling(14).min(); hh = df['High'].rolling(14).max()
    df['STOCH_K'] = 100*(c-ll)/(hh-ll).replace(0,np.nan); df['STOCH_D'] = df['STOCH_K'].rolling(3).mean()
    df['ATR'] = _atr(df); df['ADX'], df['PDI'], df['NDI'] = _adx(df)
    mid = c.rolling(20).mean(); sd = c.rolling(20).std()
    df['BB_MID']=mid; df['BB_UP']=mid+2*sd; df['BB_LO']=mid-2*sd
    df['VOL20'] = v.rolling(20).mean(); df['VOL_RATIO'] = v/df['VOL20']
    obv = (np.sign(c.diff()).fillna(0)*v).cumsum(); df['OBV']=obv; df['OBV_EMA']=_ema(obv,20)
    df['RET1']=c.pct_change(); df['RET5']=c.pct_change(5); df['RET21']=c.pct_change(21); df['RET63']=c.pct_change(63); df['RET126']=c.pct_change(126)
    # VWAP-style anchor: rolling 20d typical-price VWAP
    tp = (df['High']+df['Low']+c)/3
    df['VWAP20'] = (tp*v).rolling(20).sum()/v.rolling(20).sum().replace(0,np.nan)
    return df

# ---------- candlestick patterns (evaluated on last bar vs priors) ----------
def detect_patterns(df):
    """Return (bullish_score, bearish_score, [pattern names bullish], [bearish]) for last bar."""
    if len(df) < 5: return 0,0,[],[]
    o,h,l,c = [df[x].iloc[-1] for x in ('Open','High','Low','Close')]
    po,ph,pl,pc = [df[x].iloc[-2] for x in ('Open','High','Low','Close')]
    body = abs(c-o); rng = max(h-l, 1e-9); upper = h-max(c,o); lower = min(c,o)-l
    bull, bear = [], []
    if c>o and pc<po and c>=po and o<=pc: bull.append('Bullish engulfing')
    if c<o and pc>po and c<=po and o>=pc: bear.append('Bearish engulfing')
    if lower >= 2*max(body,1e-9) and upper <= rng*0.15 and body>0: bull.append('Hammer')
    if upper >= 2*max(body,1e-9) and lower <= rng*0.15 and body>0: bear.append('Inverted hammer / shooting star')
    if body <= rng*0.1: (bull if c>=o else bear).append('Doji (indecision)')
    # three white soldiers / black crows on last 3
    last3 = df.iloc[-3:]
    if len(last3)==3 and all(last3['Close'].values[i]>last3['Open'].values[i] for i in range(3)) and np.all(np.diff(last3['Close'].values)>0): bull.append('Three white soldiers')
    if len(last3)==3 and all(last3['Close'].values[i]<last3['Open'].values[i] for i in range(3)) and np.all(np.diff(last3['Close'].values)<0): bear.append('Three black crows')
    # morning / evening star (approx)
    a,b = df.iloc[-3], df.iloc[-2]
    if a['Close']<a['Open'] and abs(b['Close']-b['Open']) < 0.3*abs(a['Close']-a['Open']) and c>o and c>(a['Open']+a['Close'])/2: bull.append('Morning star')
    if a['Close']>a['Open'] and abs(b['Close']-b['Open']) < 0.3*abs(a['Close']-a['Open']) and c<o and c<(a['Open']+a['Close'])/2: bear.append('Evening star')
    # inside bar
    if h<=ph and l>=pl: bull.append('Inside bar (compression)')
    # breakout candle: close above 20d high with big body
    if len(df)>=21:
        prev_high = df['High'].iloc[-21:-1].max()
        if c>prev_high and body>rng*0.6 and c>o: bull.append('Breakout candle above 20-day high')
        prev_low = df['Low'].iloc[-21:-1].min()
        if c<prev_low and body>rng*0.6 and c<o: bear.append('Breakdown candle below 20-day low')
    return len(bull), len(bear), bull, bear

def swing_levels(df, look=60):
    d = df.tail(look)
    return float(d['Low'].min()), float(d['High'].max())

FEATURES = ['RET1','RET5','RET21','RET63','RSI','MACD_HIST','STOCH_K','VOL_RATIO','ADX',
            'EMA9_R','EMA21_R','EMA50_R','BB_POS','ATR_PCT','OBV_R','PAT_BULL','PAT_BEAR','RS21','RS63']

def build_features(df, nifty_close=None):
    df = add_indicators(df)
    c = df['Close']
    df['EMA9_R']=c/df['EMA9']-1; df['EMA21_R']=c/df['EMA21']-1; df['EMA50_R']=c/df['EMA50']-1
    df['BB_POS']=(c-df['BB_LO'])/((df['BB_UP']-df['BB_LO']).replace(0,np.nan))
    df['ATR_PCT']=df['ATR']/c; df['OBV_R']=df['OBV']/(df['OBV_EMA'].replace(0,np.nan))-1
    bull=[]; bear=[]
    # pattern flags per row are expensive; compute rolling on last-bar basis via vectorised engulfing only + last value broadcast is wrong.
    # Use simple per-row engulfing flags:
    o=df['Open']
    bull_eng = ((c>o)&(c.shift()>0)&(df['Close'].shift(1)<df['Open'].shift(1))&(c>=df['Open'].shift(1))&(o<=df['Close'].shift(1))).astype(float)
    bear_eng = ((c<o)&(df['Close'].shift(1)>df['Open'].shift(1))&(c<=df['Open'].shift(1))&(o>=df['Close'].shift(1))).astype(float)
    df['PAT_BULL']=bull_eng; df['PAT_BEAR']=bear_eng
    if nifty_close is not None:
        nc = nifty_close.reindex(df.index).ffill()
        df['RS21'] = (c/c.shift(21)-1) - (nc/nc.shift(21)-1)
        df['RS63'] = (c/c.shift(63)-1) - (nc/nc.shift(63)-1)
    else:
        df['RS21']=0.0; df['RS63']=0.0
    df['TARGET'] = c.shift(-HORIZON)/c - 1
    return df

def trader_score(df, nifty_close=None):
    """df = raw OHLCV (>=60 rows). Returns dict with score 0..100, reasons, metrics."""
    if df is None or len(df) < 60: return None
    d = build_features(df, nifty_close)
    last = d.iloc[-1]; c = float(last['Close'])
    reasons, score = [], 50.0
    def add(pts, msg): 
        nonlocal score; score += pts; 
        if msg: reasons.append(msg)
    # Trend (max +/-20)
    if c > last['EMA21']: add(6, f"Price above 21-EMA (₹{last['EMA21']:.2f}) — short-term uptrend")
    else: add(-6, "Price below 21-EMA — short-term trend weak")
    if c > last['EMA50']: add(6, "Price above 50-EMA — intermediate uptrend")
    else: add(-6, "Price below 50-EMA")
    if not np.isnan(last.get('EMA200', np.nan)) and c > last['EMA200']: add(5, "Above 200-EMA — long-term trend up")
    elif not np.isnan(last.get('EMA200', np.nan)): add(-5, "Below 200-EMA — long-term trend down")
    if last['EMA9'] > last['EMA21']: add(3, "9/21 EMA bullish crossover structure")
    # Momentum (+/-12) plus parabolic / overbought penalty
    rsi = last['RSI']
    if 50 <= rsi <= 70: add(6, f"RSI {rsi:.0f} — strong but not overbought")
    elif 40 <= rsi < 50: add(2, f"RSI {rsi:.0f} rising zone")
    elif rsi > 85: add(-18, f"RSI {rsi:.0f} — extreme overbought (>85), blow-off / reversal risk")
    elif rsi > 80: add(-12, f"RSI {rsi:.0f} — severely overbought (>80), parabolic chase risk")
    elif rsi > 75: add(-5, f"RSI {rsi:.0f} — overbought, chase risk")
    elif rsi < 30: add(-3, f"RSI {rsi:.0f} — oversold/weak")
    ret63_v = float(last['RET63']) if not np.isnan(last.get('RET63', np.nan)) else 0.0
    ema50_r = float(last['EMA50_R']) if not np.isnan(last.get('EMA50_R', np.nan)) else 0.0
    if ret63_v > 1.0 or ema50_r > 0.45:
        add(-15, f"Parabolic 60-day extension (+{ret63_v*100:.0f}%, {ema50_r*100:.0f}% above 50-EMA) — mean-reversion risk")
    elif ret63_v > 0.60 or ema50_r > 0.28:
        add(-8, f"Stretched 60-day run (+{ret63_v*100:.0f}%, {ema50_r*100:.0f}% above 50-EMA) — chase risk")
    if last['MACD_HIST'] > 0: add(4, "MACD histogram positive")
    else: add(-4, "MACD histogram negative")
    if last['STOCH_K'] > last['STOCH_D'] and last['STOCH_K'] < 85: add(2, "Stochastic turning up")
    # ADX
    adx = last['ADX']
    if adx > 25 and last['PDI'] > last['NDI']: add(5, f"ADX {adx:.0f} — strong uptrend")
    elif adx > 25: add(-4, f"ADX {adx:.0f} — strong downtrend")
    # Volume (+/-8)
    vr = last['VOL_RATIO']
    if vr >= 1.5 and last['RET1'] > 0: add(6, f"Volume {vr:.1f}× 20-day average on an up day")
    elif vr >= 1.5: add(-3, f"Volume {vr:.1f}× average but on a down day — distribution")
    elif vr < 0.6: add(-2, "Volume well below average — low conviction")
    if last['OBV'] > last['OBV_EMA']: add(2, "OBV trending up — accumulation")
    # Delivery % (official bhavcopy; absent on Yahoo-only frames -> no-op)
    try: deliv = float(last['DelivPer'])
    except Exception: deliv = np.nan
    try: deliv_avg5 = float(d['DelivPer'].tail(5).mean())
    except Exception: deliv_avg5 = np.nan
    if not np.isnan(deliv):
        if deliv >= 50 and last['RET1'] > 0: add(3, f"High delivery ({deliv:.0f}%) — genuine buying, not just intraday")
        elif deliv < 25 and last['RET1'] > 0.02: add(-2, "Low delivery on the rise — speculative move")
    # Patterns (+/-10)
    nb, nbe, bull_pats, bear_pats = detect_patterns(df)
    sup, res = swing_levels(df)
    near_sup = c <= sup*1.03
    for p in bull_pats: add(4, f"{p}" + (" at support" if near_sup and p in ('Bullish engulfing','Hammer','Morning star') else ""))
    for p in bear_pats: add(-4, p)
    # Levels / breakout
    hi52 = float(df['High'].tail(250).max()); lo52 = float(df['Low'].tail(250).min())
    dist_hi = c/hi52 - 1
    if c >= res*0.999: add(5, "Closing at/near 60-day high — breakout zone")
    if dist_hi > -0.05: add(2, f"Within 5% of 52-week high (₹{hi52:.2f})")
    # Relative strength
    rs63 = last.get('RS63', 0)
    if rs63 > 0.05: add(5, f"Beating NIFTY by {rs63*100:.1f}% over 3 months")
    elif rs63 < -0.05: add(-5, f"Lagging NIFTY by {abs(rs63)*100:.1f}% over 3 months")
    # HH/HL structure
    highs = df['High'].tail(20).values; 
    if len(df)>=40 and df['High'].tail(10).max() > df['High'].iloc[-20:-10].max() and df['Low'].tail(10).min() > df['Low'].iloc[-20:-10].min():
        add(3, "Higher-high / higher-low structure")
    score = float(max(0, min(100, score)))
    atr = float(last['ATR']) if not np.isnan(last['ATR']) else c*0.02
    # Dynamic stop-loss & targets based on swing structure, trend strength, and extension
    low10 = float(df['Low'].tail(10).min())
    ema21_v = float(last['EMA21']) if not np.isnan(last['EMA21']) else c - 1.5*atr
    struct_stop = max(low10 - 0.35*atr, min(ema21_v - 0.4*atr, c - 1.2*atr))
    risk_mult = float(np.clip((c - struct_stop) / max(atr, 1e-9), 1.15, 2.15))
    if rsi > 78:
        risk_mult = min(risk_mult, 1.35)
    stop_loss = round(max(0.05, c - risk_mult * atr), 2)
    adx_v = float(adx) if not np.isnan(adx) else 20.0
    rs63_v = float(rs63) if not np.isnan(rs63) else 0.0
    rew_mult = 2.1 + float(np.clip((adx_v - 20.0) / 22.0, -0.25, 1.15)) + float(np.clip(rs63_v * 2.0, -0.35, 0.55))
    if 52 <= rsi <= 68: rew_mult += 0.25
    elif rsi > 80: rew_mult *= 0.68
    elif rsi > 75: rew_mult *= 0.82
    if ret63_v > 0.80 or ema50_r > 0.35: rew_mult *= 0.78
    rew_mult = float(np.clip(rew_mult, 1.25, 3.8))
    target1 = round(c + rew_mult * atr, 2)
    target2 = round(c + (rew_mult + 1.15) * atr, 2)
    metrics = dict(price=c, rsi=float(rsi), adx=float(adx), vol_ratio=float(vr) if not np.isnan(vr) else 0,
                   ema21=float(last['EMA21']), ema50=float(last['EMA50']),
                   support=sup, resistance=res, high52=hi52, low52=lo52,
                   stop_loss=stop_loss, target1=target1, target2=target2,
                   atr=atr, ret21=float(last['RET21']) if not np.isnan(last['RET21']) else 0,
                   ret63=ret63_v,
                   rs63=rs63_v,
                   delivery_pct=(round(deliv, 1) if not np.isnan(deliv) else None),
                   delivery_avg5=(round(deliv_avg5, 1) if not np.isnan(deliv_avg5) else None),
                   patterns=bull_pats+bear_pats)
    rr = (metrics['target1']-c)/max(c-metrics['stop_loss'],1e-9)
    metrics['risk_reward'] = round(rr,2)
    return dict(score=round(score,1), reasons=reasons[:8], metrics=metrics, features=d)

# ---------- prediction: walk-forward backtest + forecast ----------
def _fit_predict(train_X, train_y, X1):
    from sklearn.ensemble import HistGradientBoostingRegressor
    m = HistGradientBoostingRegressor(max_iter=200, learning_rate=0.06, max_depth=3, random_state=42)
    m.fit(train_X, train_y); return float(m.predict(X1)[0])

def walk_forward_and_forecast(df, nifty_close=None):
    """Returns dict or None. Walk-forward on last ~12 non-overlapping horizon windows."""
    d = build_features(df, nifty_close)
    # Only drop rows where FEATURES are NaN (initial indicator warm-up period).
    # Do NOT drop NaNs from TARGET across the dataframe, because the last HORIZON rows
    # naturally have NaN forward targets but contain live features required for current (t_0) inference.
    clean = d.dropna(subset=FEATURES)
    if len(clean) < 120 + HORIZON: return None
    X = clean[FEATURES]
    y = clean['TARGET']

    # Historical training partition where forward targets are known (up to t - HORIZON)
    X_train = X.iloc[:-HORIZON].values
    y_train = y.iloc[:-HORIZON].values
    closes = clean['Close'].iloc[:-HORIZON].values

    # Live inference features: latest available bar (t_0)
    X_live = X.iloc[[-1]].values

    # walk-forward origins: step HORIZON, up to 24 non-overlapping windows with >=80 leak-free train rows.
    # Row k in (X_train, y_train) uses Close[k + HORIZON] in its target, so at origin i
    # we must train strictly on [:i - HORIZON] (and lag drift the same way) to avoid any look-ahead leak.
    origins = list(range(len(X_train)-HORIZON, 79+HORIZON, -HORIZON))[:24][::-1]
    if len(origins) < 5: return None
    ml_pred, drift_pred, naive_pred, actual, used_origins = [], [], [], [], []
    for i in origins:
        train_end = i - HORIZON
        if train_end < 60: continue
        try: p = _fit_predict(X_train[:train_end], y_train[:train_end], X_train[i:i+1])
        except Exception: continue
        hist_ret = y_train[max(0, train_end-60):train_end]
        drift = float(np.mean(hist_ret)) if len(hist_ret) else 0.0
        ml_pred.append(p); drift_pred.append(drift); naive_pred.append(0.0); actual.append(y_train[i]); used_origins.append(i)
    if len(actual) < 5: return None
    actual=np.array(actual); closes_o = closes[used_origins]
    def metrics(pred):
        pred=np.array(pred); pred_price = closes_o*(1+pred); act_price = closes_o*(1+actual)
        mape = float(np.mean(np.abs(act_price-pred_price)/act_price)*100)
        diracc = float(np.mean(np.sign(pred)==np.sign(actual))*100) if len(actual) else 0
        return mape, diracc
    ml_mape, ml_acc = metrics(ml_pred); dr_mape, dr_acc = metrics(drift_pred); nv_mape, nv_acc = metrics(naive_pred)
    candidates = {'ml': (ml_mape, ml_acc, float(np.mean(ml_pred))), 'drift': (dr_mape, dr_acc, float(np.mean(drift_pred))), 'naive': (nv_mape, nv_acc, 0.0)}
    # best = lowest MAPE among ml/drift; quality gate = beats naive on MAPE (or >=55% direction accuracy with MAPE within 5% of naive)
    best_name = min(['ml','drift'], key=lambda k: candidates[k][0])
    best_mape, best_acc, _ = candidates[best_name]
    quality_pass = (best_mape < nv_mape) or (best_acc >= 55.0 and best_mape <= nv_mape * 1.05)
    # final forecast: retrain ML on historical data with known targets (X.iloc[:-5], y.iloc[:-5]),
    # and generate live prediction on X.iloc[[-1]] (t_0)
    try: ml_f = _fit_predict(X_train, y_train, X_live)
    except Exception: ml_f = 0.0
    drift_f = float(np.mean(y_train[-60:]))
    w_ml = (1/max(ml_mape,0.1)); w_dr = (1/max(dr_mape,0.1))
    blended = (ml_f*w_ml + drift_f*w_dr)/(w_ml+w_dr)
    # Dampen overbought / parabolic extrapolation so vertical runs are not projected linearly
    last_row = clean.iloc[-1]
    rsi_now = float(last_row['RSI']) if not np.isnan(last_row.get('RSI', np.nan)) else 50.0
    ret63_now = float(last_row['RET63']) if not np.isnan(last_row.get('RET63', np.nan)) else 0.0
    ema50_now = float(last_row['EMA50_R']) if not np.isnan(last_row.get('EMA50_R', np.nan)) else 0.0
    damper = 0.65  # shrinkage toward 0 to reduce out-of-sample variance
    if rsi_now > 85 or ret63_now > 1.0 or ema50_now > 0.45:
        damper *= 0.35
    elif rsi_now > 80 or ret63_now > 0.60 or ema50_now > 0.28:
        damper *= 0.55
    elif rsi_now > 75:
        damper *= 0.75
    pred_ret = float(0.08 * np.tanh((blended * damper) / 0.08))
    last_close = float(clean['Close'].iloc[-1]); atr = float(clean['ATR'].iloc[-1]) if not np.isnan(clean['ATR'].iloc[-1]) else last_close*0.02
    resid_std = float(np.std(np.array(actual)-np.array(ml_pred)*0.65)) if best_name=='ml' else float(np.std(np.array(actual)-np.array(drift_pred)*0.65))
    pred_price = last_close*(1+pred_ret)
    band = max(resid_std, atr/last_close*np.sqrt(HORIZON)*0.8)
    return dict(model_used=('ml+drift blend, best='+best_name), predicted_return_pct=round(pred_ret*100,2),
                predicted_price=round(pred_price,2), range_low=round(last_close*(1+pred_ret-band),2),
                range_high=round(last_close*(1+pred_ret+band),2),
                backtest=dict(ml_mape=round(ml_mape,2), ml_dir_acc=round(ml_acc,1), drift_mape=round(dr_mape,2),
                              drift_dir_acc=round(dr_acc,1), naive_mape=round(nv_mape,2), naive_dir_acc=round(nv_acc,1),
                              best_model=best_name, best_mape=round(best_mape,2), best_dir_acc=round(best_acc,1), windows=len(actual)),
                quality_pass=bool(quality_pass))
