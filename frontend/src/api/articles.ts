// src/api/articles.ts
import api from './client';
import type { PaginatedArticles, IngestionStatus } from '../types';

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
