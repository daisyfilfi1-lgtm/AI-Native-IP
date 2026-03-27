'use client';

import { useState, useEffect } from 'react';
import { MainLayout } from '@/components/layout/MainLayout';
import { Card, CardHeader } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Badge } from '@/components/ui/Badge';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/Tabs';
import { 
  Cloud,
  CheckCircle2,
  AlertCircle,
  ExternalLink,
  Save,
  RefreshCw,
  BookOpen,
  ChevronRight,
  Shield,
  Database
} from 'lucide-react';
import { api } from '@/lib/api';

interface FeishuConfig {
  app_id: string;
  app_secret: string; // 仅前端输入暂存，不从后端回显
  is_configured: boolean;
  last_tested?: string;
  status?: 'connected' | 'error' | 'unknown';
}

export default function IntegrationsConfigPage() {
  const [feishuConfig, setFeishuConfig] = useState<FeishuConfig>({
    app_id: '',
    app_secret: '',
    is_configured: false,
    status: 'unknown'
  });
  const [isLoading, setIsLoading] = useState(false);
  const [isTesting, setIsTesting] = useState(false);
  const [message, setMessage] = useState<{type: 'success' | 'error', text: string} | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const cfg = await api.getFeishuConfig();
        setFeishuConfig((prev) => ({
          ...prev,
          app_id: cfg.app_id || '',
          app_secret: '',
          is_configured: cfg.configured,
          status: cfg.configured ? 'connected' : 'unknown',
        }));
      } catch {
        setFeishuConfig((prev) => ({ ...prev, status: 'error' }));
      }
    })();
  }, []);

  const handleSave = async () => {
    setIsLoading(true);
    setMessage(null);
    
    try {
      await api.saveFeishuConfig({
        app_id: feishuConfig.app_id.trim(),
        app_secret: feishuConfig.app_secret.trim(),
      });
      
      setFeishuConfig(prev => ({ ...prev, is_configured: true }));
      setMessage({ type: 'success', text: 'Feishu credentials saved successfully!' });
    } catch (error) {
      setMessage({ type: 'error', text: 'Failed to save credentials' });
    } finally {
      setIsLoading(false);
    }
  };

  const handleTest = async () => {
    setIsTesting(true);
    setMessage(null);
    
    try {
      await api.getFeishuSpaces();
      
      setFeishuConfig(prev => ({ 
        ...prev, 
        status: 'connected',
        last_tested: new Date().toISOString()
      }));
      setMessage({ type: 'success', text: 'Connection successful!' });
    } catch (error) {
      setFeishuConfig(prev => ({ ...prev, status: 'error' }));
      setMessage({ type: 'error', text: 'Connection failed' });
    } finally {
      setIsTesting(false);
    }
  };

  return (
    <MainLayout title="Integration Config">
      {/* Header */}
      <div className="mb-8 p-6 rounded-2xl bg-gradient-to-r from-accent-blue/10 via-primary-500/10 to-accent-cyan/10 border border-accent-blue/20">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-accent-blue to-primary-500 flex items-center justify-center">
            <Cloud className="w-7 h-7 text-white" />
          </div>
          <div className="flex-1">
            <h2 className="text-xl font-bold text-foreground">Third-party Integrations</h2>
            <p className="text-foreground-secondary">Manage connections to external services</p>
          </div>
        </div>
      </div>

      <Tabs defaultValue="feishu" className="w-full">
        <TabsList>
          <TabsTrigger value="feishu" className="gap-2">
            <BookOpen className="w-4 h-4" />
            Feishu KB
            {feishuConfig.is_configured && (
              <Badge variant="success" size="sm" dot />
            )}
          </TabsTrigger>
          <TabsTrigger value="ai" className="gap-2 opacity-50 cursor-not-allowed">
            <Database className="w-4 h-4" />
            AI Models
            <Badge variant="default" size="sm">Soon</Badge>
          </TabsTrigger>
          <TabsTrigger value="storage" className="gap-2 opacity-50 cursor-not-allowed">
            <Shield className="w-4 h-4" />
            Storage
            <Badge variant="default" size="sm">Soon</Badge>
          </TabsTrigger>
        </TabsList>

        <TabsContent value="feishu">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Configuration Form */}
            <div className="lg:col-span-2 space-y-6">
              <Card>
                <CardHeader 
                  title="Feishu Open Platform Config" 
                  description="Enter your Feishu app credentials"
                />
                <div className="space-y-4">
                  {/* Status Banner */}
                  {feishuConfig.status === 'connected' && (
                    <div className="p-4 rounded-xl bg-accent-green/10 border border-accent-green/20 flex items-center gap-3">
                      <CheckCircle2 className="w-5 h-5 text-accent-green" />
                      <div className="flex-1">
                        <p className="text-sm font-medium text-accent-green">Connected</p>
                        <p className="text-xs text-accent-green/80">
                          Last tested: {feishuConfig.last_tested ? new Date(feishuConfig.last_tested).toLocaleString() : 'just now'}
                        </p>
                      </div>
                    </div>
                  )}
                  
                  {feishuConfig.status === 'error' && (
                    <div className="p-4 rounded-xl bg-accent-red/10 border border-accent-red/20 flex items-center gap-3">
                      <AlertCircle className="w-5 h-5 text-accent-red" />
                      <div>
                        <p className="text-sm font-medium text-accent-red">Connection failed</p>
                        <p className="text-xs text-accent-red/80">Check credentials and permissions</p>
                      </div>
                    </div>
                  )}

                  {/* App ID */}
                  <Input
                    label="App ID"
                    placeholder="cli_xxxxxxxxxxxx"
                    value={feishuConfig.app_id}
                    onChange={(e) => setFeishuConfig(prev => ({ ...prev, app_id: e.target.value }))}
                    helper="Get from Feishu Open Platform"
                  />

                  {/* App Secret */}
                  <div>
                    <label className="block text-sm font-medium text-foreground mb-2">
                      App Secret
                    </label>
                    <div className="relative">
                      <input
                        type="password"
                        placeholder="Enter App Secret"
                        value={feishuConfig.app_secret}
                        onChange={(e) => setFeishuConfig(prev => ({ ...prev, app_secret: e.target.value }))}
                        className="w-full bg-background-tertiary border border-border rounded-xl px-4 py-3 text-foreground placeholder:text-foreground-muted focus:outline-none focus:border-primary-500/50 focus:ring-2 focus:ring-primary-500/20"
                      />
                    </div>
                    <p className="mt-1.5 text-sm text-foreground-tertiary">
                      Credentials stored securely on server
                    </p>
                  </div>

                  {/* Message */}
                  {message && (
                    <div className={`p-3 rounded-xl ${
                      message.type === 'success' 
                        ? 'bg-accent-green/10 border border-accent-green/20 text-accent-green' 
                        : 'bg-accent-red/10 border border-accent-red/20 text-accent-red'
                    }`}>
                      {message.text}
                    </div>
                  )}

                  {/* Actions */}
                  <div className="flex gap-3">
                    <Button 
                      className="flex-1"
                      onClick={handleSave}
                      isLoading={isLoading}
                      disabled={!feishuConfig.app_id.trim() || !feishuConfig.app_secret.trim()}
                      leftIcon={<Save className="w-4 h-4" />}
                    >
                      Save Config
                    </Button>
                    <Button 
                      variant="secondary"
                      onClick={handleTest}
                      isLoading={isTesting}
                      disabled={!feishuConfig.app_id || !feishuConfig.app_secret}
                      leftIcon={<RefreshCw className="w-4 h-4" />}
                    >
                      Test Connection
                    </Button>
                  </div>
                </div>
              </Card>

              {/* Quick Actions */}
              <Card>
                <CardHeader title="Quick Actions" description="Common tasks after setup" />
                <div className="grid grid-cols-2 gap-3">
                  <a 
                    href="https://open.feishu.cn/app" 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="p-4 rounded-xl bg-background-tertiary hover:bg-background-elevated transition-colors group"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <ExternalLink className="w-5 h-5 text-foreground-secondary group-hover:text-primary-400" />
                      <ChevronRight className="w-4 h-4 text-foreground-muted" />
                    </div>
                    <p className="text-sm font-medium text-foreground">Feishu Open Platform</p>
                    <p className="text-xs text-foreground-tertiary mt-1">Manage app permissions</p>
                  </a>
                  
                  <button 
                    className="p-4 rounded-xl bg-background-tertiary hover:bg-background-elevated transition-colors text-left disabled:opacity-50 disabled:cursor-not-allowed"
                    disabled={!feishuConfig.is_configured}
                    onClick={() => window.location.href = '/agents/memory'}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <BookOpen className="w-5 h-5 text-foreground-secondary" />
                      <ChevronRight className="w-4 h-4 text-foreground-muted" />
                    </div>
                    <p className="text-sm font-medium text-foreground">Sync Knowledge Base</p>
                    <p className="text-xs text-foreground-tertiary mt-1">Start document sync</p>
                  </button>
                </div>
              </Card>
            </div>

            {/* Setup Guide */}
            <div className="space-y-6">
              <Card>
                <CardHeader title="Setup Guide" description="3 steps to integrate" />
                <div className="space-y-4">
                  {[
                    {
                      step: 1,
                      title: 'Create App',
                      desc: 'Create enterprise app in Feishu Open Platform',
                      link: 'https://open.feishu.cn/app',
                      linkText: 'Create'
                    },
                    {
                      step: 2,
                      title: 'Enable Permissions',
                      desc: 'Enable wiki:space:read and wiki:node:read',
                    },
                    {
                      step: 3,
                      title: 'Authorize Access',
                      desc: 'Add app as knowledge base member (read access)',
                    }
                  ].map((item) => (
                    <div key={item.step} className="flex gap-3">
                      <div className="w-6 h-6 rounded-full bg-primary-500 text-white text-xs flex items-center justify-center flex-shrink-0 mt-0.5">
                        {item.step}
                      </div>
                      <div className="flex-1">
                        <h4 className="text-sm font-medium text-foreground">{item.title}</h4>
                        <p className="text-xs text-foreground-tertiary mt-0.5">{item.desc}</p>
                        {item.link && (
                          <a 
                            href={item.link}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-xs text-primary-400 hover:text-primary-300 mt-1 inline-block"
                          >
                            {item.linkText} →
                          </a>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </Card>

              <Card>
                <CardHeader title="FAQ" description="Common questions" />
                <div className="space-y-3">
                  {[
                    { q: 'How to get App ID and Secret?', a: 'Feishu Open Platform → Credentials' },
                    { q: 'Sync failed?', a: 'Check permissions and knowledge base membership' },
                    { q: 'Supported document types?', a: 'Currently supports doc and docx' },
                  ].map((faq, idx) => (
                    <div key={idx} className="p-3 rounded-lg bg-background-tertiary">
                      <p className="text-sm font-medium text-foreground">{faq.q}</p>
                      <p className="text-xs text-foreground-secondary mt-1">{faq.a}</p>
                    </div>
                  ))}
                </div>
              </Card>
            </div>
          </div>
        </TabsContent>
      </Tabs>
    </MainLayout>
  );
}
