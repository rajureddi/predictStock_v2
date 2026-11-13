import { useState, useEffect } from 'react'
import { ThinkingOrb } from 'thinking-orbs'
import {
  Brain, Briefcase, CaretRight, Check, CheckCircle, Cpu, Gear, Globe, Key,
  Lightning, MagnifyingGlass, ShieldCheck, Sparkle, TrendDown, TrendUp, Warning, X, XCircle, ArrowRight
} from '@phosphor-icons/react'
import { C, Holding, inr, num, pct, ScoreRing, useOrb } from './lib'

export type Candidate = {
  symbol: string
  name: string
  exchange: string
  source: string
  predicted_return_pct?: number
  predicted_price?: number
  current_price?: number
  trader_score?: number
  has_report?: boolean
  final_decision?: string
  conviction_score?: number
  target1?: number
  stop_loss?: number
}

export type TradeReport = {
  symbol: string
  name: string
  exchange: string
  yahoo_symbol: string
  timestamp: string
  analysis_time_seconds: number
  ai_engine_used?: string
  final_decision: string
  conviction_score: number
  entry_price: number
  target1: number
  target2: number
  stop_loss: number
  risk_reward: string
  max_allocation_pct: number
  agents: {
    fundamentals: any
    technicals: any
    sentiment: any
    bull_researcher: any
    bear_researcher: any
    risk_officer: any
    fund_manager: any
  }
  debate_transcript: Array<{
    speaker: string
    avatar: 'bull' | 'bear'
    round: string
    argument: string
  }>
  executive_memo: string
}

