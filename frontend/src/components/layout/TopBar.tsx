import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { useAuthStore } from '@/lib/auth';
import { StatusChip } from '../ui/StatusChip';
import { Building2 } from 'lucide-react';
import apiClient from '@/lib/api';

interface AIStatus {
  provider: string;
  mode: 'live' | 'fallback' | 'mock';
  model: string;
  last_error: string | null;
}

export const TopBar: React.FC = () => {
  const { user } = useAuthStore();

  const { data: aiStatus } = useQuery<AIStatus>({
    queryKey: ['ai-status'],
    queryFn: async () => {
      const { data } = await apiClient.get<AIStatus>('/ai/status');
      return data;
    },
    refetchInterval: 30000,
  });

  const mode = aiStatus?.mode;
  const label = mode === 'live' ? 'AI: Gemini live' : mode === 'fallback' ? 'AI: fallback' : mode === 'mock' ? 'AI: mock' : 'AI: status unavailable';

  return (
    <header className="h-16 bg-[#0F172A]/90 backdrop-blur-md border-b border-slate-800 fixed top-0 right-0 left-64 z-20 px-8 flex items-center justify-between">
      {/* Left: Org info */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2 text-slate-300 font-medium text-sm">
          <Building2 className="w-4 h-4 text-blue-400" />
          <span>Apex Global Technologies</span>
        </div>
        <span className="text-slate-600">/</span>
        <span className="text-xs font-mono text-slate-400 bg-slate-800/80 px-2 py-0.5 rounded border border-slate-700/60">
          PROD-TENANT-01
        </span>
      </div>

      {/* Right: Security & user status */}
      <div className="flex items-center gap-4">
        {/* Dynamic AI Status Badge */}
        <div
          className={`flex items-center gap-2 text-xs font-mono px-2.5 py-1 rounded-full border ${
            mode === 'live'
              ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
              : mode === 'fallback'
              ? 'bg-amber-500/10 text-amber-400 border-amber-500/20'
              : 'bg-slate-500/10 text-slate-400 border-slate-500/20'
          }`}
        >
          <span
            className={`w-2 h-2 rounded-full ${
              mode === 'live' ? 'bg-emerald-400 animate-pulse' : mode === 'fallback' ? 'bg-amber-400' : 'bg-slate-400'
            }`}
          />
          <span>{label}</span>
        </div>

        {/* User Role Chip */}
        {user?.role && (
          <StatusChip
            status={
              user.role === 'administrator'
                ? 'confirmed'
                : user.role === 'brand_manager'
                ? 'approved'
                : user.role === 'reviewer'
                ? 'low'
                : 'possible'
            }
            label={user.role.replace('_', ' ').toUpperCase()}
            size="sm"
          />
        )}
      </div>
    </header>
  );
};
