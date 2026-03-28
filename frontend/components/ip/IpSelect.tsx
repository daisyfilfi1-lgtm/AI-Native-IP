'use client';

import { useMemo } from 'react';
import Link from 'next/link';
import { Select } from '@/components/ui/Select';
import type { IP } from '@/types';

export interface IpSelectProps {
  value: string;
  onChange: (ipId: string) => void;
  ips: IP[];
  loading?: boolean;
  label?: string;
  helper?: string;
  className?: string;
  disabled?: boolean;
  /** 空选项文案（加载中时会显示「加载 IP 列表…」除非另行覆盖） */
  emptyLabel?: string;
  /** 当 value 不在列表中时仍显示一项（例如 URL ?ip= 带入） */
  showUnknownValue?: boolean;
  /** 列表为空且非加载中时是否展示「前往 IP 管理」链接 */
  showCreateLink?: boolean;
}

export function IpSelect({
  value,
  onChange,
  ips,
  loading = false,
  label = '目标 IP',
  helper,
  className,
  disabled,
  emptyLabel,
  showUnknownValue = true,
  showCreateLink = true,
}: IpSelectProps) {
  const options = useMemo(() => {
    const placeholder = loading
      ? '加载 IP 列表…'
      : emptyLabel ?? '请选择 IP';
    const base: { value: string; label: string }[] = [
      { value: '', label: placeholder },
      ...ips.map((ip) => ({
        value: ip.ip_id,
        label: `${ip.name}（${ip.ip_id}）`,
      })),
    ];
    if (showUnknownValue && value && !ips.some((ip) => ip.ip_id === value)) {
      base.push({ value, label: `${value}（未在列表中）` });
    }
    return base;
  }, [ips, loading, value, emptyLabel, showUnknownValue]);

  return (
    <div className={className}>
      <Select
        label={label}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        options={options}
        disabled={disabled || loading}
        helper={helper}
      />
      {showCreateLink && !loading && ips.length === 0 && (
        <p className="mt-2 text-sm">
          <Link href="/ip" className="text-primary-400 hover:underline">
            前往 IP 管理创建 IP
          </Link>
        </p>
      )}
    </div>
  );
}
