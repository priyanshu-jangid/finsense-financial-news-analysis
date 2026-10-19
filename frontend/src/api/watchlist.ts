// src/api/watchlist.ts
import api from './client';
import type { WatchlistItem } from '../types';

export const fetchUserWatchlist = async (userId: number): Promise<WatchlistItem[]> => {
  const response = await api.get<WatchlistItem[]>(`/users/${userId}/watchlist`);
  return Array.isArray(response.data) ? response.data : [];
};

export const addToWatchlist = async (userId: number, companyId: number): Promise<WatchlistItem> => {
  const response = await api.post<WatchlistItem>(`/users/${userId}/watchlist`, {
    company_id: companyId,
  });
  return response.data;
};

export const removeFromWatchlist = async (userId: number, companyId: number): Promise<void> => {
  await api.delete(`/users/${userId}/watchlist/${companyId}`);
};
