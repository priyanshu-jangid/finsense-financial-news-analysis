import React from 'react';
import { IconRefresh } from './Icons';

interface PageHeaderProps {
  title: string;
  subtitle?: string;
  lastUpdated?: string | null;
  onRefresh?: () => void;
  isRefreshing?: boolean;
  extraActions?: React.ReactNode;
}

export const PageHeader: React.FC<PageHeaderProps> = ({
  title,
  subtitle,
  lastUpdated,
  onRefresh,
  isRefreshing = false,
  extraActions,
}) => {
  return (
    <div
      style={{
        display: 'flex',
        flexWrap: 'wrap',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '16px',
        marginBottom: '24px',
        paddingBottom: '16px',
        borderBottom: '1px solid var(--border-subtle)',
      }}
    >
      <div>
        <h1
          style={{
            fontSize: '22px',
            fontWeight: 700,
            letterSpacing: '-0.02em',
            color: 'var(--text-primary)',
          }}
        >
          {title}
        </h1>
        {subtitle && (
          <p
            style={{
              fontSize: '13px',
              color: 'var(--text-muted)',
              marginTop: '4px',
            }}
          >
            {subtitle}
          </p>
        )}
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        {lastUpdated && (
          <span
            style={{
              fontSize: '11px',
              color: 'var(--text-muted)',
              fontFamily: 'var(--font-mono)',
            }}
          >
            Updated: {lastUpdated}
          </span>
        )}

        {extraActions}

        {onRefresh && (
          <button
            onClick={onRefresh}
            disabled={isRefreshing}
            className="fin-btn fin-btn-secondary fin-btn-sm"
            title="Refresh current data"
            aria-label="Refresh data"
          >
            <IconRefresh
              size={13}
              style={{
                animation: isRefreshing ? 'spin 1s linear infinite' : 'none',
              }}
            />
            <span>{isRefreshing ? 'Refreshing…' : 'Refresh'}</span>
          </button>
        )}
      </div>
    </div>
  );
};

export default PageHeader;
