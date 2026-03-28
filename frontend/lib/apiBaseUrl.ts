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
 * - 默认（托管站点）：浏览器直连 Railway，避免 Netlify Edge 代理约 30s 上限导致仿写/长生成 504。
 * - 若需强制走同源 Edge 代理：设置 NEXT_PUBLIC_API_MODE=edge
 */

const DEFAULT_PRODUCTION_API_ORIGIN = 'https://ai-native-ip-production.up.railway.app';

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
  const mode = getApiMode();
  
  if (typeof window !== 'undefined') {
    const host = window.location.hostname;
    const isLocal = host === 'localhost' || host === '127.0.0.1';
    const isHosted = host.endsWith('.netlify.app') || host.endsWith('.vercel.app');
    
    // 本地开发：使用配置的 API URL
    if (isLocal && u && /^https?:\/\//i.test(u)) {
      return u.replace(/\/$/, '');
    }
    
    // Edge 模式：使用同源代理（Netlify Edge Function 处理）
    if (mode === 'edge' && isHosted) {
      if (process.env.NODE_ENV === 'development') {
        // eslint-disable-next-line no-console
        console.log('[API] 使用 Edge Function 代理模式');
      }
      return '/api/v1';
    }
    
    // 直连模式：直接调用 Railway
    if (mode === 'direct') {
      const directOrigin = process.env.NEXT_PUBLIC_API_DIRECT_ORIGIN?.trim();
      const origin = directOrigin || DEFAULT_PRODUCTION_API_ORIGIN;
      
      if (origin && /^https:\/\//i.test(origin)) {
        if (process.env.NODE_ENV === 'development') {
          // eslint-disable-next-line no-console
          console.log('[API] 使用直连 Railway:', origin);
        }
        return `${origin.replace(/\/$/, '')}/api/v1`;
      }
    }
    
    // 默认回退到同源代理
    return '/api/v1';
  }
  
  // 服务端渲染：默认使用 Edge 模式
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
 * 手机号验证码登录接口（与 axios /api/v1 的 base 解析规则一致）。
 * 直连 Railway 时必须走绝对 URL，否则 fetch('/api/auth/...') 会打到 Netlify/Next 而非后端。
 */
export function getAuthSmsLoginUrl(): string {
  if (typeof window === 'undefined') {
    return '/api/auth/sms/login';
  }
  const base = getBrowserApiBaseUrl();
  if (base.startsWith('http')) {
    const origin = base.replace(/\/api\/v1\/?$/i, '').replace(/\/$/, '');
    return `${origin}/api/auth/sms/login`;
  }
  return '/api/auth/sms/login';
}

/** 发送登录验证码（与登录 URL 同源策略一致） */
export function getAuthSmsSendCodeUrl(): string {
  if (typeof window === 'undefined') {
    return '/api/auth/sms/send-code';
  }
  const base = getBrowserApiBaseUrl();
  if (base.startsWith('http')) {
    const origin = base.replace(/\/api\/v1\/?$/i, '').replace(/\/$/, '');
    return `${origin}/api/auth/sms/send-code`;
  }
  return '/api/auth/sms/send-code';
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
  return `/api/v1${rest}`;
}
