import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  CheckSquare,
  Play,
  FileText,
  AlertTriangle,
  ShieldCheck,
  Quote,
  FileCheck2,
  Copy,
  Check,
  Clock,
  Sparkles,
  ExternalLink,
  Ban,
  RotateCcw,
} from 'lucide-react';
import apiClient from '@/lib/api';
import {
  ValidationJob,
  ValidationJobList,
  Finding,
  FindingList,
  Citation,
  EvidenceReceipt,
  OverrideReasonCode,
} from '@/types';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { StatusChip } from '@/components/ui/StatusChip';
import { Modal } from '@/components/ui/Modal';
import { Table, TableHeader, TableBody, TableHead, TableRow, TableCell } from '@/components/ui/Table';
import { Spinner } from '@/components/ui/Spinner';
import { EmptyState } from '@/components/ui/EmptyState';
import { ErrorState } from '@/components/ui/ErrorState';
import { useAuthStore } from '@/lib/auth';

const PRESETS = [
  {
    title: 'Ad Banner (Logo & Tone Breaches)',
    text: 'Apex Enterprise introduces our revolutionary new AI suite that guarantees complete synergistic disruption! The hero banner places the Apex logo prominently on a vibrant red gradient (#FF0000).',
  },
  {
    title: 'Compliant Press Release (Verified Claim & Facts)',
    text: 'Apex Enterprise Cloud Platform delivers 99.995% uptime availability across all tier-1 regions. Telemetry confirms our automated governance reduces review cycles by 70% in 60 days.',
  },
  {
    title: 'Summit Deck Excerpt (Contextual Ambiguity)',
    text: 'In extreme enterprise deployment scenarios, Apex guarantees high resiliency with sub-45ms p99 latency. Custom exception routing is provided for partner integrations.',
  },
];

