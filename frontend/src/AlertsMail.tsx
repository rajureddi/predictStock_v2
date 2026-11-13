import { useEffect, useMemo, useState } from 'react'
import { Bell, EnvelopeSimple, PaperPlaneTilt, TrendDown, TrendUp } from '@phosphor-icons/react'
import { Holding, inr, pct } from './lib'

type Rule = {
  id: string
  symbol?: string
  exchange?: string
  type?: string
  price?: number
  pct?: number
  entry_price?: number
  note?: string
  enabled?: boolean
  last?: number | null
  rung?: boolean
}

type Item = {
  id: string
  symbol: string
  exchange?: string
  label: string
  level: string
  last: number | null
  move: number | null
  hit: boolean
}

const STOP = new Set(['stop', 'below', 'reversal'])
const TARGET = new Set(['target', 'target2', 'above'])
const SELL = new Set(['massive_selling', 'pct_move'])

function moveOf(rule: Rule): number | null {
  if (rule.last == null || !rule.entry_price) return null
  const move = ((rule.last - rule.entry_price) / rule.entry_price) * 100
  return Math.abs(move) < 0.05 ? null : move
}

function hitOf(rule: Rule): boolean {
  if (rule.rung) return true
  if (rule.last == null) return false
  if (STOP.has(rule.type || '') && rule.price != null) return rule.last <= rule.price
  if (TARGET.has(rule.type || '') && rule.price != null) return rule.last >= rule.price
  if (SELL.has(rule.type || '')) {
    const move = moveOf(rule)
    return move != null && move <= -Math.abs(rule.pct || 2.5)
  }
  return false
}

function toItem(rule: Rule): Item {
  const label = STOP.has(rule.type || '') ? 'Stop loss'
    : TARGET.has(rule.type || '') ? (rule.type === 'target2' ? 'Target 2' : 'Target')
    : 'Heavy selling'
  const level = rule.price != null ? inr(rule.price) : rule.pct != null ? `${rule.pct}% from the scan price` : '—'
  return {
    id: rule.id,
    symbol: rule.symbol || '—',
    exchange: rule.exchange,
    label,
    level,
    last: rule.last ?? null,
    move: moveOf(rule),
    hit: hitOf(rule),
  }
}

