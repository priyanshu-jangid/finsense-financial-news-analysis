import React, { useEffect, useState, useCallback } from 'react';
import { useAuth } from '../context/useAuth';
import { fetchCompanies, fetchCompanySentiment, triggerCompanySentimentAnalysis } from '../api/company';
import { fetchArticles, fetchCompanyArticles } from '../api/articles';
import { fetchUserWatchlist } from '../api/watchlist';
import type { Company, CompanySentimentSummary, Article } from '../types';
import { PageHeader } from '../components/PageHeader';
import { MetricCard } from '../components/MetricCard';
import { FilterToolbar } from '../components/FilterToolbar';
import { NewsFeed } from '../components/NewsFeed';
import { SentimentBadge } from '../components/SentimentBadge';
import { EmptyState } from '../components/EmptyState';
import { ErrorState } from '../components/ErrorState';
import {
  IconBuilding,
  IconNewspaper,
  IconTrendingUp,
  IconTrendingDown,
  IconActivity,
  IconBookmark,
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

export const Dashboard: React.FC = () => {
  const { user, isAuthenticated } = useAuth();

  // Data states
  const [companies, setCompanies] = useState<Company[]>([]);
  const [selectedCompanyId, setSelectedCompanyId] = useState<number | ''>('');
  const [startDate, setStartDate] = useState<string>('');
  const [endDate, setEndDate] = useState<string>('');
  const [summary, setSummary] = useState<CompanySentimentSummary | null>(null);
  const [articles, setArticles] = useState<Article[]>([]);
  const [totalArticlesCount, setTotalArticlesCount] = useState<number | null>(null);
  const [watchlistCount, setWatchlistCount] = useState<number | null>(null);

  // Status states
  const [loadingInitial, setLoadingInitial] = useState<boolean>(true);
  const [loadingSentiment, setLoadingSentiment] = useState<boolean>(false);
  const [loadingArticles, setLoadingArticles] = useState<boolean>(false);
  const [analyzing, setAnalyzing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);

  // Load initial companies and global articles count
  useEffect(() => {
    let active = true;
    const fetchInit = async () => {
      try {
        const [comps, arts] = await Promise.all([
          fetchCompanies(),
          fetchArticles(1, 10).catch(() => ({ total: 0, items: [], page: 1, page_size: 10, total_pages: 0 })),
        ]);
        if (!active) return;
        setCompanies(comps);
        setTotalArticlesCount(arts.total);

        if (comps.length > 0 && selectedCompanyId === '') {
          setSelectedCompanyId(comps[0].id);
        }

        if (isAuthenticated && user?.id) {
          try {
            const wl = await fetchUserWatchlist(user.id);
            if (active) setWatchlistCount(wl.length);
          } catch {
            if (active) setWatchlistCount(0);
          }
        }
      } catch (err: unknown) {
        if (!active) return;
        const msg = err instanceof Error ? err.message : 'Failed to connect to backend service';
        setError(msg);
      } finally {
        if (active) setLoadingInitial(false);
      }
    };

    fetchInit();
    return () => {
      active = false;
    };
  }, [isAuthenticated, user?.id, selectedCompanyId]);

  // Sentiment and company articles fetcher
  const loadSentimentAndArticles = useCallback(async (companyId?: number) => {
    const targetId = companyId ?? (typeof selectedCompanyId === 'number' ? selectedCompanyId : null);
    if (!targetId) {
      setSummary(null);
      setArticles([]);
      return;
    }

    setLoadingSentiment(true);
    setLoadingArticles(true);
    setError(null);
    setActionSuccess(null);

    try {
      const [sentData, compArticles] = await Promise.all([
        fetchCompanySentiment(
          targetId,
          startDate || undefined,
          endDate || undefined
        ),
        fetchCompanyArticles(targetId, 1, 15).catch(() => ({ total: 0, items: [], page: 1, page_size: 15, total_pages: 0 })),
      ]);

      setSummary(sentData);
      setArticles(compArticles.items || []);
      setLastUpdated(
        new Intl.DateTimeFormat('en-US', {
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit',
        }).format(new Date())
      );
    } catch {
      setError('Could not retrieve sentiment data for the selected company.');
      setSummary(null);
    } finally {
      setLoadingSentiment(false);
      setLoadingArticles(false);
    }
  }, [selectedCompanyId, startDate, endDate]);

  // Effect to load sentiment whenever company selection or dates change
  useEffect(() => {
    if (typeof selectedCompanyId !== 'number') return;
    let active = true;

    const run = async () => {
      try {
        const [sentData, compArticles] = await Promise.all([
          fetchCompanySentiment(selectedCompanyId, startDate || undefined, endDate || undefined),
          fetchCompanyArticles(selectedCompanyId, 1, 15).catch(() => ({ total: 0, items: [], page: 1, page_size: 15, total_pages: 0 })),
        ]);
        if (!active) return;
        setSummary(sentData);
        setArticles(compArticles.items || []);
        setLastUpdated(
          new Intl.DateTimeFormat('en-US', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
          }).format(new Date())
        );
      } catch {
        if (!active) return;
        setError('Could not retrieve sentiment data for the selected company.');
        setSummary(null);
      }
    };

    run();
    return () => {
      active = false;
    };
  }, [selectedCompanyId, startDate, endDate]);

  const handleApplyFilters = () => {
    if (typeof selectedCompanyId === 'number') {
      loadSentimentAndArticles(selectedCompanyId);
    }
  };

  const handleResetFilters = () => {
    setStartDate('');
    setEndDate('');
    if (companies.length > 0) {
      setSelectedCompanyId(companies[0].id);
    }
  };

  const handleRunAnalysis = async () => {
    if (typeof selectedCompanyId !== 'number') return;
    setAnalyzing(true);
    setError(null);
    setActionSuccess(null);
    try {
      const res = await triggerCompanySentimentAnalysis(selectedCompanyId);
      setActionSuccess(`Sentiment analysis completed! Processed ${res.created} new article analysis records.`);
      await loadSentimentAndArticles(selectedCompanyId);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Sentiment analysis service encountered an error.';
      setError(msg);
    } finally {
      setAnalyzing(false);
    }
  };

  const currentCompany = companies.find((c) => c.id === selectedCompanyId);

  // Distribution chart data
  const distributionData = summary
    ? [
        { name: 'Positive', count: summary.positive_count, color: '#16a34a' },
        { name: 'Neutral', count: summary.neutral_count, color: '#64748b' },
        { name: 'Negative', count: summary.negative_count, color: '#dc2626' },
      ]
    : [];

  const hasDistributionData = summary && summary.total_analyses > 0;

  // Trend chart data
  const trendData = summary?.daily_trend?.map((pt) => ({
    date: pt.date,
    count: pt.count,
    avgScore: pt.average_score !== null && pt.average_score !== undefined ? Number(pt.average_score.toFixed(2)) : 0,
  })) || [];

  return (
    <div className="fade-in">
      <PageHeader
        title="Market Intelligence"
        subtitle="Financial news aggregation and sentiment insights for your tracked watchlist."
        lastUpdated={lastUpdated}
        onRefresh={() => loadSentimentAndArticles()}
        isRefreshing={loadingSentiment || loadingArticles}
      />

      {error && <ErrorState message={error} onRetry={() => loadSentimentAndArticles()} />}

      {actionSuccess && (
        <div
          style={{
            padding: '12px 16px',
            backgroundColor: 'var(--sentiment-pos-bg)',
            border: '1px solid var(--sentiment-pos-border)',
            borderRadius: 'var(--radius-lg)',
            color: 'var(--sentiment-pos-text)',
            fontSize: '13px',
            marginBottom: '16px',
          }}
        >
          {actionSuccess}
        </div>
      )}

      {/* Row of Summary Metric Cards */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
          gap: '16px',
          marginBottom: '24px',
        }}
      >
        <MetricCard
          label="Watchlist Tracked"
          value={
            isAuthenticated
              ? (watchlistCount !== null ? watchlistCount : '—')
              : 'Log in to view'
          }
          subtitle={
            isAuthenticated
              ? 'Companies in your saved watchlist'
              : 'Secure user watchlist'
          }
          icon={<IconBookmark size={16} />}
          loading={loadingInitial}
        />

        <MetricCard
          label="Articles Available"
          value={totalArticlesCount !== null ? totalArticlesCount.toLocaleString() : '—'}
          subtitle="Total articles indexed in database"
          icon={<IconNewspaper size={16} />}
          loading={loadingInitial}
        />

        <MetricCard
          label="Positive Sentiment"
          value={summary ? summary.positive_count.toLocaleString() : '—'}
          subtitle={
            summary
              ? `${summary.total_analyses > 0 ? Math.round((summary.positive_count / summary.total_analyses) * 100) : 0}% of analyzed coverage`
              : 'Requires company selection'
          }
          icon={<IconTrendingUp size={16} />}
          tone="positive"
          loading={loadingSentiment}
        />

        <MetricCard
          label="Negative Sentiment"
          value={summary ? summary.negative_count.toLocaleString() : '—'}
          subtitle={
            summary
              ? `${summary.total_analyses > 0 ? Math.round((summary.negative_count / summary.total_analyses) * 100) : 0}% of analyzed coverage`
              : 'Requires company selection'
          }
          icon={<IconTrendingDown size={16} />}
          tone="negative"
          loading={loadingSentiment}
        />
      </div>

      {/* Filter Toolbar */}
      <FilterToolbar
        companies={companies}
        selectedCompany={selectedCompanyId}
        onSelectCompany={(id) => setSelectedCompanyId(id)}
        startDate={startDate}
        onStartDateChange={setStartDate}
        endDate={endDate}
        onEndDateChange={setEndDate}
        onApply={handleApplyFilters}
        onReset={handleResetFilters}
        isLoading={loadingSentiment || loadingArticles}
        onRunAnalysis={handleRunAnalysis}
        isAnalyzing={analyzing}
        isAuthenticated={isAuthenticated}
      />

      {/* Company Header Banner if selected */}
      {currentCompany && (
        <div
          className="fin-card"
          style={{
            marginBottom: '24px',
            padding: '16px 20px',
            display: 'flex',
            flexWrap: 'wrap',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '16px',
            backgroundColor: 'var(--bg-surface)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div
              style={{
                width: '42px',
                height: '42px',
                borderRadius: 'var(--radius-md)',
                backgroundColor: 'var(--accent-subtle)',
                color: 'var(--accent-text)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontWeight: 700,
                fontSize: '15px',
                fontFamily: 'var(--font-mono)',
              }}
            >
              {currentCompany.ticker.slice(0, 3)}
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <h2 style={{ fontSize: '18px', fontWeight: 700 }}>{currentCompany.name}</h2>
                <span className="fin-badge fin-badge-accent">{currentCompany.ticker}</span>
                {currentCompany.sector && (
                  <span
                    style={{
                      fontSize: '12px',
                      color: 'var(--text-muted)',
                      backgroundColor: 'var(--bg-surface-subtle)',
                      padding: '2px 8px',
                      borderRadius: 'var(--radius-sm)',
                    }}
                  >
                    {currentCompany.sector}
                  </span>
                )}
              </div>
              <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px' }}>
                {startDate || endDate
                  ? `Filtering analysis from ${startDate || 'earliest record'} to ${endDate || 'latest record'}`
                  : 'Displaying comprehensive sentiment across all historical dates'}
              </p>
            </div>
          </div>

          {summary && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                  Aggregate Score
                </div>
                <div
                  className="tabular-nums"
                  style={{
                    fontSize: '20px',
                    fontWeight: 700,
                    color:
                      summary.average_score === null || summary.average_score === undefined
                        ? 'var(--text-muted)'
                        : summary.average_score > 0
                        ? 'var(--sentiment-pos-text)'
                        : summary.average_score < 0
                        ? 'var(--sentiment-neg-text)'
                        : 'var(--text-primary)',
                  }}
                >
                  {summary.average_score !== null && summary.average_score !== undefined
                    ? `${summary.average_score > 0 ? '+' : ''}${summary.average_score.toFixed(2)}`
                    : 'N/A'}
                </div>
              </div>
              <SentimentBadge
                label={
                  summary.average_score !== null && summary.average_score !== undefined
                    ? summary.average_score > 0.05
                      ? 'Positive'
                      : summary.average_score < -0.05
                      ? 'Negative'
                      : 'Neutral'
                    : 'Unrated'
                }
              />
            </div>
          )}
        </div>
      )}

      {/* Main Grid: Sentiment Analysis & Visualizations */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))',
          gap: '24px',
          marginBottom: '24px',
        }}
      >
        {/* Sentiment Distribution Panel */}
        <div className="fin-card">
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              marginBottom: '16px',
            }}
          >
            <div>
              <h3 style={{ fontSize: '15px', fontWeight: 600 }}>Sentiment Distribution</h3>
              <p style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                Article classification breakdown for {currentCompany?.ticker || 'selected company'}
              </p>
            </div>
            {summary && (
              <span
                className="tabular-nums"
                style={{
                  fontSize: '11px',
                  fontWeight: 600,
                  color: 'var(--text-muted)',
                }}
              >
                {summary.total_analyses} Total Analysed
              </span>
            )}
          </div>

          {!selectedCompanyId ? (
            <EmptyState
              title="No company selected"
              description="Please choose a company from the filter toolbar above to view its sentiment distribution."
              icon={<IconBuilding size={20} />}
            />
          ) : !hasDistributionData ? (
            <EmptyState
              title="No sentiment analyses recorded"
              description={`There are currently no sentiment records for ${currentCompany?.name || 'this company'}.${
                isAuthenticated
                  ? ' Click "Trigger Analysis" to evaluate pending articles.'
                  : ' Sign in to trigger automated NLP sentiment analysis.'
              }`}
              action={
                isAuthenticated
                  ? { label: analyzing ? 'Analyzing…' : 'Trigger Analysis', onClick: handleRunAnalysis }
                  : undefined
              }
            />
          ) : (
            <div>
              {/* Distribution Badges Row */}
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(3, 1fr)',
                  gap: '12px',
                  marginBottom: '20px',
                }}
              >
                <div
                  style={{
                    padding: '10px 12px',
                    backgroundColor: 'var(--sentiment-pos-bg)',
                    border: '1px solid var(--sentiment-pos-border)',
                    borderRadius: 'var(--radius-md)',
                  }}
                >
                  <div style={{ fontSize: '11px', color: 'var(--sentiment-pos-text)', fontWeight: 600 }}>POSITIVE</div>
                  <div className="tabular-nums" style={{ fontSize: '18px', fontWeight: 700, color: 'var(--sentiment-pos-text)' }}>
                    {summary?.positive_count}
                  </div>
                  <div style={{ fontSize: '10px', color: 'var(--sentiment-pos-text)', opacity: 0.8 }}>
                    {summary ? Math.round((summary.positive_count / summary.total_analyses) * 100) : 0}% of total
                  </div>
                </div>

                <div
                  style={{
                    padding: '10px 12px',
                    backgroundColor: 'var(--sentiment-neu-bg)',
                    border: '1px solid var(--sentiment-neu-border)',
                    borderRadius: 'var(--radius-md)',
                  }}
                >
                  <div style={{ fontSize: '11px', color: 'var(--sentiment-neu-text)', fontWeight: 600 }}>NEUTRAL</div>
                  <div className="tabular-nums" style={{ fontSize: '18px', fontWeight: 700, color: 'var(--sentiment-neu-text)' }}>
                    {summary?.neutral_count}
                  </div>
                  <div style={{ fontSize: '10px', color: 'var(--sentiment-neu-text)', opacity: 0.8 }}>
                    {summary ? Math.round((summary.neutral_count / summary.total_analyses) * 100) : 0}% of total
                  </div>
                </div>

                <div
                  style={{
                    padding: '10px 12px',
                    backgroundColor: 'var(--sentiment-neg-bg)',
                    border: '1px solid var(--sentiment-neg-border)',
                    borderRadius: 'var(--radius-md)',
                  }}
                >
                  <div style={{ fontSize: '11px', color: 'var(--sentiment-neg-text)', fontWeight: 600 }}>NEGATIVE</div>
                  <div className="tabular-nums" style={{ fontSize: '18px', fontWeight: 700, color: 'var(--sentiment-neg-text)' }}>
                    {summary?.negative_count}
                  </div>
                  <div style={{ fontSize: '10px', color: 'var(--sentiment-neg-text)', opacity: 0.8 }}>
                    {summary ? Math.round((summary.negative_count / summary.total_analyses) * 100) : 0}% of total
                  </div>
                </div>
              </div>

              {/* Recharts Bar Chart */}
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
                        color: 'var(--text-primary)',
                      }}
                    />
                    <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                      {distributionData.map((entry, index) => (
                        <Cell
                          key={`cell-${index}`}
                          fill={entry.color}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}
        </div>

        {/* Sentiment Timeline Trend */}
        <div className="fin-card">
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              marginBottom: '16px',
            }}
          >
            <div>
              <h3 style={{ fontSize: '15px', fontWeight: 600 }}>Historical Sentiment Trend</h3>
              <p style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                Daily article volume and average sentiment trajectory over time
              </p>
            </div>
            <IconActivity size={16} style={{ color: 'var(--text-muted)' }} />
          </div>

          {trendData.length === 0 ? (
            <EmptyState
              title="No historical trend data"
              description="Historical trend points will plot here once multiple dates contain sentiment analysis records."
              icon={<IconActivity size={20} />}
            />
          ) : (
            <div style={{ height: '280px', width: '100%' }}>
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
                      color: 'var(--text-primary)',
                    }}
                  />
                  <Legend wrapperStyle={{ fontSize: '12px', paddingTop: '10px' }} />
                  <Line
                    type="monotone"
                    dataKey="count"
                    name="Analysis Volume"
                    stroke="#0284c7"
                    strokeWidth={2}
                    dot={{ r: 3 }}
                    activeDot={{ r: 5 }}
                  />
                  <Line
                    type="monotone"
                    dataKey="avgScore"
                    name="Average Score"
                    stroke="#16a34a"
                    strokeWidth={2}
                    dot={{ r: 3 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      </div>

      {/* Relevant News Section */}
      <NewsFeed
        articles={articles}
        title={currentCompany ? `Financial Coverage for ${currentCompany.name}` : 'Market Intelligence News Feed'}
        subtitle="Associated news items aggregated by FinSense"
        emptyMessage={`No news articles are linked to ${currentCompany?.name || 'the selected company'} yet.`}
        isLoading={loadingArticles}
      />
    </div>
  );
};

export default Dashboard;
