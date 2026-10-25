import React, { useEffect, useState, useCallback } from 'react';
import { useAuth } from '../context/useAuth';
import { fetchArticles, fetchCompanyArticles, triggerNewsIngestion, fetchIngestionStatus } from '../api/articles';
import { fetchCompanies } from '../api/company';
import type { Article, Company, IngestionStatus } from '../types';
import { PageHeader } from '../components/PageHeader';
import { NewsFeed } from '../components/NewsFeed';
import { ErrorState } from '../components/ErrorState';
import { IconSearch, IconBuilding, IconActivity, IconAlertCircle } from '../components/Icons';

export const NewsPage: React.FC = () => {
  const { isAuthenticated } = useAuth();

  const [articles, setArticles] = useState<Article[]>([]);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [totalPages, setTotalPages] = useState<number>(0);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedCompanyId, setSelectedCompanyId] = useState<number | ''>('');
  const [companies, setCompanies] = useState<Company[]>([]);

  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [ingesting, setIngesting] = useState<boolean>(false);
  const [ingestNotice, setIngestNotice] = useState<{ message: string; type: 'success' | 'warning' } | null>(null);
  const [ingestionStatus, setIngestionStatus] = useState<IngestionStatus | null>(null);

  // Load companies and ingestion status on mount
  useEffect(() => {
    let active = true;
    const loadMetadata = async () => {
      try {
        const [comps, status] = await Promise.all([
          fetchCompanies(),
          fetchIngestionStatus().catch(() => null),
        ]);
        if (!active) return;
        setCompanies(comps);
        if (status) setIngestionStatus(status);
      } catch {
        // Non-blocking
      }
    };
    loadMetadata();
    return () => {
      active = false;
    };
  }, []);

  const loadArticles = useCallback(async (page = 1) => {
    setLoading(true);
    setError(null);
    try {
      if (typeof selectedCompanyId === 'number' && selectedCompanyId > 0) {
        const data = await fetchCompanyArticles(selectedCompanyId, page, 15);
        setArticles(data.items || []);
        setTotalCount(data.total || 0);
        setTotalPages(data.total_pages || 0);
        setCurrentPage(data.page || 1);
      } else {
        const data = await fetchArticles(page, 15, searchQuery);
        setArticles(data.items || []);
        setTotalCount(data.total || 0);
        setTotalPages(data.total_pages || 0);
        setCurrentPage(data.page || 1);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to retrieve news articles';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [selectedCompanyId, searchQuery]);

  // Load articles whenever company filter or search changes
  useEffect(() => {
    let active = true;
    const fetchFeed = async () => {
      try {
        if (typeof selectedCompanyId === 'number' && selectedCompanyId > 0) {
          const data = await fetchCompanyArticles(selectedCompanyId, 1, 15);
          if (!active) return;
          setArticles(data.items || []);
          setTotalCount(data.total || 0);
          setTotalPages(data.total_pages || 0);
          setCurrentPage(data.page || 1);
        } else {
          const data = await fetchArticles(1, 15, searchQuery);
          if (!active) return;
          setArticles(data.items || []);
          setTotalCount(data.total || 0);
          setTotalPages(data.total_pages || 0);
          setCurrentPage(data.page || 1);
        }
      } catch (err: unknown) {
        if (!active) return;
        const msg = err instanceof Error ? err.message : 'Failed to retrieve news articles';
        setError(msg);
      } finally {
        if (active) setLoading(false);
      }
    };

    fetchFeed();
    return () => {
      active = false;
    };
  }, [selectedCompanyId, searchQuery]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    loadArticles(1);
  };

  const pollRef = React.useRef<ReturnType<typeof setInterval> | null>(null);

  const clearPolling = () => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  };

  const startPolling = () => {
    if (pollRef.current) return; // already polling
    pollRef.current = setInterval(async () => {
      try {
        const status = await fetchIngestionStatus();
        setIngestionStatus(status);
        const jobStatus = status.manual_job_status;
        if (jobStatus === 'success' || jobStatus === 'partial_failure' || jobStatus === 'failure') {
          clearPolling();
          if (jobStatus === 'success') {
            setIngestNotice({
              message: `Ingestion completed successfully: ${status.manual_job_total_persisted ?? 0} articles stored.`,
              type: 'success',
            });
          } else if (jobStatus === 'partial_failure') {
            setIngestNotice({
              message: `Ingestion completed with errors: ${status.manual_job_errors?.join('; ') ?? 'some issues occurred.'}`,
              type: 'warning',
            });
          } else {
            setIngestNotice({
              message: `Ingestion failed: ${status.manual_job_errors?.join('; ') ?? 'unknown error.'}`,
              type: 'warning',
            });
          }
          loadArticles(1);
        }
      } catch {
        clearPolling();
      }
    }, 3000);
  };

  // Cleanup on component unmount
  useEffect(() => {
    return () => {
      clearPolling();
    };
  }, []);

  const handleTriggerIngestion = async () => {
    if (!isAuthenticated) return;
    setIngesting(true);
    setIngestNotice(null);
    try {
      const res = await triggerNewsIngestion();
      if (res.status === 'queued') {
        startPolling();
        setIngestNotice({
          message: 'Ingestion job queued, processing in background.',
          type: 'success',
        });
      } else if (res.status === 'success' && (res.total_persisted as number) > 0) {
        setIngestNotice({
          message: `Ingestion completed: ${res.total_persisted} new articles stored.`,
          type: 'success',
        });
        loadArticles(1);
      } else {
        const errorList = (res.errors as string[]) || [];
        const errorMsg = errorList.length > 0 ? errorList.join('; ') : 'No new articles fetched (news provider returned 0 articles).';
        setIngestNotice({
          message: `Ingestion report: ${errorMsg}`,
          type: 'warning',
        });
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'News ingestion endpoint returned an error.';
      setIngestNotice({
        message: `Failed to trigger ingestion: ${msg}`,
        type: 'warning',
      });
    } finally {
      setIngesting(false);
    }
  };

  return (
    <div className="fade-in">
      <PageHeader
        title="Financial News Dispatches"
        subtitle="Aggregated macroeconomic, company-specific, and market intelligence articles."
        onRefresh={() => loadArticles(currentPage)}
        isRefreshing={loading}
        extraActions={
          isAuthenticated && (
            <button
              onClick={handleTriggerIngestion}
              disabled={ingesting}
              className="fin-btn fin-btn-secondary fin-btn-sm"
              title="Trigger live news ingestion scheduler"
              style={{
                borderColor: 'var(--accent-border)',
                color: 'var(--accent-text)',
                backgroundColor: 'var(--accent-subtle)',
              }}
            >
              <IconActivity size={13} />
              <span>{ingesting ? 'Ingesting Feeds…' : 'Trigger Ingestion'}</span>
            </button>
          )
        }
      />

      {error && <ErrorState message={error} onRetry={() => loadArticles(currentPage)} />}

      {ingestNotice && (
        <div
          style={{
            padding: '12px 16px',
            backgroundColor: ingestNotice.type === 'success' ? 'var(--sentiment-pos-bg)' : 'var(--warning-bg)',
            border: `1px solid ${ingestNotice.type === 'success' ? 'var(--sentiment-pos-border)' : 'var(--warning-border)'}`,
            borderRadius: 'var(--radius-lg)',
            color: ingestNotice.type === 'success' ? 'var(--sentiment-pos-text)' : 'var(--warning-text)',
            fontSize: '13px',
            marginBottom: '20px',
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
          }}
        >
          <IconAlertCircle size={16} style={{ flexShrink: 0 }} />
          <span>{ingestNotice.message}</span>
        </div>
      )}

      {/* Filter and Search Bar */}
      <div
        className="fin-card"
        style={{
          padding: '16px 20px',
          marginBottom: '24px',
          backgroundColor: 'var(--bg-surface)',
        }}
      >
        <div
          style={{
            display: 'flex',
            flexWrap: 'wrap',
            alignItems: 'flex-end',
            gap: '16px',
          }}
        >
          {/* Search Input */}
          <form
            onSubmit={handleSearchSubmit}
            style={{ flex: '2 1 280px', display: 'flex', flexDirection: 'column' }}
          >
            <label
              htmlFor="news-search"
              style={{
                fontSize: '11px',
                fontWeight: 600,
                textTransform: 'uppercase',
                letterSpacing: '0.04em',
                color: 'var(--text-muted)',
                marginBottom: '6px',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
              }}
            >
              <IconSearch size={13} />
              <span>Keyword Search</span>
            </label>
            <div style={{ display: 'flex', gap: '8px' }}>
              <input
                id="news-search"
                type="text"
                placeholder="Search headlines or summaries (e.g. earnings, fed, merger)…"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="fin-input"
                style={{ flex: 1 }}
              />
              <button type="submit" className="fin-btn fin-btn-secondary">
                Search
              </button>
            </div>
          </form>

          {/* Company Filter Dropdown */}
          <div style={{ flex: '1 1 200px' }}>
            <label
              htmlFor="company-news-filter"
              style={{
                fontSize: '11px',
                fontWeight: 600,
                textTransform: 'uppercase',
                letterSpacing: '0.04em',
                color: 'var(--text-muted)',
                marginBottom: '6px',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
              }}
            >
              <IconBuilding size={13} />
              <span>Company Scope</span>
            </label>
            <select
              id="company-news-filter"
              value={selectedCompanyId}
              onChange={(e) => setSelectedCompanyId(Number(e.target.value) || '')}
              className="fin-select"
              style={{ width: '100%' }}
            >
              <option value="">All Companies / Market-Wide</option>
              {companies.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.ticker} — {c.name}
                </option>
              ))}
            </select>
          </div>

          {/* Reset button */}
          {(searchQuery || selectedCompanyId) && (
            <button
              onClick={() => {
                setSearchQuery('');
                setSelectedCompanyId('');
              }}
              className="fin-btn fin-btn-ghost"
            >
              Clear
            </button>
          )}
        </div>
      </div>

      {/* Feed content */}
      <NewsFeed
        articles={articles}
        title={
          selectedCompanyId
            ? `Articles associated with ${companies.find((c) => c.id === selectedCompanyId)?.name || 'Company'}`
            : searchQuery
              ? `Articles matching "${searchQuery}"`
              : 'All Indexed News'
        }
        subtitle={`Showing ${articles.length} of ${totalCount} articles found`}
        emptyMessage={
          searchQuery
            ? `No articles match the keyword "${searchQuery}".`
            : selectedCompanyId
              ? 'No articles associated with this company in the database.'
              : 'No financial articles have been stored in the database yet. Trigger automated news ingestion to populate live coverage.'
        }
        isLoading={loading}
      />

      {/* Pagination Controls */}
      {totalPages > 1 && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginTop: '20px',
            padding: '12px 16px',
            backgroundColor: 'var(--bg-surface)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-lg)',
          }}
        >
          <span style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
            Page {currentPage} of {totalPages} ({totalCount} total)
          </span>

          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              onClick={() => loadArticles(currentPage - 1)}
              disabled={currentPage <= 1 || loading}
              className="fin-btn fin-btn-secondary fin-btn-sm"
            >
              Previous
            </button>
            <button
              onClick={() => loadArticles(currentPage + 1)}
              disabled={currentPage >= totalPages || loading}
              className="fin-btn fin-btn-secondary fin-btn-sm"
            >
              Next
            </button>
          </div>
        </div>
      )}

      {/* Ingestion status informational card */}
      {ingestionStatus && (
        <div
          className="fin-card"
          style={{
            marginTop: '32px',
            backgroundColor: 'var(--bg-surface-subtle)',
            borderStyle: 'dashed',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
            <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)' }}>
              Backend News Ingestion Service
            </span>
            <span
              className="fin-badge"
              style={{
                backgroundColor: ingestionStatus.is_scheduler_running ? 'var(--sentiment-pos-bg)' : 'var(--neutral-bg)',
                color: ingestionStatus.is_scheduler_running ? 'var(--sentiment-pos-text)' : 'var(--text-muted)',
                borderColor: 'transparent',
              }}
            >
              Scheduler: {ingestionStatus.is_scheduler_running ? 'Active' : 'Idle'} (Interval: {ingestionStatus.interval_hours}h)
            </span>
          </div>
          <p style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
            News ingestion connects to financial feeds (e.g., Marketaux, Finnhub, broad RSS feeds). Ingestion requires a valid provider API key configured in the environment variables.
          </p>
        </div>
      )}
    </div>
  );
};

export default NewsPage;
