import React from 'react';
import { IconAlertCircle, IconRefresh } from './Icons';

interface ErrorStateProps {
  message: string;
  onRetry?: () => void;
  title?: string;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  message,
  onRetry,
  title = 'Failed to load data',
}) => {
  return (
    <div
      style={{
        padding: '16px 20px',
        backgroundColor: 'var(--sentiment-neg-bg)',
        border: '1px solid var(--sentiment-neg-border)',
        borderRadius: 'var(--radius-lg)',
        color: 'var(--sentiment-neg-text)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '16px',
        margin: '16px 0',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <IconAlertCircle size={18} style={{ flexShrink: 0 }} />
        <div>
          <div style={{ fontWeight: 600, fontSize: '13px' }}>{title}</div>
          <div style={{ fontSize: '12px', opacity: 0.9, marginTop: '2px' }}>{message}</div>
        </div>
      </div>

      {onRetry && (
        <button
          onClick={onRetry}
          className="fin-btn fin-btn-sm"
          style={{
            backgroundColor: 'var(--bg-surface)',
            color: 'var(--sentiment-neg-text)',
            borderColor: 'var(--sentiment-neg-border)',
          }}
        >
          <IconRefresh size={12} />
          <span>Retry</span>
        </button>
      )}
    </div>
  );
};

export default ErrorState;
