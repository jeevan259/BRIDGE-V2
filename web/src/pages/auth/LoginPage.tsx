import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Layers, ShieldCheck, ArrowRight, UserCircle2, KeyRound, Sparkles } from 'lucide-react';
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
  const [email, setEmail] = useState('admin@aurora.local');
  const [password, setPassword] = useState('password123');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isDemoMode, setIsDemoMode] = useState<boolean>(() => {
    return Boolean(
      import.meta.env.VITE_DEMO_MODE === 'true' ||
      import.meta.env.VITE_DEMO_MODE === true
    );
  });

  // Query health endpoint for demo_mode flag if not set via VITE
  useEffect(() => {
    let isMounted = true;
    apiClient
      .get<{ demo_mode?: boolean }>('/health', { baseURL: '' })
      .then(({ data }) => {
        if (isMounted && data?.demo_mode !== undefined) {
          setIsDemoMode(Boolean(data.demo_mode));
        }
      })
      .catch(() => {
        // Fallback: check ready endpoint
        apiClient
          .get<{ demo_mode?: boolean }>('/ready', { baseURL: '' })
          .then(({ data }) => {
            if (isMounted && data?.demo_mode !== undefined) {
              setIsDemoMode(Boolean(data.demo_mode));
            }
          })
          .catch(() => {
            // Keep default
          });
      });
    return () => {
      isMounted = false;
    };
  }, []);

  const performLogin = (token: string, user: User) => {
    login(token, user);
    navigate('/dashboard');
  };

  const handleLoginWithCredentials = async (targetEmail: string, targetPassword = 'password123') => {
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
      console.warn('Backend API login failed, checking fallback:', err);
      if (isDemoMode) {
        // Auto-fallback in demo mode only
        const fallbackUser = createDemoUser(targetEmail);
        const fallbackToken = 'bridge_demo_token_' + btoa(JSON.stringify(fallbackUser));
        performLogin(fallbackToken, fallbackUser);
      } else {
        const msg =
          err?.response?.data?.detail ||
          err?.message ||
          'Failed to authenticate with BRIDGE API. Verify credentials or run seed script.';
        setError(String(msg));
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    handleLoginWithCredentials(email, password);
  };

  const handleOneClickDemoLogin = (preset: DemoUserPreset) => {
    setEmail(preset.email);
    setPassword('password123');
    handleLoginWithCredentials(preset.email, 'password123');
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
          {/* Quick Demo Role Picker — visible only in DEMO_MODE */}
          {isDemoMode && (
            <div className="p-4 bg-blue-500/5 border border-blue-500/20 rounded-xl space-y-3">
              <div className="flex items-center justify-between">
                <label className="text-xs font-semibold uppercase tracking-wider text-blue-300 font-mono flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-blue-400" />
                  One-Click Demo Personas
                </label>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-blue-500/20 text-blue-300 border border-blue-500/30">
                  DEMO_MODE=true
                </span>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {DEMO_PRESETS.map((preset) => (
                  <button
                    key={preset.role}
                    type="button"
                    disabled={isLoading}
                    onClick={() => handleOneClickDemoLogin(preset)}
                    className="p-2.5 rounded-lg border border-slate-800 bg-slate-900/80 text-left transition-all hover:border-blue-500/50 hover:bg-blue-500/10 group cursor-pointer disabled:opacity-50"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-slate-200 group-hover:text-blue-300">
                        Login as {preset.label}
                      </span>
                      <ArrowRight className="w-3 h-3 text-slate-500 group-hover:text-blue-400 transition-transform group-hover:translate-x-0.5" />
                    </div>
                    <span className="block text-[10px] text-slate-400 font-mono mt-0.5">
                      {preset.email}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {isDemoMode && (
            <div className="relative flex py-1 items-center">
              <div className="flex-grow border-t border-slate-800" />
              <span className="flex-shrink mx-4 text-xs uppercase font-mono text-slate-500">
                Or Sign In Manually
              </span>
              <div className="flex-grow border-t border-slate-800" />
            </div>
          )}

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
          </form>

          <div className="pt-2 text-center text-xs text-slate-500 font-mono">
            Tamper-evident verification • Deterministic + AI Pipeline • ISO/IEC 27001
          </div>
        </div>
      </div>
    </div>
  );
};
