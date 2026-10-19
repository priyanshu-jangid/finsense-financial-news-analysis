import React from 'react';

interface MetricCardProps {
  label: string;
  value: React.ReactNode;
  subtitle?: string;
  icon?: React.ReactNode;
  tone?: 'default' | 'positive' | 'negative' | 'neutral' | 'accent';
  loading?: boolean;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  label,
  value,
  subtitle,
  icon,
  tone = 'default',
  loading = false,
}) => {
  const getBorderColor = () => {
    switch (tone) {
      case 'positive':
        return 'var(--sentiment-pos-border)';
      case 'negative':
        return 'var(--sentiment-neg-border)';
      case 'accent':
        return 'var(--accent-border)';
      default:
        return 'var(--border-subtle)';
    }
  };

  const getValueColor = () => {
    switch (tone) {
      case 'positive':
        return 'var(--sentiment-pos-text)';
      case 'negative':
        return 'var(--sentiment-neg-text)';
      case 'accent':
        return 'var(--accent-text)';
      default:
        return 'var(--text-primary)';
    }
  };

  return (
    <div
      className="fin-card"
      style={{
        padding: '16px 18px',
        borderColor: getBorderColor(),
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        minHeight: '94px',
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: '8px',
        }}
      >
        <span
          style={{
            fontSize: '11px',
            fontWeight: 600,
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            color: 'var(--text-muted)',
          }}
        >
          {label}
        </span>
        {icon && (
          <span style={{ color: 'var(--text-muted)', display: 'flex' }}>
            {icon}
          </span>
        )}
      </div>

      <div>
        {loading ? (
          <div
            style={{
              height: '28px',
              width: '60px',
              backgroundColor: 'var(--bg-surface-subtle)',
              borderRadius: 'var(--radius-sm)',
              animation: 'pulse 1.5s infinite',
            }}
          />
        ) : (
          <div
            className="tabular-nums"
            style={{
              fontSize: '24px',
              fontWeight: 700,
              lineHeight: 1.1,
              color: getValueColor(),
            }}
          >
            {value}
          </div>
        )}

        {subtitle && (
          <div
            style={{
              fontSize: '12px',
              color: 'var(--text-muted)',
              marginTop: '4px',
            }}
          >
            {subtitle}
          </div>
        )}
      </div>
    </div>
  );
};

export default MetricCard;
