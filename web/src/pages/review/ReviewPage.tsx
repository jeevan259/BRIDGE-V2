import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  FileCheck2,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  ShieldAlert,
  Sparkles,
  Upload,
  Play,
  RotateCcw,
  Check,
  Ban,
  Quote,
  Shield,
  Clock,
  HelpCircle,
  FileText,
  Flame,
} from 'lucide-react';
import apiClient from '@/lib/api';
import { Finding, FindingList, OverrideReasonCode } from '@/types';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { StatusChip } from '@/components/ui/StatusChip';
import { Modal } from '@/components/ui/Modal';
import { Spinner } from '@/components/ui/Spinner';
import { useAuthStore } from '@/lib/auth';

const SAMPLES = {
  compliant: {
    title: 'Autumn Trail Campaign Copy (Compliant)',
    text: `Built for the high passes and mist-covered ridgelines. The Aurora Alpinist Shell pairs GRS-certified 100% recycled nylon with quiet weatherproofing. Forest Deep and Alpine Snow tones form the foundation of this trail-tested silhouette. 

Mountaineering and backcountry travel carry inherent risk. Review manufacturer specs before use. Tag @AuroraOutdoors #RoamResilient #LeaveNoTrace.`,
  },
  violating: {
    title: 'Flash Sale Promo Banner (Violating)',
    text: `HUGE FLASH SALE! Aurora Outdoors is executing a revolutionary disruptive transformation with the world's best gear! Featuring our iconic mountain logo over a vibrant neon red gradient background (#FF0000). 

Our products are completely eco-friendly and conquer nature effortlessly! Single-use plastic zip-ties secure all hangtags. Guaranteed 100% risk-free summit expeditions.`,
  },
};

