import sqlite3
import os
import sys
import pandas as pd
import numpy as np

# Set up paths for MarketMind Pro
mmp_dir = r"c:\Users\rajub\Downloads\marketmind-pro-WINDOWS-FINAL\backend"
sys.path.insert(0, mmp_dir)

from app.datafeed import local_history
from app.engine import trader_score

# Connect to PredictaStock SQLite
db_path = r"C:\Users\rajub\Desktop\RAJU_BUILDS\PredictaStock\data\predictastock.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("""
    SELECT symbol, start_date, end_date, original_reference_price, predicted_target_price, 
           actual_end_price, predicted_appreciation_pct, actual_appreciation_pct, 
           direction_correct, alpha_vs_nifty_pct 
    FROM forecast_evaluations 
    WHERE status = 'COMPLETED'
    ORDER BY start_date DESC
""")
eval_rows = cursor.fetchall()

print(f"Total historical evaluations in PredictaStock ledger: {len(eval_rows)}")

results = []

for row in eval_rows:
    sym, start_date, end_date, ps_ref, ps_target, actual_end, ps_pred_ret, ps_act_ret, ps_dir_correct, ps_alpha = row
    
    ticker = f"{sym}.NS"
    df = local_history(ticker)
    if df is None or df.empty or len(df) < 60:
        ticker = f"{sym}.BO"
        df = local_history(ticker)
        
    if df is None or df.empty or len(df) < 60:
        continue
        
    # Strict Point-in-Time: slice strictly up to start_date
    df_pit = df[df.index <= start_date]
    if len(df_pit) < 60:
        continue
        
    cmp_start = float(df_pit['Close'].iloc[-1])
    
    # Forward window: strictly between start_date and end_date
    df_fwd = df[(df.index > start_date) & (df.index <= end_date)]
    if df_fwd.empty:
        continue
        
    fwd_high = float(df_fwd['High'].max())
    fwd_low = float(df_fwd['Low'].min())
    fwd_close = float(df_fwd['Close'].iloc[-1])
    actual_move_pct = round(((fwd_close - cmp_start) / cmp_start) * 100, 2)
    
    # Run MarketMind Pro's Engine
    try:
        ts = trader_score(df_pit)
    except Exception as e:
        continue
        
    if not ts:
        continue
        
    mmp_score = ts['score']
    mmp_metrics = ts['metrics']
    mmp_target1 = mmp_metrics['target1']
    mmp_target2 = mmp_metrics['target2']
    mmp_stop = mmp_metrics['stop_loss']
    
    mmp_expected_ret = round(((mmp_target1 - cmp_start) / cmp_start) * 100, 2)
    mmp_bullish = mmp_score >= 55.0
    
    # Outcome tracking for MarketMind Pro
    mmp_target_hit = fwd_high >= mmp_target1
    mmp_stop_hit = fwd_low <= mmp_stop
    mmp_dir_correct = 1 if (actual_move_pct > 0 and mmp_bullish) or (actual_move_pct < 0 and not mmp_bullish) else 0
    mmp_error = abs(mmp_expected_ret - actual_move_pct)
    
    # Outcome tracking for PredictaStock
    ps_target_hit = fwd_high >= ps_target
    ps_error = abs(ps_pred_ret - actual_move_pct)
    
    results.append({
        "symbol": sym,
        "start_date": start_date,
        "end_date": end_date,
        "start_price": cmp_start,
        "end_price": fwd_close,
        "actual_move_pct": actual_move_pct,
        # PredictaStock
        "ps_score": round(row[8], 1),
        "ps_target": ps_target,
        "ps_expected_ret": ps_pred_ret,
        "ps_target_hit": ps_target_hit,
        "ps_dir_correct": ps_dir_correct,
        "ps_error": ps_error,
        # MarketMind Pro
        "mmp_score": mmp_score,
        "mmp_target1": mmp_target1,
        "mmp_stop": mmp_stop,
        "mmp_expected_ret": mmp_expected_ret,
        "mmp_target_hit": mmp_target_hit,
        "mmp_stop_hit": mmp_stop_hit,
        "mmp_dir_correct": mmp_dir_correct,
        "mmp_error": mmp_error
    })

res_df = pd.DataFrame(results)
print(f"\nSuccessfully evaluated {len(res_df)} overlapping trades head-to-head on identical Bhavcopy data.\n")

# Aggregate Statistics
ps_dir_acc = (res_df['ps_dir_correct'].sum() / len(res_df)) * 100
mmp_dir_acc = (res_df['mmp_dir_correct'].sum() / len(res_df)) * 100

ps_tgt_hit_rate = (res_df['ps_target_hit'].sum() / len(res_df)) * 100
mmp_tgt_hit_rate = (res_df['mmp_target_hit'].sum() / len(res_df)) * 100

ps_avg_error = res_df['ps_error'].mean()
mmp_avg_error = res_df['mmp_error'].mean()

ps_avg_expected = res_df['ps_expected_ret'].mean()
mmp_avg_expected = res_df['mmp_expected_ret'].mean()

avg_actual_ret = res_df['actual_move_pct'].mean()

print("=" * 65)
print("HEAD-TO-HEAD BENCHMARK RESULTS (IDENTICAL TEST DATA)")
print("=" * 65)
print(f"Total Evaluated Sample Size    : {len(res_df)} stocks")
print(f"Average Actual 5-Day Return    : {avg_actual_ret:+.2f}%\n")

print(f"{'Metric':<30} | {'PredictaStock':<15} | {'MarketMind Pro':<15}")
print("-" * 65)
print(f"{'Directional Accuracy (Win %)':<30} | {ps_dir_acc:.1f}%{'':<10} | {mmp_dir_acc:.1f}%")
print(f"{'Target Hit Rate (%)':<30} | {ps_tgt_hit_rate:.1f}%{'':<10} | {mmp_tgt_hit_rate:.1f}%")
print(f"{'Average Expected Target (%)':<30} | {ps_avg_expected:+.2f}%{'':<9} | {mmp_avg_expected:+.2f}%")
print(f"{'Average Forecast Error (%)':<30} | {ps_avg_error:.2f}%{'':<10} | {mmp_avg_error:.2f}%")
print(f"{'Stop-Loss Trigger Rate (%)':<30} | {'N/A (Fixed 1.5 ATR)':<15} | {res_df['mmp_stop_hit'].sum()/len(res_df)*100:.1f}%")
print("=" * 65)

print("\n--- SAMPLE INDIVIDUAL PREDICTIONS COMPARISON ---")
for idx, r in res_df.head(10).iterrows():
    print(f"Stock: {r['symbol']:<10} | Start: {r['start_date']} ({r['start_price']:.1f}) -> End: {r['end_price']:.1f} ({r['actual_move_pct']:+.2f}%)")
    print(f"   PredictaStock : Target {r['ps_target']:.1f} ({r['ps_expected_ret']:+.2f}%) | Target Hit: {r['ps_target_hit']} | Dir Correct: {r['ps_dir_correct']}")
    print(f"   MarketMind Pro: Target {r['mmp_target1']:.1f} ({r['mmp_expected_ret']:+.2f}%) | Stop: {r['mmp_stop']:.1f} | Target Hit: {r['mmp_target_hit']} | Dir Correct: {r['mmp_dir_correct']}")
    print("-" * 65)

