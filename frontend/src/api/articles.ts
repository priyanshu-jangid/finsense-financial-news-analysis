// src/api/articles.ts
import api from './client';
import type { PaginatedArticles, IngestionStatus, PaginatedFeed } from '../types';

export const fetchArticles = async (
  page = 1,
  pageSize = 20,
  search?: string
): Promise<PaginatedArticles> => {
  const params: Record<string, string | number> = {
    page,
    page_size: pageSize,
  };
  if (search && search.trim()) {
    params.search = search.trim();
  }
  const response = await api.get<PaginatedArticles>('/articles', { params });
  return response.data;
};

export const fetchMarketArticles = async (
  page = 1,
  pageSize = 20
): Promise<PaginatedArticles> => {
  const response = await api.get<PaginatedArticles>('/articles/market', {
    params: { page, page_size: pageSize },
  });
  return response.data;
};

export const fetchCompanyArticles = async (
  companyId: number,
  page = 1,
  pageSize = 20
): Promise<PaginatedArticles> => {
  const response = await api.get<PaginatedArticles>(`/articles/company/${companyId}`, {
    params: { page, page_size: pageSize },
  });
  return response.data;
};

export const triggerNewsIngestion = async (): Promise<Record<string, unknown>> => {
  const response = await api.post<Record<string, unknown>>('/articles/ingest');
  return response.data;
};

export const fetchIngestionStatus = async (): Promise<IngestionStatus> => {
  const response = await api.get<IngestionStatus>('/articles/ingestion-status');
  return response.data;
};

export interface FeedParams {
  page?: number;
  page_size?: number;
  company_id?: number | null;
  sentiment?: string | null;
  start_date?: string | null;
  end_date?: string | null;
}

export const fetchPersonalizedFeed = async (
  userId: number,
  params: FeedParams = {}
): Promise<PaginatedFeed> => {
  const query: Record<string, string | number> = {
    page: params.page ?? 1,
    page_size: params.page_size ?? 20,
  };
  if (params.company_id != null) query.company_id = params.company_id;
  if (params.sentiment) query.sentiment = params.sentiment;
  if (params.start_date) query.start_date = params.start_date;
  if (params.end_date) query.end_date = params.end_date;
  const response = await api.get<PaginatedFeed>(`/users/${userId}/feed`, { params: query });
  return response.data;
};
