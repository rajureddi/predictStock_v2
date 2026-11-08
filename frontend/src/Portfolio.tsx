import { useCallback, useEffect, useMemo, useState } from 'react'
import { ThinkingOrb } from 'thinking-orbs'
import { ArrowsClockwise, Briefcase, CheckCircle, Plus, Trash, TrendDown, TrendUp } from '@phosphor-icons/react'
import { C, Holding, inr, pct, useOrb } from './lib'
import { FallingLeaves } from "falling-leaves/react"
import SnowFall from "react-snowfall"
const shades = () => ['#FF5E1A', '#2563EB', '#10B981', '#8B5CF6', '#06B6D4', '#F59E0B', '#EC4899', '#3B82F6', '#14B8A6', '#6366F1']

function usePortfolioLiveQuotes(holdings: Holding[], picks: any[]) {
  const [quotes, setQuotes] = useState<Record<string, { price: number; isLive: boolean }>>({})
  const [loading, setLoading] = useState(false)
  const [lastUpdated, setLastUpdated] = useState<string>('')

  const symbols = useMemo(() => holdings.map(h => h.symbol).filter(Boolean), [holdings])
  const symbolsKey = symbols.sort().join(',')

  const fetchLiveQuotes = useCallback(async () => {
    if (!symbols.length) return
    setLoading(true)
    try {
      const res = await fetch(`/api/live-quotes?symbols=${encodeURIComponent(symbols.join(','))}`)
      const data = await res.json()
      if (data && data.quotes) {
        const next: Record<string, { price: number; isLive: boolean }> = {}
        for (const [s, price] of Object.entries(data.quotes)) {
          if (typeof price === 'number' && price > 0) {
            next[s] = { price, isLive: true }
          }
        }
        setQuotes(prev => ({ ...prev, ...next }))
        setLastUpdated(new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' }))
      }
    } catch {
      // Keep cached quotes on transient network failure
    } finally {
      setLoading(false)
    }
  }, [symbolsKey])

  useEffect(() => {
    fetchLiveQuotes()
    const intv = setInterval(fetchLiveQuotes, 20000)
    return () => clearInterval(intv)
  }, [fetchLiveQuotes])

  return { quotes, loading, lastUpdated, refresh: fetchLiveQuotes }
}

export default function Portfolio({ holdings, picks, onOpen, onRemove, onAddAll, onEditShares }: {
  holdings: Holding[]; picks: any[]
  onOpen: (symbol: string) => void; onRemove: (symbol: string) => void
  onAddAll: () => void; onEditShares: (symbol: string, shares: number) => void
}) {
  const { quotes, loading, lastUpdated, refresh } = usePortfolioLiveQuotes(holdings, picks)
  const orb = useOrb()
  const SHADES = shades()
  const canAddAll = picks.some(p => p.shares > 0)

  const rows = holdings.map(h => {
    const pickMatch = picks.find(p => p.symbol === h.symbol)
    const quote = quotes[h.symbol]
    // Price resolution ladder: Live API quote -> Pick live_price -> Pick current_price -> User buy price
    const currentPrice = quote?.price ?? pickMatch?.live_price ?? pickMatch?.current_price ?? h.buy
    const isLive = !!quote?.isLive || !!pickMatch?.live_price
    const cost = h.shares * h.buy
    const value = h.shares * currentPrice
    const pnl = value - cost
    const pnlPct = cost > 0 ? (pnl / cost) * 100 : 0
    const targetPrice = h.target ?? pickMatch?.target ?? h.predicted ?? pickMatch?.predicted_price
    const stopPrice = h.stop ?? pickMatch?.stop_loss
    const proj = (targetPrice != null ? h.shares * targetPrice : value)

    return {
      h,
      currentPrice,
      isLive,
      cost,
      value,
      pnl,
      pnlPct,
      proj,
      targetPrice,
      stopPrice,
      inPicks: !!pickMatch,
    }
  })

  const invested = rows.reduce((s, r) => s + r.cost, 0)
  const value = rows.reduce((s, r) => s + r.value, 0)
  const pnl = value - invested
  const pnlPct = invested > 0 ? (pnl / invested) * 100 : 0
  const projected = rows.reduce((s, r) => s + r.proj, 0)
  const sorted = [...rows].sort((a, b) => b.pnlPct - a.pnlPct)
  const bestPerformer = sorted.length ? sorted[0] : null

  if (!holdings.length) return <section className="panel emptystate">
    <ThinkingOrb state="breathing" size={64} theme={orb} />
    <h4>Your portfolio is empty</h4>
    <p>Open any pick and press <b>Add to portfolio</b>, or add this week's picks using the share counts from your saved budget. Holdings are kept in this browser only.</p>
    {canAddAll && <button className="btn dark" onClick={onAddAll}><Plus size={15} weight="bold" /> Add this week's picks</button>}
  </section>

  return (<>
    <dl className="kpis panel">
      <FallingLeaves
        fullScreen
        shapes={["maple"]}
      />
      <SnowFall
        color="#87CEEB"
        style={{
          position: "fixed",
          width: '200vh',
          height: '200vh'
        }}
      ></SnowFall>
      <div>
        <dt>Invested</dt>
        <dd className="num">{inr(Math.round(invested))}</dd>
        <dd className="s">{holdings.length} {holdings.length === 1 ? 'holding' : 'holdings'}</dd>
      </div>
      <div>
        <dt>Current value</dt>
        <dd className="num">{inr(Math.round(value))}</dd>
        <dd className="s">{lastUpdated ? `Live at ${lastUpdated}` : 'Live mark-to-market'}</dd>
      </div>
      <div>
        <dt>Unrealised P&amp;L</dt>
        <dd className={`num ${pnl >= 0 ? 'pos' : 'neg'}`}>
          {(pnl >= 0 ? '+' : '') + inr(Math.round(pnl))}
        </dd>
        <dd className={`s ${pnl >= 0 ? 'pos' : 'neg'}`}>{pct(pnlPct)}</dd>
      </div>
      <div>
        <dt>Projected at target</dt>
        <dd className="num">{inr(Math.round(projected))}</dd>
        <dd className="s">{pct(((projected / Math.max(1, invested)) - 1) * 100)} vs cost</dd>
      </div>
      <div>
        <dt>Best performer</dt>
        <dd className="num">{bestPerformer ? bestPerformer.h.symbol : '—'}</dd>
        <dd className={`s ${bestPerformer && bestPerformer.pnlPct >= 0 ? 'pos' : 'neg'}`}>
          {bestPerformer ? pct(bestPerformer.pnlPct) : '—'}
        </dd>
      </div>
    </dl>

    <div className="cols">
      <section className="panel">
        <div className="panel-head" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <h3 style={{ margin: 0 }}>Holdings</h3>
            <span className="chip pass" style={{ fontSize: 11, padding: '2px 8px', fontWeight: 700, letterSpacing: '0.4px' }}>
              ● LIVE QUOTES
            </span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            {loading && (
              <span className="orbinline mut" style={{ fontSize: 12 }}>
                <ThinkingOrb state="working" size={20} theme={orb} /> Updating…
              </span>
            )}
            <button
              className="iconbtn sm"
              onClick={refresh}
              title="Refresh live quotes"
              aria-label="Refresh quotes"
              disabled={loading}
            >
              <ArrowsClockwise size={14} weight="bold" />
            </button>
          </div>
        </div>
        <div className="tablewrap">
          <table className="pf-table">
            <thead>
              <tr>
                <th>Stock</th>
                <th className="r">Shares</th>
                <th className="r">Avg buy</th>
                <th className="r">Live price</th>
                <th className="r">Value</th>
                <th className="r">P&amp;L</th>
                <th className="r">7-Day target</th>
                <th className="r">Stop-loss</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {rows.map(r => (
                <tr key={r.h.symbol} className="clickable" title={`Open full chart for ${r.h.symbol}`} onClick={() => onOpen(r.h.symbol)}>
                  <td>
                    <b>{r.h.symbol}</b>
                    <span className="chip exch sm">{r.h.exchange}</span>
                    <div className="rowname">{r.h.name}</div>
                  </td>
                  <td className="r" onClick={e => e.stopPropagation()}>
                    <input
                      className="sharein num"
                      type="number"
                      min="1"
                      aria-label={`Shares of ${r.h.symbol}`}
                      value={r.h.shares}
                      onChange={e => {
                        const v = Math.max(1, Math.floor(Number(e.target.value) || 1))
                        onEditShares(r.h.symbol, v)
                      }}
                    />
                  </td>
                  <td className="num r">{inr(r.h.buy)}</td>
                  <td className="num r">
                    <span style={{ fontWeight: 600 }}>{inr(r.currentPrice)}</span>
                    {r.isLive && (
                      <span className="chip pass sm" style={{ marginLeft: 5, fontSize: 10, padding: '1px 5px' }}>
                        LIVE
                      </span>
                    )}
                  </td>
                  <td className="num r" style={{ fontWeight: 600 }}>{inr(Math.round(r.value))}</td>
                  <td className={`num r ${r.pnl >= 0 ? 'pos' : 'neg'}`}>
                    {(r.pnl >= 0 ? '+' : '') + inr(Math.round(r.pnl))}
                    <div className="sub" style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 2 }}>
                      {r.pnl >= 0 ? <TrendUp size={11} weight="bold" /> : <TrendDown size={11} weight="bold" />}
                      {pct(r.pnlPct)}
                    </div>
                  </td>
                  <td className="num r acc">{inr(r.targetPrice)}</td>
                  <td className="num r neg">{inr(r.stopPrice)}</td>
                  <td className="r">
                    <button
                      className="iconbtn sm"
                      aria-label={`Remove ${r.h.symbol}`}
                      onClick={e => { e.stopPropagation(); onRemove(r.h.symbol) }}
                    >
                      <Trash size={14} weight="bold" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <aside className="side">
        <section className="panel side-sec">
          <h3><Briefcase size={16} weight="bold" /> Allocation</h3>
          <div className="allocbar">
            {rows.map((r, i) => (
              <i key={r.h.symbol} style={{ flexGrow: Math.max(1, r.value), background: SHADES[i % SHADES.length] }} title={`${r.h.symbol}: ${inr(Math.round(r.value))}`} />
            ))}
          </div>
          <ul className="alloclist">
            {rows.map((r, i) => {
              const w = value > 0 ? (r.value / value) * 100 : 0
              return (
                <li key={r.h.symbol}>
                  <i style={{ background: SHADES[i % SHADES.length] }} />
                  <b>{r.h.symbol}</b>
                  <span className="num">{w.toFixed(1)}%</span>
                </li>
              )
            })}
          </ul>
        </section>
        <section className="panel side-sec">
          <h3>How this works</h3>
          <p className="hint">
            Holdings live in this browser only. Current value and unrealised profit/loss update in real time from live exchange quotes. Predicted target and stop-loss come from the AI quantitative model.
          </p>
          {canAddAll && (
            <button className="btn wide" onClick={onAddAll}>
              <Plus size={15} weight="bold" /> Add this week's picks
            </button>
          )}
        </section>
      </aside>
    </div>
  </>)
}
