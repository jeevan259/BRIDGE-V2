import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Layers,
  ShieldCheck,
  ArrowRight,
  UserCircle2,
  KeyRound,
  Sparkles,
  Zap,
  UserPlus,
  LogIn,
  CheckCircle2,
} from 'lucide-react';
import { useAuthStore } from '@/lib/auth';
import apiClient from '@/lib/api';
import { Button } from '@/components/ui/Button';
import { User, UserRole } from '@/types';

interface DemoUserPreset {
  role: UserRole;
  label: string;
  email: string;
  description: string;
}

const DEMO_PRESETS: DemoUserPreset[] = [
  {
    role: 'administrator',
    label: 'Administrator',
    email: 'admin@aurora.local',
    description: 'Full governance, impact simulation & chain verification',
  },
  {
    role: 'brand_manager',
    label: 'Brand Manager',
    email: 'brand_manager@aurora.local',
    description: 'Knowledge source management, rule approvals & GuidelineX',
  },
  {
    role: 'reviewer',
    label: 'Reviewer',
    email: 'reviewer@aurora.local',
    description: 'Content review queues, evidence override & signals logging',
  },
  {
    role: 'creator',
    label: 'Creator',
    email: 'creator@aurora.local',
    description: 'Asset submission & pre-flight deterministic validation',
  },
  {
    role: 'auditor',
    label: 'Auditor',
    email: 'auditor@aurora.local',
    description: 'Read-only compliance telemetry & cryptographic chain audit',
  },
];

const DEMO_PASSWORD = 'password123';

