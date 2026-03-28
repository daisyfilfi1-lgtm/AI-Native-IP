/// <reference types="@netlify/edge-functions" />

/**
 * Netlify Edge Function - API Proxy
 * 将 /api/* 请求代理到 Railway 后端，解决 CORS 和超时问题
 * 
 * 运行时: Deno
 * 部署位置: Netlify 全球边缘节点 (50+ locations)
 */

// Railway 后端地址
const RAILWAY_API = "https://ai-native-ip-production.up.railway.app";

// 允许的前端域名（生产环境应收紧）
const ALLOWED_ORIGINS = [
  "https://ai-native-ip.netlify.app",
];

// 开发环境额外允许的域名
const DEV_ORIGINS = [
  "http://localhost:3000",
  "http://localhost:8888",
  "https://localhost:3000",
];

// 根据环境判断
const IS_PRODUCTION = !Deno.env.get("NETLIFY_DEV") && 
                      !Deno.env.get("NODE_ENV")?.includes("dev");

const EFFECTIVE_ALLOWED_ORIGINS = IS_PRODUCTION 
  ? ALLOWED_ORIGINS 
  : [...ALLOWED_ORIGINS, ...DEV_ORIGINS];

/** Netlify 分支预览、自定义域名等：允许 *.netlify.app / *.vercel.app，及环境变量追加 */
function isOriginAllowed(origin: string): boolean {
  if (!origin) return true;
  if (EFFECTIVE_ALLOWED_ORIGINS.includes(origin)) return true;
  try {
    const u = new URL(origin);
    const h = u.hostname.toLowerCase();
    if (h.endsWith(".netlify.app") || h.endsWith(".vercel.app")) return true;
  } catch {
    return false;
  }
  const extra = Deno.env.get("NETLIFY_EXTRA_ORIGINS") || Deno.env.get("ALLOWED_ORIGINS") || "";
  const list = extra.split(",").map((s) => s.trim()).filter(Boolean);
  return list.includes(origin);
}

// 上传文件大小限制 (10MB，与后端一致)
const MAX_UPLOAD_SIZE = 10 * 1024 * 1024;

/** 普通 API 请求超时（毫秒） */
const REQUEST_TIMEOUT_DEFAULT = 30000;
/** 创作生成类接口（仿写/爆款等）可能超过 Edge 默认 30s，仍可能被平台截断；优先使用直连 Railway（见 apiBaseUrl） */
const REQUEST_TIMEOUT_LONG_MS = 120000;

function requestTimeoutMs(path: string, method: string): number {
  if (method.toUpperCase() === "POST" && path.includes("/creator/generate")) {
    return REQUEST_TIMEOUT_LONG_MS;
  }
  return REQUEST_TIMEOUT_DEFAULT;
}

// Edge Function 主入口
export default async (request: Request): Promise<Response> => {
  const url = new URL(request.url);
  const path = url.pathname;
  const startTime = Date.now();

  console.log(`[Edge] ${request.method} ${path} - Started`);

  // 1. CORS 预检请求处理
  if (request.method === "OPTIONS") {
    return handleCorsPreflight(request);
  }

  // 2. 验证请求路径
  if (!path.startsWith("/api/")) {
    return jsonResponse({ error: "Not Found" }, 404);
  }

  // 3. 验证请求来源（含 Netlify 预览域名、可选环境变量白名单）
  const origin = request.headers.get("origin") || "";
  if (origin && !isOriginAllowed(origin)) {
    console.warn(`[Edge] Blocked request from unauthorized origin: ${origin}`);
    return jsonResponse({ error: "Forbidden - Invalid origin" }, 403);
  }

  // 4. 特殊处理文件上传请求（仅 /upload，不包括 /ingest）
  if (path.includes("/upload")) {
    const validation = validateUploadRequest(request);
    if (!validation.valid) {
      return jsonResponse({ error: validation.error }, validation.status);
    }
  }

  // 5. 转发请求到 Railway
  try {
    const response = await proxyToRailway(request, path, url.search);
    
    const duration = Date.now() - startTime;
    console.log(`[Edge] ${request.method} ${path} - ${response.status} in ${duration}ms`);

    // 添加上传相关的响应头
    if (path.includes("/upload")) {
      response.headers.set("X-Edge-Processed", "true");
      response.headers.set("X-Edge-Duration", `${duration}ms`);
    }

    return response;

  } catch (error) {
    const duration = Date.now() - startTime;
    console.error(`[Edge] ${request.method} ${path} - ERROR after ${duration}ms:`, error);
    
    const err = error instanceof Error ? error : new Error(String(error));
    return handleProxyError(err, origin);
  }
};

