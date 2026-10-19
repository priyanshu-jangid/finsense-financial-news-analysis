// src/api/company.ts
import api from './client';
import type { Company, CompanySentimentSummary } from '../types';

export const fetchCompanies = async (): Promise<Company[]> => {
  const response = await api.get('/companies');
  const data = response.data;
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
  return [];
};

export const fetchCompanyById = async (companyId: number): Promise<Company> => {
  const response = await api.get<Company>(`/companies/${companyId}`);
  return response.data;
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

export const triggerCompanySentimentAnalysis = async (
  companyId: number
): Promise<{ created: number }> => {
  const response = await api.post<{ created: number }>(
    `/companies/${companyId}/sentiment/analyze`
  );
  return response.data;
};
