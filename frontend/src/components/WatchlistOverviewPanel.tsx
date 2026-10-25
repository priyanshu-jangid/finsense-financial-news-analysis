/**
 * WatchlistOverviewPanel — displays the sentiment shift summary for each
 * watchlisted company. Called from WatchlistPage when the user is authenticated
 * and has companies on their watchlist.
 */
import React, { useEffect, useState, useCallback } from 'react';
import type { WatchlistOverviewResponse, WatchlistCompanyOverview } from '../types';
import { fetchWatchlistOverview } from '../api/watchlist';
import { SentimentBadge } from './SentimentBadge';
import {
  IconTrendingUp,
  IconTrendingDown,
  IconRefresh,
  IconNewspaper,
} from './Icons';

interface Props {
  userId: number;
}

const shiftLabel: Record<string, string> = {
  improving: 'Improving',
  deteriorating: 'Deteriorating',
  stable: 'Stable',
  insufficient_data: 'Insufficient data',
};

function ShiftChip({ status }: { status: string }) {
  const base: React.CSSProperties = {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '4px',
    padding: '2px 8px',
    borderRadius: 'var(--radius-full)',
    fontSize: '11px',
    fontWeight: 600,
    whiteSpace: 'nowrap',
  };

  if (status === 'improving') {
    return (
      <span style={{ ...base, backgroundColor: 'var(--sentiment-pos-bg)', color: 'var(--sentiment-pos-text)', border: '1px solid var(--sentiment-pos-border)' }}>
        <IconTrendingUp size={11} /> {shiftLabel[status]}
      </span>
    );
  }
  if (status === 'deteriorating') {
    return (
      <span style={{ ...base, backgroundColor: 'var(--sentiment-neg-bg)', color: 'var(--sentiment-neg-text)', border: '1px solid var(--sentiment-neg-border)' }}>
        <IconTrendingDown size={11} /> {shiftLabel[status]}
      </span>
    );
  }
  return (
    <span style={{ ...base, backgroundColor: 'var(--bg-surface-subtle)', color: 'var(--text-muted)', border: '1px solid var(--border-subtle)' }}>
      {shiftLabel[status] ?? status}
    </span>
  );
}

function fmt(iso: string | null) {
  if (!iso) return '—';
  try {
    return new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', year: 'numeric' }).format(new Date(iso));
  } catch { return iso; }
}

function fmtScore(n: number | null) {
  if (n === null) return '—';
  return (n > 0 ? '+' : '') + n.toFixed(3);
}

function CompanyRow({ c }: { c: WatchlistCompanyOverview }) {
  return (
    <tr>
      <td>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontWeight: 700, fontSize: '13px', color: 'var(--text-primary)' }}>{c.ticker}</span>
          <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>{c.name}</span>
        </div>
        {c.sector && <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>{c.sector}</div>}
      </td>
      <td>
        <ShiftChip status={c.shift_status} />
      </td>
      <td className="tabular-nums" style={{ fontSize: '12px' }}>
        {c.score_delta !== null ? (
          <span style={{ color: c.score_delta > 0 ? 'var(--sentiment-pos)' : c.score_delta < 0 ? 'var(--sentiment-neg)' : 'var(--text-muted)' }}>
            {fmtScore(c.score_delta)}
          </span>
        ) : <span style={{ color: 'var(--text-muted)' }}>—</span>}
      </td>
      <td className="tabular-nums" style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
        {c.current_window.average_score !== null ? c.current_window.average_score.toFixed(3) : '—'}
        <span style={{ color: 'var(--text-muted)', margin: '0 4px' }}>vs</span>
        {c.previous_window.average_score !== null ? c.previous_window.average_score.toFixed(3) : '—'}
      </td>
      <td className="tabular-nums" style={{ fontSize: '12px' }}>
        <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
          <SentimentBadge label="positive" score={null} confidence={null} size="sm" />
          <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{c.current_label_counts.positive}</span>
          <SentimentBadge label="negative" score={null} confidence={null} size="sm" />
          <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{c.current_label_counts.negative}</span>
        </div>
      </td>
      <td className="tabular-nums" style={{ fontSize: '12px', color: c.negative_article_count > 0 ? 'var(--sentiment-neg)' : 'var(--text-muted)' }}>
        {c.negative_article_count}
      </td>
      <td style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
        {fmt(c.latest_article_published_at)}
      </td>
    </tr>
  );
}

