// src/components/Dashboard.tsx
import { useEffect, useState } from 'react';
import { fetchCompanies, fetchCompanySentiment } from '../api/company';
import type { Company, CompanySentimentSummary } from '../types';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ResponsiveContainer,
} from 'recharts';

const Dashboard = () => {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [selectedCompany, setSelectedCompany] = useState<number | ''>('');
  const [startDate, setStartDate] = useState<string>('');
  const [endDate, setEndDate] = useState<string>('');
  const [summary, setSummary] = useState<CompanySentimentSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load company list on mount
  useEffect(() => {
    fetchCompanies()
      .then(setCompanies)
      .catch(() => setError('Failed to load companies'));
  }, []);

  const loadSentiment = async () => {
    if (!selectedCompany) return;
    setLoading(true);
    setError(null);
    try {
      const data = await fetchCompanySentiment(
        selectedCompany,
        startDate || undefined,
        endDate || undefined
      );
      setSummary(data);
    } catch {
      setError('Failed to load sentiment data');
      setSummary(null);
    } finally {
      setLoading(false);
    }
  };

  const renderChart = () => {
    if (!summary || summary.daily_trend.length === 0) {
      return <p>No trend data available.</p>;
    }
    const chartData = summary.daily_trend.map((pt) => ({
      date: pt.date,
      count: pt.count,
      avg: pt.average_score ?? 0,
    }));
    return (
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" />
          <YAxis />
          <Tooltip />
          <Line type="monotone" dataKey="count" stroke="#8884d8" name="Count" />
          <Line type="monotone" dataKey="avg" stroke="#82ca9d" name="Avg Score" />
        </LineChart>
      </ResponsiveContainer>
    );
  };

  return (
    <div className="dashboard container mx-auto p-4">
      <h1 className="text-2xl font-bold mb-4">Company Sentiment Dashboard</h1>
      <div className="controls flex flex-wrap gap-4 mb-4">
        <select
          value={selectedCompany}
          onChange={(e) => setSelectedCompany(Number(e.target.value) || '')}
          className="border rounded p-2"
        >
          <option value="">Select Company</option>
          {companies.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name} ({c.ticker})
            </option>
          ))}
        </select>
        <input
          type="date"
          value={startDate}
          onChange={(e) => setStartDate(e.target.value)}
          className="border rounded p-2"
        />
        <input
          type="date"
          value={endDate}
          onChange={(e) => setEndDate(e.target.value)}
          className="border rounded p-2"
        />
        <button
          onClick={loadSentiment}
          className="bg-blue-500 text-white rounded px-4 py-2 disabled:opacity-50"
          disabled={loading || !selectedCompany}
        >
          {loading ? 'Loading…' : 'Refresh'}
        </button>
      </div>
      {error && <p className="text-red-600 mb-2">{error}</p>}
      {summary && (
        <div className="summary grid grid-cols-2 gap-4 mb-6">
          {[
            { label: 'Total Analyses', value: summary.total_analyses },
            { label: 'Positive', value: summary.positive_count },
            { label: 'Neutral', value: summary.neutral_count },
            { label: 'Negative', value: summary.negative_count },
            { label: 'Avg Score', value: summary.average_score !== null && summary.average_score !== undefined ? summary.average_score.toFixed(2) : 'N/A' },
          ].map((item, idx) => (
            <div key={item.label} className="fade-in" style={{ '--i': idx + 1 } as React.CSSProperties}>
              {item.label}: {item.value}
            </div>
          ))}
        </div>
      )}
      {renderChart()}
    </div>
  );
};

export default Dashboard;
