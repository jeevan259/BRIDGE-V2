import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Inbox,
  CheckCircle2,
  AlertTriangle,
  RotateCcw,
  Quote,
  FileCheck2,
  Check,
  Ban,
  Filter,
} from 'lucide-react';
import apiClient from '@/lib/api';
import { Finding, FindingList, OverrideReasonCode } from '@/types';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { StatusChip } from '@/components/ui/StatusChip';
import { Modal } from '@/components/ui/Modal';
import { Table, TableHeader, TableBody, TableHead, TableRow, TableCell } from '@/components/ui/Table';
import { Spinner } from '@/components/ui/Spinner';
import { EmptyState } from '@/components/ui/EmptyState';
import { ErrorState } from '@/components/ui/ErrorState';
import { useAuthStore } from '@/lib/auth';

export const ReviewPage: React.FC = () => {
  const queryClient = useQueryClient();
  const { user } = useAuthStore();
  const canReview = user?.role === 'administrator' || user?.role === 'brand_manager' || user?.role === 'reviewer';

  const [activeOverrideFinding, setActiveOverrideFinding] = useState<Finding | null>(null);
  const [overrideReason, setOverrideReason] = useState<OverrideReasonCode>('context_exception');
  const [overrideText, setOverrideText] = useState('');

  // Fetch all recent validation jobs and findings
  const {
    data: jobsData,
    isLoading: isLoadingJobs,
  } = useQuery({
    queryKey: ['validation-jobs'],
    queryFn: async () => {
      const { data } = await apiClient.get('/validation/jobs');
      return data;
    },
  });

  const firstJobId = jobsData?.items?.[0]?.id;

  const {
    data: findingsData,
    isLoading: isLoadingFindings,
    isError,
    refetch,
  } = useQuery<FindingList>({
    queryKey: ['review-findings', firstJobId],
    queryFn: async () => {
      if (!firstJobId) return { items: [], total: 0, page: 1, page_size: 20 };
      const { data } = await apiClient.get<FindingList>(`/validation/jobs/${firstJobId}/findings`);
      return data;
    },
    enabled: !!firstJobId,
  });

  const overrideMutation = useMutation({
    mutationFn: async () => {
      if (!activeOverrideFinding) return;
      await apiClient.post(`/validation/findings/${activeOverrideFinding.id}/override`, {
        override_reason_code: overrideReason,
        override_reason_text: overrideText,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['review-findings'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard-stats'] });
      setActiveOverrideFinding(null);
      setOverrideText('');
    },
  });

  const findings = findingsData?.items || [];
  const pendingFindings = findings.filter((f) => f.status === 'pending');

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      <div>
        <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2.5">
          <Inbox className="w-6 h-6 text-blue-400" />
          <span>Brand Review Queue</span>
        </h1>
        <p className="text-sm text-slate-400 mt-1">
          Reviewer queue for flagged content items, tone issues, and exception override requests.
        </p>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between w-full">
            <div>
              <CardTitle className="text-base flex items-center gap-2">
                <span>Active Review Queue</span>
                <span className="text-xs font-mono bg-amber-500/10 text-amber-400 border border-amber-500/20 px-2 py-0.5 rounded-full">
                  {pendingFindings.length} Pending
                </span>
              </CardTitle>
              <CardDescription>
                Items requiring editorial decision or documented compliance override.
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {isLoadingFindings || isLoadingJobs ? (
            <Spinner size="lg" className="py-20" label="Loading review queue..." />
          ) : isError ? (
            <ErrorState onRetry={() => refetch()} />
          ) : findings.length === 0 ? (
            <EmptyState
              title="Review Queue Clear"
              description="No findings requiring review action at this time."
            />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Severity</TableHead>
                  <TableHead>Issue / Rule Breached</TableHead>
                  <TableHead>Evidence Status</TableHead>
                  <TableHead>Current State</TableHead>
                  <TableHead className="text-right">Decision</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {findings.map((f) => (
                  <TableRow key={f.id}>
                    <TableCell>
                      <StatusChip status={f.severity} size="sm" />
                    </TableCell>
                    <TableCell>
                      <span className="font-semibold text-slate-200 block text-xs max-w-md">
                        {f.description}
                      </span>
                      <span className="text-[10px] text-slate-500 font-mono">
                        TYPE: {f.finding_type.toUpperCase()}
                      </span>
                    </TableCell>
                    <TableCell>
                      <StatusChip
                        status={f.is_evidence_backed ? 'supported' : 'possible'}
                        label={f.is_evidence_backed ? 'Backed' : 'Heuristic'}
                        size="sm"
                      />
                    </TableCell>
                    <TableCell>
                      <StatusChip status={f.status} size="sm" />
                    </TableCell>
                    <TableCell className="text-right">
                      {canReview && f.status !== 'overridden' ? (
                        <Button
                          size="sm"
                          variant="outline"
                          leftIcon={<RotateCcw className="w-3.5 h-3.5" />}
                          onClick={() => setActiveOverrideFinding(f)}
                        >
                          Override
                        </Button>
                      ) : (
                        <span className="text-xs font-mono text-slate-500">Decided</span>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Override Modal */}
      <Modal
        isOpen={!!activeOverrideFinding}
        onClose={() => setActiveOverrideFinding(null)}
        title="Review Decision: Override Finding"
        description="Provide a formal reason code and regulatory justification."
        footer={
          <>
            <Button variant="ghost" onClick={() => setActiveOverrideFinding(null)}>
              Cancel
            </Button>
            <Button
              variant="primary"
              isLoading={overrideMutation.isPending}
              onClick={() => overrideMutation.mutate()}
            >
              Sign-Off Override
            </Button>
          </>
        }
      >
        <div className="space-y-4 text-xs">
          <div>
            <label className="block font-medium text-slate-300 mb-1">Reason Code</label>
            <select
              value={overrideReason}
              onChange={(e) => setOverrideReason(e.target.value as OverrideReasonCode)}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-blue-500"
            >
              <option value="context_exception">Context Exception (Partner/NDA)</option>
              <option value="rule_unclear">Rule Ambiguity</option>
              <option value="finding_incorrect">False Positive</option>
              <option value="source_not_relevant">Source Not Relevant</option>
              <option value="content_corrected">Content Corrected</option>
            </select>
          </div>
          <div>
            <label className="block font-medium text-slate-300 mb-1">Justification Note</label>
            <textarea
              rows={3}
              value={overrideText}
              onChange={(e) => setOverrideText(e.target.value)}
              placeholder="State the regulatory or business justification..."
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-blue-500"
            />
          </div>
        </div>
      </Modal>
    </div>
  );
};

