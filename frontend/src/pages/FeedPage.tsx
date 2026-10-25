
/**
 * FeedPage — personalized news feed for the authenticated user.
 */
import React, { useEffect, useState, useCallback } from 'react';
import { NavLink } from 'react-router-dom';
import { useAuth } from '../context/useAuth';
import { fetchPersonalizedFeed } from '../api/articles';
import { fetchUserWatchlist } from '../api/watchlist';
import { fetchCompanies } from '../api/company';
import type { FeedArticle, WatchlistItem, Company } from '../types';
import { PageHeader } from '../components/PageHeader';
import { SentimentBadge } from '../components/SentimentBadge';
import { ErrorState } from '../components/ErrorState';
import { EmptyState } from '../components/EmptyState';
import {
  IconExternalLink,
  IconCalendar,
  IconNewspaper,
} from '../components/Icons';

const PAGE_SIZE = 20;
const SENTIMENTS = ['', 'positive', 'neutral', 'negative'] as const;

function formatDate(iso?: string | null): string {
  if (!iso) return 'Recent';

  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;

  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
}

interface ArticleCardProps {
  article: FeedArticle;
}

function ArticleCard({ article }: ArticleCardProps) {
  const matchedCompanies = article.matched_companies ?? [];
  const primarySentiment = matchedCompanies[0] ?? null;

  return (
    <div
      className="fin-card-interactive"
      style={{
        padding: '16px 20px',
        borderBottom: '1px solid var(--border-subtle)',
        transition: 'background-color 0.15s ease',
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'flex-start',
          justifyContent: 'space-between',
          gap: '16px',
        }}
      >
        <div style={{ flex: 1 }}>
          <div
            style={{
              display: 'flex',
              flexWrap: 'wrap',
              alignItems: 'center',
              gap: '6px',
              marginBottom: '6px',
            }}
          >
            {matchedCompanies.map((company) => (
              <span
                key={company.company_id}
                className="fin-badge fin-badge-accent"
                style={{ fontSize: '10px' }}
              >
                {company.company_ticker}
              </span>
            ))}

            <span
              style={{
                fontSize: '12px',
                fontWeight: 600,
                color: 'var(--text-primary)',
              }}
            >
              {article.source?.name || 'Financial Wire'}
            </span>

            <span style={{ color: 'var(--text-muted)', fontSize: '11px' }}>
              •
            </span>

            <span
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                fontSize: '11px',
                color: 'var(--text-muted)',
              }}
            >
              <IconCalendar size={11} />
              {formatDate(article.published_at || article.fetched_at)}
            </span>

            {primarySentiment && (
              <SentimentBadge
                label={primarySentiment.label}
                score={primarySentiment.score}
                confidence={primarySentiment.confidence}
                size="sm"
              />
            )}
          </div>

          <h4
            style={{
              fontSize: '14px',
              fontWeight: 600,
              lineHeight: 1.4,
            }}
          >
            <a
              href={article.url}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                color: 'var(--text-primary)',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
              }}
            >
              <span>{article.title}</span>
              <IconExternalLink
                size={12}
                style={{ color: 'var(--text-muted)', flexShrink: 0 }}
              />
            </a>
          </h4>

          {article.summary && (
            <p
              style={{
                fontSize: '12px',
                color: 'var(--text-secondary)',
                marginTop: '6px',
                lineHeight: 1.45,
                display: '-webkit-box',
                WebkitLineClamp: 2,
                WebkitBoxOrient: 'vertical',
                overflow: 'hidden',
              }}
            >
              {article.summary}
            </p>
          )}

          {matchedCompanies.length > 1 && (
            <div
              style={{
                display: 'flex',
                flexWrap: 'wrap',
                gap: '6px',
                marginTop: '8px',
              }}
            >
              {matchedCompanies.map((company) => (
                <span
                  key={company.company_id}
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '4px',
                  }}
                >
                  <span
                    style={{
                      fontSize: '10px',
                      fontWeight: 700,
                      color: 'var(--text-muted)',
                    }}
                  >
                    {company.company_ticker}
                  </span>
                  <SentimentBadge
                    label={company.label}
                    score={company.score}
                    confidence={company.confidence}
                    size="sm"
                  />
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export const FeedPage: React.FC = () => {
  const { user, isAuthenticated } = useAuth();
  const userId = user?.id;

  const [selectedCompanyId, setSelectedCompanyId] = useState<number | ''>('');
  const [selectedSentiment, setSelectedSentiment] = useState<string>('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [dateError, setDateError] = useState<string | null>(null);

  const [articles, setArticles] = useState<FeedArticle[]>([]);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [watchedCompanies, setWatchedCompanies] = useState<Company[]>([]);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load the user's watchlisted companies for the filter dropdown.
  useEffect(() => {
    if (!isAuthenticated || !userId) return;

    let active = true;

    const loadCompanies = async () => {
      try {
        const [watchlist, companies] = await Promise.all([
          fetchUserWatchlist(userId),
          fetchCompanies(),
        ]);

        if (!active) return;

        const companyIds = new Set(
          (watchlist as WatchlistItem[]).map((item) => item.company_id),
        );

        setWatchedCompanies(
          companies.filter((company) => companyIds.has(company.id)),
        );
      } catch {
        if (active) setWatchedCompanies([]);
      }
    };

    void loadCompanies();

    return () => {
      active = false;
    };
  }, [isAuthenticated, userId]);

  const loadFeed = useCallback(
    async (page: number, isActive: () => boolean = () => true) => {
      if (!userId) return;

      if (
        startDate &&
        endDate &&
        new Date(startDate).getTime() > new Date(endDate).getTime()
      ) {
        setDateError('Start date must not be after end date.');
        setArticles([]);
        setTotal(0);
        setTotalPages(0);
        return;
      }

      setDateError(null);
      setLoading(true);
      setError(null);

      try {
        const result = await fetchPersonalizedFeed(userId, {
          page,
          page_size: PAGE_SIZE,
          company_id:
            typeof selectedCompanyId === 'number'
              ? selectedCompanyId
              : null,
          sentiment: selectedSentiment || null,
          start_date: startDate
            ? new Date(startDate).toISOString()
            : null,
          end_date: endDate
            ? new Date(endDate).toISOString()
            : null,
        });

        if (!isActive()) return;

        setArticles(result.items);
        setTotal(result.total);
        setTotalPages(result.total_pages);
        setCurrentPage(result.page);
      } catch (err: unknown) {
        if (!isActive()) return;
        setError(
          err instanceof Error ? err.message : 'Failed to load feed.',
        );
      } finally {
        if (isActive()) setLoading(false);
      }
    },
    [
      userId,
      selectedCompanyId,
      selectedSentiment,
      startDate,
      endDate,
    ],
  );

  // Schedule loading after the effect runs and ignore stale requests.
  useEffect(() => {
    if (!isAuthenticated || !userId) return;

    let active = true;
    const timer = window.setTimeout(() => {
      void loadFeed(1, () => active);
    }, 0);

    return () => {
      active = false;
      window.clearTimeout(timer);
    };
  }, [isAuthenticated, userId, loadFeed]);

  const handleRefresh = useCallback(() => {
    void loadFeed(currentPage);
  }, [loadFeed, currentPage]);

  const handlePageChange = (page: number) => {
    if (page < 1 || page > totalPages || loading) return;
    void loadFeed(page);
  };

  if (!isAuthenticated) {
    return (
      <div className="fade-in">
        <PageHeader
          title="My News Feed"
          subtitle="Personalised articles from your watchlisted companies."
        />
        <div
          className="fin-card"
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '16px',
            flexWrap: 'wrap',
          }}
        >
          <div>
            <div
              style={{
                fontWeight: 600,
                color: 'var(--accent-text)',
                fontSize: '14px',
              }}
            >
              Sign in to view your feed
            </div>
            <div
              style={{
                fontSize: '13px',
                color: 'var(--text-secondary)',
                marginTop: '2px',
              }}
            >
              Your personalised feed requires an authenticated session.
            </div>
          </div>
          <div style={{ display: 'flex', gap: '8px' }}>
            <NavLink to="/login" className="fin-btn fin-btn-secondary fin-btn-sm">
              Sign In
            </NavLink>
            <NavLink to="/register" className="fin-btn fin-btn-primary fin-btn-sm">
              Register
            </NavLink>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="fade-in">
      <PageHeader
        title="My News Feed"
        subtitle="Articles from your watchlisted companies, sorted by recency."
        onRefresh={handleRefresh}
        isRefreshing={loading}
      />

      <div
        className="fin-card"
        style={{
          padding: '14px 20px',
          marginBottom: '20px',
          display: 'flex',
          flexWrap: 'wrap',
          gap: '12px',
          alignItems: 'flex-end',
        }}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', flex: '1 1 180px', minWidth: '140px' }}>
          <label htmlFor="feed-company-filter" style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-muted)' }}>
            Company
          </label>
          <select
            id="feed-company-filter"
            className="fin-input"
            value={selectedCompanyId}
            onChange={(event) => {
              setSelectedCompanyId(
                event.target.value === '' ? '' : Number(event.target.value),
              );
              setCurrentPage(1);
            }}
          >
            <option value="">All watchlisted</option>
            {watchedCompanies.map((company) => (
              <option key={company.id} value={company.id}>
                {company.ticker} — {company.name}
              </option>
            ))}
          </select>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', flex: '0 1 150px', minWidth: '120px' }}>
          <label htmlFor="feed-sentiment-filter" style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-muted)' }}>
            Sentiment
          </label>
          <select
            id="feed-sentiment-filter"
            className="fin-input"
            value={selectedSentiment}
            onChange={(event) => {
              setSelectedSentiment(event.target.value);
              setCurrentPage(1);
            }}
          >
            {SENTIMENTS.map((sentiment) => (
              <option key={sentiment} value={sentiment}>
                {sentiment
                  ? sentiment.charAt(0).toUpperCase() + sentiment.slice(1)
                  : 'All'}
              </option>
            ))}
          </select>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', flex: '1 1 160px', minWidth: '140px' }}>
          <label htmlFor="feed-start-date" style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-muted)' }}>
            From
          </label>
          <input
            id="feed-start-date"
            type="datetime-local"
            className="fin-input"
            value={startDate}
            onChange={(event) => {
              setStartDate(event.target.value);
              setCurrentPage(1);
            }}
          />
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', flex: '1 1 160px', minWidth: '140px' }}>
          <label htmlFor="feed-end-date" style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-muted)' }}>
            To
          </label>
          <input
            id="feed-end-date"
            type="datetime-local"
            className="fin-input"
            value={endDate}
            onChange={(event) => {
              setEndDate(event.target.value);
              setCurrentPage(1);
            }}
          />
        </div>

        {(selectedCompanyId !== '' || selectedSentiment || startDate || endDate) && (
          <button
            type="button"
            className="fin-btn fin-btn-ghost fin-btn-sm"
            style={{ alignSelf: 'flex-end' }}
            onClick={() => {
              setSelectedCompanyId('');
              setSelectedSentiment('');
              setStartDate('');
              setEndDate('');
              setDateError(null);
              setCurrentPage(1);
            }}
          >
            Clear
          </button>
        )}
      </div>

      {dateError && (
        <div
          role="alert"
          style={{
            marginBottom: '12px',
            padding: '10px 14px',
            backgroundColor: 'var(--sentiment-neg-bg)',
            border: '1px solid var(--sentiment-neg-border)',
            borderRadius: 'var(--radius-md)',
            fontSize: '13px',
            color: 'var(--sentiment-neg-text)',
          }}
        >
          {dateError}
        </div>
      )}

      {error && <ErrorState message={error} onRetry={handleRefresh} />}

      {!error && (
        <>
          {loading ? (
            <div className="fin-card" style={{ padding: 0, overflow: 'hidden' }}>
              <div style={{ padding: '14px 20px', borderBottom: '1px solid var(--border-subtle)' }}>
                <h3 style={{ fontSize: '15px', fontWeight: 600 }}>My Feed</h3>
              </div>
              <div style={{ padding: '16px 20px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {[1, 2, 3].map((item) => (
                  <div
                    key={item}
                    style={{
                      height: '72px',
                      backgroundColor: 'var(--bg-surface-subtle)',
                      borderRadius: 'var(--radius-md)',
                      animation: 'pulse 1.5s infinite',
                    }}
                  />
                ))}
              </div>
            </div>
          ) : articles.length === 0 ? (
            <EmptyState
              title="No articles in your feed"
              description={
                selectedCompanyId || selectedSentiment || startDate || endDate
                  ? 'No articles matched the selected filters. Try widening the criteria.'
                  : watchedCompanies.length === 0
                    ? 'Follow companies on your watchlist to see articles here.'
                    : 'No articles linked to your watchlisted companies yet. Run ingestion to populate.'
              }
              icon={<IconNewspaper size={20} />}
            />
          ) : (
            <div className="fin-card" style={{ padding: 0, overflow: 'hidden' }}>
              <div
                style={{
                  padding: '12px 20px',
                  borderBottom: '1px solid var(--border-subtle)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                }}
              >
                <h3 style={{ fontSize: '15px', fontWeight: 600 }}>My Feed</h3>
                <span
                  className="tabular-nums"
                  style={{
                    fontSize: '11px',
                    color: 'var(--text-muted)',
                    backgroundColor: 'var(--bg-surface-subtle)',
                    padding: '3px 8px',
                    borderRadius: 'var(--radius-sm)',
                    border: '1px solid var(--border-subtle)',
                  }}
                >
                  {total} article{total !== 1 ? 's' : ''}
                </span>
              </div>
              <div>
                {articles.map((article) => (
                  <ArticleCard key={article.id} article={article} />
                ))}
              </div>
            </div>
          )}

          {totalPages > 1 && (
            <div
              style={{
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                gap: '8px',
                marginTop: '20px',
              }}
            >
              <button
                type="button"
                className="fin-btn fin-btn-secondary fin-btn-sm"
                disabled={currentPage <= 1 || loading}
                onClick={() => handlePageChange(currentPage - 1)}
              >
                ← Prev
              </button>
              <span className="tabular-nums" style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                Page {currentPage} of {totalPages}
              </span>
              <button
                type="button"
                className="fin-btn fin-btn-secondary fin-btn-sm"
                disabled={currentPage >= totalPages || loading}
                onClick={() => handlePageChange(currentPage + 1)}
              >
                Next →
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default FeedPage;
