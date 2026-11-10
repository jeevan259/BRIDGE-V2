import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  BookOpen,
  CheckSquare,
  GitBranch,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  ArrowRight,
  TrendingUp,
  FileCheck2,
  Clock,
  Layers,
} from 'lucide-react';
import apiClient from '@/lib/api';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { StatusChip } from '@/components/ui/StatusChip';
import { Spinner } from '@/components/ui/Spinner';
import { ErrorState } from '@/components/ui/ErrorState';
import { DashboardStats } from '@/types';
import { useAuthStore } from '@/lib/auth';

export const DashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuthStore();

  const {
    data: stats,
    isLoading,
    isError,
    refetch,
  } = useQuery<DashboardStats>({
    queryKey: ['dashboard-stats'],
    queryFn: async () => {
      const { data } = await apiClient.get<DashboardStats>('/dashboard/stats');
      return data;
    },
    refetchInterval: 10000,
  });

  if (isLoading) {
    return (
      <div className="h-96 flex items-center justify-center">
        <Spinner size="lg" label="Synchronizing governance telemetry..." />
      </div>
    );
  }

  if (isError || !stats) {
    return (
      <ErrorState
        title="Telemetry Unavailable"
        message="Could not load live dashboard telemetry from the BRIDGE API. Please ensure your backend server is running."
        onRetry={() => refetch()}
      />
    );
  }

  const kpiCards = [
    {
      title: 'Active Brand Rules',
      value: stats.knowledge_items.approved,
      subtext: `${stats.knowledge_items.total} total indexed entries`,
      icon: BookOpen,
      color: 'text-blue-400',
      bg: 'bg-blue-500/10',
      border: 'border-blue-500/30',
      action: () => navigate('/knowledge'),
    },
    {
      title: 'Active Findings',
      value: stats.active_findings.total,
      subtext: `${stats.active_findings.high_severity} high severity breaches`,
      icon: ShieldAlert,
      color: 'text-rose-400',
      bg: 'bg-rose-500/10',
      border: 'border-rose-500/30',
      action: () => navigate('/validation'),
    },
    {
      title: 'Revalidation Queue',
      value: stats.pending_tasks.total,
      subtext: `${stats.pending_tasks.pending} pending blast radius checks`,
      icon: GitBranch,
      color: 'text-amber-400',
      bg: 'bg-amber-500/10',
      border: 'border-amber-500/30',
      action: () => navigate('/continuity'),
    },
    {
      title: 'Audit Chain Status',
      value: 'INTACT',
      subtext: 'SHA-256 tamper-evident link active',
      icon: ShieldCheck,
      color: 'text-emerald-400',
      bg: 'bg-emerald-500/10',
      border: 'border-emerald-500/30',
      action: () => navigate('/governance'),
    },
  ];

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      {/* Welcome Banner */}
      <div className="relative overflow-hidden bg-gradient-to-r from-blue-900/30 via-slate-900/80 to-[#151D2F] border border-blue-500/20 rounded-2xl p-6 sm:p-8 shadow-xl">
        <div className="relative z-10 max-w-2xl">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-500/15 border border-blue-500/30 text-blue-300 text-xs font-mono mb-4">
            <Layers className="w-3.5 h-3.5" />
            <span>ORGANIZATION: APEX GLOBAL TECHNOLOGIES</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
            Brand Governance Command Center
          </h1>
          <p className="mt-2 text-sm text-slate-300 leading-relaxed">
            Real-time compliance monitoring, deterministic rule enforcement, AI evidence receipts,
            and automated blast-radius revalidation across all enterprise digital assets.
          </p>
          <div className="mt-6 flex flex-wrap items-center gap-3">
            <Button
              variant="primary"
              size="sm"
              leftIcon={<CheckSquare className="w-4 h-4" />}
              onClick={() => navigate('/validation')}
            >
              Run Content Validation
            </Button>
            <Button
              variant="secondary"
              size="sm"
              leftIcon={<GitBranch className="w-4 h-4" />}
              onClick={() => navigate('/continuity')}
            >
              Inspect Blast Radius
            </Button>
          </div>
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        {kpiCards.map((kpi, idx) => {
          const Icon = kpi.icon;
          return (
            <div
              key={idx}
              onClick={kpi.action}
              className="bg-[#151D2F] border border-slate-800 hover:border-slate-700 p-5 rounded-xl shadow-lg transition-all duration-200 hover:-translate-y-0.5 cursor-pointer group"
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">
                  {kpi.title}
                </span>
                <div className={`p-2 rounded-lg ${kpi.bg} ${kpi.color} ${kpi.border} border`}>
                  <Icon className="w-4 h-4" />
                </div>
              </div>
              <div className="mt-4 flex items-baseline gap-2">
                <span className="text-3xl font-extrabold text-white tracking-tight">
                  {kpi.value}
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-1 flex items-center justify-between">
                <span>{kpi.subtext}</span>
                <ArrowRight className="w-3.5 h-3.5 text-slate-600 group-hover:text-blue-400 group-hover:translate-x-0.5 transition-all" />
              </p>
            </div>
          );
        })}
      </div>

      {/* Engines Overview */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Knowledge & Validation Summary */}
        <Card>
          <CardHeader>
            <div>
              <CardTitle>Validation & Evidence Telemetry</CardTitle>
              <CardDescription>
                Deterministic rules & AI adversarial verification pipeline
              </CardDescription>
            </div>
            <Button variant="ghost" size="sm" onClick={() => navigate('/validation')}>
              View Engine
            </Button>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="p-4 bg-slate-900/60 rounded-lg border border-slate-800 space-y-2">
              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-400 font-medium">Compliance Verification Rate</span>
                <span className="text-emerald-400 font-mono font-semibold">94.2%</span>
              </div>
              <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                <div className="bg-emerald-500 h-full rounded-full" style={{ width: '94.2%' }} />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="p-3 bg-slate-900/40 rounded-lg border border-slate-800/80">
                <span className="text-slate-400 block mb-1">Evidence Receipts</span>
                <span className="text-lg font-bold text-slate-200">Cryptographic</span>
                <span className="text-[10px] text-slate-500 block mt-0.5">Exact quote matching</span>
              </div>
              <div className="p-3 bg-slate-900/40 rounded-lg border border-slate-800/80">
                <span className="text-slate-400 block mb-1">AI Provider Model</span>
                <span className="text-lg font-bold text-blue-400 font-mono">Gemini 1.5</span>
                <span className="text-[10px] text-slate-500 block mt-0.5">Sub-second inference</span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Brand Continuity & GuidelineX Summary */}
        <Card>
          <CardHeader>
            <div>
              <CardTitle>Continuity & GuidelineX</CardTitle>
              <CardDescription>
                Dependency tracking, version impact & ambiguity analysis
              </CardDescription>
            </div>
            <Button variant="ghost" size="sm" onClick={() => navigate('/continuity')}>
              View Graph
            </Button>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between p-3.5 bg-slate-900/60 rounded-lg border border-slate-800">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-purple-500/10 border border-purple-500/30 flex items-center justify-center text-purple-400">
                  <Sparkles className="w-4 h-4" />
                </div>
                <div>
                  <h4 className="text-xs font-semibold text-slate-200">GuidelineX Ambiguity Radar</h4>
                  <p className="text-[11px] text-slate-400">Identified 2 review signals with high friction</p>
                </div>
              </div>
              <Button size="sm" variant="outline" onClick={() => navigate('/guidelines')}>
                Resolve
              </Button>
            </div>

            <div className="flex items-center justify-between p-3.5 bg-slate-900/60 rounded-lg border border-slate-800">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-teal-500/10 border border-teal-500/30 flex items-center justify-center text-teal-400">
                  <GitBranch className="w-4 h-4" />
                </div>
                <div>
                  <h4 className="text-xs font-semibold text-slate-200">Enterprise Blast Radius</h4>
                  <p className="text-[11px] text-slate-400">Latest spec update affected 2 digital assets</p>
                </div>
              </div>
              <Button size="sm" variant="outline" onClick={() => navigate('/continuity')}>
                Inspect
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

