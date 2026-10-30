import { useEffect, useState } from 'react'
import { ThinkingOrb } from 'thinking-orbs'
import { Briefcase, Plus, Trash } from '@phosphor-icons/react'
import { C, Holding, fetchSeries, inr, pct, useOrb } from './lib'

const shades = () => [C.ink, C.accent, C.mut, '#C2410C', C.faint, '#7C8189', '#FFA36E', '#4A4E56']

function useLastPrices(holdings: Holding[]) {
  const [px, setPx] = useState<Record<string, { close: number; date: string } | null>>({})
  const key = holdings.map(h => h.exchange + ':' + h.symbol).join('|')
  useEffect(() => {
    let on = true
    holdings.forEach(h => fetchSeries(h.symbol, h.exchange).then(s => {
      if (!on) return
      const last = s[s.length - 1]
      setPx(m => ({ ...m, [h.symbol]: last ? { close: last.close, date: last.date } : null }))
    }))
    return () => { on = false }
  }, [key])
  return px
}

export default function Portfolio({ holdings, picks, onOpen, onRemove, onAddAll, onEditShares }: {
  holdings: Holding[]; picks: any[]
  onOpen: (symbol: string) => void; onRemove: (symbol: string) => void
  onAddAll: () => void; onEditShares: (symbol: string, shares: number) => void
}) {
  const px = useLastPrices(holdings)
  const orb = useOrb()
  const SHADES = shades()
  const canAddAll = picks.some(p => p.shares > 0)
  const rows = holdings.map(h => {
    const last = px[h.symbol]?.close ?? null
    const cost = h.shares * h.buy
    const value = last == null ? null : h.shares * last
    const pnl = value == null ? null : value - cost
    const proj = h.predicted == null ? null : h.shares * h.predicted
    return { h, last, cost, value, pnl, pnlPct: pnl == null ? null : (pnl / cost) * 100, proj, inPicks: picks.some(p => p.symbol === h.symbol) }
  })
  const invested = rows.reduce((s, r) => s + r.cost, 0)
  const priced = rows.filter(r => r.value != null)
  const value = priced.length ? rows.reduce((s, r) => s + (r.value ?? r.cost), 0) : null
  const pnl = value == null ? null : value - invested
  const projected = rows.reduce((s, r) => s + (r.proj ?? r.value ?? r.cost), 0)
  const loading = holdings.length > 0 && priced.length < holdings.filter(h => px[h.symbol] !== null).length

  if (!holdings.length) return <section className="panel emptystate">
    <ThinkingOrb state="breathing" size={64} theme={orb} />
    <h4>Your portfolio is empty</h4>
    <p>Open any pick and press <b>Add to portfolio</b>, or add this week's picks using the share counts from your saved budget. Holdings are kept in this browser only.</p>
    {canAddAll && <button className="btn dark" onClick={onAddAll}><Plus size={15} weight="bold" /> Add this week's picks</button>}
  </section>

  return (<>
    <dl className="kpis panel">
      <div><dt>Invested</dt><dd className="num">{inr(Math.round(invested))}</dd><dd className="s">{holdings.length} {holdings.length === 1 ? 'holding' : 'holdings'}</dd></div>
      <div><dt>Current value</dt><dd className="num">{value == null ? '—' : inr(Math.round(value))}</dd><dd className="s">Last official close</dd></div>
      <div><dt>Unrealised P&amp;L</dt><dd className={`num ${(pnl ?? 0) >= 0 ? 'pos' : 'neg'}`}>{pnl == null ? '—' : (pnl >= 0 ? '+' : '') + inr(Math.round(pnl))}</dd><dd className="s">{pnl == null ? '—' : pct((pnl / invested) * 100)}</dd></div>
      <div><dt>Projected at prediction</dt><dd className="num">{inr(Math.round(projected))}</dd><dd className="s">{pct(((projected / invested) - 1) * 100)} vs cost</dd></div>
      <div><dt>Best performer</dt><dd className="num">{priced.length ? [...priced].sort((a, b) => b.pnlPct! - a.pnlPct!)[0].h.symbol : '—'}</dd><dd className="s">{priced.length ? pct([...priced].sort((a, b) => b.pnlPct! - a.pnlPct!)[0].pnlPct) : '—'}</dd></div>
    </dl>

    <div className="cols">
      <section className="panel">
        <div className="panel-head">
          <h3>Holdings</h3>
          {loading && <span className="orbinline mut"><ThinkingOrb state="working" size={20} theme={orb} />Fetching prices…</span>}
        </div>
        <div className="tablewrap"><table className="pf-table"><thead><tr>
          <th>Stock</th><th className="r">Shares</th><th className="r">Avg buy</th><th className="r">Last price</th>
          <th className="r">Value</th><th className="r">P&amp;L</th><th className="r">Predicted</th><th className="r">Stop</th><th />
        </tr></thead><tbody>{rows.map(r => <tr key={r.h.symbol} className={r.inPicks ? 'clickable' : ''} onClick={() => r.inPicks && onOpen(r.h.symbol)}>
          <td><b>{r.h.symbol}</b><span className="chip exch sm">{r.h.exchange}</span><div className="rowname">{r.h.name}</div></td>
          <td className="r" onClick={e => e.stopPropagation()}>
            <input className="sharein num" type="number" min="1" aria-label={`Shares of ${r.h.symbol}`} value={r.h.shares}
              onChange={e => { const v = Math.max(1, Math.floor(Number(e.target.value) || 1)); onEditShares(r.h.symbol, v) }} />
          </td>
          <td className="num r">{inr(r.h.buy)}</td>
          <td className="num r">{r.last == null ? (px[r.h.symbol] === null ? 'n/a' : '…') : inr(r.last)}</td>
          <td className="num r">{r.value == null ? '—' : inr(Math.round(r.value))}</td>
          <td className={`num r ${(r.pnl ?? 0) >= 0 ? 'pos' : 'neg'}`}>{r.pnl == null ? '—' : <>{(r.pnl >= 0 ? '+' : '') + inr(Math.round(r.pnl))}<div className="sub">{pct(r.pnlPct)}</div></>}</td>
          <td className="num r acc">{inr(r.h.predicted)}</td>
          <td className="num r neg">{inr(r.h.stop)}</td>
          <td className="r"><button className="iconbtn sm" aria-label={`Remove ${r.h.symbol}`} onClick={e => { e.stopPropagation(); onRemove(r.h.symbol) }}><Trash size={14} weight="bold" /></button></td>
        </tr>)}</tbody></table></div>
      </section>

      <aside className="side">
        <section className="panel side-sec">
          <h3><Briefcase size={16} weight="bold" /> Allocation</h3>
          <div className="allocbar">{rows.map((r, i) => <i key={r.h.symbol} style={{ flexGrow: r.value ?? r.cost, background: SHADES[i % SHADES.length] }} title={r.h.symbol} />)}</div>
          <ul className="alloclist">{rows.map((r, i) => {
            const w = ((r.value ?? r.cost) / (value ?? invested)) * 100
            return <li key={r.h.symbol}><i style={{ background: SHADES[i % SHADES.length] }} /><b>{r.h.symbol}</b><span className="num">{w.toFixed(1)}%</span></li>
          })}</ul>
        </section>
        <section className="panel side-sec">
          <h3>How this works</h3>
          <p className="hint">Holdings live in this browser only. Last price is the latest official close from the exchange data; predicted and stop-loss come from the week the stock was added. Click a holding from this week's picks to open its full analysis.</p>
          {canAddAll && <button className="btn wide" onClick={onAddAll}><Plus size={15} weight="bold" /> Add this week's picks</button>}
        </section>
      </aside>
    </div>
  </>)
}