function OfflineScreen({ onOpenChart }: { onOpenChart: (symbol: string, exchange: string, name: string, price?: number) => void }) {
  const orb = useOrb()
  const [data, setData] = useState<any>(null)
  const [status, setStatus] = useState<any>(null)
  const [showAll, setShowAll] = useState(false)

  const load = () => fetch('/api/trade-analyser/offline').then(r => r.json()).then(setData).catch(() => {})
  useEffect(() => { load() }, [])
  useEffect(() => {
    const id = setInterval(() => {
      fetch('/api/trade-analyser/offline/status').then(r => r.json()).then(s => {
        setStatus(s)
        if (s?.running) load()
        else if (s && !s.running && s.progress_pct === 100) load()
      }).catch(() => {})
    }, 1500)
    return () => clearInterval(id)
  }, [])

  const start = async () => {
    await fetch('/api/trade-analyser/offline', { method: 'POST' })
    setStatus(await (await fetch('/api/trade-analyser/offline/status')).json())
  }

  const running = !!status?.running
  const rows = showAll ? (data?.all || []) : (data?.picks || [])
  const c = data?.counts || {}
  const color = (o: string) => o?.includes('BUY') ? 'var(--up)' : o?.includes('ACCUMULATE') ? 'var(--info)' : o?.includes('HOLD') ? 'var(--amber)' : 'var(--down)'

  return (
    <div>
      <section className="panel" style={{ padding: 20, marginBottom: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap' }}>
          <div>
            <h3 style={{ margin: '0 0 6px' }}>Offline committee screen</h3>
            <p className="hint" style={{ margin: 0, maxWidth: 640 }}>
              Same scoring bands as TradeAnalyser (fundamentals 40%, technicals 35%, news 15%, bear skepticism 10%).
              Uses local prices and the fundamentals cache only — no Groq, no API key. Does not change the weekly prediction engine.
              Universe is this week's liquid top 50 plus the Multibagger list.
            </p>
            {data?.run_date && <div className="note" style={{ marginTop: 10 }}>Last run {data.run_date} · scanned {c.scanned ?? '—'} · Strong Buy {c.strong_buy ?? 0} · Accumulate {c.accumulate ?? 0} · Watch {c.watch ?? 0} · Reject {c.reject ?? 0}</div>}
          </div>
          <button className="btn dark" disabled={running} onClick={start}>
            {running ? <><ThinkingOrb state="working" size={20} theme={orb} /> Scoring {status?.current_symbol || ''} ({status?.progress_pct ?? 0}%)</> : 'Run offline screen'}
          </button>
        </div>
      </section>
      <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
        <button className={`btn ${!showAll ? 'dark' : 'ghost'} sm`} onClick={() => setShowAll(false)}>Buy / Accumulate ({data?.picks?.length ?? 0})</button>
        <button className={`btn ${showAll ? 'dark' : 'ghost'} sm`} onClick={() => setShowAll(true)}>All scored ({data?.all?.length ?? 0})</button>
      </div>
      {!rows.length && !running ? <section className="panel emptystate" style={{ padding: 40, textAlign: 'center' }}>
        <p>No offline results yet. Press Run offline screen.</p>
      </section> : (
        <section className="panel tablewrap">
          <table>
            <thead><tr>
              <th>#</th><th>Stock</th><th>Order</th><th>Conviction</th><th>Fund</th><th>Tech</th><th>Entry</th><th>Target 1</th><th>Stop</th><th>R:R</th>
            </tr></thead>
            <tbody>
              {rows.map((r: any, i: number) => (
                <tr key={r.symbol} className="clickable" onClick={() => onOpenChart(r.symbol, r.exchange, r.name, r.entry)}>
                  <td className="num">{i + 1}</td>
                  <td><b>{r.symbol}</b><div className="rowname">{r.name}</div></td>
                  <td style={{ fontWeight: 700, color: color(r.final_order) }}>{r.final_order}</td>
                  <td className="num">{r.conviction_score}</td>
                  <td className="num">{r.fund_score}</td>
                  <td className="num">{r.tech_score}</td>
                  <td className="num">{inr(r.entry)}</td>
                  <td className="num pos">{inr(r.target1)}</td>
                  <td className="num neg">{inr(r.stop_loss)}</td>
                  <td className="num">{r.risk_reward}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
    </div>
  )
}

export default function TradeAnalyser({
  onOpenStock,
  onOpenChart,
  onSaveHolding,
  holdings
}: {
  onOpenStock: (symbol: string, exchange: string, name: string) => void
  onOpenChart: (symbol: string, exchange: string, name: string, price?: number) => void
  onSaveHolding: (p: any, shares: number, buy: number) => void
  holdings: Holding[]
}) {
  const orb = useOrb()
  const [candidates, setCandidates] = useState<Candidate[]>([])
  const [loadingCandidates, setLoadingCandidates] = useState(true)
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null)
  const [currentReport, setCurrentReport] = useState<TradeReport | null>(null)
  const [analyzingSymbol, setAnalyzingSymbol] = useState<string | null>(null)
  const [reportError, setReportError] = useState<string | null>(null)
  const [retryTick, setRetryTick] = useState(0)
  const [batchStatus, setBatchStatus] = useState<any>(null)
  const [customSearch, setCustomSearch] = useState('')
  const [activeTab, setActiveTab] = useState<'debate' | 'analysts' | 'risk' | 'memo'>('debate')
  const [deskTab, setDeskTab] = useState<'ai' | 'offline'>('ai')

  // AI Configuration State
  const [showAiModal, setShowAiModal] = useState(false)
  const [aiConfig, setAiConfig] = useState<{
    enabled: boolean
    provider: 'gemini' | 'groq' | 'openai' | 'xai' | 'custom'
    api_key: string
    base_url: string
    model: string
    has_key?: boolean
    masked_key?: string
    defaults?: Record<string, any>
  }>({
    enabled: false,
    provider: 'xai',
    api_key: '',
    base_url: 'https://api.x.ai/v1',
    model: 'grok-4.7'
  })
  const [testingAi, setTestingAi] = useState(false)
  const [testResult, setTestResult] = useState<{ success?: boolean; message?: string; error?: string } | null>(null)
  const [savingAi, setSavingAi] = useState(false)

  // Load AI configuration
  const loadAiConfig = async () => {
    try {
      const res = await fetch('/api/trade-analyser/ai-config')
      const data = await res.json()
      if (data) setAiConfig(data)
    } catch {}
  }

  useEffect(() => {
    loadAiConfig()
  }, [])

  // Load candidates
  const loadCandidates = async () => {
    try {
      setLoadingCandidates(true)
      const res = await fetch('/api/trade-analyser/candidates')
      const data = await res.json()
      if (data?.candidates) {
        setCandidates(data.candidates)
        if (!selectedSymbol && data.candidates.length > 0) {
          setSelectedSymbol(data.candidates[0].symbol)
        }
      }
    } catch (e) {
      console.error('Failed to load candidates:', e)
    } finally {
      setLoadingCandidates(false)
    }
  }

  useEffect(() => {
    loadCandidates()
  }, [])

  // Load report when selectedSymbol changes
  useEffect(() => {
    if (!selectedSymbol) return
    let active = true
    const fetchReport = async () => {
      setCurrentReport(prev => (prev?.symbol === selectedSymbol ? prev : null))
      setReportError(null)
      setAnalyzingSymbol(selectedSymbol)
      try {
        const res = await fetch(`/api/trade-analyser/report?symbol=${encodeURIComponent(selectedSymbol)}`)
        const data = await res.json().catch(() => null)
        if (!active) return
        if (res.ok && data?.symbol) {
          setCurrentReport(data)
        } else {
          if (data?.needs_ai) setShowAiModal(true)
          setReportError(data?.error || `Analysis failed (status ${res.status}).`)
        }
      } catch (e) {
        if (active) setReportError('Could not reach the analysis server.')
      } finally {
        if (active) setAnalyzingSymbol(null)
      }
    }
    fetchReport()
    return () => { active = false }
  }, [selectedSymbol, retryTick])

  // Poll batch status
  useEffect(() => {
    let intv: any = null
    const checkStatus = async () => {
      try {
        const res = await fetch('/api/trade-analyser/status')
        const data = await res.json()
        setBatchStatus(data)
        if (data?.running) {
          loadCandidates()
        }
      } catch {}
    }
    checkStatus()
    intv = setInterval(checkStatus, 3000)
    return () => clearInterval(intv)
  }, [])

  const startBatch = async () => {
    if (!aiConfig.enabled || !aiConfig.has_key) {
      setShowAiModal(true)
      return
    }
    try {
      await fetch('/api/trade-analyser/batch', { method: 'POST' })
      const res = await fetch('/api/trade-analyser/status')
      setBatchStatus(await res.json())
    } catch {}
  }

  const triggerAnalyze = async (sym: string, ex: string = 'NSE', nm?: string) => {
    if (!aiConfig.enabled || !aiConfig.has_key) {
      setShowAiModal(true)
      return
    }
    try {
      setAnalyzingSymbol(sym)
      const res = await fetch('/api/trade-analyser/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symbol: sym, exchange: ex, name: nm })
      })
      if (res.ok) {
        const data = await res.json()
        if (data?.symbol) {
          setCurrentReport(data)
          setSelectedSymbol(data.symbol)
          loadCandidates()
        }
      } else {
        const txt = await res.text()
        try {
          const err = JSON.parse(txt)
          if (err.needs_ai) {
            setShowAiModal(true)
          }
        } catch {}
        console.error('Analysis returned error:', txt)
      }
    } catch (e) {
      console.error('Analysis failed:', e)
    } finally {
      setAnalyzingSymbol(null)
    }
  }

  const handleCustomSearch = (e: React.FormEvent) => {
    e.preventDefault()
    const q = customSearch.trim().toUpperCase()
    if (!q) return
    triggerAnalyze(q, 'NSE')
    setCustomSearch('')
  }

  const switchProvider = (prov: 'gemini' | 'groq' | 'openai' | 'xai' | 'custom') => {
    const defaults = aiConfig.defaults?.[prov]
    setAiConfig(prev => ({
      ...prev,
      provider: prov,
      base_url: defaults?.base_url || prev.base_url,
      model: defaults?.model || prev.model
    }))
    setTestResult(null)
  }

  const handleTestAi = async () => {
    setTestingAi(true)
    setTestResult(null)
    try {
      const res = await fetch('/api/trade-analyser/test-ai', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          provider: aiConfig.provider,
          api_key: aiConfig.api_key,
          base_url: aiConfig.base_url,
          model: aiConfig.model
        })
      })
      if (!res.ok) {
        const txt = await res.text()
        try {
          const jsonErr = JSON.parse(txt)
          setTestResult({ success: false, error: jsonErr.error || jsonErr.detail || `Server error (${res.status})` })
        } catch {
          setTestResult({ success: false, error: `Server error (${res.status}): ${txt.slice(0, 120)}` })
        }
        return
      }
      const data = await res.json()
      setTestResult(data)
    } catch (e: any) {
      setTestResult({ success: false, error: e.message || 'Network error' })
    } finally {
      setTestingAi(false)
    }
  }

  const handleSaveAi = async () => {
    setSavingAi(true)
    try {
      const res = await fetch('/api/trade-analyser/ai-config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(aiConfig)
      })
      if (res.ok) {
        const data = await res.json()
        if (data) setAiConfig(data)
        setShowAiModal(false)
      } else {
        const txt = await res.text()
        console.error('Failed to save AI config:', txt)
      }
    } catch (e) {
      console.error('Failed to save AI config:', e)
    } finally {
      setSavingAi(false)
    }
  }

  const isBatchRunning = batchStatus?.running

  return (
    <div className="trade-analyser-desk" style={{ maxWidth: 1200, margin: '0 auto', paddingBottom: 60 }}>
      <div className="ta-tabs" style={{ display: 'flex', gap: 10, marginBottom: 16 }}>
        <button className={`btn ${deskTab === 'ai' ? 'dark' : 'ghost'} sm`} onClick={() => setDeskTab('ai')}>AI Committee</button>
        <button className={`btn ${deskTab === 'offline' ? 'dark' : 'ghost'} sm`} onClick={() => setDeskTab('offline')}>Offline Screen (test)</button>
      </div>
      {deskTab === 'offline' && <OfflineScreen onOpenChart={onOpenChart} />}
      {deskTab === 'ai' && <>
      {/* Header Banner */}
      <section className="panel" style={{ padding: '26px 30px', marginBottom: 20 }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: 18 }}>
          <div style={{ maxWidth: 760 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10, flexWrap: 'wrap' }}>
              <span className="chip pass" style={{ fontSize: 11, fontWeight: 700, padding: '3px 9px', letterSpacing: '0.4px' }}>
                <Brain size={14} weight="fill" /> TRADINGAGENTS FRAMEWORK
              </span>
              <span className="chip" style={{ fontSize: 11, background: 'rgba(255,94,26,0.1)', color: 'var(--accent)', fontWeight: 600 }}>
                UCLA / MIT Multi-Agent Architecture
              </span>
              {aiConfig.enabled && aiConfig.has_key ? (
                <span className="chip" style={{ fontSize: 11, background: 'rgba(255,94,26,0.12)', color: 'var(--info)', fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                  <Cpu size={12} weight="bold" /> 100% LLM Active: {aiConfig.provider.toUpperCase()} ({aiConfig.model})
                  <button
                    onClick={() => { setShowAiModal(true); setTestResult(null) }}
                    style={{
                      background: 'transparent',
                      border: 'none',
                      color: 'var(--accent)',
                      cursor: 'pointer',
                      padding: '0 2px',
                      fontSize: 11,
                      fontWeight: 700,
                      textDecoration: 'underline'
                    }}
                  >
                    Edit
                  </button>
                </span>
              ) : (
                <span className="chip" style={{ fontSize: 11, background: 'rgba(255,94,26,0.12)', color: 'var(--amber)', fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                  <Cpu size={12} weight="bold" /> AI Key Required (No Offline Fallback)
                  <button
                    onClick={() => { setShowAiModal(true); setTestResult(null) }}
                    style={{
                      background: 'transparent',
                      border: 'none',
                      color: 'var(--accent)',
                      cursor: 'pointer',
                      padding: '0 2px',
                      fontSize: 11,
                      fontWeight: 700,
                      textDecoration: 'underline'
                    }}
                  >
                    Configure
                  </button>
                </span>
              )}
            </div>
            <h2 style={{ margin: '0 0 10px', fontSize: 25, fontWeight: 600, letterSpacing: '-0.025em' }}>
              TradeAnalyser Institutional Committee
            </h2>
            <p style={{ margin: 0, color: 'var(--mut)', fontSize: 13.5, lineHeight: 1.6 }}>
              Instead of relying on a single prediction model, TradeAnalyser simulates a complete institutional investment firm:
              <b> Fundamentals Analyst</b>, <b>Technical Analyst</b>, and <b>News Analyst</b> gather parallel intelligence, which is then
              tested through a live <b>Bull vs. Bear Researcher Debate</b>, audited by the <b>Chief Risk Officer</b>, and signed off by the <b>Fund Manager</b>.
            </p>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 10 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              {/* Configure AI Engine Button */}
              <button
                className="btn ghost sm"
                onClick={() => { setShowAiModal(true); setTestResult(null) }}
                style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '8px 14px', fontSize: 12.5 }}
              >
                <Gear size={15} weight="bold" />
                <span>AI Providers &amp; Custom API</span>
              </button>

              <button
                className="btn dark sm"
                disabled={isBatchRunning}
                onClick={startBatch}
                style={{ display: 'inline-flex', alignItems: 'center', gap: 7, padding: '9px 16px', fontSize: 13, fontWeight: 600 }}
              >
                {isBatchRunning ? (
                  <>
                    <ThinkingOrb state="working" size={20} theme={orb} />
                    <span>Deliberating ({batchStatus?.progress_pct ?? 0}%)</span>
                  </>
                ) : (
                  <>
                    <Lightning size={15} weight="fill" />
                    <span>Deliberate All Top 10</span>
                  </>
                )}
              </button>
            </div>

            {/* Custom stock ticker search */}
            <form onSubmit={handleCustomSearch} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <input
                type="text"
                placeholder="Analyze any NSE/BSE symbol..."
                value={customSearch}
                onChange={e => setCustomSearch(e.target.value)}
                style={{
                  padding: '7px 12px',
                  borderRadius: 'var(--r-sm)',
                  border: '1px solid var(--line)',
                  background: 'var(--surface)',
                  color: 'var(--ink)',
                  fontSize: 12.5,
                  width: 210,
                  outline: 'none'
                }}
              />
              <button type="submit" className="btn ghost sm" style={{ padding: '7px 12px' }}>
                <MagnifyingGlass size={13} weight="bold" />
              </button>
            </form>
          </div>
        </div>
      </section>

      {/* Top 10 Candidate Selector Ribbon */}
      <div style={{ marginBottom: 20 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
          <span style={{ fontSize: 12.5, fontWeight: 600, color: 'var(--mut)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            Committee Candidates
          </span>
          <span style={{ fontSize: 12, color: 'var(--mut)' }}>
            Select a stock to review the multi-agent committee findings
          </span>
        </div>

        {[
          { key: 'weekly', title: "This Week's ML Picks", match: (s: string) => s === 'Weekly ML Prediction' },
          { key: 'multi', title: 'From Multibaggers (long-term, 1-year targets)', match: (s: string) => s === 'Multibagger Compounder' },
          { key: 'bench', title: 'Benchmark Large-Caps (filler, no model prediction)', match: (s: string) => s !== 'Weekly ML Prediction' && s !== 'Multibagger Compounder' },
        ].map(group => {
          const items = candidates.filter(c => group.match(c.source))
          if (!items.length) return null
          return (
        <div key={group.key} style={{ marginBottom: 14 }}>
        <div style={{ fontSize: 11.5, fontWeight: 600, color: 'var(--mut)', margin: '6px 0' }}>
          {group.title} · {items.length}
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(210px, 1fr))', gap: 10 }}>
          {items.map((cand, idx) => {
            const isSelected = cand.symbol === selectedSymbol
            const isReportReady = cand.has_report
            const verdict = cand.final_decision

            return (
              <div
                key={cand.symbol}
                onClick={() => setSelectedSymbol(cand.symbol)}
                className="panel"
                style={{
                  padding: '12px 14px',
                  cursor: 'pointer',
                  border: isSelected ? '2px solid var(--accent)' : '1px solid var(--line)',
                  background: isSelected ? 'var(--surface)' : 'transparent',
                  transition: 'all 0.15s ease',
                  boxShadow: isSelected ? '0 4px 14px rgba(255,94,26,0.12)' : 'none'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
                  <span style={{ fontWeight: 700, fontSize: 14 }}>{cand.symbol}</span>
                  <span className="chip exch" style={{ fontSize: 10, padding: '1px 6px' }}>
                    #{idx + 1}
                  </span>
                </div>
                <div style={{ fontSize: 11.5, color: 'var(--mut)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', marginBottom: 8 }}>
                  {cand.name}
                </div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 11 }}>
                  {verdict ? (
                    <span
                      style={{
                        fontWeight: 700,
                        color: verdict.includes('BUY') ? 'var(--up)' : verdict.includes('ACCUMULATE') ? 'var(--info)' : 'var(--amber)'
                      }}
                    >
                      {verdict}
                    </span>
                  ) : (
                    <span className="mut">Analysis Pending</span>
                  )}
                  {cand.conviction_score ? (
                    <span className="num" style={{ fontWeight: 600 }}>{cand.conviction_score}%</span>
                  ) : cand.predicted_return_pct ? (
                    <span className="num pos">+{cand.predicted_return_pct}%</span>
                  ) : null}
                </div>
              </div>
            )
          })}
        </div>
        </div>
          )
        })}
      </div>

      {/* Main Deliberation Desk for Selected Stock */}
      {analyzingSymbol || (selectedSymbol && !reportError && currentReport?.symbol !== selectedSymbol) ? (
        <section className="panel emptystate" style={{ padding: 60, textAlign: 'center' }}>
          <ThinkingOrb state="searching" size={64} theme={orb} />
          <h4 style={{ margin: '18px 0 6px', fontSize: 17 }}>Deliberating {analyzingSymbol || selectedSymbol}…</h4>
          <p style={{ maxWidth: 520, margin: '0 auto', color: 'var(--mut)', fontSize: 13.5, lineHeight: 1.6 }}>
            The <b>Fundamentals Analyst</b>, <b>Technical Analyst</b>, and <b>News Analyst</b> are compiling data,
            while the <b>Bull &amp; Bear Researchers</b> stage their cross-examination debate.
          </p>
        </section>
      ) : reportError && currentReport?.symbol !== selectedSymbol ? (
        <section className="panel emptystate" style={{ padding: 48, textAlign: 'center' }}>
          <h4 style={{ margin: '0 0 6px' }}>Could not deliberate {selectedSymbol}</h4>
          <p style={{ maxWidth: 520, margin: '0 auto 14px', color: 'var(--mut)', fontSize: 13.5 }}>{reportError}</p>
          <button className="btn dark" onClick={() => setRetryTick(t => t + 1)}>Retry {selectedSymbol}</button>
        </section>
      ) : currentReport && currentReport.symbol === selectedSymbol ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          {/* Executive Overview Panel */}
          <section className="panel" style={{ padding: '24px 28px' }}>
            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: 20 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 18 }}>
                <ScoreRing score={currentReport.conviction_score} size={70} />
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
                    <h2 style={{ margin: 0, fontSize: 22, fontWeight: 700 }}>{currentReport.name}</h2>
                    <span className="chip exch">{currentReport.symbol} · {currentReport.exchange}</span>
                    <span
                      className="chip"
                      style={{
                        fontSize: 12,
                        fontWeight: 700,
                        padding: '4px 12px',
                        background: currentReport.final_decision.includes('BUY')
                          ? 'rgba(30,158,90,0.15)'
                          : currentReport.final_decision.includes('ACCUMULATE')
                          ? 'rgba(255,94,26,0.15)'
                          : 'rgba(255,94,26,0.15)',
                        color: currentReport.final_decision.includes('BUY')
                          ? 'var(--up)'
                          : currentReport.final_decision.includes('ACCUMULATE')
                          ? 'var(--info)'
                          : 'var(--amber)'
                      }}
                    >
                      {currentReport.final_decision}
                    </span>
                    {currentReport.ai_engine_used && (
                      <span className="chip" style={{ fontSize: 11, background: 'rgba(255,94,26,0.08)', color: 'var(--info)', display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                        <Cpu size={12} weight="bold" /> {currentReport.ai_engine_used}
                        <button
                          onClick={() => { setShowAiModal(true); setTestResult(null) }}
                          style={{
                            background: 'transparent',
                            border: 'none',
                            color: 'var(--accent)',
                            cursor: 'pointer',
                            padding: '0 2px',
                            fontSize: 10.5,
                            fontWeight: 700,
                            textDecoration: 'underline'
                          }}
                        >
                          Edit
                        </button>
                      </span>
                    )}
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginTop: 8, fontSize: 13, color: 'var(--mut)' }}>
                    <span>Entry: <b className="num">{inr(currentReport.entry_price)}</b></span>
                    <span>Target 1: <b className="num pos">{inr(currentReport.target1)}</b></span>
                    <span>Target 2: <b className="num acc">{inr(currentReport.target2)}</b></span>
                    <span>Stop-Loss: <b className="num neg">{inr(currentReport.stop_loss)}</b></span>
                    <span>R:R: <b>{currentReport.risk_reward}</b></span>
                    <span>Max Size: <b className="pos">{currentReport.max_allocation_pct}%</b></span>
                  </div>
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <button
                  className="btn ghost sm"
                  onClick={() => triggerAnalyze(currentReport.symbol, currentReport.exchange, currentReport.name)}
                >
                  <Lightning size={14} weight="bold" /> Re-Deliberate
                </button>
                <button
                  className="btn ghost sm"
                  onClick={() => onOpenStock(currentReport.symbol, currentReport.exchange, currentReport.name)}
                >
                  StockDesk <ArrowRight size={13} weight="bold" />
                </button>
                <button
                  className="btn dark sm"
                  onClick={() => onSaveHolding(
                    { symbol: currentReport.symbol, name: currentReport.name, current_price: currentReport.entry_price, exchange: currentReport.exchange },
                    10,
                    currentReport.entry_price
                  )}
                >
                  <Briefcase size={14} weight="bold" /> + Add to Portfolio
                </button>
              </div>
            </div>

            {/* Department Navigation Tabs */}
            <div style={{ display: 'flex', gap: 8, marginTop: 22, borderTop: '1px solid var(--line)', paddingTop: 16 }}>
              {[
                { id: 'debate', label: '🗣️ Bull vs. Bear Debate Arena' },
                { id: 'analysts', label: '📊 3 Analyst Department Reports' },
                { id: 'risk', label: '🛡️ Chief Risk Officer Audit' },
                { id: 'memo', label: '📜 Signed Investment Committee Memo' }
              ].map(t => (
                <button
                  key={t.id}
                  className={`btn sm ${activeTab === t.id ? 'dark' : 'ghost'}`}
                  onClick={() => setActiveTab(t.id as any)}
                  style={{ fontSize: 12.5, padding: '7px 15px' }}
                >
                  {t.label}
                </button>
              ))}
            </div>
          </section>

          {/* TAB 1: THE BULL VS BEAR DEBATE ARENA */}
          {activeTab === 'debate' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              {/* Bull and Bear Thesis Headers */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                <div className="panel" style={{ padding: '20px', borderLeft: '4px solid var(--up)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
                    <span style={{ fontWeight: 700, fontSize: 14, color: 'var(--up)', display: 'flex', alignItems: 'center', gap: 6 }}>
                      <TrendUp size={16} weight="bold" /> BULL RESEARCHER THESIS
                    </span>
                    <span className="chip pass" style={{ fontSize: 11 }}>
                      {currentReport.agents.bull_researcher.confidence_pct}% Conviction
                    </span>
                  </div>
                  <h4 style={{ margin: '0 0 10px', fontSize: 15, fontWeight: 600 }}>
                    {currentReport.agents.bull_researcher.thesis_title}
                  </h4>
                  <p style={{ margin: 0, fontSize: 13, color: 'var(--mut)', lineHeight: 1.55 }}>
                    {currentReport.agents.bull_researcher.bullish_thesis}
                  </p>
                  <div style={{ marginTop: 12 }}>
                    <span style={{ fontSize: 12, fontWeight: 600 }}>Core Growth Catalysts:</span>
                    <ul style={{ margin: '6px 0 0', paddingLeft: 18, fontSize: 12.5, color: 'var(--mut)', lineHeight: 1.5 }}>
                      {currentReport.agents.bull_researcher.core_pillars.map((pil: string, idx: number) => (
                        <li key={idx}>{pil}</li>
                      ))}
                    </ul>
                  </div>
                </div>

                <div className="panel" style={{ padding: '20px', borderLeft: '4px solid var(--down)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
                    <span style={{ fontWeight: 700, fontSize: 14, color: 'var(--down)', display: 'flex', alignItems: 'center', gap: 6 }}>
                      <TrendDown size={16} weight="bold" /> BEAR RESEARCHER CRITIQUE
                    </span>
                    <span className="chip neg" style={{ fontSize: 11 }}>
                      {currentReport.agents.bear_researcher.skepticism_pct}% Skepticism
                    </span>
                  </div>
                  <h4 style={{ margin: '0 0 10px', fontSize: 15, fontWeight: 600 }}>
                    {currentReport.agents.bear_researcher.thesis_title}
                  </h4>
                  <p style={{ margin: 0, fontSize: 13, color: 'var(--mut)', lineHeight: 1.55 }}>
                    {currentReport.agents.bear_researcher.bearish_critique}
                  </p>
                  <div style={{ marginTop: 12 }}>
                    <span style={{ fontSize: 12, fontWeight: 600 }}>Downside Vulnerabilities:</span>
                    <ul style={{ margin: '6px 0 0', paddingLeft: 18, fontSize: 12.5, color: 'var(--mut)', lineHeight: 1.5 }}>
                      {currentReport.agents.bear_researcher.key_vulnerabilities.map((vul: string, idx: number) => (
                        <li key={idx}>{vul}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>

              {/* Multi-Round Debate Exchange Dialogue */}
              <div className="panel" style={{ padding: '24px 28px' }}>
                <h3 style={{ margin: '0 0 16px', fontSize: 16, fontWeight: 600, display: 'flex', alignItems: 'center', gap: 8 }}>
                  <Brain size={18} weight="fill" /> Interactive Bull-Bear Debate Transcript
                </h3>

                <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                  {currentReport.debate_transcript.map((turn, i) => {
                    const isBull = turn.avatar === 'bull'
                    return (
                      <div
                        key={i}
                        style={{
                          display: 'flex',
                          flexDirection: 'column',
                          alignSelf: isBull ? 'flex-start' : 'flex-end',
                          maxWidth: '85%',
                          background: isBull ? 'rgba(30,158,90,0.06)' : 'rgba(214,69,69,0.06)',
                          border: `1px solid ${isBull ? 'rgba(30,158,90,0.2)' : 'rgba(214,69,69,0.2)'}`,
                          borderRadius: 'var(--r-md)',
                          padding: '14px 18px'
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6, gap: 14 }}>
                          <span style={{ fontWeight: 700, fontSize: 13, color: isBull ? 'var(--up)' : 'var(--down)' }}>
                            {turn.speaker}
                          </span>
                          <span className="mut" style={{ fontSize: 11 }}>{turn.round}</span>
                        </div>
                        <p style={{ margin: 0, fontSize: 13.5, lineHeight: 1.6, color: 'var(--ink)' }}>
                          {turn.argument}
                        </p>
                      </div>
                    )
                  })}
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: ANALYST DEPARTMENT REPORTS */}
          {activeTab === 'analysts' && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 16 }}>
              {/* Fundamentals Analyst */}
              <div className="panel" style={{ padding: '22px' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
                  <h4 style={{ margin: 0, fontSize: 15, fontWeight: 600 }}>1. Fundamentals Analyst</h4>
                  <ScoreRing score={currentReport.agents.fundamentals.score} size={48} />
                </div>
                <div style={{ fontSize: 12.5, fontWeight: 600, color: 'var(--up)', marginBottom: 8 }}>
                  {currentReport.agents.fundamentals.verdict}
                </div>
                <p style={{ fontSize: 13, color: 'var(--mut)', lineHeight: 1.55, marginBottom: 14 }}>
                  {currentReport.agents.fundamentals.summary}
                </p>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 12, borderTop: '1px solid var(--line)', paddingTop: 10 }}>
                  <div>Piotroski: <b>{currentReport.agents.fundamentals.metrics.piotroski_score}/9</b></div>
                  <div>Altman Z: <b>{currentReport.agents.fundamentals.metrics.altman_z}</b></div>
                  <div>ROE: <b>{currentReport.agents.fundamentals.metrics.roe_pct}%</b></div>
                  <div>OPM: <b>{currentReport.agents.fundamentals.metrics.opm_pct}%</b></div>
                  <div>D/E: <b>{currentReport.agents.fundamentals.metrics.debt_to_equity}</b></div>
                  <div>P/E: <b>{currentReport.agents.fundamentals.metrics.pe || '—'}</b></div>
                </div>
              </div>

              {/* Technical Analyst */}
              <div className="panel" style={{ padding: '22px' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
                  <h4 style={{ margin: 0, fontSize: 15, fontWeight: 600 }}>2. Technical Analyst</h4>
                  <ScoreRing score={currentReport.agents.technicals.score} size={48} />
                </div>
                <div style={{ fontSize: 12.5, fontWeight: 600, color: 'var(--accent)', marginBottom: 8 }}>
                  {currentReport.agents.technicals.trend_state}
                </div>
                <p style={{ fontSize: 13, color: 'var(--mut)', lineHeight: 1.55, marginBottom: 14 }}>
                  {currentReport.agents.technicals.summary}
                </p>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 12, borderTop: '1px solid var(--line)', paddingTop: 10 }}>
                  <div>20-EMA: <b>₹{currentReport.agents.technicals.metrics.ema20}</b></div>
                  <div>50-EMA: <b>₹{currentReport.agents.technicals.metrics.ema50}</b></div>
                  <div>RSI (14): <b>{currentReport.agents.technicals.metrics.rsi}</b></div>
                  <div>Support: <b>₹{currentReport.agents.technicals.metrics.support}</b></div>
                  <div>Resistance: <b>₹{currentReport.agents.technicals.metrics.resistance}</b></div>
                  <div>Volume Ratio: <b>{currentReport.agents.technicals.metrics.volume_ratio}×</b></div>
                </div>
              </div>

              {/* Sentiment & News Analyst */}
              <div className="panel" style={{ padding: '22px' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
                  <h4 style={{ margin: 0, fontSize: 15, fontWeight: 600 }}>3. Sentiment &amp; Regulatory Analyst</h4>
                  <ScoreRing score={currentReport.agents.sentiment.score} size={48} />
                </div>
                <div style={{ fontSize: 12.5, fontWeight: 600, color: 'var(--info)', marginBottom: 8 }}>
                  {currentReport.agents.sentiment.verdict}
                </div>
                <p style={{ fontSize: 13, color: 'var(--mut)', lineHeight: 1.55, marginBottom: 14 }}>
                  {currentReport.agents.sentiment.summary}
                </p>
                <div style={{ fontSize: 12, borderTop: '1px solid var(--line)', paddingTop: 10 }}>
                  <span style={{ fontWeight: 600 }}>Recent Corporate Headlines:</span>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginTop: 6 }}>
                    {currentReport.agents.sentiment.headlines?.length > 0 ? (
                      currentReport.agents.sentiment.headlines.map((hl: any, j: number) => (
                        <div key={j} style={{ fontSize: 11.5, color: 'var(--mut)', display: 'flex', justifyContent: 'space-between' }}>
                          <span>• {hl.title}</span>
                          <span style={{ opacity: 0.6 }}>{hl.publisher}</span>
                        </div>
                      ))
                    ) : (
                      <span className="mut" style={{ fontSize: 11.5 }}>No adverse news or regulatory actions detected.</span>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: CHIEF RISK OFFICER AUDIT */}
          {activeTab === 'risk' && (
            <div className="panel" style={{ padding: '26px 30px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 18 }}>
                <h3 style={{ margin: 0, fontSize: 17, fontWeight: 600, display: 'flex', alignItems: 'center', gap: 8 }}>
                  <ShieldCheck size={20} weight="fill" color="var(--up)" /> Chief Risk Officer (CRO) Portfolio Audit
                </h3>
                <span className="chip pass" style={{ fontSize: 12, fontWeight: 700 }}>
                  {currentReport.agents.risk_officer.audit_verdict}
                </span>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 14, marginBottom: 20 }}>
                <div style={{ padding: 14, background: 'var(--surface)', border: '1px solid var(--line)', borderRadius: 'var(--r-sm)' }}>
                  <div style={{ fontSize: 11.5, color: 'var(--mut)' }}>Stop-Loss Level</div>
                  <div style={{ fontSize: 20, fontWeight: 700, color: 'var(--down)', marginTop: 4 }}>
                    {inr(currentReport.agents.risk_officer.stop_loss_price)}
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--down)', marginTop: 2 }}>
                    {currentReport.agents.risk_officer.stop_loss_pct}% risk threshold
                  </div>
                </div>

                <div style={{ padding: 14, background: 'var(--surface)', border: '1px solid var(--line)', borderRadius: 'var(--r-sm)' }}>
                  <div style={{ fontSize: 11.5, color: 'var(--mut)' }}>Risk-to-Reward Ratio</div>
                  <div style={{ fontSize: 20, fontWeight: 700, marginTop: 4 }}>
                    {currentReport.agents.risk_officer.risk_reward_ratio}
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--up)', marginTop: 2 }}>Asymmetric institutional upside</div>
                </div>

                <div style={{ padding: 14, background: 'var(--surface)', border: '1px solid var(--line)', borderRadius: 'var(--r-sm)' }}>
                  <div style={{ fontSize: 11.5, color: 'var(--mut)' }}>Max Allocation Ceiling</div>
                  <div style={{ fontSize: 20, fontWeight: 700, color: 'var(--accent)', marginTop: 4 }}>
                    {currentReport.agents.risk_officer.max_portfolio_allocation_pct}%
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--mut)', marginTop: 2 }}>Position sizing discipline</div>
                </div>

                <div style={{ padding: 14, background: 'var(--surface)', border: '1px solid var(--line)', borderRadius: 'var(--r-sm)' }}>
                  <div style={{ fontSize: 11.5, color: 'var(--mut)' }}>Daily Value-at-Risk (95% VaR)</div>
                  <div style={{ fontSize: 20, fontWeight: 700, marginTop: 4 }}>
                    {currentReport.agents.risk_officer.daily_var_95_pct}%
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--mut)', marginTop: 2 }}>Statistical volatility estimate</div>
                </div>
              </div>

              <div style={{ padding: 16, background: 'rgba(10,10,12,0.03)', borderRadius: 'var(--r-sm)', fontSize: 13, lineHeight: 1.6 }}>
                <b>Risk Mandate:</b> {currentReport.agents.risk_officer.summary}
              </div>
            </div>
          )}

          {/* TAB 4: SIGNED INVESTMENT COMMITTEE MEMO */}
          {activeTab === 'memo' && (
            <div className="panel" style={{ padding: '26px 30px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
                <h3 style={{ margin: 0, fontSize: 17, fontWeight: 600 }}>
                  Institutional Investment Committee Memo
                </h3>
                <span className="chip" style={{ fontSize: 11, color: 'var(--mut)' }}>
                  Generated {currentReport.timestamp}
                </span>
              </div>

              <pre
                style={{
                  background: 'var(--surface)',
                  padding: 20,
                  borderRadius: 'var(--r-sm)',
                  border: '1px solid var(--line)',
                  fontFamily: 'monospace',
                  fontSize: 13,
                  lineHeight: 1.65,
                  whiteSpace: 'pre-wrap',
                  color: 'var(--ink)'
                }}
              >
                {currentReport.executive_memo}
              </pre>
            </div>
          )}
        </div>
      ) : (
        <section className="panel emptystate" style={{ padding: 48, textAlign: 'center' }}>
          <Brain size={48} weight="duotone" color="var(--accent)" />
          <h4 style={{ margin: '14px 0 6px' }}>Select a stock to view TradeAnalyser deliberation</h4>
          <p style={{ maxWidth: 520, margin: '0 auto', color: 'var(--mut)', fontSize: 13.5 }}>
            Pick one of the top 10 machine-predicted stocks above or search any Indian stock ticker to initiate the multi-agent committee.
          </p>
        </section>
      )}

      </>}
      {/* AI ENGINE CONFIGURATION MODAL */}
      {showAiModal && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            zIndex: 1000,
            background: 'rgba(0,0,0,0.65)',
            backdropFilter: 'blur(5px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: 20
          }}
          onClick={e => {
            if (e.target === e.currentTarget) setShowAiModal(false)
          }}
        >
          <div
            className="panel"
            style={{
              width: '100%',
              maxWidth: 620,
              padding: '28px 32px',
              borderRadius: 'var(--r-md)',
              boxShadow: '0 12px 40px rgba(0,0,0,0.3)',
              background: 'var(--surface)'
            }}
          >
            {/* Modal Header */}
            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 20 }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                  <Cpu size={18} weight="bold" color="var(--accent)" />
                  <h3 style={{ margin: 0, fontSize: 19, fontWeight: 700 }}>AI Deliberation Engine Settings</h3>
                </div>
                <p style={{ margin: 0, fontSize: 12.5, color: 'var(--mut)' }}>
                  Power the Bull vs. Bear debate transcript and CIO memo using Gemini, Groq, OpenAI, or any custom API / Cursor endpoint.
                </p>
              </div>
              <button className="iconbtn" onClick={() => setShowAiModal(false)} aria-label="Close">
                <X size={16} weight="bold" />
              </button>
            </div>

            {/* Enable AI Toggle */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '12px 16px',
                background: aiConfig.enabled ? 'rgba(255,94,26,0.08)' : 'rgba(10,10,12,0.04)',
                border: `1px solid ${aiConfig.enabled ? 'rgba(255,94,26,0.25)' : 'var(--line)'}`,
                borderRadius: 'var(--r-sm)',
                marginBottom: 20
              }}
            >
              <div>
                <div style={{ fontWeight: 600, fontSize: 13.5 }}>Enable Generative AI Multi-Agent Deliberation</div>
                <div style={{ fontSize: 12, color: 'var(--mut)' }}>
                  When enabled, real LLMs dynamically write the arguments. When disabled, uses the fast offline quantitative engine.
                </div>
              </div>
              <label style={{ position: 'relative', display: 'inline-block', width: 44, height: 24, cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={aiConfig.enabled}
                  onChange={e => setAiConfig(prev => ({ ...prev, enabled: e.target.checked }))}
                  style={{ opacity: 0, width: 0, height: 0 }}
                />
                <span
                  style={{
                    position: 'absolute',
                    cursor: 'pointer',
                    top: 0, left: 0, right: 0, bottom: 0,
                    backgroundColor: aiConfig.enabled ? 'var(--info)' : 'var(--line)',
                    transition: '0.2s',
                    borderRadius: 24
                  }}
                >
                  <span
                    style={{
                      position: 'absolute',
                      height: 18,
                      width: 18,
                      left: aiConfig.enabled ? 22 : 3,
                      bottom: 3,
                      backgroundColor: 'white',
                      transition: '0.2s',
                      borderRadius: '50%'
                    }}
                  />
                </span>
              </label>
            </div>

            {/* Provider Selection (5 Options) */}
            <div style={{ marginBottom: 18 }}>
              <label style={{ display: 'block', fontSize: 12.5, fontWeight: 600, marginBottom: 8, color: 'var(--ink)' }}>
                Select AI Provider:
              </label>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 10 }}>
                {[
                  { id: 'xai', title: 'xAI (Grok)', desc: 'grok-2-latest / grok-beta (Direct x.ai)' },
                  { id: 'gemini', title: 'Google Gemini', desc: 'gemini-1.5-flash / 2.0 (Fast & Free Tier)' },
                  { id: 'groq', title: 'Groq (Llama-3.3)', desc: 'Ultra-fast inference (Free Tier)' },
                  { id: 'openai', title: 'OpenAI', desc: 'gpt-4o-mini / gpt-4o' },
                  { id: 'custom', title: 'Cursor / Custom Base URL', desc: 'Cursor proxy, OpenRouter, AgentRouter, Ollama' }
                ].map(p => {
                  const isCur = aiConfig.provider === p.id
                  return (
                    <div
                      key={p.id}
                      onClick={() => switchProvider(p.id as any)}
                      style={{
                        padding: '12px 14px',
                        borderRadius: 'var(--r-sm)',
                        cursor: 'pointer',
                        border: isCur ? '2px solid var(--info)' : '1px solid var(--line)',
                        background: isCur ? 'rgba(255,94,26,0.06)' : 'var(--surface)',
                        transition: 'all 0.15s ease'
                      }}
                    >
                      <div style={{ fontWeight: 700, fontSize: 13, color: isCur ? 'var(--info)' : 'var(--ink)' }}>
                        {p.title}
                      </div>
                      <div style={{ fontSize: 11, color: 'var(--mut)', marginTop: 2 }}>{p.desc}</div>
                    </div>
                  )
                })}
              </div>
            </div>

            {/* API Key Input */}
            <div style={{ marginBottom: 16 }}>
              <label style={{ display: 'block', fontSize: 12.5, fontWeight: 600, marginBottom: 6, color: 'var(--ink)' }}>
                <Key size={13} weight="bold" style={{ marginRight: 5 }} /> API Key:
              </label>
              <input
                type="password"
                placeholder={aiConfig.has_key ? '•••••••••••••••• (Leave unchanged to keep)' : 'Enter API Key...'}
                value={aiConfig.api_key}
                onChange={e => setAiConfig(prev => ({ ...prev, api_key: e.target.value }))}
                style={{
                  width: '100%',
                  padding: '9px 12px',
                  borderRadius: 'var(--r-sm)',
                  border: '1px solid var(--line)',
                  background: 'var(--surface)',
                  color: 'var(--ink)',
                  fontSize: 13,
                  outline: 'none',
                  boxSizing: 'border-box'
                }}
              />
              <span className="mut" style={{ fontSize: 11, marginTop: 4, display: 'block' }}>
                Stored locally on your server in <code>data/ai_config.json</code>.
              </span>
            </div>

            {/* Custom API Base URL Input */}
            <div style={{ marginBottom: 16 }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
                <label style={{ fontSize: 12.5, fontWeight: 600, color: 'var(--ink)' }}>
                  <Globe size={13} weight="bold" style={{ marginRight: 5 }} /> API Base URL (OpenAI-compatible):
                </label>
                <span className="mut" style={{ fontSize: 11 }}>Editable</span>
              </div>
              <input
                type="text"
                placeholder="e.g. https://api.x.ai/v1 or https://openrouter.ai/api/v1 or http://localhost:3000/v1"
                value={aiConfig.base_url}
                onChange={e => setAiConfig(prev => ({ ...prev, base_url: e.target.value }))}
                style={{
                  width: '100%',
                  padding: '9px 12px',
                  borderRadius: 'var(--r-sm)',
                  border: '1px solid var(--line)',
                  background: 'var(--surface)',
                  color: 'var(--ink)',
                  fontSize: 13,
                  outline: 'none',
                  boxSizing: 'border-box',
                  fontFamily: 'monospace'
                }}
              />
              {/* Quick Preset Buttons for Base URL */}
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 6, alignItems: 'center' }}>
                <span style={{ fontSize: 10.5, color: 'var(--mut)', marginRight: 2 }}>Quick Presets:</span>
                <button type="button" className="btn ghost sm" style={{ fontSize: 10.5, padding: '2px 8px' }} onClick={() => setAiConfig(p => ({ ...p, base_url: 'https://api.x.ai/v1', provider: 'xai', model: 'grok-4.7' }))}>
                  xAI (api.x.ai)
                </button>
                <button type="button" className="btn ghost sm" style={{ fontSize: 10.5, padding: '2px 8px' }} onClick={() => setAiConfig(p => ({ ...p, base_url: 'https://openrouter.ai/api/v1', provider: 'custom', model: 'x-ai/grok-2-1212' }))}>
                  OpenRouter
                </button>
                <button type="button" className="btn ghost sm" style={{ fontSize: 10.5, padding: '2px 8px' }} onClick={() => setAiConfig(p => ({ ...p, base_url: 'http://localhost:3000/v1', provider: 'custom', model: 'grok-4.7' }))}>
                  Cursor Local (:3000)
                </button>
                <button type="button" className="btn ghost sm" style={{ fontSize: 10.5, padding: '2px 8px' }} onClick={() => setAiConfig(p => ({ ...p, base_url: 'https://generativelanguage.googleapis.com/v1beta/openai/', provider: 'gemini', model: 'gemini-1.5-flash' }))}>
                  Gemini
                </button>
                <button type="button" className="btn ghost sm" style={{ fontSize: 10.5, padding: '2px 8px' }} onClick={() => setAiConfig(p => ({ ...p, base_url: 'https://api.groq.com/openai/v1', provider: 'groq', model: 'llama-3.3-70b-versatile' }))}>
                  Groq
                </button>
              </div>
            </div>

            {/* Model Name Input */}
            <div style={{ marginBottom: 20 }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
                <label style={{ fontSize: 12.5, fontWeight: 600, color: 'var(--ink)' }}>
                  <Cpu size={13} weight="bold" style={{ marginRight: 5 }} /> Model Identifier (Editable):
                </label>
                <span className="mut" style={{ fontSize: 11 }}>Type or click below</span>
              </div>
              <input
                type="text"
                placeholder="e.g. grok-4.7, grok-2-latest, gemini-1.5-flash, llama-3.3-70b"
                value={aiConfig.model}
                onChange={e => setAiConfig(prev => ({ ...prev, model: e.target.value }))}
                style={{
                  width: '100%',
                  padding: '9px 12px',
                  borderRadius: 'var(--r-sm)',
                  border: '1px solid var(--line)',
                  background: 'var(--surface)',
                  color: 'var(--ink)',
                  fontSize: 13,
                  outline: 'none',
                  boxSizing: 'border-box',
                  fontFamily: 'monospace'
                }}
              />
              {/* Quick Select Model Chips */}
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 7, alignItems: 'center' }}>
                <span style={{ fontSize: 10.5, color: 'var(--mut)', marginRight: 2 }}>Quick Select:</span>
                <button
                  type="button"
                  className={`btn sm ${aiConfig.model === 'grok-4.7' ? 'dark' : 'ghost'}`}
                  style={{ fontSize: 11, padding: '3px 9px', fontWeight: 700, borderColor: 'var(--info)' }}
                  onClick={() => setAiConfig(p => ({ ...p, model: 'grok-4.7' }))}
                >
                  ★ grok-4.7 (Base Model)
                </button>
                <button
                  type="button"
                  className={`btn sm ${aiConfig.model === 'grok-2-latest' ? 'dark' : 'ghost'}`}
                  style={{ fontSize: 11, padding: '3px 9px' }}
                  onClick={() => setAiConfig(p => ({ ...p, model: 'grok-2-latest' }))}
                >
                  grok-2-latest
                </button>
                <button
                  type="button"
                  className={`btn sm ${aiConfig.model === 'grok-beta' ? 'dark' : 'ghost'}`}
                  style={{ fontSize: 11, padding: '3px 9px' }}
                  onClick={() => setAiConfig(p => ({ ...p, model: 'grok-beta' }))}
                >
                  grok-beta
                </button>
                <button
                  type="button"
                  className={`btn sm ${aiConfig.model === 'x-ai/grok-2-1212' ? 'dark' : 'ghost'}`}
                  style={{ fontSize: 11, padding: '3px 9px' }}
                  onClick={() => setAiConfig(p => ({ ...p, model: 'x-ai/grok-2-1212' }))}
                >
                  x-ai/grok-2-1212
                </button>
                <button
                  type="button"
                  className={`btn sm ${aiConfig.model === 'gemini-1.5-flash' ? 'dark' : 'ghost'}`}
                  style={{ fontSize: 11, padding: '3px 9px' }}
                  onClick={() => setAiConfig(p => ({ ...p, model: 'gemini-1.5-flash' }))}
                >
                  gemini-1.5-flash
                </button>
                <button
                  type="button"
                  className={`btn sm ${aiConfig.model === 'llama-3.3-70b-versatile' ? 'dark' : 'ghost'}`}
                  style={{ fontSize: 11, padding: '3px 9px' }}
                  onClick={() => setAiConfig(p => ({ ...p, model: 'llama-3.3-70b-versatile' }))}
                >
                  llama-3.3-70b
                </button>
              </div>
            </div>

            {/* Test Connection Result Banner */}
            {testResult && (
              <div
                style={{
                  padding: '10px 14px',
                  borderRadius: 'var(--r-sm)',
                  marginBottom: 18,
                  fontSize: 12.5,
                  background: testResult.success ? 'rgba(30,158,90,0.1)' : 'rgba(214,69,69,0.1)',
                  color: testResult.success ? 'var(--up)' : 'var(--down)',
                  border: `1px solid ${testResult.success ? 'rgba(30,158,90,0.3)' : 'rgba(214,69,69,0.3)'}`,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8
                }}
              >
                {testResult.success ? <CheckCircle size={16} weight="bold" /> : <Warning size={16} weight="bold" />}
                <span>{testResult.message || testResult.error}</span>
              </div>
            )}

            {/* Actions */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderTop: '1px solid var(--line)', paddingTop: 18 }}>
              <button
                type="button"
                className="btn ghost sm"
                disabled={testingAi}
                onClick={handleTestAi}
                style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}
              >
                {testingAi ? <ThinkingOrb state="working" size={20} theme={orb} /> : <Lightning size={14} weight="bold" />}
                <span>{testingAi ? 'Testing Ping…' : 'Test Connection'}</span>
              </button>

              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <button type="button" className="btn ghost sm" onClick={() => setShowAiModal(false)}>
                  Cancel
                </button>
                <button
                  type="button"
                  className="btn dark sm"
                  disabled={savingAi}
                  onClick={handleSaveAi}
                  style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontWeight: 600 }}
                >
                  <Check size={14} weight="bold" />
                  <span>{savingAi ? 'Saving…' : 'Save Settings'}</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