// ─────────────────────────────────────────────
// 上传请求验证（仅用于 /upload 路径）
// ─────────────────────────────────────────────
function validateUploadRequest(request: Request): { 
  valid: boolean; 
  error?: string; 
  status?: number 
} {
  // 检查文件大小
  const contentLength = request.headers.get("content-length");
  if (contentLength) {
    const size = parseInt(contentLength, 10);
    if (isNaN(size) || size > MAX_UPLOAD_SIZE) {
      return {
        valid: false,
        error: `文件大小超过限制 (最大 ${MAX_UPLOAD_SIZE / 1024 / 1024}MB)`,
        status: 413,
      };
    }
  }

  // 检查 Content-Type（上传请求必须是 multipart/form-data）
  const contentType = request.headers.get("content-type") || "";
  if (!contentType.includes("multipart/form-data")) {
    return {
      valid: false,
      error: "必须使用 multipart/form-data 格式上传",
      status: 400,
    };
  }

  // 检查 boundary
  if (!contentType.includes("boundary=")) {
    return {
      valid: false,
      error: "无效的上传请求格式 (缺少 boundary)",
      status: 400,
    };
  }

  return { valid: true };
}

// ─────────────────────────────────────────────
// 代理请求到 Railway
// ─────────────────────────────────────────────
async function proxyToRailway(
  request: Request,
  path: string,
  search: string
): Promise<Response> {
  const targetUrl = `${RAILWAY_API}${path}${search}`;
  
  // 构建请求头
  const headers = new Headers();
  request.headers.forEach((value, key) => {
    // 排除可能导致问题的头部
    const lowerKey = key.toLowerCase();
    if (lowerKey !== "host" && lowerKey !== "origin") {
      headers.set(key, value);
    }
  });

  // 添加转发标识头
  headers.set("X-Forwarded-By", "netlify-edge-function");
  headers.set("X-Forwarded-Proto", "https");

  const timeoutMs = requestTimeoutMs(path, request.method);
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(targetUrl, {
      method: request.method,
      headers,
      body: request.body,  // 直接转发 body，支持 JSON 和 FormData
      signal: controller.signal,
    });
    clearTimeout(timer);

    // 构建带 CORS 头的响应
    const corsHeaders = new Headers(response.headers);
    corsHeaders.set("Access-Control-Allow-Origin", "*");
    corsHeaders.set("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS");
    corsHeaders.set("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Requested-With");

    return new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers: corsHeaders,
    });

  } catch (error) {
    clearTimeout(timer);
    throw error;
  }
}

// ─────────────────────────────────────────────
// CORS 预检处理
// ─────────────────────────────────────────────
function handleCorsPreflight(request: Request): Response {
  const origin = request.headers.get("origin") || "";
  
  // 验证来源是否允许
  if (origin && !isOriginAllowed(origin)) {
    return new Response(null, { status: 403 });
  }
  
  return new Response(null, {
    status: 204,
    headers: {
      "Access-Control-Allow-Origin": origin && isOriginAllowed(origin) ? origin : ALLOWED_ORIGINS[0],
      "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With, X-API-Key",
      "Access-Control-Max-Age": "86400",
    },
  });
}

// ─────────────────────────────────────────────
// 代理错误处理
// ─────────────────────────────────────────────
function handleProxyError(error: Error, origin: string): Response {
  let status = 502;
  let message = "服务暂时不可用，请稍后重试";
  let code = "EDGE_PROXY_ERROR";

  if (error.name === "AbortError") {
    status = 504;
    message = "请求超时，请稍后重试或尝试较小的文件";
    code = "EDGE_TIMEOUT";
  }

  return jsonResponse(
    {
      error: message,
      code,
      timestamp: new Date().toISOString(),
    },
    status,
    origin
  );
}

// ─────────────────────────────────────────────
// 工具函数：JSON 响应
// ─────────────────────────────────────────────
function jsonResponse(
  data: any,
  status: number = 200,
  origin: string = ""
): Response {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": origin || "*",
    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
  };

  return new Response(JSON.stringify(data), {
    status,
    headers,
  });
}