export const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const { login } = useAuthStore();
  const [mode, setMode] = useState<'signin' | 'signup'>('signin');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isGuestLoading, setIsGuestLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const performLogin = (token: string, user: User, targetPath = '/dashboard') => {
    login(token, user);
    navigate(targetPath);
  };

  const handleGuestLogin = async () => {
    setIsGuestLoading(true);
    setError(null);
    try {
      const { data: tokenData } = await apiClient.post<{ access_token: string }>('/auth/guest');
      localStorage.setItem('bridge_access_token', tokenData.access_token);
      const { data: userData } = await apiClient.get<User>('/auth/me');
      performLogin(tokenData.access_token, userData, '/review');
    } catch (err: any) {
      localStorage.removeItem('bridge_access_token');
      const detail =
        err?.response?.data?.error?.message ||
        err?.response?.data?.detail ||
        err?.message ||
        'Guest access temporarily unavailable';
      setError(String(detail));
    } finally {
      setIsGuestLoading(false);
    }
  };

  const handleLoginWithCredentials = async (targetEmail: string, targetPassword: string) => {
    setIsLoading(true);
    setError(null);

    try {
      const { data: tokenData } = await apiClient.post<{ access_token: string }>(
        '/auth/login',
        { email: targetEmail, password: targetPassword }
      );

      localStorage.setItem('bridge_access_token', tokenData.access_token);
      const { data: userData } = await apiClient.get<User>('/auth/me');
      performLogin(tokenData.access_token, userData);
    } catch (err: any) {
      localStorage.removeItem('bridge_access_token');
      const status = err?.response?.status;
      const detail =
        err?.response?.data?.error?.message ||
        err?.response?.data?.detail ||
        err?.message ||
        'Authentication failed';
      setError(status ? `HTTP ${status}: ${String(detail)}` : `Network error: ${String(detail)}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    try {
      const { data: tokenData } = await apiClient.post<{ access_token: string }>(
        '/auth/register',
        { email, password, full_name: fullName || undefined }
      );
      localStorage.setItem('bridge_access_token', tokenData.access_token);
      const { data: userData } = await apiClient.get<User>('/auth/me');
      performLogin(tokenData.access_token, userData, '/review');
    } catch (err: any) {
      localStorage.removeItem('bridge_access_token');
      const detail =
        err?.response?.data?.error?.message ||
        err?.response?.data?.detail ||
        err?.message ||
        'Failed to register account';
      setError(String(detail));
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (mode === 'signup') {
      handleSignup(e);
    } else {
      handleLoginWithCredentials(email, password);
    }
  };

  return (
    <div className="min-h-screen bg-[#090D16] flex flex-col justify-center py-12 sm:px-6 lg:px-8 relative overflow-hidden">
      {/* Background ambient gradient glow */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[400px] bg-gradient-to-b from-blue-600/15 via-sky-500/5 to-transparent blur-3xl pointer-events-none" />

      <div className="sm:mx-auto sm:w-full sm:max-w-md relative z-10 text-center">
        <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-gradient-to-tr from-blue-600 to-sky-400 shadow-glow mb-4">
          <Layers className="w-8 h-8 text-white" />
        </div>
        <h2 className="text-3xl font-extrabold text-white tracking-tight">BRIDGE</h2>
        <p className="mt-1 text-sm text-slate-400">
          Brand Rules, Intelligence, Dependency, Governance & Evidence
        </p>
      </div>

      <div className="mt-6 sm:mx-auto sm:w-full sm:max-w-xl relative z-10 px-4">
        {/* Instant Access Banner */}
        <div className="mb-4 p-5 bg-gradient-to-r from-blue-950/60 via-indigo-950/40 to-slate-900 border border-blue-500/30 rounded-2xl shadow-xl flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="space-y-1 text-center sm:text-left">
            <div className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-300 text-[11px] font-mono">
              <Sparkles className="w-3 h-3 text-blue-400" />
              Round 2 Evaluation
            </div>
            <h3 className="text-sm font-semibold text-white">Experience BRIDGE Instantly</h3>
            <p className="text-xs text-slate-400">
              No sign-up or credentials needed. Opens the live Review Workspace.
            </p>
          </div>
          <Button
            type="button"
            variant="primary"
            size="lg"
            isLoading={isGuestLoading}
            onClick={handleGuestLogin}
            rightIcon={<Zap className="w-4 h-4 fill-current" />}
            className="w-full sm:w-auto shrink-0 bg-blue-600 hover:bg-blue-500 font-semibold shadow-lg shadow-blue-500/20"
          >
            Try it now (no sign-up)
          </Button>
        </div>

        <div className="bg-[#151D2F] py-7 px-6 sm:px-10 border border-slate-800 rounded-2xl shadow-2xl space-y-5">
          {/* Persona Presets */}
          <div className="p-4 bg-slate-900/60 border border-slate-800 rounded-xl space-y-2.5">
            <div className="flex items-center justify-between">
              <label className="text-xs font-semibold uppercase tracking-wider text-slate-300 font-mono flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5 text-blue-400" />
                One-Click Role Personas
              </label>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
                pw: {DEMO_PASSWORD}
              </span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {DEMO_PRESETS.map((preset) => (
                <button
                  key={preset.role}
                  type="button"
                  disabled={isLoading}
                  onClick={() => handleLoginWithCredentials(preset.email, DEMO_PASSWORD)}
                  className="p-2.5 rounded-lg border border-slate-800 bg-slate-900/90 text-left transition-all hover:border-blue-500/50 hover:bg-blue-500/10 group cursor-pointer disabled:opacity-50"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-slate-200 group-hover:text-blue-300">
                      Login as {preset.label}
                    </span>
                    <ArrowRight className="w-3 h-3 text-slate-500 group-hover:text-blue-400 transition-transform group-hover:translate-x-0.5" />
                  </div>
                  <span className="block text-[10px] text-slate-400 font-mono mt-0.5 truncate">
                    {preset.email}
                  </span>
                </button>
              ))}
            </div>
          </div>

          {/* Mode Switcher */}
          <div className="flex border-b border-slate-800 text-sm">
            <button
              type="button"
              onClick={() => { setMode('signin'); setError(null); }}
              className={`pb-2 px-4 font-medium transition-colors border-b-2 -mb-[2px] flex items-center gap-1.5 ${
                mode === 'signin'
                  ? 'text-blue-400 border-blue-500'
                  : 'text-slate-400 border-transparent hover:text-slate-200'
              }`}
            >
              <LogIn className="w-3.5 h-3.5" />
              Sign In
            </button>
            <button
              type="button"
              onClick={() => { setMode('signup'); setError(null); }}
              className={`pb-2 px-4 font-medium transition-colors border-b-2 -mb-[2px] flex items-center gap-1.5 ${
                mode === 'signup'
                  ? 'text-blue-400 border-blue-500'
                  : 'text-slate-400 border-transparent hover:text-slate-200'
              }`}
            >
              <UserPlus className="w-3.5 h-3.5" />
              Self Sign-Up
            </button>
          </div>

          {error && (
            <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-lg text-rose-400 text-xs flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {mode === 'signup' && (
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Full Name (optional)
                </label>
                <input
                  type="text"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="e.g. Alex Morgan"
                  className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-colors"
                />
              </div>
            )}

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Corporate Email
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
                  <UserCircle2 className="w-4 h-4" />
                </div>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="e.g. reviewer@aurora.local"
                  required
                  className="w-full pl-9 pr-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-colors"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Password
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
                  <KeyRound className="w-4 h-4" />
                </div>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  className="w-full pl-9 pr-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-colors"
                />
              </div>
            </div>

            <Button
              type="submit"
              variant="primary"
              size="lg"
              isLoading={isLoading}
              rightIcon={<ArrowRight className="w-4 h-4" />}
              className="w-full mt-2"
            >
              {mode === 'signup' ? 'Create Reviewer Account' : 'Sign In to BRIDGE Tenant'}
            </Button>
          </form>

          <div className="pt-1 text-center text-xs text-slate-500 font-mono">
            Demo Credentials: <span className="text-slate-300">admin@aurora.local</span> / <span className="text-slate-300">password123</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
