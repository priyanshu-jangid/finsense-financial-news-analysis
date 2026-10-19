import React from 'react';
import type { Company } from '../types';
import { IconCalendar, IconBuilding, IconActivity } from './Icons';

interface FilterToolbarProps {
  companies: Company[];
  selectedCompany: number | '';
  onSelectCompany: (companyId: number | '') => void;
  startDate: string;
  onStartDateChange: (date: string) => void;
  endDate: string;
  onEndDateChange: (date: string) => void;
  onApply: () => void;
  onReset: () => void;
  isLoading?: boolean;
  onRunAnalysis?: () => void;
  isAnalyzing?: boolean;
  isAuthenticated?: boolean;
}

export const FilterToolbar: React.FC<FilterToolbarProps> = ({
  companies,
  selectedCompany,
  onSelectCompany,
  startDate,
  onStartDateChange,
  endDate,
  onEndDateChange,
  onApply,
  onReset,
  isLoading = false,
  onRunAnalysis,
  isAnalyzing = false,
  isAuthenticated = false,
}) => {
  // Date range validation
  const isDateRangeInvalid = !!(startDate && endDate && startDate > endDate);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !isDateRangeInvalid && selectedCompany) {
      onApply();
    }
  };

  return (
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
        onKeyDown={handleKeyDown}
      >
        {/* Company Selector */}
        <div style={{ flex: '1 1 220px', minWidth: '200px' }}>
          <label
            htmlFor="company-filter-select"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              fontSize: '11px',
              fontWeight: 600,
              textTransform: 'uppercase',
              letterSpacing: '0.04em',
              color: 'var(--text-muted)',
              marginBottom: '6px',
            }}
          >
            <IconBuilding size={13} />
            <span>Target Company</span>
          </label>
          <select
            id="company-filter-select"
            value={selectedCompany}
            onChange={(e) => onSelectCompany(Number(e.target.value) || '')}
            className="fin-select"
            style={{ width: '100%' }}
            disabled={isLoading}
          >
            <option value="">Select a company…</option>
            {companies.map((c) => (
              <option key={c.id} value={c.id}>
                {c.ticker} — {c.name} {c.sector ? `(${c.sector})` : ''}
              </option>
            ))}
          </select>
        </div>

        {/* Start Date */}
        <div style={{ flex: '0 1 160px', minWidth: '140px' }}>
          <label
            htmlFor="start-date-filter"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              fontSize: '11px',
              fontWeight: 600,
              textTransform: 'uppercase',
              letterSpacing: '0.04em',
              color: 'var(--text-muted)',
              marginBottom: '6px',
            }}
          >
            <IconCalendar size={13} />
            <span>From Date</span>
          </label>
          <input
            id="start-date-filter"
            type="date"
            value={startDate}
            onChange={(e) => onStartDateChange(e.target.value)}
            className="fin-input"
            style={{ width: '100%' }}
            disabled={isLoading}
          />
        </div>

        {/* End Date */}
        <div style={{ flex: '0 1 160px', minWidth: '140px' }}>
          <label
            htmlFor="end-date-filter"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              fontSize: '11px',
              fontWeight: 600,
              textTransform: 'uppercase',
              letterSpacing: '0.04em',
              color: 'var(--text-muted)',
              marginBottom: '6px',
            }}
          >
            <IconCalendar size={13} />
            <span>To Date</span>
          </label>
          <input
            id="end-date-filter"
            type="date"
            value={endDate}
            onChange={(e) => onEndDateChange(e.target.value)}
            className="fin-input"
            style={{ width: '100%' }}
            disabled={isLoading}
          />
        </div>

        {/* Action Buttons */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          <button
            onClick={onApply}
            disabled={isLoading || !selectedCompany || isDateRangeInvalid}
            className="fin-btn fin-btn-primary"
            style={{ minWidth: '110px' }}
          >
            {isLoading ? 'Loading…' : 'Apply Filters'}
          </button>

          <button
            onClick={onReset}
            disabled={isLoading || (!selectedCompany && !startDate && !endDate)}
            className="fin-btn fin-btn-secondary"
          >
            Reset
          </button>

          {isAuthenticated && onRunAnalysis && selectedCompany && (
            <button
              onClick={onRunAnalysis}
              disabled={isAnalyzing || isLoading}
              className="fin-btn fin-btn-secondary"
              title="Run sentiment analysis on pending articles for this company"
              style={{
                borderColor: 'var(--accent-border)',
                color: 'var(--accent-text)',
                backgroundColor: 'var(--accent-subtle)',
              }}
            >
              <IconActivity size={14} />
              <span>{isAnalyzing ? 'Analyzing…' : 'Trigger Analysis'}</span>
            </button>
          )}
        </div>
      </div>

      {/* Date validation warning */}
      {isDateRangeInvalid && (
        <div
          style={{
            marginTop: '12px',
            padding: '8px 12px',
            backgroundColor: 'var(--sentiment-neg-bg)',
            border: '1px solid var(--sentiment-neg-border)',
            borderRadius: 'var(--radius-md)',
            color: 'var(--sentiment-neg-text)',
            fontSize: '12px',
          }}
        >
          Start date cannot be after end date. Please adjust your date range.
        </div>
      )}
    </div>
  );
};

export default FilterToolbar;
