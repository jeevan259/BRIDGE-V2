import React from 'react';
import {
  CheckCircle2,
  XCircle,
  AlertTriangle,
  AlertCircle,
  Info,
  Clock,
  Check,
  RefreshCw,
  Ban,
  ShieldCheck,
  HelpCircle,
} from 'lucide-react';

export type StatusType =
  | 'supported'
  | 'unsupported'
  | 'high'
  | 'medium'
  | 'low'
  | 'pending'
  | 'approved'
  | 'superseded'
  | 'rejected'
  | 'confirmed'
  | 'possible'
  | 'completed'
  | 'running'
  | 'failed';

interface StatusChipProps {
  status: StatusType | string;
  label?: string;
  size?: 'sm' | 'md';
  showIcon?: boolean;
  className?: string;
}

const statusConfigs: Record<
  string,
  {
    bg: string;
    text: string;
    border: string;
    icon: React.ComponentType<{ className?: string }>;
    defaultLabel: string;
  }
> = {
  supported: {
    bg: 'bg-emerald-500/10',
    text: 'text-emerald-400',
    border: 'border-emerald-500/30',
    icon: CheckCircle2,
    defaultLabel: 'Supported',
  },
  unsupported: {
    bg: 'bg-rose-500/10',
    text: 'text-rose-400',
    border: 'border-rose-500/30',
    icon: XCircle,
    defaultLabel: 'Unsupported',
  },
  high: {
    bg: 'bg-red-500/15',
    text: 'text-red-400',
    border: 'border-red-500/35',
    icon: AlertTriangle,
    defaultLabel: 'High',
  },
  medium: {
    bg: 'bg-amber-500/15',
    text: 'text-amber-400',
    border: 'border-amber-500/35',
    icon: AlertCircle,
    defaultLabel: 'Medium',
  },
  low: {
    bg: 'bg-sky-500/10',
    text: 'text-sky-400',
    border: 'border-sky-500/30',
    icon: Info,
    defaultLabel: 'Low',
  },
  info: {
    bg: 'bg-blue-500/10',
    text: 'text-blue-400',
    border: 'border-blue-500/30',
    icon: Info,
    defaultLabel: 'Info',
  },
  pending: {
    bg: 'bg-amber-500/10',
    text: 'text-amber-400',
    border: 'border-amber-500/30',
    icon: Clock,
    defaultLabel: 'Pending',
  },
  approved: {
    bg: 'bg-emerald-500/15',
    text: 'text-emerald-400',
    border: 'border-emerald-500/35',
    icon: Check,
    defaultLabel: 'Approved',
  },
  superseded: {
    bg: 'bg-purple-500/10',
    text: 'text-purple-400',
    border: 'border-purple-500/30',
    icon: RefreshCw,
    defaultLabel: 'Superseded',
  },
  rejected: {
    bg: 'bg-rose-500/15',
    text: 'text-rose-400',
    border: 'border-rose-500/35',
    icon: Ban,
    defaultLabel: 'Rejected',
  },
  confirmed: {
    bg: 'bg-teal-500/15',
    text: 'text-teal-400',
    border: 'border-teal-500/35',
    icon: ShieldCheck,
    defaultLabel: 'Confirmed',
  },
  possible: {
    bg: 'bg-slate-500/15',
    text: 'text-slate-400',
    border: 'border-slate-500/30',
    icon: HelpCircle,
    defaultLabel: 'Possible',
  },
  completed: {
    bg: 'bg-emerald-500/10',
    text: 'text-emerald-400',
    border: 'border-emerald-500/30',
    icon: CheckCircle2,
    defaultLabel: 'Completed',
  },
  running: {
    bg: 'bg-blue-500/10',
    text: 'text-blue-400',
    border: 'border-blue-500/30',
    icon: RefreshCw,
    defaultLabel: 'Running',
  },
  failed: {
    bg: 'bg-rose-500/15',
    text: 'text-rose-400',
    border: 'border-rose-500/35',
    icon: XCircle,
    defaultLabel: 'Failed',
  },
  overridden: {
    bg: 'bg-indigo-500/15',
    text: 'text-indigo-400',
    border: 'border-indigo-500/35',
    icon: ShieldCheck,
    defaultLabel: 'Overridden',
  },
};

export const StatusChip: React.FC<StatusChipProps> = ({
  status,
  label,
  size = 'sm',
  showIcon = true,
  className = '',
}) => {
  const normalizedKey = status.toLowerCase();
  const config = statusConfigs[normalizedKey] || {
    bg: 'bg-slate-800',
    text: 'text-slate-300',
    border: 'border-slate-700',
    icon: Info,
    defaultLabel: status,
  };

  const Icon = config.icon;
  const isSm = size === 'sm';

  return (
    <span
      className={`inline-flex items-center gap-1.5 font-medium rounded-full border transition-colors ${config.bg} ${config.text} ${config.border} ${
        isSm ? 'px-2 py-0.5 text-xs' : 'px-3 py-1 text-sm'
      } ${className}`}
    >
      {showIcon && <Icon className={isSm ? 'w-3 h-3' : 'w-4 h-4'} />}
      <span>{label || config.defaultLabel}</span>
    </span>
  );
};

