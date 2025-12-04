import React, { useEffect, useMemo, useRef, useState } from 'react'

const API = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

function useSymbolsMap() {
  const [symbols, setSymbols] = useState([])
  const [mapById, setMapById] = useState({})
  const refresh = async () => {
    try {
      const res = await fetch(`${API}/symbols`)
      const data = await res.json()
      setSymbols(data)
      const m = {}
      for (const s of data) m[s.id] = s.name
      setMapById(m)
    } catch {}
  }
  useEffect(() => { refresh(); const id = setInterval(refresh, 15000); return () => clearInterval(id) }, [])
  return { symbols, mapById }
}

function usePrices() {
  const [prices, setPrices] = useState([])
  const wsRef = useRef(null)

  const fetchLatest = async () => {
    const res = await fetch(`${API}/prices/latest`)
    const data = await res.json()
    setPrices(data)
  }

  useEffect(() => {
    fetchLatest()
    const wsUrl = API.replace('http', 'ws') + '/ws/prices'
    wsRef.current = new WebSocket(wsUrl)
    wsRef.current.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data)
        if (msg.type === 'price') {
          setPrices((prev) => {
            const p = msg.data
            const idx = prev.findIndex((x) => x.symbol_id === p.symbol_id)
            if (idx >= 0) {
              const copy = [...prev]
              copy[idx] = p
              return copy
            }
            return [p, ...prev]
          })
        }
      } catch {}
    }
    const keepalive = setInterval(() => wsRef.current?.send?.('ping'), 10000)
    const refreshTimer = setInterval(fetchLatest, 20000) // ensure refresh every 20s
    return () => {
      clearInterval(keepalive)
      clearInterval(refreshTimer)
      wsRef.current?.close()
    }
  }, [])

  return { prices, refresh: fetchLatest }
}

function useTop24h() {
  const [data, setData] = useState({ gainers: [], losers: [], updated_at: 0, stale: true, meta: {}, filters: {}, universe_size: 0 })
  const load = async () => {
    try {
      const res = await fetch(`${API}/v1/monitor/trending`)
      const json = await res.json()
      setData(json)
    } catch (e) {
      // ignore
    }
  }
  useEffect(() => {
    load()
    const id = setInterval(load, 20000)
    return () => clearInterval(id)
  }, [])
  return data
}

