import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Layers, ShieldCheck, ArrowRight, UserCircle2, KeyRound } from 'lucide-react';
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
    email: 'admin@bridge.local',
    description: 'Full system governance, impact simulation & chain verification',
  },
  {
    role: 'brand_manager',
    label: 'Brand Manager',
    email: 'brand_manager@bridge.local',
    description: 'Knowledge source management, rule approvals & GuidelineX',
  },
  {
    role: 'reviewer',
    label: 'Reviewer',
    email: 'reviewer@bridge.local',
    description: 'Content review queues, evidence override & signals logging',
  },
  {
    role: 'creator',
    label: 'Creator',
    email: 'creator@bridge.local',
    description: 'Asset submission & pre-flight deterministic validation',
  },
  {
    role: 'auditor',
    label: 'Auditor',
    email: 'auditor@bridge.local',
    description: 'Read-only compliance telemetry & cryptographic chain audit',
  },
];

const createDemoUser = (userEmail: string): User => {
  const preset =
    DEMO_PRESETS.find((p) => p.email.toLowerCase() === userEmail.toLowerCase()) ||
    DEMO_PRESETS[0];
  return {
    id: '00000000-0000-0000-0000-000000000001',
    org_id: '11111111-1111-1111-1111-111111111111',
    email: userEmail || preset.email,
    full_name: preset.label,
    role: preset.role,
    is_active: true,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };
};

export const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const { login } = useAuthStore();
  const [email, setEmail] = useState('admin@bridge.local');
  const [password, setPassword] = useState('password123');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const performLogin = (token: string, user: User) => {
    login(token, user);
    navigate('/dashboard');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);

    try {
      const { data: tokenData } = await apiClient.post<{ access_token: string }>(
        '/auth/login',
        { email, password }
      );

      // Store token so immediate subsequent requests have it
      localStorage.setItem('bridge_access_token', tokenData.access_token);

      // Fetch user profile
      const { data: userData } = await apiClient.get<User>('/auth/me');

      performLogin(tokenData.access_token, userData);
    } catch (err: any) {
      console.warn('Backend API unseeded or unavailable, auto-activating demo profile:', err);
      // Auto-fallback for demo / manual mode
      const fallbackUser = createDemoUser(email);
      const fallbackToken = 'bridge_demo_token_' + btoa(JSON.stringify(fallbackUser));
      performLogin(fallbackToken, fallbackUser);
    } finally {
      setIsLoading(false);
    }
  };

  const handleManualLogin = () => {
    const fallbackUser = createDemoUser(email);
    const fallbackToken = 'bridge_demo_token_' + btoa(JSON.stringify(fallbackUser));
    performLogin(fallbackToken, fallbackUser);
  };

  const handleSelectPreset = (preset: DemoUserPreset) => {
    setEmail(preset.email);
    setPassword('password123');
    setError(null);
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

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-xl relative z-10 px-4">
        <div className="bg-[#151D2F] py-8 px-6 sm:px-10 border border-slate-800 rounded-2xl shadow-2xl space-y-6">
          {/* Quick Demo Role Picker */}
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2 font-mono">
              Demo Quick-Select Profile
            </label>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {DEMO_PRESETS.map((preset) => {
                const isSelected = email === preset.email;
                return (
                  <button
                    key={preset.role}
                    type="button"
                    onClick={() => handleSelectPreset(preset)}
                    className={`p-2.5 rounded-lg border text-left transition-all ${
                      isSelected
                        ? 'border-blue-500 bg-blue-500/10 text-blue-300 ring-1 ring-blue-500'
                        : 'border-slate-800 bg-slate-900/60 text-slate-400 hover:border-slate-700 hover:text-slate-200'
                    }`}
                  >
                    <span className="block text-xs font-semibold">{preset.label}</span>
                    <span className="block text-[10px] text-slate-500 truncate mt-0.5">
                      {preset.email.split('@')[0]}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          <div className="relative flex py-1 items-center">
            <div className="flex-grow border-t border-slate-800" />
            <span className="flex-shrink mx-4 text-xs uppercase font-mono text-slate-500">
              Sign In
            </span>
            <div className="flex-grow border-t border-slate-800" />
          </div>

          {error && (
            <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-lg text-rose-400 text-xs flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
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
              Sign In to BRIDGE Tenant
            </Button>

            <Button
              type="button"
              variant="outline"
              size="md"
              onClick={handleManualLogin}
              className="w-full mt-2 border-slate-700 hover:bg-slate-800 text-slate-300"
            >
              Instant Manual Demo Sign-In
            </Button>
          </form>

          <div className="pt-2 text-center text-xs text-slate-500 font-mono">
            Tamper-evident verification • Deterministic + AI Pipeline • ISO/IEC 27001
          </div>
        </div>
      </div>
    </div>
  );
};

