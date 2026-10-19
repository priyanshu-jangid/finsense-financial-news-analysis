import React from 'react';
import { Navbar } from './Navbar';

interface AppLayoutProps {
  children: React.ReactNode;
}

export const AppLayout: React.FC<AppLayoutProps> = ({ children }) => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      <Navbar />
      <main className="app-container">{children}</main>
      <footer
        style={{
          borderTop: '1px solid var(--border-subtle)',
          backgroundColor: 'var(--bg-surface)',
          padding: '16px 20px',
          marginTop: 'auto',
          fontSize: '12px',
          color: 'var(--text-muted)',
        }}
      >
        <div
          style={{
            maxWidth: '1360px',
            margin: '0 auto',
            display: 'flex',
            flexWrap: 'wrap',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '12px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>FinSense</span>
            <span>—</span>
            <span>Automated Financial News Aggregation & Sentiment Analysis</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            <span>Backend: FastAPI + PostgreSQL</span>
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '5px',
                color: 'var(--sentiment-pos-text)',
              }}
            >
              <span
                style={{
                  width: '6px',
                  height: '6px',
                  borderRadius: '50%',
                  backgroundColor: 'var(--sentiment-pos)',
                }}
              />
              System Connected
            </span>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default AppLayout;
