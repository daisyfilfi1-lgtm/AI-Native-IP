'use client';

import { useState, useEffect, useCallback } from 'react';
import { api } from '@/lib/api';
import type { IP } from '@/types';

/** 全站复用：拉取 IP 列表（创建/管理页与各类 Agent 表单） */
export function useIpList() {
  const [ips, setIps] = useState<IP[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(() => {
    setLoading(true);
    setError(null);
    api
      .listIPs()
      .then((items) => setIps(items || []))
      .catch((e) => {
        setIps([]);
        setError(e instanceof Error ? e.message : '加载失败');
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { ips, loading, error, refresh };
}
