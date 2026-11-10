import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Users,
  Building,
  Shield,
  Plus,
  KeyRound,
  CheckCircle2,
  UserCheck,
  Building2,
  RotateCcw,
  AlertTriangle,
} from 'lucide-react';
import apiClient from '@/lib/api';
import { User, UserList, UserRole } from '@/types';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { StatusChip } from '@/components/ui/StatusChip';
import { Modal } from '@/components/ui/Modal';
import { Table, TableHeader, TableBody, TableHead, TableRow, TableCell } from '@/components/ui/Table';
import { Spinner } from '@/components/ui/Spinner';
import { ErrorState } from '@/components/ui/ErrorState';
import { useAuthStore } from '@/lib/auth';

export const AdminPage: React.FC = () => {
  const queryClient = useQueryClient();
  const { user } = useAuthStore();
  const [isAddUserOpen, setIsAddUserOpen] = useState(false);
  const [newUserEmail, setNewUserEmail] = useState('');
  const [newUserName, setNewUserName] = useState('');
  const [newUserPassword, setNewUserPassword] = useState('password123');
  const [newUserRole, setNewUserRole] = useState<UserRole>('creator');
  const [isResetConfirmOpen, setIsResetConfirmOpen] = useState(false);

  // Check health probe for demo_mode flag
  const { data: healthData } = useQuery<{ demo_mode?: boolean }>({
    queryKey: ['system-health'],
    queryFn: async () => {
      try {
        const { data } = await apiClient.get('/health', { baseURL: '' });
        return data;
      } catch {
        // Fallback to checking ready endpoint
        try {
          const { data } = await apiClient.get('/ready', { baseURL: '' });
          return data;
        } catch {
          return { demo_mode: false };
        }
      }
    },
    staleTime: 60000,
  });

  const isDemoMode = Boolean(
    import.meta.env.VITE_DEMO_MODE === 'true' ||
    import.meta.env.VITE_DEMO_MODE === true ||
    healthData?.demo_mode
  );

  // Fetch users
  const {
    data: usersData,
    isLoading: isLoadingUsers,
    isError: isErrorUsers,
    refetch: refetchUsers,
  } = useQuery<UserList>({
    queryKey: ['admin-users'],
    queryFn: async () => {
      const { data } = await apiClient.get<UserList>('/users');
      return data;
    },
  });

  const createUserMutation = useMutation({
    mutationFn: async () => {
      await apiClient.post('/users', {
        email: newUserEmail,
        full_name: newUserName,
        password: newUserPassword,
        role: newUserRole,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-users'] });
      setIsAddUserOpen(false);
      setNewUserEmail('');
      setNewUserName('');
    },
  });

  const resetDemoMutation = useMutation({
    mutationFn: async () => {
      await apiClient.post('/demo/seed?reset=true');
    },
    onSuccess: () => {
      queryClient.invalidateQueries();
      setIsResetConfirmOpen(false);
    },
  });

  const users = usersData?.items || [];

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2.5">
            <Users className="w-6 h-6 text-blue-400" />
            <span>Administration & Access Control</span>
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Manage organization personas, role-based authorization, and tenant parameters.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {isDemoMode && user?.role === 'administrator' && (
            <Button
              variant="outline"
              size="sm"
              leftIcon={<RotateCcw className="w-4 h-4 text-amber-400" />}
              onClick={() => setIsResetConfirmOpen(true)}
              className="border-amber-500/30 text-amber-400 hover:bg-amber-500/10"
            >
              Reset Demo
            </Button>
          )}
          <Button
            variant="primary"
            size="sm"
            leftIcon={<Plus className="w-4 h-4" />}
            onClick={() => setIsAddUserOpen(true)}
          >
            Provision User
          </Button>
        </div>
      </div>

      {/* Tenant Metadata Card */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2.5">
            <Building2 className="w-5 h-5 text-blue-400" />
            <div>
              <CardTitle className="text-base">Tenant Identity</CardTitle>
              <CardDescription>Apex Global Technologies (Active Enterprise Tenant)</CardDescription>
            </div>
          </div>
          <span className="text-xs font-mono px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            ENTERPRISE TIER
          </span>
        </CardHeader>
      </Card>

      {/* Users Table */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Organization Members & Roles</CardTitle>
          <CardDescription>Configured team members and their RBAC permissions.</CardDescription>
        </CardHeader>
        <CardContent>
          {isLoadingUsers ? (
            <Spinner size="lg" className="py-20" label="Loading users..." />
          ) : isErrorUsers ? (
            <ErrorState onRetry={() => refetchUsers()} />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Member</TableHead>
                  <TableHead>Role</TableHead>
                  <TableHead>Email</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Joined</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {users.map((u) => (
                  <TableRow key={u.id}>
                    <TableCell>
                      <div className="flex items-center gap-2.5">
                        <div className="w-8 h-8 rounded-full bg-blue-500/15 border border-blue-500/30 flex items-center justify-center text-xs font-bold text-blue-300">
                          {u.full_name ? u.full_name[0] : 'U'}
                        </div>
                        <span className="font-semibold text-slate-200 text-xs">
                          {u.full_name || '—'}
                        </span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <StatusChip
                        status={
                          u.role === 'administrator'
                            ? 'confirmed'
                            : u.role === 'brand_manager'
                            ? 'approved'
                            : u.role === 'reviewer'
                            ? 'low'
                            : 'possible'
                        }
                        label={u.role.replace('_', ' ').toUpperCase()}
                        size="sm"
                      />
                    </TableCell>
                    <TableCell className="text-xs font-mono text-slate-400">
                      {u.email}
                    </TableCell>
                    <TableCell>
                      <span className="text-xs text-emerald-400 font-mono flex items-center gap-1">
                        <CheckCircle2 className="w-3.5 h-3.5" /> Active
                      </span>
                    </TableCell>
                    <TableCell className="text-xs text-slate-400 font-mono">
                      {new Date(u.created_at).toLocaleDateString()}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Provision User Modal */}
      <Modal
        isOpen={isAddUserOpen}
        onClose={() => setIsAddUserOpen(false)}
        title="Provision New Organization User"
        description="Creates an authorized identity inside Apex Global Technologies."
        footer={
          <>
            <Button variant="ghost" onClick={() => setIsAddUserOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="primary"
              isLoading={createUserMutation.isPending}
              onClick={() => createUserMutation.mutate()}
              disabled={!newUserEmail.trim()}
            >
              Provision Identity
            </Button>
          </>
        }
      >
        <div className="space-y-4 text-xs">
          <div>
            <label className="block font-medium text-slate-300 mb-1">Full Name</label>
            <input
              type="text"
              value={newUserName}
              onChange={(e) => setNewUserName(e.target.value)}
              placeholder="e.g. Rachel Adams"
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-blue-500"
            />
          </div>
          <div>
            <label className="block font-medium text-slate-300 mb-1">Corporate Email</label>
            <input
              type="email"
              value={newUserEmail}
              onChange={(e) => setNewUserEmail(e.target.value)}
              placeholder="e.g. rachel@bridge.local"
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-blue-500"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block font-medium text-slate-300 mb-1">Assigned Role</label>
              <select
                value={newUserRole}
                onChange={(e) => setNewUserRole(e.target.value as UserRole)}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-blue-500"
              >
                <option value="creator">Creator</option>
                <option value="reviewer">Reviewer</option>
                <option value="brand_manager">Brand Manager</option>
                <option value="administrator">Administrator</option>
                <option value="auditor">Auditor</option>
              </select>
            </div>
            <div>
              <label className="block font-medium text-slate-300 mb-1">Default Password</label>
              <input
                type="password"
                value={newUserPassword}
                onChange={(e) => setNewUserPassword(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-blue-500"
              />
            </div>
          </div>
        </div>
      </Modal>

      {/* Reset Demo Confirmation Modal */}
      <Modal
        isOpen={isResetConfirmOpen}
        onClose={() => setIsResetConfirmOpen(false)}
        title="Reset Demo Tenant"
        description="This action will purge and re-initialize the Aurora Outdoors demo tenant data."
        footer={
          <>
            <Button variant="ghost" onClick={() => setIsResetConfirmOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="danger"
              isLoading={resetDemoMutation.isPending}
              onClick={() => resetDemoMutation.mutate()}
            >
              Reset All Demo Data
            </Button>
          </>
        }
      >
        <div className="flex items-start gap-3 p-3 bg-amber-500/10 border border-amber-500/20 rounded-lg text-xs text-amber-300">
          <AlertTriangle className="w-5 h-5 shrink-0 text-amber-400 mt-0.5" />
          <div className="space-y-1">
            <p className="font-semibold text-amber-200">Warning: Destructive Reset</p>
            <p className="text-slate-400">
              This will remove all created assets, findings, reviewer overrides, and re-create the pristine Aurora Outdoors brand demo dataset. This action cannot be undone.
            </p>
          </div>
        </div>
      </Modal>
    </div>
  );
};

