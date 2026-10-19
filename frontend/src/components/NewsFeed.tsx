import React from 'react';
import type { Article } from '../types';
import { SentimentBadge } from './SentimentBadge';
import { IconExternalLink, IconNewspaper, IconCalendar } from './Icons';

interface NewsFeedProps {
  articles: Article[];
  title?: string;
  subtitle?: string;
  emptyMessage?: string;
  isLoading?: boolean;
}

export const NewsFeed: React.FC<NewsFeedProps> = ({
  articles,
  title = 'Latest Financial News & Coverage',
  subtitle,
  emptyMessage = 'No financial news articles found for this selection.',
  isLoading = false,
}) => {
  const formatDate = (isoString?: string | null) => {
    if (!isoString) return 'Recent';
    try {
      const d = new Date(isoString);
      return new Intl.DateTimeFormat('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      }).format(d);
    } catch {
      return isoString;
    }
  };

  if (isLoading) {
    return (
      <div className="fin-card">
        <h3 style={{ fontSize: '15px', fontWeight: 600, marginBottom: '16px' }}>{title}</h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              style={{
                height: '70px',
                backgroundColor: 'var(--bg-surface-subtle)',
                borderRadius: 'var(--radius-md)',
                animation: 'pulse 1.5s infinite',
              }}
            />
          ))}
        </div>
      </div>
    );
  }

  if (articles.length === 0) {
    return (
      <div className="fin-card">
        <div style={{ marginBottom: '12px' }}>
          <h3 style={{ fontSize: '15px', fontWeight: 600 }}>{title}</h3>
          {subtitle && <p style={{ fontSize: '12px', color: 'var(--text-muted)' }}>{subtitle}</p>}
        </div>
        <div
          style={{
            padding: '36px 20px',
            textAlign: 'center',
            color: 'var(--text-muted)',
            backgroundColor: 'var(--bg-surface-subtle)',
            borderRadius: 'var(--radius-md)',
            border: '1px dashed var(--border-subtle)',
          }}
        >
          <IconNewspaper size={24} style={{ marginBottom: '8px', opacity: 0.6 }} />
          <div style={{ fontSize: '13px', fontWeight: 500 }}>{emptyMessage}</div>
          <div style={{ fontSize: '12px', marginTop: '4px' }}>
            When live news ingestion runs, incoming market articles and sentiment scores will appear here.
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="fin-card" style={{ padding: 0, overflow: 'hidden' }}>
      <div
        style={{
          padding: '16px 20px',
          borderBottom: '1px solid var(--border-subtle)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        <div>
          <h3 style={{ fontSize: '15px', fontWeight: 600 }}>{title}</h3>
          {subtitle && (
            <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px' }}>
              {subtitle}
            </p>
          )}
        </div>
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
          {articles.length} article{articles.length !== 1 ? 's' : ''}
        </span>
      </div>

      <div>
        {articles.map((article) => {
          // Check if article has associated sentiment
          const firstSentiment = article.sentiments && article.sentiments.length > 0 ? article.sentiments[0] : null;

          // Check company tag
          const companyTag = article.entities && article.entities.length > 0 && article.entities[0].company
            ? article.entities[0].company.ticker
            : null;

          return (
            <div
              key={article.id}
              style={{
                padding: '16px 20px',
                borderBottom: '1px solid var(--border-subtle)',
                transition: 'background-color 0.15s ease',
              }}
              className="fin-card-interactive"
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
                  {/* Metadata Row: Source, Time, Company Tag, Sentiment */}
                  <div
                    style={{
                      display: 'flex',
                      flexWrap: 'wrap',
                      alignItems: 'center',
                      gap: '8px',
                      marginBottom: '6px',
                    }}
                  >
                    {companyTag && (
                      <span
                        className="fin-badge fin-badge-accent"
                        style={{ fontSize: '10px' }}
                      >
                        {companyTag}
                      </span>
                    )}

                    <span
                      style={{
                        fontSize: '12px',
                        fontWeight: 600,
                        color: 'var(--text-primary)',
                      }}
                    >
                      {article.source?.name || 'Financial Wire'}
                    </span>

                    <span style={{ color: 'var(--text-muted)', fontSize: '11px' }}>•</span>

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

                    {firstSentiment && (
                      <SentimentBadge
                        label={firstSentiment.label}
                        score={firstSentiment.score}
                        confidence={firstSentiment.confidence}
                        size="sm"
                      />
                    )}
                  </div>

                  {/* Headline Link */}
                  <h4 style={{ fontSize: '14px', fontWeight: 600, lineHeight: 1.4 }}>
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

                  {/* Summary */}
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
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default NewsFeed;
