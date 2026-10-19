import React from 'react';

interface SentimentBadgeProps {
  label?: string | null;
  score?: number | null;
  confidence?: number | null;
  size?: 'sm' | 'md';
}

export const SentimentBadge: React.FC<SentimentBadgeProps> = ({
  label,
  score,
  confidence,
  size = 'md',
}) => {
  const normalizedLabel = (label || '').toLowerCase();

  let badgeClass = 'fin-badge-neu';
  let dotColor = 'var(--sentiment-neu)';
  let displayLabel = 'Neutral';

  if (normalizedLabel.includes('pos')) {
    badgeClass = 'fin-badge-pos';
    dotColor = 'var(--sentiment-pos)';
    displayLabel = 'Positive';
  } else if (normalizedLabel.includes('neg')) {
    badgeClass = 'fin-badge-neg';
    dotColor = 'var(--sentiment-neg)';
    displayLabel = 'Negative';
  } else if (!normalizedLabel) {
    displayLabel = 'Unrated';
  }

  const isSmall = size === 'sm';

  return (
    <span
      className={`fin-badge ${badgeClass}`}
      style={{
        padding: isSmall ? '1px 6px' : '3px 8px',
        fontSize: isSmall ? '10px' : '11px',
      }}
    >
      <span
        style={{
          width: isSmall ? '4px' : '6px',
          height: isSmall ? '4px' : '6px',
          borderRadius: '50%',
          backgroundColor: dotColor,
        }}
      />
      <span>{displayLabel}</span>
      {score !== undefined && score !== null && (
        <span
          className="tabular-nums"
          style={{
            marginLeft: '2px',
            opacity: 0.85,
            fontWeight: 500,
          }}
        >
          {score > 0 ? `+${score.toFixed(2)}` : score.toFixed(2)}
        </span>
      )}
      {confidence !== undefined && confidence !== null && (
        <span
          className="tabular-nums"
          style={{
            marginLeft: '2px',
            fontSize: '9px',
            opacity: 0.7,
          }}
        >
          ({Math.round(confidence * 100)}%)
        </span>
      )}
    </span>
  );
};

export default SentimentBadge;
