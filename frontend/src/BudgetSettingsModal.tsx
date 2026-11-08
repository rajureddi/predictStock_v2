import React, { useState, useEffect } from 'react'
import { X, SlidersHorizontal, CheckCircle, CurrencyInr, ShieldCheck, Lightning, ArrowRight, Sparkle } from '@phosphor-icons/react'
import { inr } from './lib'

export interface ScreenRules {
  budget_inr: number | null
  price_cap_mode: 'no_heavy' | 'moderate' | 'allow_heavy' | 'ultra_heavy' | 'custom'
  min_stock_price: number
  max_stock_price: number
  min_profit_inr: number
  profit_basis: 'auto' | 'per_share' | 'per_position'
}

interface Props {
  open: boolean
  onClose: () => void
  onRulesSaved: () => void
  initialRules?: Partial<ScreenRules>
}

export default function BudgetSettingsModal({ open, onClose, onRulesSaved, initialRules }: Props) {
  const [budget, setBudget] = useState<string>('')
  const [capMode, setCapMode] = useState<ScreenRules['price_cap_mode']>('moderate')
  const [minProfit, setMinProfit] = useState<number>(100)
  const [profitBasis, setProfitBasis] = useState<ScreenRules['profit_basis']>('auto')
  const [saving, setSaving] = useState(false)
  const [savedNote, setSavedNote] = useState(false)

  useEffect(() => {
    if (!open) return
    fetch('/api/screen/rules')
      .then(r => r.json())
      .then((cfg: ScreenRules) => {
        if (cfg) {
          setBudget(cfg.budget_inr != null ? String(cfg.budget_inr) : '')
          setCapMode(cfg.price_cap_mode || 'moderate')
          setMinProfit(cfg.min_profit_inr ?? 100)
          setProfitBasis(cfg.profit_basis || 'auto')
        }
      })
      .catch(() => {
        if (initialRules) {
          setBudget(initialRules.budget_inr != null ? String(initialRules.budget_inr) : '')
          if (initialRules.price_cap_mode) setCapMode(initialRules.price_cap_mode)
          if (initialRules.min_profit_inr != null) setMinProfit(initialRules.min_profit_inr)
        }
      })
  }, [open])

  if (!open) return null

  const handleSave = async () => {
    setSaving(true)
    const bNum = budget.trim() === '' ? null : Number(budget)
    const payload = {
      budget_inr: bNum && bNum > 0 ? bNum : null,
      price_cap_mode: capMode,
      min_profit_inr: Number(minProfit) || 100,
      profit_basis: profitBasis,
    }
    try {
      await fetch('/api/screen/rules', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      setSavedNote(true)
      setTimeout(() => {
        setSavedNote(false)
        onRulesSaved()
        onClose()
      }, 500)
    } finally {
      setSaving(false)
    }
  }

  const weightOptions: Array<{
    mode: ScreenRules['price_cap_mode']
    title: string
    badge: string
    desc: string
    color: string
    recommended?: boolean
  }> = [
    {
      mode: 'no_heavy',
      title: 'No Heavy Stocks (Retail Focus)',
      badge: '≤ ₹2,500',
      desc: 'Only stocks under ₹2,500 (e.g. TCS, Laurus Labs, SG Mart, SMS Pharma). Strictly blocks all ₹3,000+ stocks.',
      color: '#0A1931',
    },
    {
      mode: 'moderate',
      title: 'Moderate Weight (Recommended)',
      badge: '≤ ₹4,500',
      desc: 'Top quality institutional leaders (e.g. TCPL, Tata Elxsi, LTTS, TCS). Excludes ultra-heavy ₹8k–₹50k giants.',
      color: '#FF5E1A',
      recommended: true,
    },
    {
      mode: 'allow_heavy',
      title: 'Allow Heavy Stocks',
      badge: '≤ ₹9,500',
      desc: 'Allows heavy industrials (e.g. Garware Hi-Tech, Navin Fluorine) while blocking extreme mega-cap outliers.',
      color: '#1A3663',
    },
    {
      mode: 'ultra_heavy',
      title: 'Ultra-Heavy Uncapped',
      badge: 'No Limit',
      desc: 'Includes highest-ticket NSE stocks (e.g. Bosch Ltd ₹50,700+, Force Motors ₹18,968+, MRF).',
      color: '#768CA8',
    },
  ]

  return (
    <div className="modal-backdrop" onClick={onClose} role="dialog" aria-modal="true">
      <div className="budget-rules-modal" onClick={e => e.stopPropagation()}>
        <header className="brm-header">
          <div className="brm-header-left">
            <span className="brm-icon-pill">
              <SlidersHorizontal size={20} weight="bold" />
            </span>
            <div>
              <h3>Budget &amp; Stock Selection Rules</h3>
              <p>Configure which budget stocks to pick, price ceilings, and minimum profit targets.</p>
            </div>
          </div>
          <button className="iconbtn brm-close" onClick={onClose} aria-label="Close settings">
            <X size={18} weight="bold" />
          </button>
        </header>

        <div className="brm-body">
          {/* SECTION 1: STOCK WEIGHT RULE */}
          <div className="brm-section">
            <div className="brm-sec-title">
              <h4>1. Stock Price Weight Rule ("No Heavy / Ultra-Heavy")</h4>
              <span className="brm-sec-sub">Set the maximum price ceiling for selected stocks</span>
            </div>
            <div className="brm-weight-grid">
              {weightOptions.map(opt => {
                const active = capMode === opt.mode
                return (
                  <div
                    key={opt.mode}
                    className={`brm-weight-card ${active ? 'active' : ''}`}
                    onClick={() => setCapMode(opt.mode)}
                  >
                    <div className="brm-wc-top">
                      <div className="brm-wc-radio">
                        <span className={`brm-radio-dot ${active ? 'checked' : ''}`} />
                        <span className="brm-wc-title">{opt.title}</span>
                      </div>
                      <span className="brm-wc-badge num" style={{ borderColor: opt.color, color: opt.color }}>
                        {opt.badge}
                      </span>
                    </div>
                    <p className="brm-wc-desc">{opt.desc}</p>
                    {opt.recommended && <span className="brm-rec-tag">Recommended</span>}
                  </div>
                )
              })}
            </div>
          </div>

          {/* SECTION 2: MINIMUM PROFIT REQUIREMENT */}
          <div className="brm-section">
            <div className="brm-sec-title">
              <h4>2. Minimum 5-Day Profit Rule</h4>
              <span className="brm-sec-sub">Require at least ₹100+ predicted profit (stops tiny ₹5–₹10 predictions)</span>
            </div>
            <div className="brm-profit-box">
              <div className="brm-presets-row">
                {[50, 100, 150, 200, 300].map(val => (
                  <button
                    key={val}
                    type="button"
                    className={`brm-pill-btn ${minProfit === val ? 'active' : ''}`}
                    onClick={() => setMinProfit(val)}
                  >
                    ≥ ₹{val} {val === 100 ? '(Required Rule)' : ''}
                  </button>
                ))}
              </div>
              <div className="brm-input-row" style={{ marginTop: 10 }}>
                <label htmlFor="min-profit-inp">Custom Minimum Profit (₹):</label>
                <input
                  id="min-profit-inp"
                  type="number"
                  min="10"
                  step="10"
                  value={minProfit}
                  onChange={e => setMinProfit(Number(e.target.value))}
                  className="brm-num-input num"
                />
              </div>
            </div>
          </div>

          {/* SECTION 3: PORTFOLIO BUDGET */}
          <div className="brm-section">
            <div className="brm-sec-title">
              <h4>3. Portfolio Budget Tier</h4>
              <span className="brm-sec-sub">Pick stocks in that budget's affordable range &amp; size whole shares</span>
            </div>
            <div className="brm-budget-box">
              <div className="brm-presets-row">
                <button
                  type="button"
                  className={`brm-pill-btn ${budget === '' ? 'active' : ''}`}
                  onClick={() => setBudget('')}
                >
                  Unbudgeted (Ranked Only)
                </button>
                {[5000, 10000, 25000, 50000, 100000].map(amt => (
                  <button
                    key={amt}
                    type="button"
                    className={`brm-pill-btn ${budget === String(amt) ? 'active' : ''}`}
                    onClick={() => setBudget(String(amt))}
                  >
                    ₹{amt >= 100000 ? '1 Lakh' : `${amt / 1000}k`}
                  </button>
                ))}
              </div>
              <div className="brm-input-row" style={{ marginTop: 10 }}>
                <label htmlFor="modal-budget-inp">Custom Budget in Rupees:</label>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <input
                    id="modal-budget-inp"
                    type="number"
                    min="0"
                    placeholder="e.g. 5000 or 10000"
                    value={budget}
                    onChange={e => setBudget(e.target.value)}
                    className="brm-num-input num"
                  />
                  {budget !== '' && (
                    <button type="button" className="btn ghost sm" onClick={() => setBudget('')}>
                      Clear
                    </button>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>

        <footer className="brm-footer">
          <div className="brm-footer-summary">
            <b>Active Strategy:</b>{' '}
            <span>
              {capMode === 'no_heavy'
                ? 'No Heavy (≤ ₹2,500)'
                : capMode === 'moderate'
                ? 'Moderate (≤ ₹4,500)'
                : capMode === 'allow_heavy'
                ? 'Heavy (≤ ₹9,500)'
                : 'Ultra-Heavy Uncapped'}
              {' · '}Min Profit ≥ ₹{minProfit}
              {budget ? ` · Budget ${inr(Number(budget))}` : ' · Unbudgeted'}
            </span>
          </div>
          <div className="brm-footer-actions">
            <button type="button" className="btn ghost" onClick={onClose}>
              Cancel
            </button>
            <button
              type="button"
              className="btn dark brm-apply-btn"
              disabled={saving}
              onClick={handleSave}
            >
              {saving ? 'Applying Rules…' : savedNote ? '✓ Rules Applied!' : 'Apply Rules & Chase Stocks'}
            </button>
          </div>
        </footer>
      </div>
    </div>
  )
}