export const ValidationPage: React.FC = () => {
  const queryClient = useQueryClient();
  const { user } = useAuthStore();
  const canOverride =
    user?.role === 'administrator' || user?.role === 'brand_manager' || user?.role === 'reviewer';

  const [contentTitle, setContentTitle] = useState('');
  const [contentText, setContentText] = useState('');
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);

  // Citation Drawer
  const [activeFindingForCitation, setActiveFindingForCitation] = useState<Finding | null>(null);

  // Evidence Receipt Modal
  const [activeFindingForReceipt, setActiveFindingForReceipt] = useState<Finding | null>(null);
  const [copiedReceipt, setCopiedReceipt] = useState(false);

  // Override Modal
  const [activeFindingForOverride, setActiveFindingForOverride] = useState<Finding | null>(null);
  const [overrideCode, setOverrideCode] = useState<OverrideReasonCode>('context_exception');
  const [overrideText, setOverrideText] = useState('');

  // 1. Fetch Validation Jobs
  const {
    data: jobsData,
    isLoading: isLoadingJobs,
    isError: isErrorJobs,
    refetch: refetchJobs,
  } = useQuery<ValidationJobList>({
    queryKey: ['validation-jobs'],
    queryFn: async () => {
      const { data } = await apiClient.get<ValidationJobList>('/validation/jobs');
      return data;
    },
    refetchInterval: 4000, // poll status for running background jobs
  });

  const jobs = jobsData?.items || [];
  const currentJobId = selectedJobId || (jobs.length > 0 ? jobs[0].id : null);
  const currentJob = jobs.find((j) => j.id === currentJobId);

  // 2. Fetch Findings for the selected job
  const {
    data: findingsData,
    isLoading: isLoadingFindings,
    isError: isErrorFindings,
    refetch: refetchFindings,
  } = useQuery<FindingList>({
    queryKey: ['job-findings', currentJobId],
    queryFn: async () => {
      if (!currentJobId) return { items: [], total: 0, page: 1, page_size: 20 };
      const { data } = await apiClient.get<FindingList>(
        `/validation/jobs/${currentJobId}/findings`
      );
      return data;
    },
    enabled: !!currentJobId,
  });

  const findings = findingsData?.items || [];

  // 3. Fetch Citations for active finding
  const { data: citations, isLoading: isLoadingCitations } = useQuery<Citation[]>({
    queryKey: ['finding-citations', activeFindingForCitation?.id],
    queryFn: async () => {
      if (!activeFindingForCitation) return [];
      const { data } = await apiClient.get<Citation[]>(
        `/validation/findings/${activeFindingForCitation.id}/citations`
      );
      return data;
    },
    enabled: !!activeFindingForCitation,
  });

  // 4. Fetch Evidence Receipts for active finding
  const { data: receipts, isLoading: isLoadingReceipts } = useQuery<EvidenceReceipt[]>({
    queryKey: ['finding-evidence', activeFindingForReceipt?.id],
    queryFn: async () => {
      if (!activeFindingForReceipt) return [];
      const { data } = await apiClient.get<EvidenceReceipt[]>(
        `/validation/findings/${activeFindingForReceipt.id}/evidence`
      );
      return data;
    },
    enabled: !!activeFindingForReceipt,
  });

  // Mutations
  const submitJobMutation = useMutation({
    mutationFn: async () => {
      const { data } = await apiClient.post<ValidationJob>('/validation/jobs', {
        content_title: contentTitle || 'Untitled Draft Submission',
        content_text: contentText,
      });
      return data;
    },
    onSuccess: (newJob) => {
      queryClient.invalidateQueries({ queryKey: ['validation-jobs'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard-stats'] });
      setSelectedJobId(newJob.id);
      setContentTitle('');
      setContentText('');
    },
  });

  const overrideMutation = useMutation({
    mutationFn: async () => {
      if (!activeFindingForOverride) return;
      await apiClient.post(`/validation/findings/${activeFindingForOverride.id}/override`, {
        override_reason_code: overrideCode,
        override_reason_text: overrideText,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['job-findings', currentJobId] });
      queryClient.invalidateQueries({ queryKey: ['dashboard-stats'] });
      setActiveFindingForOverride(null);
      setOverrideText('');
    },
  });

  const handleCopyReceipt = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedReceipt(true);
    setTimeout(() => setCopiedReceipt(false), 2000);
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2.5">
            <CheckSquare className="w-6 h-6 text-blue-400" />
            <span>Validation Engine</span>
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Dual-stage deterministic rule matching and adversarial AI evidence verification.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs font-mono text-slate-400 bg-slate-900 px-3 py-1.5 rounded-lg border border-slate-800">
            PROVIDER: GEMINI-1.5-PRO / MOCK
          </span>
        </div>
      </div>

      {/* Grid: Submission Form (Left) & Recent Jobs / Inspection (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Submission Panel (5 cols) */}
        <div className="lg:col-span-5 space-y-4">
          <Card>
            <CardHeader>
              <div>
                <CardTitle className="text-base">Submit Asset for Validation</CardTitle>
                <CardDescription>
                  Evaluates against active brand rules, facts, and guidelines.
                </CardDescription>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Presets */}
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2 font-mono">
                  Test Scenarios (Quick Fill)
                </label>
                <div className="space-y-1.5">
                  {PRESETS.map((p, i) => (
                    <button
                      key={i}
                      type="button"
                      onClick={() => {
                        setContentTitle(p.title);
                        setContentText(p.text);
                      }}
                      className="w-full text-left text-xs p-2 rounded-lg bg-slate-900/60 border border-slate-800 hover:border-slate-700 hover:bg-slate-800/50 text-slate-300 transition-colors"
                    >
                      <span className="font-semibold block text-blue-400">{p.title}</span>
                      <span className="text-slate-500 line-clamp-1 mt-0.5">{p.text}</span>
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Content Title / Identifier
                </label>
                <input
                  type="text"
                  value={contentTitle}
                  onChange={(e) => setContentTitle(e.target.value)}
                  placeholder="e.g. Q1 Campaign Landing Page Hero"
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Content Copy / Asset Description
                </label>
                <textarea
                  rows={6}
                  value={contentText}
                  onChange={(e) => setContentText(e.target.value)}
                  placeholder="Paste marketing copy, visual asset description, or press statement..."
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-blue-500 leading-relaxed"
                />
              </div>

              <Button
                variant="primary"
                size="md"
                className="w-full"
                isLoading={submitJobMutation.isPending}
                disabled={!contentText.trim()}
                leftIcon={<Play className="w-4 h-4 fill-current" />}
                onClick={() => submitJobMutation.mutate()}
              >
                Execute Validation Checks
              </Button>
            </CardContent>
          </Card>

          {/* Validation History Sidebar */}
          <Card>
            <CardHeader className="py-3">
              <span className="text-xs font-semibold uppercase text-slate-400 tracking-wider">
                Recent Validation Jobs
              </span>
            </CardHeader>
            <div className="max-h-60 overflow-y-auto divide-y divide-slate-800/60">
              {isLoadingJobs ? (
                <div className="py-6 text-center">
                  <Spinner size="sm" />
                </div>
              ) : jobs.length === 0 ? (
                <p className="text-xs text-slate-500 p-4 text-center">No validation jobs run yet.</p>
              ) : (
                jobs.map((job) => {
                  const isSelected = job.id === currentJobId;
                  return (
                    <div
                      key={job.id}
                      onClick={() => setSelectedJobId(job.id)}
                      className={`p-3 cursor-pointer text-xs transition-colors flex items-center justify-between ${
                        isSelected
                          ? 'bg-blue-600/15 border-l-2 border-blue-500'
                          : 'hover:bg-slate-800/40'
                      }`}
                    >
                      <div className="min-w-0 pr-2">
                        <span className="font-semibold text-slate-200 truncate block">
                          {job.content_title || 'Untitled Job'}
                        </span>
                        <span className="text-[10px] text-slate-500 font-mono">
                          {new Date(job.created_at).toLocaleTimeString()}
                        </span>
                      </div>
                      <StatusChip status={job.status} size="sm" />
                    </div>
                  );
                })
              )}
            </div>
          </Card>
        </div>

        {/* Findings & Evidence Panel (7 cols) */}
        <div className="lg:col-span-7 space-y-4">
          <Card className="min-h-[500px]">
            <CardHeader>
              <div>
                <CardTitle className="text-base flex items-center gap-2">
                  <span>Findings & Evidence Receipts</span>
                  {currentJob && <StatusChip status={currentJob.status} size="sm" />}
                </CardTitle>
                <CardDescription>
                  {currentJob
                    ? `Job: ${currentJob.content_title || currentJob.id.slice(0, 8)}`
                    : 'Select a validation job to inspect findings'}
                </CardDescription>
              </div>
            </CardHeader>
            <CardContent>
              {isLoadingFindings ? (
                <div className="py-24 text-center">
                  <Spinner size="lg" label="Analyzing compliance findings..." />
                </div>
              ) : !currentJob ? (
                <EmptyState
                  title="No Job Selected"
                  description="Submit content on the left or select an existing validation job to inspect evidence."
                />
              ) : findings.length === 0 ? (
                <div className="text-center py-16 space-y-3">
                  <div className="w-12 h-12 rounded-full bg-emerald-500/15 border border-emerald-500/30 text-emerald-400 flex items-center justify-center mx-auto">
                    <ShieldCheck className="w-6 h-6" />
                  </div>
                  <h4 className="text-base font-semibold text-slate-200">
                    Full Compliance Confirmed
                  </h4>
                  <p className="text-xs text-slate-400 max-w-sm mx-auto">
                    No brand violations, tone discrepancies, or unsupported factual claims detected.
                  </p>
                </div>
              ) : (
                <div className="space-y-4">
                  {findings.map((f) => (
                    <div
                      key={f.id}
                      className="p-4 bg-slate-900/60 border border-slate-800 rounded-xl space-y-3 hover:border-slate-700 transition-colors"
                    >
                      {/* Top badge row */}
                      <div className="flex items-center justify-between gap-2 flex-wrap">
                        <div className="flex items-center gap-2">
                          <StatusChip status={f.severity} size="sm" />
                          <span className="text-xs font-mono text-slate-400 uppercase">
                            {f.finding_type.replace('_', ' ')}
                          </span>
                        </div>
                        <div className="flex items-center gap-2">
                          <StatusChip status={f.status} size="sm" />
                          {f.is_evidence_backed && (
                            <span className="text-[10px] font-mono bg-blue-500/10 text-blue-400 border border-blue-500/20 px-1.5 py-0.5 rounded">
                              EVIDENCE BACKED
                            </span>
                          )}
                        </div>
                      </div>

                      {/* Description */}
                      <p className="text-xs text-slate-200 leading-relaxed font-medium">
                        {f.description}
                      </p>

                      {/* Overridden callout */}
                      {f.status === 'overridden' && (
                        <div className="p-2.5 bg-indigo-500/10 border border-indigo-500/30 rounded-lg text-xs text-indigo-300 space-y-0.5">
                          <span className="font-semibold block">
                            Overridden: {f.override_reason_code?.replace('_', ' ')}
                          </span>
                          <span className="text-slate-400 block text-[11px]">
                            {f.override_reason_text || 'No note provided.'}
                          </span>
                        </div>
                      )}

                      {/* Action buttons */}
                      <div className="pt-2 border-t border-slate-800 flex items-center justify-between text-xs">
                        <div className="flex items-center gap-2">
                          <Button
                            size="sm"
                            variant="secondary"
                            leftIcon={<Quote className="w-3.5 h-3.5" />}
                            onClick={() => setActiveFindingForCitation(f)}
                          >
                            Citations
                          </Button>
                          <Button
                            size="sm"
                            variant="secondary"
                            leftIcon={<FileCheck2 className="w-3.5 h-3.5" />}
                            onClick={() => setActiveFindingForReceipt(f)}
                          >
                            Evidence Receipt
                          </Button>
                        </div>

                        {canOverride && f.status !== 'overridden' && (
                          <Button
                            size="sm"
                            variant="outline"
                            leftIcon={<RotateCcw className="w-3.5 h-3.5" />}
                            onClick={() => setActiveFindingForOverride(f)}
                          >
                            Override
                          </Button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* DRAWER / MODAL: Exact Citation Viewer */}
      <Modal
        isOpen={!!activeFindingForCitation}
        onClose={() => setActiveFindingForCitation(null)}
        title="Authoritative Citation Grounding"
        description="Exact source quote and indexed document passages supporting this finding."
        maxWidth="2xl"
      >
        <div className="space-y-4">
          {isLoadingCitations ? (
            <Spinner size="md" label="Resolving citations..." />
          ) : (citations || []).length === 0 ? (
            <p className="text-xs text-slate-400 py-6 text-center">
              No direct passage citations found for this heuristic finding.
            </p>
          ) : (
            (citations || []).map((c) => (
              <div
                key={c.id}
                className="p-4 bg-slate-900 border border-slate-800 rounded-xl space-y-3"
              >
                <div>
                  <span className="text-[10px] uppercase font-mono tracking-wider text-blue-400 block mb-1">
                    Exact Matched Quotation
                  </span>
                  <div className="p-3 bg-blue-950/40 border-l-2 border-blue-500 text-xs font-mono text-blue-200">
                    "{c.exact_quote}"
                  </div>
                </div>

                <div>
                  <span className="text-[10px] uppercase font-mono tracking-wider text-slate-400 block mb-1">
                    Surrounding Context in Source Passage
                  </span>
                  <p className="text-xs text-slate-300 leading-relaxed bg-slate-950 p-3 rounded-lg border border-slate-800/80">
                    {c.passage_text_at_citation}
                  </p>
                </div>
              </div>
            ))
          )}
        </div>
      </Modal>

      {/* MODAL: Verifiable Evidence Receipt */}
      <Modal
        isOpen={!!activeFindingForReceipt}
        onClose={() => setActiveFindingForReceipt(null)}
        title="Cryptographic Evidence Receipt"
        description="Deterministic proof receipt generated during verification pipeline."
        maxWidth="2xl"
        footer={
          <Button
            size="sm"
            variant="outline"
            leftIcon={copiedReceipt ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
            onClick={() => {
              const receipt = receipts?.[0];
              if (receipt) handleCopyReceipt(JSON.stringify(receipt.receipt_json, null, 2));
            }}
          >
            {copiedReceipt ? 'Copied to Clipboard' : 'Copy JSON'}
          </Button>
        }
      >
        <div className="space-y-3">
          {isLoadingReceipts ? (
            <Spinner size="md" label="Loading evidence receipt..." />
          ) : (receipts || []).length === 0 ? (
            <p className="text-xs text-slate-400 py-6 text-center">
              No evidence receipt generated for this finding.
            </p>
          ) : (
            <div className="relative">
              <pre className="p-4 bg-slate-950 border border-slate-800 rounded-xl font-mono text-xs text-emerald-400 overflow-x-auto max-h-96 leading-relaxed">
                {JSON.stringify(receipts![0].receipt_json, null, 2)}
              </pre>
            </div>
          )}
        </div>
      </Modal>

      {/* MODAL: Override Finding */}
      <Modal
        isOpen={!!activeFindingForOverride}
        onClose={() => setActiveFindingForOverride(null)}
        title="Override Finding with Reason Code"
        description="Overrides are recorded into the tamper-evident audit chain and fed to GuidelineX."
        footer={
          <>
            <Button variant="ghost" onClick={() => setActiveFindingForOverride(null)}>
              Cancel
            </Button>
            <Button
              variant="primary"
              isLoading={overrideMutation.isPending}
              onClick={() => overrideMutation.mutate()}
            >
              Confirm Override
            </Button>
          </>
        }
      >
        <div className="space-y-4 text-sm">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Standardized Reason Code
            </label>
            <select
              value={overrideCode}
              onChange={(e) => setOverrideCode(e.target.value as OverrideReasonCode)}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-blue-500"
            >
              <option value="context_exception">Context Exception (Partner/NDA/Executive)</option>
              <option value="rule_unclear">Rule Ambiguity (Rule requires refinement)</option>
              <option value="finding_incorrect">False Positive (Finding is incorrect)</option>
              <option value="source_not_relevant">Source Not Relevant (Mismatched target)</option>
              <option value="content_corrected">Content Corrected</option>
              <option value="other">Other Justified Exception</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Justification & Reviewer Note
            </label>
            <textarea
              rows={3}
              value={overrideText}
              onChange={(e) => setOverrideText(e.target.value)}
              placeholder="State the regulatory or business justification for this override..."
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-blue-500 text-xs"
            />
          </div>
        </div>
      </Modal>
    </div>
  );
};