function GainersLosersPanels() {
  const { gainers, losers, updated_at, stale, meta, universe_size } = useTop24h()
  const updated = useMemo(() => updated_at ? new Date(updated_at * 1000).toLocaleTimeString() : '—', [updated_at])
  const headerInfo = meta?.label ? `${meta.label}` : 'Session-based'
  const thresholds = (meta && (meta.loss_pct !== undefined) && (meta.recovery_pct !== undefined)) ? `• Loss ≥${meta.loss_pct}% • Recovery ≥${meta.recovery_pct}%` : ''
  return (
    <div className="grid md:grid-cols-2 gap-4 mb-4">
      <Panel title={`Top Gainers (${headerInfo}) • Updated ${updated} ${stale ? '• Stale' : ''} ${thresholds}`}>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="text-gray-400">
              <tr>
                <th className="text-left p-2">Symbol</th>
                <th className="text-left p-2">Last</th>
                <th className="text-left p-2">24h %</th>
                <th className="text-left p-2">High</th>
                <th className="text-left p-2">Low</th>
              </tr>
            </thead>
            <tbody>
              {gainers.length === 0 && (
                <tr><td className="p-2 text-gray-400" colSpan="5">No 24h stats yet — refreshing every 20s. If this persists, check backend logs.</td></tr>
              )}
              {gainers.map((g) => (
                <tr key={g.symbol} className="border-t border-gray-800">
                  <td className="p-2">{g.symbol}</td>
                  <td className="p-2">{Number(g.lastPrice).toFixed(6)}</td>
                  <td className="p-2 text-green-400">{Number(g.priceChangePercent).toFixed(2)}%</td>
                  <td className="p-2">{Number(g.highPrice).toFixed(6)}</td>
                  <td className="p-2">{Number(g.lowPrice).toFixed(6)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
      <Panel title={`Top Losers (${headerInfo}) • Updated ${updated} ${stale ? '• Stale' : ''} ${thresholds}`}>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="text-gray-400">
              <tr>
                <th className="text-left p-2">Symbol</th>
                <th className="text-left p-2">Last</th>
                <th className="text-left p-2">24h %</th>
                <th className="text-left p-2">High</th>
                <th className="text-left p-2">Low</th>
              </tr>
            </thead>
            <tbody>
              {losers.length === 0 && (
                <tr><td className="p-2 text-gray-400" colSpan="5">No 24h stats yet — refreshing every 20s. If this persists, check backend logs.</td></tr>
              )}
              {losers.map((g) => (
                <tr key={g.symbol} className="border-t border-gray-800">
                  <td className="p-2">{g.symbol}</td>
                  <td className="p-2">{Number(g.lastPrice).toFixed(6)}</td>
                  <td className="p-2 text-red-400">{Number(g.priceChangePercent).toFixed(2)}%</td>
                  <td className="p-2">{Number(g.highPrice).toFixed(6)}</td>
                  <td className="p-2">{Number(g.lowPrice).toFixed(6)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  )
}

function useList(path) {
  const [data, setData] = useState([])
  const refresh = async () => {
    const res = await fetch(`${API}${path}`)
    setData(await res.json())
  }
  useEffect(() => {
    refresh()
    const id = setInterval(refresh, 4000)
    return () => clearInterval(id)
  }, [])
  return { data, refresh }
}

function Panel({ title, children }) {
  return (
    <div className="p-4 bg-gray-900 rounded border border-gray-800">
      <h2 className="text-xl font-semibold mb-3">{title}</h2>
      {children}
    </div>
  )
}

function MonitorUI() {
  const { prices } = usePrices()
  const { mapById } = useSymbolsMap()
  return (
    <div className="space-y-4">
      <GainersLosersPanels />
      <Panel title="Monitor (Latest Prices)">
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="text-gray-400">
              <tr>
                <th className="text-left p-2">Symbol</th>
                <th className="text-left p-2">Price</th>
                <th className="text-left p-2">Updated</th>
              </tr>
            </thead>
            <tbody>
              {prices.length === 0 && (
                <tr><td className="p-2 text-gray-400" colSpan="3">No prices yet — waiting for worker to write data...</td></tr>
              )}
              {prices.map((p) => (
                <tr key={p.id} className="border-t border-gray-800">
                  <td className="p-2">{mapById[p.symbol_id] || p.symbol_id}</td>
                  <td className="p-2">{p.price.toFixed(6)}</td>
                  <td className="p-2">{new Date(p.ts).toLocaleTimeString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-2 text-xs text-gray-500">Top panels refresh every 20s from Binance 24h stats. Table shows your latest DB prices (live‑fed by the worker).</p>
      </Panel>
    </div>
  )
}

function TradingUI() {
  const orders = useList('/orders')
  const positions = useList('/positions')
  const { mapById } = useSymbolsMap()

  const [status, setStatus] = useState({ enabled: false })
  const [busy, setBusy] = useState(false)
  const refreshStatus = async () => {
    try {
      const res = await fetch(`${API}/v1/trading/status`)
      setStatus(await res.json())
    } catch {}
  }
  const callPost = async (path) => {
    setBusy(true)
    try {
      await fetch(`${API}/v1/trading/${path}`, { method: 'POST' })
      await refreshStatus()
      orders.refresh()
      positions.refresh()
    } catch {} finally { setBusy(false) }
  }
  useEffect(() => { refreshStatus(); const id = setInterval(refreshStatus, 5000); return () => clearInterval(id) }, [])

  return (
    <div className="space-y-4">
      <Panel title="Trading Controls">
        <div className="flex items-center gap-3 text-sm">
          <span className={`px-2 py-1 rounded border ${status.enabled? 'border-green-600 text-green-400' : 'border-gray-600 text-gray-300'}`}>Trading: {status.enabled? 'ON' : 'OFF'}</span>
          <button disabled={busy} onClick={() => callPost('start')} className="px-3 py-1 rounded bg-green-700 disabled:opacity-50">Start Trading</button>
          <button disabled={busy} onClick={() => callPost('stop')} className="px-3 py-1 rounded bg-yellow-700 disabled:opacity-50">Stop Trading</button>
          <button disabled={busy} onClick={() => callPost('reset')} className="px-3 py-1 rounded bg-gray-700 disabled:opacity-50">Reset Session (prices)</button>
          <span className="text-gray-500">Reset drops price rows and restarts session-based gainers/losers; symbols and orders/positions remain.</span>
        </div>
      </Panel>
      <div className="grid md:grid-cols-2 gap-4">
      <Panel title="Orders">
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="text-gray-400">
              <tr>
                <th className="text-left p-2">ID</th>
                <th className="text-left p-2">Symbol</th>
                <th className="text-left p-2">Side</th>
                <th className="text-left p-2">Qty</th>
                <th className="text-left p-2">Price</th>
                <th className="text-left p-2">Status</th>
              </tr>
            </thead>
            <tbody>
              {orders.data.length === 0 && (
                <tr><td className="p-2 text-gray-400" colSpan="6">No orders yet — the AI may still be holding.</td></tr>
              )}
              {orders.data.map((o) => (
                <tr key={o.id} className="border-t border-gray-800">
                  <td className="p-2">{o.id}</td>
                  <td className="p-2">{mapById[o.symbol_id] || o.symbol_id}</td>
                  <td className="p-2">{o.side}</td>
                  <td className="p-2">{o.qty}</td>
                  <td className="p-2">{o.price.toFixed(2)}</td>
                  <td className="p-2">{o.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
      <Panel title="Positions">
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="text-gray-400">
              <tr>
                <th className="text-left p-2">Symbol</th>
                <th className="text-left p-2">Qty</th>
                <th className="text-left p-2">Avg Price</th>
                <th className="text-left p-2">Updated</th>
              </tr>
            </thead>
            <tbody>
              {positions.data.length === 0 && (
                <tr><td className="p-2 text-gray-400" colSpan="4">No positions yet — you’ll see entries after the first BUY/SELL.</td></tr>
              )}
              {positions.data.map((p) => (
                <tr key={p.id} className="border-t border-gray-800">
                  <td className="p-2">{mapById[p.symbol_id] || p.symbol_id}</td>
                  <td className="p-2">{p.qty}</td>
                  <td className="p-2">{p.avg_price.toFixed(2)}</td>
                  <td className="p-2">{new Date(p.updated_at).toLocaleTimeString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
    </div>
  )
}

function PortfolioUI() {
  const positions = useList('/positions')
  const { prices } = usePrices()
  const { mapById } = useSymbolsMap()
  const priceBySymbolId = useMemo(() => {
    const m = {}
    for (const p of prices) m[p.symbol_id] = p.price
    return m
  }, [prices])
  const rows = positions.data.map((p) => {
    const latest = priceBySymbolId[p.symbol_id] ?? p.avg_price
    const value = p.qty * latest
    const cost = p.qty * p.avg_price
    const pnl = value - cost
    const pnlPct = p.avg_price > 0 ? ((latest / p.avg_price) - 1) * 100 : 0
    return { ...p, latest, value, cost, pnl, pnlPct }
  })
  const totals = rows.reduce((acc, r) => ({
    value: acc.value + r.value,
    cost: acc.cost + r.cost,
    pnl: acc.pnl + r.pnl,
    profits: acc.profits + Math.max(0, r.pnl),
    losses: acc.losses + Math.min(0, r.pnl),
  }), { value: 0, cost: 0, pnl: 0, profits: 0, losses: 0 })
  return (
    <Panel title="Portfolio">
      {/* Top totals summary */}
      <div className="mb-3 grid md:grid-cols-4 gap-2 text-sm">
        <div className="p-2 bg-gray-800 rounded border border-gray-700">Total Value: <span className="font-semibold">{totals.value.toFixed(2)} USDT</span></div>
        <div className="p-2 bg-gray-800 rounded border border-gray-700">Total Cost: <span className="font-semibold">{totals.cost.toFixed(2)} USDT</span></div>
        <div className="p-2 bg-gray-800 rounded border border-gray-700">Total PnL: <span className={`font-semibold ${totals.pnl>=0? 'text-green-400':'text-red-400'}`}>{totals.pnl.toFixed(2)} USDT</span></div>
        <div className="p-2 bg-gray-800 rounded border border-gray-700">Profit / Loss: <span className="text-green-400">{totals.profits.toFixed(2)}</span> / <span className="text-red-400">{totals.losses.toFixed(2)}</span></div>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead className="text-gray-400">
            <tr>
              <th className="text-left p-2">Symbol</th>
              <th className="text-left p-2">Qty</th>
              <th className="text-left p-2">Avg Price</th>
              <th className="text-left p-2">Last Price</th>
              <th className="text-left p-2">Value</th>
              <th className="text-left p-2">PnL</th>
              <th className="text-left p-2">PnL %</th>
              <th className="text-left p-2">Updated</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && (
              <tr><td className="p-2 text-gray-400" colSpan="8">No positions yet — PnL appears after first BUY/SELL.</td></tr>
            )}
            {rows.map((r) => (
              <tr key={r.id} className="border-t border-gray-800">
                <td className="p-2">{mapById[r.symbol_id] || r.symbol_id}</td>
                <td className="p-2">{r.qty}</td>
                <td className="p-2">{r.avg_price.toFixed(4)}</td>
                <td className="p-2">{r.latest.toFixed(4)}</td>
                <td className="p-2">{r.value.toFixed(2)}</td>
                <td className={`p-2 ${r.pnl>=0? 'text-green-400':'text-red-400'}`}>{r.pnl.toFixed(2)}</td>
                <td className={`p-2 ${r.pnlPct>=0? 'text-green-400':'text-red-400'}`}>{r.pnlPct.toFixed(2)}%</td>
                <td className="p-2">{new Date(r.updated_at).toLocaleTimeString()}</td>
              </tr>
            ))}
          </tbody>
          {rows.length > 0 && (
            <tfoot>
              <tr className="border-t border-gray-700">
                <td className="p-2 font-semibold" colSpan="4">Totals</td>
                <td className="p-2">{totals.value.toFixed(2)}</td>
                <td className={`p-2 ${totals.pnl>=0? 'text-green-400':'text-red-400'}`}>{totals.pnl.toFixed(2)}</td>
                <td className="p-2" colSpan="2"></td>
              </tr>
            </tfoot>
          )}
        </table>
      </div>
      <p className="mt-2 text-xs text-gray-500">Prices are fetched live from Binance when configured (WORKER_PRICE_SOURCE=binance). In dry‑run mode we never place real orders.</p>
    </Panel>
  )
}

function AIPanel() {
  const logs = useList('/ai/logs')
  const [symbol, setSymbol] = useState('BTCUSDT')
  const [intent, setIntent] = useState(null)
  const [loading, setLoading] = useState(false)
  const requestIntent = async () => {
    setLoading(true)
    setIntent(null)
    try {
      const res = await fetch(`${API}/v1/ai/intents/next?symbol=${encodeURIComponent(symbol)}&lot_size=${symbol.startsWith('BTC')? '0.001' : '0.01'}`)
      if (res.ok) {
        setIntent(await res.json())
      } else {
        setIntent({ error: `HTTP ${res.status}` })
      }
    } catch (e) {
      setIntent({ error: String(e) })
    } finally {
      setLoading(false)
    }
  }
  return (
    <Panel title="AI Panel (Explainability)">
      <div className="flex items-end gap-2 mb-3">
        <div>
          <label className="block text-sm text-gray-400">Symbol</label>
          <input value={symbol} onChange={(e) => setSymbol(e.target.value.toUpperCase())} className="mt-1 p-2 bg-gray-800 border border-gray-700 rounded" />
        </div>
        <button onClick={requestIntent} className="px-3 h-10 rounded bg-indigo-600 disabled:opacity-50" disabled={loading}>{loading? 'Thinking...' : 'Request Next Intent'}</button>
      </div>
      {intent && (
        <div className="p-3 mb-3 bg-gray-800 rounded">
          {intent.error ? (
            <div className="text-red-400 text-sm">{intent.error}</div>
          ) : (
            <div>
              <div className="text-sm text-gray-400">Intent for {intent.symbol}</div>
              <div className="mt-1"><span className="font-semibold">Action:</span> {intent.action} • <span className="font-semibold">Size:</span> {intent.size} • <span className="font-semibold">Conf:</span> {(intent.confidence*100).toFixed(1)}%</div>
              <div className="mt-1 text-gray-300">{intent.explanation}</div>
            </div>
          )}
        </div>
      )}
      <ul className="space-y-2">
        {logs.data.map((l) => (
          <li key={l.id} className="p-3 bg-gray-800 rounded">
            <div className="text-sm text-gray-400">#{l.id} • {new Date(l.ts).toLocaleTimeString()}</div>
            <div className="mt-1"><span className="font-semibold">Symbol:</span> {l.symbol_id} • <span className="font-semibold">Decision:</span> {l.decision} • <span className="font-semibold">Conf:</span> {(l.confidence*100).toFixed(1)}%</div>
            <div className="mt-1 text-gray-300">{l.rationale}</div>
          </li>
        ))}
      </ul>
    </Panel>
  )
}

function AdminPanel() {
  const [apiKey, setApiKey] = useState('')
  const [apiSecret, setApiSecret] = useState('')
  const [adminToken, setAdminToken] = useState('')
  const [status, setStatus] = useState({ provider: 'binance', api_key_masked: '', updated_at: null })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const loadStatus = async () => {
    setError('')
    try {
      const res = await fetch(`${API}/admin/credentials`, { headers: { 'X-Admin-Token': adminToken || '' }})
      if (!res.ok) throw new Error(`GET failed: ${res.status}`)
      setStatus(await res.json())
    } catch (e) {
      setError(String(e))
    }
  }

  useEffect(() => { /* no auto load until token is set by user */ }, [])

  const save = async (e) => {
    e.preventDefault()
    setSaving(true)
    setError('')
    try {
      const res = await fetch(`${API}/admin/credentials`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Admin-Token': adminToken || '' },
        body: JSON.stringify({ provider: 'binance', api_key: apiKey, api_secret: apiSecret })
      })
      if (!res.ok) throw new Error(`Save failed: ${res.status}`)
      const data = await res.json()
      setStatus(data)
      setApiSecret('')
    } catch (e) {
      setError(String(e))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Panel title="Admin (Binance Credentials)">
      <form onSubmit={save} className="space-y-3">
        <div>
          <label className="block text-sm text-gray-400">Admin Token (required)</label>
          <input value={adminToken} onChange={(e) => setAdminToken(e.target.value)} type="password" className="mt-1 w-full p-2 bg-gray-800 border border-gray-700 rounded" placeholder="Enter admin token" />
        </div>
        <div className="grid md:grid-cols-2 gap-3">
          <div>
            <label className="block text-sm text-gray-400">Binance API Key</label>
            <input value={apiKey} onChange={(e) => setApiKey(e.target.value)} className="mt-1 w-full p-2 bg-gray-800 border border-gray-700 rounded" placeholder="Paste API Key" />
          </div>
          <div>
            <label className="block text-sm text-gray-400">Binance API Secret</label>
            <input value={apiSecret} onChange={(e) => setApiSecret(e.target.value)} type="password" className="mt-1 w-full p-2 bg-gray-800 border border-gray-700 rounded" placeholder="Paste API Secret" />
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button disabled={saving || !adminToken} className="px-4 py-2 rounded bg-indigo-600 disabled:opacity-50">{saving? 'Saving...' : 'Save Credentials'}</button>
          <button type="button" onClick={loadStatus} disabled={!adminToken} className="px-3 py-2 rounded bg-gray-700 disabled:opacity-50">Refresh Status</button>
          {error && <span className="text-red-400 text-sm">{error}</span>}
        </div>
        <div className="text-sm text-gray-300">
          <div><span className="text-gray-400">Provider:</span> {status.provider}</div>
          <div><span className="text-gray-400">Stored Key (masked):</span> {status.api_key_masked || '—'}</div>
          <div><span className="text-gray-400">Updated:</span> {status.updated_at ? new Date(status.updated_at).toLocaleString() : '—'}</div>
        </div>
        <p className="text-xs text-gray-500">Your secret is encrypted server-side and never returned by the API. Keep your admin token private.</p>
      </form>
    </Panel>
  )
}

export default function App() {
  const [tab, setTab] = useState('monitor')
  return (
    <div className="max-w-6xl mx-auto p-6 space-y-4">
      <header className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Crypto AI Platform</h1>
        <nav className="flex gap-2">
          {[
            ['monitor','Monitor'],
            ['trading','Trading'],
            ['portfolio','Portfolio'],
            ['ai','AI Panel'],
            ['admin','Admin']
          ].map(([id, label]) => (
            <button key={id} onClick={() => setTab(id)} className={`px-3 py-1 rounded border ${tab===id? 'bg-indigo-600 border-indigo-500' : 'bg-gray-800 border-gray-700'} hover:opacity-90`}>
              {label}
            </button>
          ))}
        </nav>
      </header>
      {tab === 'monitor' && <MonitorUI />}
      {tab === 'trading' && <TradingUI />}
      {tab === 'portfolio' && <PortfolioUI />}
      {tab === 'ai' && <AIPanel />}
      {tab === 'admin' && <AdminPanel />}
      <footer className="text-xs text-gray-500">Paper trading mode. Backend: {API}</footer>
    </div>
  )
}
