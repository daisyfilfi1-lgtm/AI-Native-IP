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
 * - 生产环境：设置 NEXT_PUBLIC_API_MODE=edge
 * - 或在 netlify.toml 中配置 Edge Function 路由
 */

const DEFAULT_PRODUCTION_API_ORIGIN = 'https://ai-native-ip-production.up.railway.app';

/** API 模式 */
type ApiMode = 'direct' | 'edge' | 'proxy';

function getApiMode(): ApiMode {
  if (typeof window === 'undefined') return 'edge';
  
  const mode = process.env.NEXT_PUBLIC_API_MODE?.trim()?.toLowerCase();
  
  // 显式设置 edge 模式
  if (mode === 'edge') return 'edge';
  
  // 显式设置 direct 模式
  if (mode === 'direct') return 'direct';
  
  // 默认使用 Edge 模式
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
      console.log('[API] 使用 Edge Function 代理模式');
      return '/api/v1';
    }
    
    // 直连模式：直接调用 Railway
    if (mode === 'direct') {
      const directOrigin = process.env.NEXT_PUBLIC_API_DIRECT_ORIGIN?.trim();
      const origin = directOrigin || DEFAULT_PRODUCTION_API_ORIGIN;
      
      if (origin && /^https:\/\//i.test(origin)) {
        console.log('[API] 使用直连 Railway:', origin);
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
