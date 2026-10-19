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

export interface Source {
  id: number;
  name: string;
  domain: string;
  credibility_tier: number;
}

export interface CompanyBrief {
  id: number;
  ticker: string;
  name: string;
}

export interface ArticleEntity {
  id: number;
  company_id: number;
  relevance_score?: number | null;
  company?: CompanyBrief | null;
}

export interface SentimentAnalysisItem {
  id?: number;
  label: 'positive' | 'neutral' | 'negative' | string;
  score: number;
  confidence: number;
  model_used?: string;
}

export interface Article {
  id: number;
  title: string;
  url: string;
  summary?: string | null;
  published_at?: string | null;
  fetched_at: string;
  provider_id?: string | null;
  image_url?: string | null;
  author?: string | null;
  source: Source;
  entities?: ArticleEntity[];
  sentiments?: SentimentAnalysisItem[];
}

export interface PaginatedArticles {
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  items: Article[];
}

export interface WatchlistItem {
  id: number;
  user_id: number;
  company_id: number;
}

export interface UserProfile {
  id: number;
  email: string;
}

export interface IngestionCheckpoint {
  id: number;
  feed_type: string;
  last_successful_published_at: string | null;
  last_run_at: string;
  status: string;
  articles_fetched: number;
  articles_persisted: number;
  error_message?: string | null;
}

export interface IngestionStatus {
  is_scheduler_running: boolean;
  interval_hours: number;
  checkpoints: IngestionCheckpoint[];
}
