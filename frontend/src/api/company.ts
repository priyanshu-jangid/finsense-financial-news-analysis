// src/api/company.ts
import api from './client';
import type { Company, CompanySentimentSummary } from '../types';

export const fetchCompanies = async (): Promise<Company[]> => {
  const response = await api.get('/companies');
  const data = response.data;
  // Backend may return an array directly or an object containing the array under a key.
  if (Array.isArray(data)) {
    return data as Company[];
  }
  if (
    data &&
    typeof data === 'object' &&
    'companies' in data &&
    Array.isArray((data as Record<string, unknown>)['companies'])
  ) {
    return (data as Record<string, unknown>)['companies'] as Company[];
  }
  // Fallback to empty list to avoid runtime errors.
  return [];
};

export const fetchCompanySentiment = async (
  companyId: number,
  startDate?: string,
  endDate?: string
): Promise<CompanySentimentSummary> => {
  const params: Record<string, string> = {};
  if (startDate) params.start_date = startDate;
  if (endDate) params.end_date = endDate;
  const response = await api.get<CompanySentimentSummary>(
    `/companies/${companyId}/sentiment`,
    { params }
  );
  return response.data;
};
