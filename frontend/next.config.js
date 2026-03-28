/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  
  // 图片配置
  images: {
    unoptimized: true,  // Netlify 部署需要
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'ai-native-ip-production.up.railway.app',
      },
    ],
  },
  
  // 本地开发时重写 API 请求到 Railway
  // 生产环境默认浏览器直连 Railway（见 lib/apiBaseUrl）；此配置仅 dev 生效
  async rewrites() {
    if (process.env.NODE_ENV === 'production') {
      return [];
    }
    
    const backend = (process.env.RAILWAY_API_ORIGIN || 'http://127.0.0.1:8000').replace(/\/$/, '');
    // 统一转发 /api/*（含 /api/v1、/api/auth、/api/creator），否则本地仅 /api/v1 时验证码登录等无法到达后端
    return [
      {
        source: '/api/:path*',
        destination: `${backend}/api/:path*`,
      },
    ];
  },
  
  // 输出配置
  output: 'standalone',  // 推荐用于 Netlify
};

module.exports = nextConfig;