export const WatchlistOverviewPanel: React.FC<Props> = ({ userId }) => {
  const [overview, setOverview] = useState<WatchlistOverviewResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchWatchlistOverview(userId);
      setOverview(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load overview.');
    } finally {
      setLoading(false);
    }
  }, [userId]);

  useEffect(() => {
    let active = true;

    const run = async () => {
      if (!active) return;
      await load();
    };
    void Promise.resolve().then(run);

    return () => {
      active = false;
    };
  }, [load]);

  if (loading) {
    return (
      <div className="fin-card" style={{ marginBottom: '20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
          <h3 style={{ fontSize: '15px', fontWeight: 600 }}>Sentiment Shift Overview</h3>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {[1, 2, 3].map(i => (
            <div key={i} style={{ height: '40px', backgroundColor: 'var(--bg-surface-subtle)', borderRadius: 'var(--radius-md)', animation: 'pulse 1.5s infinite' }} />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="fin-card" style={{ marginBottom: '20px', borderColor: 'var(--sentiment-neg-border)', backgroundColor: 'var(--sentiment-neg-bg)' }}>
        <div style={{ fontSize: '13px', color: 'var(--sentiment-neg-text)' }}>Could not load overview: {error}</div>
        <button className="fin-btn fin-btn-secondary fin-btn-sm" onClick={load} style={{ marginTop: '8px' }}>Retry</button>
      </div>
    );
  }

  if (!overview || overview.companies.length === 0) {
    return (
      <div className="fin-card" style={{ marginBottom: '20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
          <h3 style={{ fontSize: '15px', fontWeight: 600 }}>Sentiment Shift Overview</h3>
        </div>
        <div style={{ padding: '24px', textAlign: 'center', color: 'var(--text-muted)', backgroundColor: 'var(--bg-surface-subtle)', borderRadius: 'var(--radius-md)', border: '1px dashed var(--border-subtle)' }}>
          <IconNewspaper size={20} style={{ marginBottom: '6px', opacity: 0.5 }} />
          <div style={{ fontSize: '13px' }}>No companies with recent sentiment data. Follow companies and run ingestion to populate this panel.</div>
        </div>
      </div>
    );
  }

  const { totals, companies, window_days } = overview;

  return (
    <div className="fin-card" style={{ marginBottom: '20px', padding: 0, overflow: 'hidden' }}>
      {/* Header */}
      <div style={{ padding: '14px 20px', borderBottom: '1px solid var(--border-subtle)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
        <div>
          <h3 style={{ fontSize: '15px', fontWeight: 600 }}>Sentiment Shift Overview</h3>
          <p style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>
            {window_days}-day comparison window · as of {fmt(overview.as_of)}
          </p>
        </div>
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          {/* Summary chips */}
          <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
            <strong className="tabular-nums" style={{ color: 'var(--text-primary)' }}>{totals.companies_with_sentiment_shift}</strong> shifting
          </span>
          <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
            <strong className="tabular-nums" style={{ color: totals.negative_article_count > 0 ? 'var(--sentiment-neg)' : 'var(--text-primary)' }}>{totals.negative_article_count}</strong> neg. articles
          </span>
          <button className="fin-btn fin-btn-ghost fin-btn-sm" onClick={load} title="Refresh overview">
            <IconRefresh size={13} />
          </button>
        </div>
      </div>

      {/* Table */}
      <div className="fin-table-container">
        <table className="fin-table">
          <thead>
            <tr>
              <th>Company</th>
              <th>Shift</th>
              <th>Δ Score</th>
              <th>Avg (cur / prev)</th>
              <th>Label breakdown</th>
              <th>Neg. articles</th>
              <th>Latest article</th>
            </tr>
          </thead>
          <tbody>
            {companies.map(c => <CompanyRow key={c.company_id} c={c} />)}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default WatchlistOverviewPanel;
