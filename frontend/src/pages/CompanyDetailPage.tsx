import React, { useEffect, useState, useCallback } from 'react';
import { useParams, NavLink } from 'react-router-dom';
import { useAuth } from '../context/useAuth';
import { fetchCompanyById, fetchCompanySentiment, triggerCompanySentimentAnalysis } from '../api/company';
import { fetchCompanyArticles } from '../api/articles';
import { fetchUserWatchlist, addToWatchlist, removeFromWatchlist } from '../api/watchlist';
import type { Company, CompanySentimentSummary, Article } from '../types';
import { PageHeader } from '../components/PageHeader';
import { MetricCard } from '../components/MetricCard';
import { NewsFeed } from '../components/NewsFeed';
import { EmptyState } from '../components/EmptyState';
import { ErrorState } from '../components/ErrorState';
import {
  IconCheck,
  IconPlus,
  IconTrendingUp,
  IconTrendingDown,
  IconActivity,
  IconNewspaper,
} from '../components/Icons';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ResponsiveContainer,
  BarChart,
  Bar,
  Cell,
  Legend,
} from 'recharts';

export const CompanyDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const companyId = Number(id);

  const { user, isAuthenticated } = useAuth();

  const [company, setCompany] = useState<Company | null>(null);
  const [summary, setSummary] = useState<CompanySentimentSummary | null>(null);
  const [articles, setArticles] = useState<Article[]>([]);
  const [isWatched, setIsWatched] = useState<boolean>(false);

  const [loading, setLoading] = useState<boolean>(true);
  const [analyzing, setAnalyzing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [actionNotice, setActionNotice] = useState<string | null>(null);

  useEffect(() => {
    if (!companyId) return;
    let active = true;

    const loadData = async () => {
      try {
        const [comp, sent, arts] = await Promise.all([
          fetchCompanyById(companyId),
          fetchCompanySentiment(companyId),
          fetchCompanyArticles(companyId, 1, 20).catch(() => ({ items: [], total: 0, page: 1, page_size: 20, total_pages: 0 })),
        ]);
        if (!active) return;
        setCompany(comp);
        setSummary(sent);
        setArticles(arts.items || []);

        if (isAuthenticated && user?.id) {
          try {
            const wl = await fetchUserWatchlist(user.id);
            if (active) setIsWatched(wl.some((item) => item.company_id === companyId));
          } catch {
            if (active) setIsWatched(false);
          }
        }
      } catch (err: unknown) {
        if (!active) return;
        const msg = err instanceof Error ? err.message : 'Failed to retrieve company profile';
        setError(msg);
      } finally {
        if (active) setLoading(false);
      }
    };

    loadData();
    return () => {
      active = false;
    };
  }, [companyId, isAuthenticated, user?.id]);

  const refreshData = useCallback(async () => {
    if (!companyId) return;
    setLoading(true);
    setError(null);
    try {
      const [comp, sent, arts] = await Promise.all([
        fetchCompanyById(companyId),
        fetchCompanySentiment(companyId),
        fetchCompanyArticles(companyId, 1, 20).catch(() => ({ items: [], total: 0, page: 1, page_size: 20, total_pages: 0 })),
      ]);

      setCompany(comp);
      setSummary(sent);
      setArticles(arts.items || []);

      if (isAuthenticated && user?.id) {
        try {
          const wl = await fetchUserWatchlist(user.id);
          setIsWatched(wl.some((item) => item.company_id === companyId));
        } catch {
          setIsWatched(false);
        }
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to retrieve company profile';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [companyId, isAuthenticated, user]);

  const handleToggleWatchlist = async () => {
    if (!isAuthenticated || !user?.id || !company) return;
    try {
      if (isWatched) {
        await removeFromWatchlist(user.id, company.id);
        setIsWatched(false);
        setActionNotice(`Removed ${company.ticker} from watchlist.`);
      } else {
        await addToWatchlist(user.id, company.id);
        setIsWatched(true);
        setActionNotice(`Added ${company.ticker} to watchlist.`);
      }
    } catch {
      setError('Could not update watchlist status.');
    }
  };

  const handleTriggerAnalysis = async () => {
    if (!companyId) return;
    setAnalyzing(true);
    setError(null);
    try {
      const res = await triggerCompanySentimentAnalysis(companyId);
      setActionNotice(`Analysis finished: created ${res.created} sentiment analysis rows.`);
      const sent = await fetchCompanySentiment(companyId);
      setSummary(sent);
    } catch {
      setError('Failed to execute sentiment analysis engine.');
    } finally {
      setAnalyzing(false);
    }
  };

  const distributionData = summary
    ? [
        { name: 'Positive', count: summary.positive_count, color: '#16a34a' },
        { name: 'Neutral', count: summary.neutral_count, color: '#64748b' },
        { name: 'Negative', count: summary.negative_count, color: '#dc2626' },
      ]
    : [];

  const trendData = summary?.daily_trend?.map((pt) => ({
    date: pt.date,
    count: pt.count,
    avgScore: pt.average_score !== null && pt.average_score !== undefined ? Number(pt.average_score.toFixed(2)) : 0,
  })) || [];

  if (loading && !company) {
    return (
      <div style={{ padding: '48px 0', textAlign: 'center' }}>
        <div style={{ fontSize: '14px', color: 'var(--text-muted)' }}>Loading company intelligence…</div>
      </div>
    );
  }

  return (
    <div className="fade-in">
      {/* Breadcrumb back to dashboard */}
      <div style={{ marginBottom: '16px' }}>
        <NavLink
          to="/"
          style={{
            fontSize: '12px',
            color: 'var(--text-muted)',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '4px',
          }}
        >
          ← Back to Market Intelligence Dashboard
        </NavLink>
      </div>

      <PageHeader
        title={company ? `${company.name} (${company.ticker})` : 'Company Intelligence'}
        subtitle={company?.sector ? `Sector: ${company.sector}` : 'Institutional Company Research'}
        onRefresh={refreshData}
        isRefreshing={loading}
        extraActions={
          <div style={{ display: 'flex', gap: '8px' }}>
            {isAuthenticated && company && (
              <button
                onClick={handleToggleWatchlist}
                className={`fin-btn fin-btn-sm ${isWatched ? 'fin-btn-secondary' : 'fin-btn-primary'}`}
              >
                {isWatched ? (
                  <>
                    <IconCheck size={11} />
                    <span>Watchlist Tracked</span>
                  </>
                ) : (
                  <>
                    <IconPlus size={11} />
                    <span>Add to Watchlist</span>
                  </>
                )}
              </button>
            )}
            {isAuthenticated && (
              <button
                onClick={handleTriggerAnalysis}
                disabled={analyzing}
                className="fin-btn fin-btn-secondary fin-btn-sm"
              >
                <IconActivity size={12} />
                <span>{analyzing ? 'Analyzing…' : 'Trigger Sentiment NLP'}</span>
              </button>
            )}
          </div>
        }
      />

      {error && <ErrorState message={error} onRetry={refreshData} />}

      {actionNotice && (
        <div
          style={{
            padding: '10px 14px',
            backgroundColor: 'var(--sentiment-pos-bg)',
            border: '1px solid var(--sentiment-pos-border)',
            borderRadius: 'var(--radius-md)',
            color: 'var(--sentiment-pos-text)',
            fontSize: '12px',
            marginBottom: '16px',
          }}
        >
          {actionNotice}
        </div>
      )}

      {/* Metrics Row */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: '16px',
          marginBottom: '24px',
        }}
      >
        <MetricCard
          label="Aggregate Score"
          value={
            summary?.average_score !== null && summary?.average_score !== undefined
              ? `${summary.average_score > 0 ? '+' : ''}${summary.average_score.toFixed(2)}`
              : 'N/A'
          }
          subtitle="Polarity score (-1.0 to +1.0)"
          tone={
            summary?.average_score && summary.average_score > 0
              ? 'positive'
              : summary?.average_score && summary.average_score < 0
              ? 'negative'
              : 'default'
          }
        />
        <MetricCard
          label="Total Analyses"
          value={summary ? summary.total_analyses : 0}
          subtitle="Processed news records"
          icon={<IconNewspaper size={16} />}
        />
        <MetricCard
          label="Positive Signals"
          value={summary ? summary.positive_count : 0}
          subtitle={
            summary && summary.total_analyses > 0
              ? `${Math.round((summary.positive_count / summary.total_analyses) * 100)}% of total`
              : '—'
          }
          tone="positive"
          icon={<IconTrendingUp size={16} />}
        />
        <MetricCard
          label="Negative Signals"
          value={summary ? summary.negative_count : 0}
          subtitle={
            summary && summary.total_analyses > 0
              ? `${Math.round((summary.negative_count / summary.total_analyses) * 100)}% of total`
              : '—'
          }
          tone="negative"
          icon={<IconTrendingDown size={16} />}
        />
      </div>

      {/* Charts Grid */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))',
          gap: '24px',
          marginBottom: '24px',
        }}
      >
        {/* Distribution */}
        <div className="fin-card">
          <h3 style={{ fontSize: '15px', fontWeight: 600, marginBottom: '16px' }}>Sentiment Breakdown</h3>
          {summary && summary.total_analyses > 0 ? (
            <div style={{ height: '220px', width: '100%' }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={distributionData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border-subtle)" />
                  <XAxis dataKey="name" stroke="var(--text-muted)" fontSize={12} tickLine={false} />
                  <YAxis stroke="var(--text-muted)" fontSize={12} tickLine={false} axisLine={false} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'var(--bg-surface)',
                      borderColor: 'var(--border-default)',
                      borderRadius: '6px',
                    }}
                  />
                  <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                    {distributionData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <EmptyState
              title="No sentiment analyses recorded"
              description="Articles have not yet been evaluated for this specific company."
            />
          )}
        </div>

        {/* Trend */}
        <div className="fin-card">
          <h3 style={{ fontSize: '15px', fontWeight: 600, marginBottom: '16px' }}>Daily Sentiment Trajectory</h3>
          {trendData.length > 0 ? (
            <div style={{ height: '220px', width: '100%' }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={trendData} margin={{ top: 10, right: 20, left: -10, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border-subtle)" />
                  <XAxis dataKey="date" stroke="var(--text-muted)" fontSize={11} tickLine={false} />
                  <YAxis stroke="var(--text-muted)" fontSize={11} tickLine={false} axisLine={false} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'var(--bg-surface)',
                      borderColor: 'var(--border-default)',
                      borderRadius: '6px',
                    }}
                  />
                  <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '8px' }} />
                  <Line type="monotone" dataKey="count" name="Articles" stroke="#0284c7" strokeWidth={2} dot={{ r: 3 }} />
                  <Line type="monotone" dataKey="avgScore" name="Avg Score" stroke="#16a34a" strokeWidth={2} dot={{ r: 3 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <EmptyState
              title="No historical trend"
              description="Historical trend points will appear once multiple analysis dates exist."
            />
          )}
        </div>
      </div>

      {/* News Feed */}
      <NewsFeed
        articles={articles}
        title={`Recent News Coverage for ${company?.name || 'Company'}`}
        subtitle="Articles indexed and linked to this company"
        emptyMessage="No articles have been indexed for this company yet."
        isLoading={loading}
      />
    </div>
  );
};

export default CompanyDetailPage;
