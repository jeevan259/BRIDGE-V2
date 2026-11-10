import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Sparkles,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Plus,
  ArrowRight,
  TrendingUp,
  BrainCircuit,
  MessageSquare,
  FileCheck,
  Check,
  Ban,
} from 'lucide-react';
import apiClient from '@/lib/api';
import {
  ReviewSignal,
  ReviewSignalList,
  AmbiguityAnalysis,
  GuidelineRecommendation,
  GuidelineRecommendationList,
  SignalSourceType,
  SignalSeverity,
  RecommendationStatus,
  KnowledgeItemList,
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

export const GuidelinePage: React.FC = () => {
  const queryClient = useQueryClient();
  const { user } = useAuthStore();
  const canApprove = user?.role === 'administrator' || user?.role === 'brand_manager';

  const [isAddSignalOpen, setIsAddSignalOpen] = useState(false);
  const [signalText, setSignalText] = useState('');
  const [signalType, setSignalType] = useState<SignalSourceType>('reviewer_comment');
  const [signalSeverity, setSignalSeverity] = useState<SignalSeverity>('medium');
  const [selectedItemId, setSelectedItemId] = useState('');

  // 1. Fetch Review Signals
  const {
    data: signalsData,
    isLoading: isLoadingSignals,
    isError: isErrorSignals,
    refetch: refetchSignals,
  } = useQuery<ReviewSignalList>({
    queryKey: ['review-signals'],
    queryFn: async () => {
      const { data } = await apiClient.get<ReviewSignalList>('/guidelines/signals');
      return data;
    },
  });

  // 2. Fetch Ambiguity Analyses
  const {
    data: analyses,
    isLoading: isLoadingAnalyses,
  } = useQuery<AmbiguityAnalysis[]>({
    queryKey: ['ambiguity-analyses'],
    queryFn: async () => {
      const { data } = await apiClient.get<AmbiguityAnalysis[]>('/guidelines/analyses');
      return data;
    },
  });

  // 3. Fetch Recommendations
  const {
    data: recsData,
    isLoading: isLoadingRecs,
    refetch: refetchRecs,
  } = useQuery<GuidelineRecommendationList>({
    queryKey: ['guideline-recommendations'],
    queryFn: async () => {
      const { data } = await apiClient.get<GuidelineRecommendationList>(
        '/guidelines/recommendations'
      );
      return data;
    },
  });

  // 4. Fetch Knowledge Items (for signal dropdown)
  const { data: itemsData } = useQuery<KnowledgeItemList>({
    queryKey: ['knowledge-items'],
    queryFn: async () => {
      const { data } = await apiClient.get<KnowledgeItemList>('/knowledge/items');
      return data;
    },
  });

  // Mutations
  const createSignalMutation = useMutation({
    mutationFn: async () => {
      await apiClient.post('/guidelines/signals', {
        item_id: selectedItemId,
        source_type: signalType,
        signal_text: signalText,
        severity: signalSeverity,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['review-signals'] });
      setIsAddSignalOpen(false);
      setSignalText('');
    },
  });

  const reviewRecMutation = useMutation({
    mutationFn: async ({
      recId,
      status,
      reviewNote,
    }: {
      recId: string;
      status: RecommendationStatus;
      reviewNote?: string;
    }) => {
      await apiClient.post(`/guidelines/recommendations/${recId}/review`, {
        status,
        review_note: reviewNote,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['guideline-recommendations'] });
      queryClient.invalidateQueries({ queryKey: ['knowledge-items'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard-stats'] });
    },
  });

  const signals = signalsData?.items || [];
  const recs = recsData?.items || [];
  const items = itemsData?.items || [];

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2.5">
            <Sparkles className="w-6 h-6 text-purple-400" />
            <span>GuidelineX Intelligence</span>
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Detect semantic guideline ambiguity from review friction signals and synthesize normative updates.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Button
            variant="primary"
            size="sm"
            leftIcon={<Plus className="w-4 h-4" />}
            onClick={() => {
              if (items.length > 0) setSelectedItemId(items[0].id);
              setIsAddSignalOpen(true);
            }}
          >
            Log Review Signal
          </Button>
        </div>
      </div>

      {/* Ambiguity Analyses Highlights */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Analysis Card */}
        <Card className="border-purple-500/20 bg-gradient-to-br from-[#151D2F] via-[#151D2F] to-purple-950/20">
          <CardHeader>
            <div className="flex items-center gap-2.5">
              <div className="p-2 rounded-lg bg-purple-500/15 border border-purple-500/30 text-purple-400">
                <BrainCircuit className="w-5 h-5" />
              </div>
              <div>
                <CardTitle className="text-base">Ambiguity Detection Radar</CardTitle>
                <CardDescription>
                  Synthesized across {signals.length} reviewer overrides & comments
                </CardDescription>
              </div>
            </div>
            <span className="text-xs font-mono px-2 py-0.5 rounded bg-purple-500/10 text-purple-300 border border-purple-500/20">
              91% CONFIDENCE
            </span>
          </CardHeader>
          <CardContent className="space-y-4">
            {(analyses || []).map((analysis) => (
              <div key={analysis.id} className="space-y-3">
                <p className="text-xs text-slate-200 leading-relaxed font-sans bg-slate-900/60 p-3.5 rounded-lg border border-slate-800">
                  {analysis.analysis_summary}
                </p>

                {analysis.ambiguous_aspects_json?.conflicting_contexts && (
                  <div className="space-y-1.5">
                    <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400">
                      Identified Conflicting Contexts:
                    </span>
                    <div className="grid grid-cols-1 gap-1.5">
                      {analysis.ambiguous_aspects_json.conflicting_contexts.map(
                        (ctx: string, i: number) => (
                          <div
                            key={i}
                            className="p-2 bg-slate-950 border border-slate-800/80 rounded text-xs text-slate-300 flex items-center gap-2"
                          >
                            <span className="w-1.5 h-1.5 rounded-full bg-purple-400" />
                            <span>{ctx}</span>
                          </div>
                        )
                      )}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </CardContent>
        </Card>

        {/* Advisory Recommendations */}
        <Card className="border-blue-500/20 bg-gradient-to-br from-[#151D2F] via-[#151D2F] to-blue-950/20">
          <CardHeader>
            <div className="flex items-center gap-2.5">
              <div className="p-2 rounded-lg bg-blue-500/15 border border-blue-500/30 text-blue-400">
                <FileCheck className="w-5 h-5" />
              </div>
              <div>
                <CardTitle className="text-base">Synthesized Guideline Updates</CardTitle>
                <CardDescription>Advisory recommendations ready for administrator sign-off</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {recs.map((rec) => (
              <div
                key={rec.id}
                className="p-4 bg-slate-900/70 border border-slate-800 rounded-xl space-y-3"
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-200">Proposed Normative Language</span>
                  <StatusChip status={rec.status} size="sm" />
                </div>

                <div className="p-3 bg-slate-950 rounded-lg border border-blue-500/30 text-xs font-mono text-blue-200 leading-relaxed">
                  {rec.proposed_content}
                </div>

                {rec.rationale && (
                  <p className="text-xs text-slate-400 italic">Rationale: {rec.rationale}</p>
                )}

                {canApprove && rec.status === 'pending' && (
                  <div className="pt-2 border-t border-slate-800 flex items-center justify-end gap-2">
                    <Button
                      size="sm"
                      variant="secondary"
                      leftIcon={<Ban className="w-3.5 h-3.5 text-rose-400" />}
                      onClick={() =>
                        reviewRecMutation.mutate({
                          recId: rec.id,
                          status: 'rejected',
                          reviewNote: 'Rejected by admin review',
                        })
                      }
                    >
                      Reject
                    </Button>
                    <Button
                      size="sm"
                      variant="primary"
                      leftIcon={<Check className="w-3.5 h-3.5" />}
                      onClick={() =>
                        reviewRecMutation.mutate({
                          recId: rec.id,
                          status: 'approved',
                          reviewNote: 'Approved. Adopted as official normative guideline standard.',
                        })
                      }
                    >
                      Approve & Adopt Standard
                    </Button>
                  </div>
                )}
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      {/* Review Signals Table */}
      <Card>
        <CardHeader>
          <div>
            <CardTitle className="text-base flex items-center gap-2">
              <MessageSquare className="w-4 h-4 text-slate-400" />
              <span>Review Friction Signals</span>
            </CardTitle>
            <CardDescription>
              Aggregated from reviewer overrides, editorial feedback, and validation exceptions.
            </CardDescription>
          </div>
        </CardHeader>
        <CardContent>
          {isLoadingSignals ? (
            <Spinner size="md" className="py-12" label="Loading review signals..." />
          ) : signals.length === 0 ? (
            <EmptyState
              title="No Review Signals Logged"
              description="Review signals will appear here when content reviewers override findings or submit guideline feedback."
            />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Severity</TableHead>
                  <TableHead>Source Type</TableHead>
                  <TableHead>Signal Observation / Friction Note</TableHead>
                  <TableHead>Logged At</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {signals.map((sig) => (
                  <TableRow key={sig.id}>
                    <TableCell>
                      <StatusChip status={sig.severity} size="sm" />
                    </TableCell>
                    <TableCell>
                      <span className="text-xs font-mono uppercase bg-slate-800 text-slate-300 px-2 py-0.5 rounded border border-slate-700">
                        {sig.source_type.replace('_', ' ')}
                      </span>
                    </TableCell>
                    <TableCell className="text-xs text-slate-200 max-w-md">
                      {sig.signal_text}
                    </TableCell>
                    <TableCell className="text-xs text-slate-400 font-mono">
                      {new Date(sig.created_at).toLocaleDateString()}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* MODAL: Log Review Signal */}
      <Modal
        isOpen={isAddSignalOpen}
        onClose={() => setIsAddSignalOpen(false)}
        title="Log Review Friction Signal"
        description="Records editorial ambiguity or friction observations for GuidelineX clustering."
        footer={
          <>
            <Button variant="ghost" onClick={() => setIsAddSignalOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="primary"
              isLoading={createSignalMutation.isPending}
              onClick={() => createSignalMutation.mutate()}
              disabled={!signalText.trim() || !selectedItemId}
            >
              Submit Signal
            </Button>
          </>
        }
      >
        <div className="space-y-4 text-sm">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">Target Rule / Guideline</label>
            <select
              value={selectedItemId}
              onChange={(e) => setSelectedItemId(e.target.value)}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-blue-500 text-xs"
            >
              {items.map((i) => (
                <option key={i.id} value={i.id}>
                  {i.title} ({i.item_type})
                </option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">Signal Source</label>
              <select
                value={signalType}
                onChange={(e) => setSignalType(e.target.value as SignalSourceType)}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-blue-500 text-xs"
              >
                <option value="reviewer_comment">Reviewer Comment</option>
                <option value="override">Override Trend</option>
                <option value="external_feedback">External Audit Feedback</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">Severity / Friction</label>
              <select
                value={signalSeverity}
                onChange={(e) => setSignalSeverity(e.target.value as SignalSeverity)}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-blue-500 text-xs"
              >
                <option value="low">Low Friction</option>
                <option value="medium">Medium Friction</option>
                <option value="high">High Friction</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">Observation Details</label>
            <textarea
              rows={3}
              value={signalText}
              onChange={(e) => setSignalText(e.target.value)}
              placeholder="Describe where users are getting stuck or why the rule wording causes confusion..."
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-blue-500 text-xs leading-relaxed"
            />
          </div>
        </div>
      </Modal>
    </div>
  );
};

