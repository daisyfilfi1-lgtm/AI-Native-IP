/**
 * 浏览器端 Memory / IP 等 API 的 base URL（一般为 `/api/v1`）。
 * 
 * 架构演进：
 * 
 * 1. 传统架构（已废弃）：
 *    浏览器 → Netlify CDN → 302重定向 → Railway
 *    问题：多一次跳转，CORS预检延迟
 * 
 * 2. 直连架构（当前默认）：
 *    浏览器 → Railway（绕过Netlify）
 *    问题：CORS预检请求增加延迟
 * 
 * 3. Edge Functions架构（推荐）：
 *    浏览器 → Netlify Edge (Deno) → Railway
 *    优势：
 *    - 边缘缓存静态资源（减少90%后端请求）
 *    - 上传预处理（大小验证、格式检查）
 *    - 失败请求优雅降级
 *    - 全球边缘节点 <50ms延迟
 *    - 解决CORS预检问题
 * 
 * 使用方法：
 * - 托管站点：始终直连 Railway（见 productionApiV1Base）；netlify.toml 不再对 /api 做代理，避免网关 504。
 * - 本地：next.config rewrites 将 /api 转到后端，或设 NEXT_PUBLIC_API_URL。
 */

const DEFAULT_PRODUCTION_API_ORIGIN = 'https://ai-native-ip-production.up.railway.app';

/** 生产后端 API base（浏览器与 SSR 共用） */
function productionApiV1Base(): string {
  const origin = (
    process.env.NEXT_PUBLIC_API_DIRECT_ORIGIN?.trim() || DEFAULT_PRODUCTION_API_ORIGIN
  ).replace(/\/$/, '');
  return /^https:\/\//i.test(origin)
    ? `${origin}/api/v1`
    : `${DEFAULT_PRODUCTION_API_ORIGIN.replace(/\/$/, '')}/api/v1`;
}

/** API 模式 */
type ApiMode = 'direct' | 'edge' | 'proxy';

function getApiMode(): ApiMode {
  if (typeof window === 'undefined') {
    return 'edge';
  }

  const mode = process.env.NEXT_PUBLIC_API_MODE?.trim()?.toLowerCase();
  if (mode === 'edge') return 'edge';
  if (mode === 'direct') return 'direct';

  const host = window.location.hostname;
  const isLocal = host === 'localhost' || host === '127.0.0.1';
  const isHosted =
    host.endsWith('.netlify.app') ||
    host.endsWith('.vercel.app');

  // 非本机访问：默认直连 Railway（Edge 代理 fetch 超时过短，仿写易 504）
  if (!isLocal && (isHosted || process.env.NODE_ENV === 'production')) {
    return 'direct';
  }

  return 'edge';
}

export function getBrowserApiBaseUrl(): string {
  const u = process.env.NEXT_PUBLIC_API_URL?.trim();

  if (typeof window !== 'undefined') {
    const host = window.location.hostname;
    const isLocal = host === 'localhost' || host === '127.0.0.1';
    const isHosted =
      host.endsWith('.netlify.app') || host.endsWith('.vercel.app');

    // 本地开发：使用配置的 API URL（完整 origin，可含路径）
    if (isLocal && u && /^https?:\/\//i.test(u)) {
      return u.replace(/\/$/, '');
    }

    // 托管站或生产构建的前端：一律直连 Railway，不使用同源 /api（已移除 Netlify /api 代理）
    if (!isLocal && (isHosted || process.env.NODE_ENV === 'production')) {
      return productionApiV1Base();
    }

    return '/api/v1';
  }

  // SSR：生产构建时直连 Railway，避免相对 /api 在 Netlify 上无代理
  if (process.env.NODE_ENV === 'production') {
    return productionApiV1Base();
  }
  return '/api/v1';
}

export function getApiOriginOrEmpty(): string {
  const mode = getApiMode();
  const base = getBrowserApiBaseUrl();
  
  // Edge 模式：同源，不需要 origin
  if (mode === 'edge') return '';
  
  // 直连模式：返回 Railway origin
  if (base.startsWith('http')) {
    return base.replace(/\/api\/v1\/?$/, '').replace(/\/$/, '');
  }
  
  return '';
}

