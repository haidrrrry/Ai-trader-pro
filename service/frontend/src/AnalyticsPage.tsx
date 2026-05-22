import { useEffect, useMemo, useState } from 'react'

import { API_BASE, useLanguage } from './appShared'

type AgentRanking = {
  agent_id: number
  name: string
  metrics: {
    total_return_pct: number
    sharpe_ratio: number
    sortino_ratio: number
    max_drawdown_pct: number
    trade_count: number
    position_count: number
    equity: number
    win_rate: number
  }
}

type PlatformSummary = {
  agent_count: number
  operation_signals: number
  open_positions: number
  total_cash: number
  active_copy_relationships: number
}

export function AnalyticsPage() {
  const { language } = useLanguage()
  const [summary, setSummary] = useState<PlatformSummary | null>(null)
  const [agents, setAgents] = useState<AgentRanking[]>([])
  const [metric, setMetric] = useState('sharpe_ratio')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const title = language === 'zh' ? 'Agent 分析看板' : 'Agent Analytics Dashboard'
  const subtitle =
    language === 'zh'
      ? '平台级统计 + 每个 Agent 的风险收益指标'
      : 'Platform stats and per-agent risk/return metrics'

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      setLoading(true)
      try {
        const [summaryRes, agentsRes] = await Promise.all([
          fetch(`${API_BASE}/analytics/summary`),
          fetch(`${API_BASE}/analytics/agents?limit=50&metric=${metric}`),
        ])
        const summaryData = await summaryRes.json()
        const agentsData = await agentsRes.json()
        if (!summaryRes.ok) throw new Error(summaryData.detail || 'summary_failed')
        if (!agentsRes.ok) throw new Error(agentsData.detail || 'agents_failed')
        if (!cancelled) {
          setSummary(summaryData)
          setAgents(agentsData.agents || [])
          setError(null)
        }
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : 'load_failed')
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => {
      cancelled = true
    }
  }, [metric])

  const metricOptions = useMemo(
    () => [
      { value: 'sharpe_ratio', label: 'Sharpe' },
      { value: 'sortino_ratio', label: 'Sortino' },
      { value: 'total_return', label: language === 'zh' ? '总收益' : 'Total Return' },
      { value: 'equity', label: language === 'zh' ? '权益' : 'Equity' },
      { value: 'trade_count', label: language === 'zh' ? '交易数' : 'Trades' },
    ],
    [language],
  )

  return (
    <div className="page-shell">
      <div className="page-header">
        <div>
          <h1>{title}</h1>
          <p className="page-subtitle">{subtitle}</p>
        </div>
        <select value={metric} onChange={(e) => setMetric(e.target.value)} className="input-select">
          {metricOptions.map((option) => (
            <option key={option.value} value={option.value}>
              {language === 'zh' ? '排序' : 'Sort'}: {option.label}
            </option>
          ))}
        </select>
      </div>

      {error && <div className="error-banner">{error}</div>}

      {summary && (
        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-label">{language === 'zh' ? 'Agent 数量' : 'Agents'}</div>
            <div className="stat-value">{summary.agent_count}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">{language === 'zh' ? '交易信号' : 'Trade Signals'}</div>
            <div className="stat-value">{summary.operation_signals}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">{language === 'zh' ? '持仓数' : 'Open Positions'}</div>
            <div className="stat-value">{summary.open_positions}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">{language === 'zh' ? '平台现金' : 'Platform Cash'}</div>
            <div className="stat-value">${summary.total_cash.toLocaleString()}</div>
          </div>
        </div>
      )}

      <div className="card">
        <div className="card-header">
          <h2>{language === 'zh' ? 'Agent 排名' : 'Agent Rankings'}</h2>
        </div>
        {loading ? (
          <p className="muted">{language === 'zh' ? '加载中…' : 'Loading…'}</p>
        ) : (
          <div className="table-container">
            <table className="table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>{language === 'zh' ? 'Agent' : 'Agent'}</th>
                  <th>{language === 'zh' ? '权益' : 'Equity'}</th>
                  <th>{language === 'zh' ? '收益%' : 'Return %'}</th>
                  <th>Sharpe</th>
                  <th>Sortino</th>
                  <th>{language === 'zh' ? '最大回撤%' : 'Max DD %'}</th>
                  <th>{language === 'zh' ? '胜率' : 'Win Rate'}</th>
                  <th>{language === 'zh' ? '交易' : 'Trades'}</th>
                </tr>
              </thead>
              <tbody>
                {agents.map((agent, index) => (
                  <tr key={agent.agent_id}>
                    <td>{index + 1}</td>
                    <td>{agent.name}</td>
                    <td>${agent.metrics.equity.toLocaleString()}</td>
                    <td>{agent.metrics.total_return_pct.toFixed(2)}%</td>
                    <td>{agent.metrics.sharpe_ratio.toFixed(3)}</td>
                    <td>{agent.metrics.sortino_ratio.toFixed(3)}</td>
                    <td>{agent.metrics.max_drawdown_pct.toFixed(2)}%</td>
                    <td>{(agent.metrics.win_rate * 100).toFixed(1)}%</td>
                    <td>{agent.metrics.trade_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
