export interface Company {
  id: number;
  ticker: string;
  name: string;
  sector?: string | null;
}

export interface DailyTrendPoint {
  date: string; // ISO date string (YYYY-MM-DD)
  count: number;
  average_score?: number | null;
}

export interface CompanySentimentSummary {
  company_id: number;
  start_date?: string | null;
  end_date?: string | null;
  total_analyses: number;
  positive_count: number;
  neutral_count: number;
  negative_count: number;
  average_score?: number | null;
  daily_trend: DailyTrendPoint[];
}