/**
 * 获取完整的 API URL
 * 用于需要绝对 URL 的场景（如文件上传）
 */
export function getFullApiUrl(path: string): string {
  const base = getBrowserApiBaseUrl();
  const cleanPath = path.replace(/^\//, '');
  
  if (base.startsWith('http')) {
    return `${base}/${cleanPath}`;
  }
  
  // 同源：使用当前域名的 API
  if (typeof window !== 'undefined') {
    const protocol = window.location.protocol;
    const host = window.location.host;
    return `${protocol}//${host}/${cleanPath}`;
  }
  
  return `/${cleanPath}`;
}

/**
 * `/api/auth/*` 不在 Next 站内，相对路径会打到 Netlify 域名导致 404。
 * 当 `getBrowserApiBaseUrl()` 为相对 `/api/v1` 时，回退到与直连相同的后端 origin。
 */
function resolveAuthBackendOrigin(): string {
  const fallback = (
    process.env.NEXT_PUBLIC_API_DIRECT_ORIGIN?.trim() || DEFAULT_PRODUCTION_API_ORIGIN
  ).replace(/\/$/, '');

  if (typeof window === 'undefined') {
    return fallback;
  }

  const base = getBrowserApiBaseUrl();
  if (base.startsWith('http')) {
    return base.replace(/\/api\/v1\/?$/i, '').replace(/\/$/, '');
  }
  return fallback;
}

/**
 * 手机号验证码登录接口（与 axios /api/v1 的 base 解析规则一致）。
 */
export function getAuthSmsLoginUrl(): string {
  return `${resolveAuthBackendOrigin()}/api/auth/sms/login`;
}

/** 邮箱 + 密码登录 */
export function getAuthEmailLoginUrl(): string {
  return `${resolveAuthBackendOrigin()}/api/auth/login`;
}

/** 发送登录验证码 */
export function getAuthSmsSendCodeUrl(): string {
  return `${resolveAuthBackendOrigin()}/api/auth/sms/send-code`;
}

/**
 * 长耗时创作接口：走 Netlify 同源 `/api` 代理时网关常在约 30s 内返回 504。
 * 在必须使用相对路径时（如 NEXT_PUBLIC_API_MODE=edge），强制直连 Railway。
 */
const LONG_RUNNING_V1_PATH_PREFIXES: readonly string[] = [
  '/api/v1/creator/generate/viral',
  '/api/v1/creator/generate/original',
  '/api/v1/creator/generate/voice',
  '/api/v1/creator/generate/topic',
  '/api/v1/creator/generate/refine',
  '/api/v1/creator/topics/refresh',
];

function shouldForceDirectRailwayForV1Path(ep: string): boolean {
  const path = ep.split('?')[0];
  return LONG_RUNNING_V1_PATH_PREFIXES.some(
    (p) => path === p || path.startsWith(`${p}/`)
  );
}

/**
 * 将 `/api/v1/...` 路径解析为 fetch 可用的 URL（与 axios 的 base 规则一致）。
 * creator 等使用 fetch 的模块应使用此函数，避免与 `lib/api.ts` 在直连模式下分叉。
 */
export function resolveV1ApiFetchUrl(endpoint: string): string {
  const ep = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  if (!ep.startsWith('/api/v1')) {
    throw new Error(`resolveV1ApiFetchUrl: expected path starting with /api/v1, got: ${ep}`);
  }
  const rest = ep.slice('/api/v1'.length) || '/';
  const base = getBrowserApiBaseUrl().replace(/\/$/, '');
  if (base.startsWith('http')) {
    const baseHasV1 = /\/api\/v1$/i.test(base);
    const prefix = baseHasV1 ? base : `${base}/api/v1`;
    return `${prefix}${rest}`;
  }
  if (typeof window !== 'undefined' && shouldForceDirectRailwayForV1Path(ep)) {
    const origin = (
      process.env.NEXT_PUBLIC_API_DIRECT_ORIGIN?.trim() || DEFAULT_PRODUCTION_API_ORIGIN
    ).replace(/\/$/, '');
    if (/^https:\/\//i.test(origin)) {
      return `${origin}/api/v1${rest}`;
    }
  }
  return `/api/v1${rest}`;
}
