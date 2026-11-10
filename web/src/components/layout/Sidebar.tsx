import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  BookOpen,
  Send,
  Inbox,
  GitBranch,
  Sparkles,
  ShieldCheck,
  Users,
  LogOut,
  Layers,
} from 'lucide-react';
import { useAuthStore } from '@/lib/auth';
import { UserRole } from '@/types';

interface NavItem {
  label: string;
  path: string;
  icon: React.ComponentType<{ className?: string }>;
  allowedRoles: UserRole[];
  badge?: string;
}

const navItems: NavItem[] = [
  {
    label: 'Overview',
    path: '/dashboard',
    icon: LayoutDashboard,
    allowedRoles: ['administrator', 'brand_manager', 'reviewer', 'creator', 'auditor'],
  },
  {
    label: 'Knowledge',
    path: '/knowledge',
    icon: BookOpen,
    allowedRoles: ['administrator', 'brand_manager', 'reviewer', 'creator', 'auditor'],
  },
  {
    label: 'Submissions',
    path: '/submissions',
    icon: Send,
    allowedRoles: ['administrator', 'brand_manager', 'reviewer', 'creator', 'auditor'],
  },
  {
    label: 'Review',
    path: '/review',
    icon: Inbox,
    allowedRoles: ['administrator', 'brand_manager', 'reviewer', 'auditor'],
  },
  {
    label: 'Continuity',
    path: '/continuity',
    icon: GitBranch,
    allowedRoles: ['administrator', 'brand_manager', 'reviewer', 'auditor'],
  },
  {
    label: 'GuidelineX',
    path: '/guidelines',
    icon: Sparkles,
    allowedRoles: ['administrator', 'brand_manager', 'reviewer', 'auditor'],
  },
  {
    label: 'Audit',
    path: '/governance',
    icon: ShieldCheck,
    allowedRoles: ['administrator', 'brand_manager', 'reviewer', 'auditor'],
  },
  {
    label: 'Admin',
    path: '/admin',
    icon: Users,
    allowedRoles: ['administrator'],
  },
];

export const Sidebar: React.FC = () => {
  const { user, logout } = useAuthStore();
  const userRole = user?.role || 'creator';

  const visibleNav = navItems.filter((item) => item.allowedRoles.includes(userRole));

  return (
    <aside className="w-64 bg-[#0F172A] border-r border-slate-800 flex flex-col h-screen fixed left-0 top-0 z-30 select-none">
      {/* Brand Header */}
      <div className="h-16 px-6 flex items-center gap-3 border-b border-slate-800 bg-[#0B0F19]/60">
        <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-blue-600 to-sky-400 flex items-center justify-center shadow-glow">
          <Layers className="w-5 h-5 text-white" />
        </div>
        <div>
          <span className="font-bold text-lg tracking-wider text-white">BRIDGE</span>
          <span className="text-[10px] block text-sky-400 font-mono tracking-widest font-semibold uppercase">
            GOVERNANCE V2
          </span>
        </div>
      </div>

      {/* Navigation List */}
      <nav className="flex-1 px-3 py-6 space-y-1.5 overflow-y-auto">
        <div className="px-3 pb-2 text-[11px] font-semibold tracking-wider text-slate-500 uppercase font-mono">
          Core Navigation
        </div>
        {visibleNav.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                `flex items-center justify-between px-3.5 py-2.5 rounded-lg text-sm font-medium transition-all group ${
                  isActive
                    ? 'bg-blue-600/15 text-blue-400 border border-blue-500/30 shadow-sm'
                    : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800/60'
                }`
              }
            >
              <div className="flex items-center gap-3">
                <Icon className="w-4 h-4 transition-transform group-hover:scale-110" />
                <span>{item.label}</span>
              </div>
              {item.badge && (
                <span className="px-1.5 py-0.5 text-[10px] font-mono bg-blue-500/20 text-blue-300 rounded border border-blue-500/30">
                  {item.badge}
                </span>
              )}
            </NavLink>
          );
        })}
      </nav>

      {/* User profile footer */}
      <div className="p-4 border-t border-slate-800 bg-slate-900/40">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3 min-w-0">
            <div className="w-8 h-8 rounded-full bg-blue-500/20 border border-blue-500/30 flex items-center justify-center text-xs font-bold text-blue-300 shrink-0">
              {user?.full_name ? user.full_name[0] : 'U'}
            </div>
            <div className="min-w-0">
              <p className="text-xs font-semibold text-slate-200 truncate">
                {user?.full_name || user?.email || 'User'}
              </p>
              <p className="text-[10px] text-slate-400 capitalize font-mono">
                {user?.role?.replace('_', ' ')}
              </p>
            </div>
          </div>
          <button
            onClick={() => logout()}
            title="Log out"
            className="p-1.5 text-slate-400 hover:text-rose-400 rounded-lg hover:bg-slate-800 transition-colors"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </aside>
  );
};
