'use client';

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react';
import { AxiosError } from 'axios';

import { api } from '@/lib/api';
import { getStoredToken } from '@/lib/auth';
import type { IP } from '@/types';

const STORAGE_KEY = 'creator_selected_ip_id';

export type CreatorIpState = {
  ipId: string | null;
  ips: IP[];
  setIpId: (id: string) => void;
  loading: boolean;
  error: string | null;
  needsLogin: boolean;
  noIp: boolean;
  refresh: () => void;
};

const CreatorIpContext = createContext<CreatorIpState | null>(null);

export function CreatorIpProvider({ children }: { children: React.ReactNode }) {
  const [ips, setIps] = useState<IP[]>([]);
  const [ipId, setIpIdState] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [needsLogin, setNeedsLogin] = useState(false);

  const load = useCallback(async () => {
    const token = getStoredToken();
    if (!token) {
      setIps([]);
      setIpIdState(null);
      setNeedsLogin(true);
      setError(null);
      setLoading(false);
      return;
    }
    setNeedsLogin(false);
    setLoading(true);
    setError(null);
    try {
      const list = await api.listMyIPs();
      setIps(list);
      if (list.length === 0) {
        setIpIdState(null);
      } else {
        let saved: string | null = null;
        if (typeof window !== 'undefined') {
          saved = localStorage.getItem(STORAGE_KEY);
        }
        const pick = saved && list.some((i) => i.ip_id === saved) ? saved : list[0].ip_id;
        setIpIdState(pick);
        if (typeof window !== 'undefined') {
          localStorage.setItem(STORAGE_KEY, pick);
        }
      }
    } catch (e) {
      setIps([]);
      setIpIdState(null);
      const ax = e as AxiosError<{ detail?: string }>;
      if (ax.response?.status === 401) {
        setNeedsLogin(true);
        setError(null);
      } else {
        const detail = ax.response?.data?.detail;
        setError(
          typeof detail === 'string'
            ? detail
            : e instanceof Error
              ? e.message
              : '加载失败'
        );
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const setIpId = useCallback((id: string) => {
    setIpIdState(id);
    if (typeof window !== 'undefined') {
      localStorage.setItem(STORAGE_KEY, id);
    }
  }, []);

  const noIp = !loading && !needsLogin && ips.length === 0;

  const value = useMemo(
    () => ({
      ipId,
      ips,
      setIpId,
      loading,
      error,
      needsLogin,
      noIp,
      refresh: load,
    }),
    [ipId, ips, setIpId, loading, error, needsLogin, noIp, load]
  );

  return (
    <CreatorIpContext.Provider value={value}>{children}</CreatorIpContext.Provider>
  );
}

export function useCreatorIp(): CreatorIpState {
  const ctx = useContext(CreatorIpContext);
  if (!ctx) {
    throw new Error('useCreatorIp must be used within CreatorIpProvider');
  }
  return ctx;
}
