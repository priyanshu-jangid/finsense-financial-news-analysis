import React from 'react';
import { IconAlertCircle } from './Icons';

interface EmptyStateProps {
  title: string;
  description: string;
  icon?: React.ReactNode;
  action?: {
    label: string;
    onClick: () => void;
  };
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title,
  description,
  icon,
  action,
}) => {
  return (
    <div
      style={{
        padding: '48px 24px',
        textAlign: 'center',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        borderRadius: 'var(--radius-lg)',
        border: '1px dashed var(--border-default)',
        backgroundColor: 'var(--bg-surface-subtle)',
        margin: '16px 0',
      }}
    >
      <div
        style={{
          width: '40px',
          height: '40px',
          borderRadius: '50%',
          backgroundColor: 'var(--bg-surface)',
          border: '1px solid var(--border-subtle)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'var(--text-muted)',
          marginBottom: '16px',
        }}
      >
        {icon || <IconAlertCircle size={20} />}
      </div>
      <h3
        style={{
          fontSize: '15px',
          fontWeight: 600,
          color: 'var(--text-primary)',
          marginBottom: '6px',
        }}
      >
        {title}
      </h3>
      <p
        style={{
          fontSize: '13px',
          color: 'var(--text-muted)',
          maxWidth: '440px',
          lineHeight: 1.5,
          marginBottom: action ? '16px' : '0',
        }}
      >
        {description}
      </p>
      {action && (
        <button
          onClick={action.onClick}
          className="fin-btn fin-btn-secondary fin-btn-sm"
        >
          {action.label}
        </button>
      )}
    </div>
  );
};

export default EmptyState;
