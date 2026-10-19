import React, { useEffect, useState, useCallback } from 'react';
import { NavLink } from 'react-router-dom';
import { useAuth } from '../context/useAuth';
import { fetchCompanies } from '../api/company';
import { fetchUserWatchlist, addToWatchlist, removeFromWatchlist } from '../api/watchlist';
import type { Company, WatchlistItem } from '../types';
import { PageHeader } from '../components/PageHeader';
import { ErrorState } from '../components/ErrorState';
import { EmptyState } from '../components/EmptyState';
import {
  IconSearch,
  IconCheck,
  IconPlus,
  IconBuilding,
} from '../components/Icons';

export const WatchlistPage: React.FC = () => {
  const { user, isAuthenticated } = useAuth();

  const [companies, setCompanies] = useState<Company[]>([]);
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>([]);
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [activeTab, setActiveTab] = useState<'all' | 'watched'>('all');

  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [actionCompanyId, setActionCompanyId] = useState<number | null>(null);

  // Load companies and user watchlist on mount or auth change
  useEffect(() => {
    let active = true;
    const fetchData = async () => {
      try {
        const comps = await fetchCompanies();
        if (!active) return;
        setCompanies(comps);

        if (isAuthenticated && user?.id) {
          const wl = await fetchUserWatchlist(user.id);
          if (!active) return;
          setWatchlist(wl);
        } else {
          if (!active) return;
          setWatchlist([]);
        }
      } catch (err: unknown) {
        if (!active) return;
        const msg = err instanceof Error ? err.message : 'Failed to retrieve watchlist data.';
        setError(msg);
      } finally {
        if (active) setLoading(false);
      }
    };

    fetchData();
    return () => {
      active = false;
    };
  }, [isAuthenticated, user?.id]);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const comps = await fetchCompanies();
      setCompanies(comps);

      if (isAuthenticated && user?.id) {
        const wl = await fetchUserWatchlist(user.id);
        setWatchlist(wl);
      } else {
        setWatchlist([]);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to retrieve watchlist data.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [isAuthenticated, user]);

  // Set of watched company IDs
  const watchedCompanyIds = new Set(watchlist.map((item) => item.company_id));

  const handleToggleWatchlist = async (company: Company) => {
    if (!isAuthenticated || !user?.id) return;
    const isWatched = watchedCompanyIds.has(company.id);
    setActionCompanyId(company.id);
    setError(null);

    try {
      if (isWatched) {
        await removeFromWatchlist(user.id, company.id);
        setWatchlist((prev) => prev.filter((item) => item.company_id !== company.id));
      } else {
        const newItem = await addToWatchlist(user.id, company.id);
        setWatchlist((prev) => [...prev, newItem]);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Could not update watchlist.';
      setError(msg);
    } finally {
      setActionCompanyId(null);
    }
  };

  // Filtered companies based on search and tab
  const filteredCompanies = companies.filter((c) => {
    const matchesSearch =
      c.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      c.ticker.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (c.sector && c.sector.toLowerCase().includes(searchTerm.toLowerCase()));

    if (activeTab === 'watched') {
      return matchesSearch && watchedCompanyIds.has(c.id);
    }
    return matchesSearch;
  });

  return (
    <div className="fade-in">
      <PageHeader
        title="Institutional Watchlist"
        subtitle="Curate and monitor targeted companies for sentiment shifts and incoming news coverage."
        onRefresh={loadData}
        isRefreshing={loading}
      />

      {error && <ErrorState message={error} onRetry={loadData} />}

      {!isAuthenticated && (
        <div
          className="fin-card"
          style={{
            marginBottom: '24px',
            backgroundColor: 'var(--accent-subtle)',
            borderColor: 'var(--accent-border)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '16px',
            flexWrap: 'wrap',
          }}
        >
          <div>
            <div style={{ fontWeight: 600, color: 'var(--accent-text)', fontSize: '14px' }}>
              Authentication Required for Watchlist Storage
            </div>
            <div style={{ fontSize: '13px', color: 'var(--text-secondary)', marginTop: '2px' }}>
              Sign in with your FinSense account to create and maintain your personalized company watchlist.
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
      )}

      {/* Control Bar: Search & Tabs */}
      <div
        className="fin-card"
        style={{
          padding: '16px 20px',
          marginBottom: '20px',
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '16px',
        }}
      >
        {/* Search */}
        <div style={{ position: 'relative', flex: '1 1 260px', minWidth: '220px' }}>
          <IconSearch
            size={14}
            style={{
              position: 'absolute',
              left: '12px',
              top: '50%',
              transform: 'translateY(-50%)',
              color: 'var(--text-muted)',
            }}
          />
          <input
            type="text"
            placeholder="Search company directory by ticker, name, or sector…"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="fin-input"
            style={{ width: '100%', paddingLeft: '34px' }}
          />
        </div>

        {/* Tab Switcher */}
        <div
          style={{
            display: 'inline-flex',
            backgroundColor: 'var(--bg-surface-subtle)',
            borderRadius: 'var(--radius-md)',
            padding: '3px',
            border: '1px solid var(--border-subtle)',
          }}
        >
          <button
            onClick={() => setActiveTab('all')}
            style={{
              padding: '6px 14px',
              fontSize: '12px',
              fontWeight: 600,
              borderRadius: 'var(--radius-sm)',
              border: 'none',
              cursor: 'pointer',
              backgroundColor: activeTab === 'all' ? 'var(--bg-surface)' : 'transparent',
              color: activeTab === 'all' ? 'var(--text-primary)' : 'var(--text-muted)',
              boxShadow: activeTab === 'all' ? 'var(--shadow-xs)' : 'none',
              transition: 'all 0.15s ease',
            }}
          >
            All Companies ({companies.length})
          </button>
          <button
            onClick={() => setActiveTab('watched')}
            style={{
              padding: '6px 14px',
              fontSize: '12px',
              fontWeight: 600,
              borderRadius: 'var(--radius-sm)',
              border: 'none',
              cursor: 'pointer',
              backgroundColor: activeTab === 'watched' ? 'var(--bg-surface)' : 'transparent',
              color: activeTab === 'watched' ? 'var(--text-primary)' : 'var(--text-muted)',
              boxShadow: activeTab === 'watched' ? 'var(--shadow-xs)' : 'none',
              transition: 'all 0.15s ease',
            }}
          >
            My Watchlist ({watchedCompanyIds.size})
          </button>
        </div>
      </div>

      {/* Directory Table */}
      {filteredCompanies.length === 0 ? (
        <EmptyState
          title={
            activeTab === 'watched'
              ? 'Your watchlist is empty'
              : searchTerm
              ? 'No matching companies found'
              : 'No companies registered'
          }
          description={
            activeTab === 'watched'
              ? 'Browse the complete company directory to follow securities and track market sentiment.'
              : searchTerm
              ? `No companies matched "${searchTerm}". Try another search keyword.`
              : 'The database does not contain any companies yet.'
          }
          icon={<IconBuilding size={20} />}
          action={
            activeTab === 'watched'
              ? { label: 'View All Companies', onClick: () => setActiveTab('all') }
              : undefined
          }
        />
      ) : (
        <div className="fin-table-container">
          <table className="fin-table">
            <thead>
              <tr>
                <th style={{ width: '100px' }}>Ticker</th>
                <th>Company Name</th>
                <th>Sector</th>
                <th style={{ width: '140px', textAlign: 'center' }}>Watchlist Status</th>
                <th style={{ width: '130px', textAlign: 'right' }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {filteredCompanies.map((company) => {
                const isWatched = watchedCompanyIds.has(company.id);
                const isPending = actionCompanyId === company.id;

                return (
                  <tr key={company.id}>
                    <td>
                      <span
                        className="tabular-nums"
                        style={{
                          fontWeight: 700,
                          fontSize: '13px',
                          color: 'var(--text-primary)',
                        }}
                      >
                        {company.ticker}
                      </span>
                    </td>
                    <td>
                      <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                        {company.name}
                      </div>
                    </td>
                    <td>
                      <span style={{ color: 'var(--text-muted)', fontSize: '12px' }}>
                        {company.sector || 'Unassigned'}
                      </span>
                    </td>
                    <td style={{ textAlign: 'center' }}>
                      {isWatched ? (
                        <span
                          className="fin-badge fin-badge-pos"
                          style={{ fontSize: '10px' }}
                        >
                          <IconCheck size={10} />
                          <span>Tracked</span>
                        </span>
                      ) : (
                        <span
                          style={{
                            fontSize: '11px',
                            color: 'var(--text-muted)',
                          }}
                        >
                          Not followed
                        </span>
                      )}
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <div style={{ display: 'inline-flex', gap: '8px', alignItems: 'center' }}>
                        {isAuthenticated ? (
                          <button
                            onClick={() => handleToggleWatchlist(company)}
                            disabled={isPending}
                            className={`fin-btn fin-btn-sm ${
                              isWatched ? 'fin-btn-secondary' : 'fin-btn-primary'
                            }`}
                            style={{ minWidth: '94px' }}
                          >
                            {isPending ? (
                              'Saving…'
                            ) : isWatched ? (
                              <span>Unfollow</span>
                            ) : (
                              <>
                                <IconPlus size={11} />
                                <span>Follow</span>
                              </>
                            )}
                          </button>
                        ) : (
                          <NavLink
                            to="/login"
                            className="fin-btn fin-btn-ghost fin-btn-sm"
                            title="Sign in to add to watchlist"
                          >
                            Sign In
                          </NavLink>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default WatchlistPage;
