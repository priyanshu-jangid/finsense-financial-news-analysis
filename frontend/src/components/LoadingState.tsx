import React from 'react';

interface LoadingStateProps {
  message?: string;
  rows?: number;
}

export const LoadingState: React.FC<LoadingStateProps> = ({
  message = 'Loading financial data…',
  rows = 3,
}) => {
  return (
    <div
      style={{
        padding: '32px 20px',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '12px',
        borderRadius: 'var(--radius-lg)',
        border: '1px solid var(--border-subtle)',
        backgroundColor: 'var(--bg-surface)',
      }}
    >
      <div
        style={{
          width: '24px',
          height: '24px',
          border: '2px solid var(--border-default)',
          borderTopColor: 'var(--accent-primary)',
          borderRadius: '50%',
          animation: 'spin 0.8s linear infinite',
        }}
      />
      <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
        {message}
      </span>
      {rows > 1 && (
        <div style={{ width: '100%', maxWidth: '400px', display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '8px' }}>
          {Array.from({ length: rows }).map((_, i) => (
            <div
              key={i}
              style={{
                height: '12px',
                backgroundColor: 'var(--bg-surface-subtle)',
                borderRadius: 'var(--radius-sm)',
                opacity: 1 - i * 0.25,
              }}
            />
          ))}
        </div>
      )}
    </div>
  );
};

export default LoadingState;