function Board({ title, tone, empty, items }: { title: string; tone: 'down' | 'up'; empty: string; items: Item[] }) {
  return (
    <section className="panel alert-board">
      <div className="panel-head">
        <h3>
          {tone === 'down' ? <TrendDown size={16} weight="bold" /> : <TrendUp size={16} weight="bold" />}
          {title}
        </h3>
        <span className={`tag ${items.length ? (tone === 'down' ? 'neg' : 'pass') : ''}`}>{items.length}</span>
      </div>
      {items.length === 0 ? <p className="hint alert-empty">{empty}</p> : (
        <ul className="alert-list">
          {items.map(item => (
            <li key={item.id}>
              <div>
                <b>{item.symbol}</b>
                {item.exchange && item.exchange !== 'NSE' ? <span className="chip exch sm">{item.exchange}</span> : null}
                <div className="mut">{item.label} · {item.level}</div>
              </div>
              <div className="alert-px">
                <span className="num">{item.last != null ? inr(item.last) : '—'}</span>
                {item.move != null && <span className={item.move >= 0 ? 'pos' : 'neg'}>{pct(item.move)}</span>}
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

export default function AlertsMail({ holdings }: { holdings: Holding[] }) {
  const [rules, setRules] = useState<Rule[]>([])
  const [quotes, setQuotes] = useState<Record<string, number>>({})
  const [busy, setBusy] = useState('')
  const [note, setNote] = useState('')
  const [loaded, setLoaded] = useState(false)
  const [mail, setMail] = useState({ tos: [''], smtp_user: '', smtp_password: '', scan_start: '07:00', email_by: '09:15' })
  const [plan, setPlan] = useState<{ scan_start: string; email_by: string; alerts_until: string; now: string; today: { started?: boolean; emailed?: boolean; mail_error?: string | null } | null }>({
    scan_start: '07:00', email_by: '09:15', alerts_until: '16:00', now: '', today: null,
  })
  const [hasPassword, setHasPassword] = useState(false)

  const load = async () => {
    try {
      const [ar, mr, pr] = await Promise.all([fetch('/api/alerts'), fetch('/api/mail'), fetch('/api/morning')])
      if (!ar.ok || !mr.ok) throw new Error('alerts api')
      const [a, m, p] = await Promise.all([ar.json(), mr.json(), pr.ok ? pr.json() : null])
      const tos = String(m.to || '').split(/[\s,;]+/).map((s: string) => s.trim()).filter(Boolean)
      setRules(a?.rules || [])
      setMail({
        tos: tos.length ? tos : [''],
        smtp_user: m.smtp_user || '',
        smtp_password: '',
        scan_start: m.scan_start || '07:00',
        email_by: m.email_by || '09:15',
      })
      setHasPassword(!!m.has_password)
      if (p) setPlan({
        scan_start: p.scan_start || '07:00',
        email_by: p.email_by || '09:15',
        alerts_until: p.alerts_until || '16:00',
        now: p.now || '',
        today: p.today || null,
      })
    } catch {
      setNote('Alerts could not load.')
    } finally {
      setLoaded(true)
    }
  }

  useEffect(() => { load() }, [])

  useEffect(() => {
    const symbols = holdings.map(h => h.symbol).filter(Boolean)
    if (!symbols.length) return
    let stop = false
    const pull = async () => {
      try {
        const data = await fetch(`/api/live-quotes?symbols=${encodeURIComponent(symbols.join(','))}`).then(r => r.json())
        if (!stop && data?.quotes) setQuotes(data.quotes)
      } catch { /* keep the last prices */ }
    }
    pull()
    const t = setInterval(pull, 60000)
    return () => { stop = true; clearInterval(t) }
  }, [holdings])

  const check = async () => {
    setBusy('check')
    try {
      const data = await fetch('/api/alerts/check', { method: 'POST' }).then(r => r.json())
      setRules(data?.rules || [])
      const n = data?.rings?.length || 0
      setNote(n ? `${n} new alert${n === 1 ? '' : 's'}.` : 'Nothing new hit.')
    } catch {
      setNote('Check failed.')
    } finally { setBusy('') }
  }

  useEffect(() => {
    const t = setInterval(() => {
      fetch('/api/alerts/check', { method: 'POST' }).then(r => r.json()).then(data => {
        if (data?.rules) setRules(data.rules)
      }).catch(() => {})
    }, 60000)
    return () => clearInterval(t)
  }, [])

  const sync = async () => {
    setBusy('sync')
    try {
      const data = await fetch('/api/alerts/sync', { method: 'POST' }).then(r => r.json())
      setRules(data?.rules || [])
      setNote('Watching this week’s picks.')
    } catch {
      setNote('Could not read this week’s picks.')
    } finally { setBusy('') }
  }

  const mailBody = () => ({
    to: mail.tos.map(s => s.trim()).filter(Boolean).join('\n'),
    smtp_user: mail.smtp_user,
    smtp_password: mail.smtp_password,
    smtp_host: 'smtp.gmail.com',
    smtp_port: 587,
    from_addr: mail.smtp_user,
    scan_start: mail.scan_start,
    email_by: mail.email_by,
  })

  const saveMail = async () => {
    setBusy('mail')
    try {
      const saved = await fetch('/api/mail', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(mailBody()),
      }).then(r => r.json())
      if (saved.error) { setNote(saved.error); return }
      setHasPassword(!!saved.has_password)
      const tos = (saved.recipients && saved.recipients.length ? saved.recipients : ['']) as string[]
      setMail(s => ({ ...s, tos, smtp_password: '', scan_start: saved.scan_start || s.scan_start, email_by: saved.email_by || s.email_by }))
      setPlan(p => ({ ...p, scan_start: saved.scan_start || p.scan_start, email_by: saved.email_by || p.email_by }))
      setNote('Schedule and mail settings saved. The auto scan and alert emails use these times.')
    } catch {
      setNote('Could not save mail settings.')
    } finally { setBusy('') }
  }

  const send = async (test: boolean) => {
    setBusy(test ? 'test' : 'send')
    try {
      const saved = await fetch('/api/mail', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(mailBody()),
      }).then(r => r.json())
      if (saved.error) { setNote(saved.error); return }
      setHasPassword(!!saved.has_password)
      setMail(s => ({ ...s, smtp_password: '' }))
      const res = await fetch(`/api/mail/send?test=${test ? 'true' : 'false'}`, { method: 'POST' }).then(r => r.json())
      setNote(res.ok ? `Sent to ${res.to}.` : (res.error || 'Send failed.'))
    } catch {
      setNote('Send failed.')
    } finally { setBusy('') }
  }

  const stockRules = rules.filter(r => r.type !== 'cutoff' && r.symbol && r.symbol !== 'MARKET')
  const stops = stockRules.filter(r => STOP.has(r.type || '')).map(toItem).filter(i => i.hit)
  const targets = stockRules.filter(r => TARGET.has(r.type || '')).map(toItem).filter(i => i.hit)
  const selling = stockRules.filter(r => SELL.has(r.type || '')).map(toItem).filter(i => i.hit)
  const watching = [...stockRules.reduce((map, rule) => {
    const symbol = rule.symbol || ''
    const row = map.get(symbol) || { symbol, exchange: rule.exchange, last: null as number | null, entry: null as number | null, stop: null as number | null, target: null as number | null }
    if (rule.last != null) row.last = rule.last
    if (rule.entry_price) row.entry = rule.entry_price
    if (rule.type === 'stop' && rule.price != null) row.stop = rule.price
    if (rule.type === 'target' && rule.price != null) row.target = rule.price
    map.set(symbol, row)
    return map
  }, new Map<string, { symbol: string; exchange?: string; last: number | null; entry: number | null; stop: number | null; target: number | null }>()).values()]

  const rising = useMemo(() => holdings.map(h => {
    const last = quotes[h.symbol]
    const move = last && h.buy ? ((last - h.buy) / h.buy) * 100 : null
    return { h, last: last ?? null, move }
  }).filter(row => row.move != null && row.move > 0), [holdings, quotes])

  return (
    <div className="alert-page">
      <section className="panel schedule-panel">
        <div className="panel-head">
          <h3><Bell size={16} weight="bold" /> Automatic times</h3>
        </div>
        <p className="hint schedule-note">
          Scan starts at <b>{plan.scan_start} IST</b>. The report goes out by <b>{plan.email_by} IST</b>, once each weekday.
          Alerts email from <b>{plan.email_by}</b> to <b>{plan.alerts_until} IST</b>.
          {plan.now ? ` Now ${plan.now}.` : ''}
          {plan.today?.emailed
            ? ' Today’s report was already sent. Changing the time does not send a second copy. Check the inbox and spam for “MarketMind Pro — predictions”.'
            : plan.today?.mail_error
              ? ` Today’s send failed: ${plan.today.mail_error}`
              : plan.today?.started
                ? ' Today’s scan is underway. The mail leaves when it finishes.'
                : ' Today’s automatic scan has not started yet.'}
        </p>
        <div className="schedule-card">
          <label>Auto scan starts
            <input type="time" value={mail.scan_start} onChange={e => setMail(s => ({ ...s, scan_start: e.target.value }))} />
          </label>
          <label>Email report by
            <input type="time" value={mail.email_by} onChange={e => setMail(s => ({ ...s, email_by: e.target.value }))} />
          </label>
          <button className="btn dark" onClick={saveMail} disabled={!!busy || !loaded}>Save times</button>
        </div>
      </section>
      {!loaded ? <p className="hint">Loading alerts…</p> : (
        <>
          <div className="alert-grid">
            <Board title="Stop loss hit" tone="down" empty="No predicted stock is at its stop." items={stops} />
            <Board title="Target hit" tone="up" empty="No predicted stock has reached its target." items={targets} />
            <Board title="Heavy selling" tone="down" empty="No predicted stock is down 2.5% from the scan price." items={selling} />
            <section className="panel alert-board">
              <div className="panel-head">
                <h3><TrendUp size={16} weight="bold" /> Portfolio rising</h3>
                <span className={`tag ${rising.length ? 'pass' : ''}`}>{rising.length}</span>
              </div>
              {holdings.length === 0 ? <p className="hint alert-empty">Add stocks from This Week’s Picks. A holding shows here when the latest close is above your buy price.</p>
                : rising.length === 0 ? <p className="hint alert-empty">None of your holdings are above the buy price.</p>
                : (
                  <ul className="alert-list">
                    {rising.map(({ h, last, move }) => (
                      <li key={h.symbol}>
                        <div>
                          <b>{h.symbol}</b>
                          {h.exchange && h.exchange !== 'NSE' ? <span className="chip exch sm">{h.exchange}</span> : null}
                          <div className="mut">Buy {inr(h.buy)}</div>
                        </div>
                        <div className="alert-px">
                          <span className="num">{last != null ? inr(last) : '—'}</span>
                          <span className="pos">{pct(move)}</span>
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
            </section>
          </div>

          <section className="panel">
            <div className="panel-head">
              <h3><Bell size={16} weight="bold" /> Still watching</h3>
              <div className="alert-toolbar">
                <button className="btn dark" onClick={sync} disabled={!!busy}>Use this week’s picks</button>
                <button className="btn" onClick={check} disabled={!!busy}>Check prices</button>
                {note && <span className="mut">{note}</span>}
              </div>
            </div>
            {watching.length === 0 ? <p className="hint alert-empty">Use this week’s picks to watch each stop, target, and 2.5% drop.</p> : (
              <div className="tablewrap"><table>
                <thead><tr><th>Stock</th><th>Last</th><th>Stop</th><th>Target</th><th>From scan</th></tr></thead>
                <tbody>
                  {watching.map(row => {
                    const move = row.last != null && row.entry ? ((row.last - row.entry) / row.entry) * 100 : null
                    const flat = move == null || Math.abs(move) < 0.05
                    return (
                      <tr key={row.symbol}>
                        <td><b>{row.symbol}</b>{row.exchange && row.exchange !== 'NSE' ? <span className="chip exch sm">{row.exchange}</span> : null}</td>
                        <td className="num">{row.last != null ? inr(row.last) : '—'}</td>
                        <td className="num">{row.stop != null ? inr(row.stop) : '—'}</td>
                        <td className="num">{row.target != null ? inr(row.target) : '—'}</td>
                        <td className={flat ? 'mut' : move! >= 0 ? 'pos' : 'neg'}>{flat ? 'Unchanged' : pct(move)}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table></div>
            )}
          </section>
        </>
      )}

      <section className="panel pf-fields mail-setup">
        <div className="panel-head">
          <h3><EnvelopeSimple size={16} weight="bold" /> Email before the open</h3>
        </div>
        <div className="mail-copy">
          <p>The scan starts at the time above and the report is emailed by the second time. A full scan takes 30–60 minutes. Nobody has to press Scan. Saturday and Sunday stay quiet.</p>
          <p>Stops, targets, heavy selling, and the 15:20 review email every address when they hit, from the email-by time until 16:00 IST. The same hit is marked on this page. Leave this app running. The computer has to be on.</p>
          <p>Gmail is already set to <span className="num">smtp.gmail.com</span> port <span className="num">587</span>. Add one row for each inbox.</p>
        </div>
        <div className="mail-recipients">
          {mail.tos.map((addr, i) => (
            <label key={i}>Send to {mail.tos.length > 1 ? i + 1 : ''}
              <span className="mail-recipient">
                <input value={addr} placeholder="name@gmail.com" onChange={e => setMail(s => ({ ...s, tos: s.tos.map((v, j) => j === i ? e.target.value : v) }))} />
                {mail.tos.length > 1 && <button type="button" className="btn ghost sm" onClick={() => setMail(s => ({ ...s, tos: s.tos.filter((_, j) => j !== i) }))}>Remove</button>}
              </span>
            </label>
          ))}
          <button type="button" className="btn" onClick={() => setMail(s => ({ ...s, tos: [...s.tos, ''] }))}>Add another email</button>
        </div>
        <div className="mail-fields">
          <label>Gmail address
            <input value={mail.smtp_user} placeholder="you@gmail.com" onChange={e => setMail(s => ({ ...s, smtp_user: e.target.value }))} />
          </label>
          <label>App password
            <input type="password" value={mail.smtp_password} placeholder={hasPassword ? 'Saved. Type a new one to replace it.' : '16-letter app password'} onChange={e => setMail(s => ({ ...s, smtp_password: e.target.value }))} />
          </label>
        </div>
        <div className="alert-toolbar">
          <button className="btn" onClick={saveMail} disabled={!!busy || !loaded}>Save</button>
          <button className="btn" onClick={() => send(true)} disabled={!!busy || !loaded}>Send test</button>
          <button className="btn dark" onClick={() => send(false)} disabled={!!busy || !loaded}><PaperPlaneTilt size={14} weight="bold" /> Email this week’s picks</button>
        </div>
      </section>
    </div>
  )
}