export const ReviewPage: React.FC = () => {
  const queryClient = useQueryClient();
  const { user } = useAuthStore();

  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [isChecking, setIsChecking] = useState(false);
  const [serverWaking, setServerWaking] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  // Finding interaction states
  const [activeOverrideFinding, setActiveOverrideFinding] = useState<Finding | null>(null);
  const [overrideReason, setOverrideReason] = useState<OverrideReasonCode>('context_exception');
  const [overrideText, setOverrideText] = useState('');
  const [acceptedFindingIds, setAcceptedFindingIds] = useState<string[]>([]);
  const [disputedFindingIds, setDisputedFindingIds] = useState<string[]>([]);

  // Final job decision
  const [finalDecision, setFinalDecision] = useState<{
    decision: string;
    decided_by: string;
    decided_at: string;
  } | null>(null);

  // Query findings for the active validation job
  const {
    data: findingsData,
    isLoading: isLoadingFindings,
    refetch: refetchFindings,
  } = useQuery<FindingList>({
    queryKey: ['review-findings', activeJobId],
    queryFn: async () => {
      if (!activeJobId) return { items: [], total: 0, page: 1, page_size: 50 };
      const { data } = await apiClient.get<FindingList>(`/validation/jobs/${activeJobId}/findings`);
      return data;
    },
    enabled: !!activeJobId,
    refetchInterval: (query) => {
      const items = query.state.data?.items;
      return items && items.length > 0 ? false : 2000;
    },
  });

  // Query quarantined hallucinations
  const { data: defenseData } = useQuery<FindingList>({
    queryKey: ['review-defense', activeJobId],
    queryFn: async () => {
      if (!activeJobId) return { items: [], total: 0, page: 1, page_size: 50 };
      const { data } = await apiClient.get<FindingList>(
        `/validation/jobs/${activeJobId}/hallucination-defense`
      );
      return data;
    },
    enabled: !!activeJobId,
  });

  // Check against guidelines mutation
  const handleCheck = async () => {
    if (!content.trim()) return;
    setIsChecking(true);
    setSubmitError(null);
    setServerWaking(false);
    setFinalDecision(null);

    let retries = 0;
    const maxRetries = 2;

    const executeSubmit = async (): Promise<any> => {
      try {
        const { data: job } = await apiClient.post('/validation/jobs', {
          content_title: title.trim() || 'Ad-Hoc Review Submission',
          content_text: content.trim(),
        });
        return job;
      } catch (err: any) {
        if (retries < maxRetries) {
          retries++;
          setServerWaking(true);
          await new Promise((r) => setTimeout(r, 3000));
          return executeSubmit();
        }
        throw err;
      }
    };

    try {
      const job = await executeSubmit();
      setActiveJobId(job.id);
      // Wait a moment for async worker to complete analysis
      setTimeout(() => {
        refetchFindings();
        setIsChecking(false);
        setServerWaking(false);
      }, 2500);
    } catch (err: any) {
      setIsChecking(false);
      setServerWaking(false);
      const detail =
        err?.response?.data?.error?.message ||
        err?.response?.data?.detail ||
        err?.message ||
        'Server timed out or is asleep. Please retry.';
      setSubmitError(String(detail));
    }
  };

  // Override mutation
  const overrideMutation = useMutation({
    mutationFn: async () => {
      if (!activeOverrideFinding) return;
      await apiClient.post(`/validation/findings/${activeOverrideFinding.id}/override`, {
        override_reason_code: overrideReason,
        override_reason_text: overrideText,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['review-findings', activeJobId] });
      setActiveOverrideFinding(null);
      setOverrideText('');
    },
  });

  // Final human decision mutation
  const handleFinalDecision = async (decision: 'approved' | 'changes_requested') => {
    if (!activeJobId) return;
    try {
      const { data } = await apiClient.post(`/validation/jobs/${activeJobId}/decide`, {
        decision,
        notes: decision === 'approved' ? 'Compliance sign-off granted' : 'Revision requested by reviewer',
      });
      setFinalDecision({
        decision: data.decision,
        decided_by: data.decided_by,
        decided_at: new Date(data.decided_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      });
    } catch (err) {
      console.error('Failed to submit decision:', err);
    }
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setTitle(file.name.replace(/\.[^/.]+$/, ''));
    const reader = new FileReader();
    reader.onload = (event) => {
      const text = event.target?.result;
      if (typeof text === 'string') {
        setContent(text);
      }
    };
    reader.readAsText(file);
  };

  const findings = findingsData?.items || [];
  const quarantined = defenseData?.items || [];
  const criticalOrHighCount = findings.filter(
    (f) => f.severity === 'high' && f.status !== 'overridden'
  ).length;
  const mediumCount = findings.filter(
    (f) => f.severity === 'medium' && f.status !== 'overridden'
  ).length;

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2.5">
            <FileCheck2 className="w-6 h-6 text-blue-400" />
            <span>Review Workspace</span>
          </h1>
          <p className="text-sm text-slate-400 mt-0.5">
            Real-time brand compliance scanner, deterministic rules engine, and evidence auditor.
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs font-mono">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <span className="text-slate-300">Live Tenant: Aurora Outdoors</span>
        </div>
      </div>

      {/* Input Section Card */}
      <Card>
        <CardHeader>
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <CardTitle className="text-base flex items-center gap-2">
                <span>Content Intake & Inspection</span>
              </CardTitle>
              <CardDescription>
                Paste text copy, upload a document, or load a preset sample to inspect.
              </CardDescription>
            </div>
            {/* Quick Load Buttons */}
            <div className="flex items-center gap-2 shrink-0">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => {
                  setTitle(SAMPLES.compliant.title);
                  setContent(SAMPLES.compliant.text);
                  setSubmitError(null);
                }}
                className="text-xs border-emerald-500/30 text-emerald-300 hover:bg-emerald-500/10"
              >
                <Check className="w-3.5 h-3.5 mr-1 text-emerald-400" />
                Load Compliant Sample
              </Button>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => {
                  setTitle(SAMPLES.violating.title);
                  setContent(SAMPLES.violating.text);
                  setSubmitError(null);
                }}
                className="text-xs border-rose-500/30 text-rose-300 hover:bg-rose-500/10"
              >
                <Flame className="w-3.5 h-3.5 mr-1 text-rose-400" />
                Load Violating Sample
              </Button>
            </div>
          </div>
        </CardHeader>

        <CardContent className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Asset / Campaign Title
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Q4 Alpine Shell Launch Copy"
              className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-blue-500"
            />
          </div>

          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="block text-xs font-medium text-slate-300">
                Content Copy to Verify
              </label>
              <label className="text-xs text-blue-400 hover:text-blue-300 cursor-pointer flex items-center gap-1 font-mono">
                <Upload className="w-3.5 h-3.5" />
                <span>Upload .txt / .docx / .pdf</span>
                <input
                  type="file"
                  accept=".txt,.docx,.pdf"
                  onChange={handleFileUpload}
                  className="hidden"
                />
              </label>
            </div>
            <textarea
              rows={5}
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="Paste draft copy, advertisement text, email newsletter, or script here..."
              className="w-full p-3 bg-slate-900 border border-slate-700 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-blue-500 font-sans leading-relaxed"
            />
          </div>

          {serverWaking && (
            <div className="p-3 bg-amber-500/10 border border-amber-500/30 rounded-lg text-amber-300 text-xs flex items-center gap-2">
              <Spinner size="sm" />
              <span>Waking up the server... Please hold for initial cold-start spin-up.</span>
            </div>
          )}

          {submitError && (
            <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-lg text-rose-400 text-xs flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 shrink-0" />
              <span>{submitError}</span>
            </div>
          )}

          <div className="flex items-center justify-between pt-1">
            <span className="text-xs text-slate-400 font-mono">
              Deterministic Rules Engine + Live Model Grounding
            </span>
            <Button
              type="button"
              variant="primary"
              size="lg"
              isLoading={isChecking}
              disabled={!content.trim()}
              onClick={handleCheck}
              rightIcon={<Play className="w-4 h-4 fill-current" />}
              className="bg-blue-600 hover:bg-blue-500 font-semibold px-6 shadow-lg shadow-blue-500/20"
            >
              Check against guidelines
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Results Section */}
      {activeJobId && (
        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-300">
          {/* Verdict Line */}
          <div
            className={`p-4 rounded-xl border flex flex-col sm:flex-row sm:items-center justify-between gap-3 ${
              criticalOrHighCount > 0 || mediumCount > 0
                ? 'bg-amber-950/30 border-amber-500/40 text-amber-200'
                : 'bg-emerald-950/30 border-emerald-500/40 text-emerald-200'
            }`}
          >
            <div className="flex items-center gap-3">
              {criticalOrHighCount > 0 || mediumCount > 0 ? (
                <ShieldAlert className="w-6 h-6 text-amber-400 shrink-0" />
              ) : (
                <CheckCircle2 className="w-6 h-6 text-emerald-400 shrink-0" />
              )}
              <div>
                <h3 className="font-semibold text-sm">
                  {criticalOrHighCount > 0 || mediumCount > 0
                    ? `VERDICT: ${criticalOrHighCount} High-Severity Violations, ${mediumCount} Tone Breaches — Needs Human Decision`
                    : 'VERDICT: All Automated Checks Passed — 100% Brand Compliant'}
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Verified against Aurora Outdoors Brand Identity Standards (v3).
                </p>
              </div>
            </div>

            {/* Final Human Decision Buttons */}
            <div className="flex items-center gap-2 shrink-0">
              {finalDecision ? (
                <div className="px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-xs font-mono text-slate-300 flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  <span>
                    Decided: <strong className="uppercase text-white">{finalDecision.decision}</strong> by{' '}
                    {finalDecision.decided_by} at {finalDecision.decided_at}
                  </span>
                </div>
              ) : (
                <>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => handleFinalDecision('changes_requested')}
                    className="border-rose-500/40 text-rose-300 hover:bg-rose-500/20 text-xs"
                  >
                    <XCircle className="w-3.5 h-3.5 mr-1" />
                    Request changes
                  </Button>
                  <Button
                    type="button"
                    variant="primary"
                    size="sm"
                    onClick={() => handleFinalDecision('approved')}
                    className="bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-xs"
                  >
                    <Check className="w-3.5 h-3.5 mr-1" />
                    Approve content
                  </Button>
                </>
              )}
            </div>
          </div>

          {/* Severity-Sorted Finding Cards */}
          <div className="space-y-4">
            <h2 className="text-base font-semibold text-white flex items-center justify-between">
              <span>Verified Rule Findings ({findings.length})</span>
              <span className="text-xs font-mono text-slate-400">Sorted by Severity</span>
            </h2>

            {isLoadingFindings ? (
              <div className="p-8 text-center bg-slate-900/50 rounded-xl border border-slate-800">
                <Spinner size="md" label="Analyzing content against approved knowledge..." />
              </div>
            ) : findings.length === 0 ? (
              <div className="p-8 text-center bg-slate-900/30 rounded-xl border border-slate-800 text-slate-400">
                No violations detected. All brand rules satisfied.
              </div>
            ) : (
              findings.map((f) => {
                const isOverridden = f.status === 'overridden';
                const isAccepted = acceptedFindingIds.includes(f.id);
                const isDisputed = disputedFindingIds.includes(f.id);

                return (
                  <Card key={f.id} className="border-slate-800 bg-[#121927]">
                    <CardContent className="p-5 space-y-3">
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex items-center gap-2">
                          <StatusChip status={f.severity} size="sm" />
                          <span className="text-xs uppercase font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                            {f.finding_type.replace('_', ' ')}
                          </span>
                          {isOverridden && (
                            <span className="text-xs font-mono px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">
                              OVERRIDDEN ({f.override_reason_code})
                            </span>
                          )}
                          {isAccepted && (
                            <span className="text-xs font-mono px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                              ACCEPTED
                            </span>
                          )}
                          {isDisputed && (
                            <span className="text-xs font-mono px-2 py-0.5 rounded bg-rose-500/20 text-rose-300 border border-rose-500/30">
                              DISPUTED
                            </span>
                          )}
                        </div>

                        {/* Action Buttons */}
                        <div className="flex items-center gap-1.5 shrink-0">
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            disabled={isAccepted}
                            onClick={() =>
                              setAcceptedFindingIds((prev) => [...prev, f.id])
                            }
                            className="text-xs text-slate-300 hover:text-emerald-400 h-7 px-2"
                          >
                            <Check className="w-3.5 h-3.5 mr-1" />
                            Accept
                          </Button>
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            onClick={() => setActiveOverrideFinding(f)}
                            className="text-xs text-slate-300 hover:text-amber-400 h-7 px-2"
                          >
                            <RotateCcw className="w-3.5 h-3.5 mr-1" />
                            Override
                          </Button>
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            disabled={isDisputed}
                            onClick={() =>
                              setDisputedFindingIds((prev) => [...prev, f.id])
                            }
                            className="text-xs text-slate-300 hover:text-rose-400 h-7 px-2"
                          >
                            <Ban className="w-3.5 h-3.5 mr-1" />
                            Dispute
                          </Button>
                        </div>
                      </div>

                      {/* Explanation */}
                      <p className="text-sm text-slate-200 font-medium leading-relaxed">
                        {f.description}
                      </p>

                      {/* Suggested Fix */}
                      <div className="p-3 bg-blue-950/20 border border-blue-500/20 rounded-lg text-xs text-blue-200">
                        <strong className="text-blue-300 font-semibold uppercase tracking-wider text-[10px] block mb-1">
                          Recommended Remediation:
                        </strong>
                        {f.finding_type === 'brand_violation'
                          ? 'Swap prohibited color (#FF0000) or layout intrusion with primary Forest Deep (#1A3A2A) or Alpine Snow (#F5F9F6).'
                          : f.finding_type === 'tone_issue'
                          ? 'Replace hyperbolic sales buzzwords with precise, measured technical specs.'
                          : 'Ensure accredited standard references (e.g. GRS, ISO 811) accompany environmental or performance claims.'}
                      </div>
                    </CardContent>
                  </Card>
                );
              })
            )}
          </div>

          {/* Hallucination Defense Panel */}
          <div className="p-5 bg-gradient-to-r from-purple-950/30 via-slate-900 to-indigo-950/30 border border-purple-500/30 rounded-xl space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Shield className="w-5 h-5 text-purple-400" />
                <h3 className="text-sm font-semibold text-white">
                  Hallucination Defense & Quarantine Trap
                </h3>
              </div>
              <span className="text-xs font-mono px-2 py-0.5 rounded bg-purple-500/20 text-purple-300 border border-purple-500/30">
                {quarantined.length} Quarantined Claims
              </span>
            </div>

            <p className="text-xs text-slate-400 leading-relaxed">
              Server-side citation resolver intercepts any AI claim citing unapproved or fabricated
              guidelines. Trapped hallucinations are quarantined here and stripped from the normal findings view.
            </p>

            {quarantined.length === 0 ? (
              <div className="p-3 bg-slate-900/60 border border-slate-800 rounded-lg text-xs text-slate-400 text-center">
                No ungrounded or hallucinated citations detected in this submission.
              </div>
            ) : (
              quarantined.map((q) => (
                <div
                  key={q.id}
                  className="p-3 bg-slate-900/80 border border-purple-500/40 rounded-lg space-y-1.5"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] font-mono text-purple-300 font-semibold uppercase">
                      [QUARANTINED BY CITATION RESOLVER]
                    </span>
                    <span className="text-[10px] font-mono text-slate-500">Zero Evidence Backing</span>
                  </div>
                  <p className="text-xs text-slate-200">{q.description}</p>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* Override Reason Modal */}
      <Modal
        isOpen={!!activeOverrideFinding}
        onClose={() => setActiveOverrideFinding(null)}
        title="Document Compliance Exception Override"
      >
        <div className="space-y-4">
          <p className="text-xs text-slate-400">
            Rule 7 Compliance Invariant: Overrides require an auditable reason code and justification.
            This action appends a cryptographically signed event to the immutable audit chain.
          </p>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Reason Code
            </label>
            <select
              value={overrideReason}
              onChange={(e) => setOverrideReason(e.target.value as OverrideReasonCode)}
              className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-blue-500"
            >
              <option value="context_exception">Context Exception (Approved Campaign Exemption)</option>
              <option value="rule_unclear">Rule Unclear (Flags Ambiguity in GuidelineX)</option>
              <option value="finding_incorrect">Finding Incorrect (False Positive Rule Trigger)</option>
              <option value="source_not_relevant">Source Not Relevant to Channel</option>
              <option value="other">Other Editorial Justification</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Justification & Editorial Notes
            </label>
            <textarea
              rows={3}
              value={overrideText}
              onChange={(e) => setOverrideText(e.target.value)}
              placeholder="Provide reason for granting compliance override..."
              className="w-full p-2.5 bg-slate-900 border border-slate-700 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-blue-500"
            />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setActiveOverrideFinding(null)}
            >
              Cancel
            </Button>
            <Button
              type="button"
              variant="primary"
              size="sm"
              isLoading={overrideMutation.isPending}
              onClick={() => overrideMutation.mutate()}
              className="bg-amber-600 hover:bg-amber-500 text-white"
            >
              Confirm Audited Override
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
};

export default ReviewPage;
