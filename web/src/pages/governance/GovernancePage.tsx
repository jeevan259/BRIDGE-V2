import React, { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import {
  ShieldCheck,
  ShieldAlert,
  RotateCw,
  Hash,
  User,
  Clock,
  Layers,
  Filter,
  Eye,
  CheckCircle2,
  AlertCircle,
  Copy,
  Check,
} from 'lucide-react';
import apiClient from '@/lib/api';
import {
  AuditEvent,
  AuditEventList,
  AuditVerifyResponse,
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

export const GovernancePage: React.FC = () => {
  const { user } = useAuthStore();
  const [page, setPage] = useState(1);
  const [eventTypeFilter, setEventTypeFilter] = useState('');
  const [selectedEvent, setSelectedEvent] = useState<AuditEvent | null>(null);
  const [copiedHash, setCopiedHash] = useState(false);

  // 1. Fetch Audit Events
  const {
    data: auditData,
    isLoading: isLoadingEvents,
    isError: isErrorEvents,
    refetch: refetchEvents,
  } = useQuery<AuditEventList>({
    queryKey: ['audit-events', page, eventTypeFilter],
    queryFn: async () => {
      const url = eventTypeFilter
        ? `/audit/events?page=${page}&page_size=30&event_type=${eventTypeFilter}`
        : `/audit/events?page=${page}&page_size=30`;
      const { data } = await apiClient.get<AuditEventList>(url);
      return data;
    },
  });

  // 2. Fetch Hash Chain Verification
  const {
    data: verifyResult,
    isLoading: isVerifying,
    refetch: triggerVerify,
  } = useQuery<AuditVerifyResponse>({
    queryKey: ['audit-verify'],
    queryFn: async () => {
      const { data } = await apiClient.get<AuditVerifyResponse>('/audit/verify');
      return data;
    },
    refetchOnWindowFocus: false,
  });

  const tamperMutation = useMutation({
    mutationFn: async () => {
      await apiClient.post('/demo/tamper');
    },
    onSuccess: () => {
      triggerVerify();
      refetchEvents();
    },
  });

  const untamperMutation = useMutation({
    mutationFn: async () => {
      await apiClient.post('/demo/untamper');
    },
    onSuccess: () => {
      triggerVerify();
      refetchEvents();
    },
  });

  const events = auditData?.items || [];
  const isValid = verifyResult?.valid ?? verifyResult?.is_valid ?? true;
  const brokenSeq = verifyResult?.first_broken_seq;
  const checkedCount = verifyResult?.checked_count ?? verifyResult?.total_events ?? auditData?.total ?? 0;

  const handleCopyHash = (hash: string) => {
    navigator.clipboard.writeText(hash);
    setCopiedHash(true);
    setTimeout(() => setCopiedHash(false), 2000);
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2.5">
            <ShieldCheck className="w-6 h-6 text-emerald-400" />
            <span>Governance & Tamper-Evident Audit Chain</span>
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Immutable, SHA-256 hash-chained telemetry logging every brand rule, review override, and validation event.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {user?.role === 'administrator' && (
            <>
              <Button
                variant="danger"
                size="sm"
                leftIcon={<ShieldAlert className="w-4 h-4" />}
                isLoading={tamperMutation.isPending}
                onClick={() => tamperMutation.mutate()}
              >
                Simulate attacker
              </Button>
              <Button
                variant="outline"
                size="sm"
                leftIcon={<CheckCircle2 className="w-4 h-4 text-emerald-400" />}
                isLoading={untamperMutation.isPending}
                onClick={() => untamperMutation.mutate()}
              >
                Restore chain
              </Button>
            </>
          )}
          <Button
            variant="outline"
            size="sm"
            leftIcon={<RotateCw className={`w-4 h-4 ${isVerifying ? 'animate-spin' : ''}`} />}
            isLoading={isVerifying}
            onClick={() => triggerVerify()}
          >
            Verify Chain
          </Button>
        </div>
      </div>

      {/* Verification Health Status Card */}
      <div
        className={`p-6 rounded-2xl border transition-all ${
          isValid
            ? 'bg-emerald-950/20 border-emerald-500/30'
            : 'bg-rose-950/20 border-rose-500/30'
        }`}
      >
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div
              className={`w-12 h-12 rounded-xl flex items-center justify-center shrink-0 ${
                isValid
                  ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                  : 'bg-rose-500/15 text-rose-400 border border-rose-500/30'
              }`}
            >
              {isValid ? <CheckCircle2 className="w-7 h-7" /> : <ShieldAlert className="w-7 h-7" />}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className={`text-lg font-bold ${isValid ? 'text-emerald-400' : 'text-rose-400'}`}>
                  {isValid ? 'Chain intact' : `Tampering detected at #${brokenSeq ?? '?'}`}
                </h3>
                <StatusChip
                  status={isValid ? 'confirmed' : 'high'}
                  label={isValid ? 'IMMUTABLE' : 'INTEGRITY BREACH'}
                  size="sm"
                />
              </div>
              <p className="text-xs text-slate-300 mt-1">
                {isValid
                  ? (verifyResult?.message || `All ${checkedCount} sequential events pass cryptographic SHA-256 ancestor digest matching.`)
                  : `Cryptographic SHA-256 link mismatch detected at block #${brokenSeq}. Ledger tampering prevented.`}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-6 text-xs font-mono">
            <div className="p-3 bg-slate-900/80 border border-slate-800 rounded-lg">
              <span className="text-slate-500 block">TOTAL LOGGED EVENTS</span>
              <span className="text-lg font-bold text-slate-200">
                {checkedCount}
              </span>
            </div>
            <div className="p-3 bg-slate-900/80 border border-slate-800 rounded-lg">
              <span className="text-slate-500 block">ALGORITHM</span>
              <span className="text-lg font-bold text-blue-400">SHA-256</span>
            </div>
          </div>
        </div>
      </div>

      {/* Audit Log Table */}
      <Card>
        <CardHeader>
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 w-full">
            <div>
              <CardTitle className="text-base flex items-center gap-2">
                <Hash className="w-4 h-4 text-slate-400" />
                <span>Immutable Telemetry Ledger</span>
              </CardTitle>
              <CardDescription>
                Chronologically ordered governance events linked by sequential cryptographic hashes.
              </CardDescription>
            </div>

            <div className="flex items-center gap-2">
              <Filter className="w-3.5 h-3.5 text-slate-400" />
              <select
                value={eventTypeFilter}
                onChange={(e) => setEventTypeFilter(e.target.value)}
                className="bg-slate-900 border border-slate-700 text-xs text-slate-200 rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-blue-500"
              >
                <option value="">All Event Types</option>
                <option value="ORGANISATION_INITIALIZED">ORGANISATION_INITIALIZED</option>
                <option value="KNOWLEDGE_ITEM_APPROVED">KNOWLEDGE_ITEM_APPROVED</option>
                <option value="FINDING_OVERRIDDEN">FINDING_OVERRIDDEN</option>
                <option value="CONTINUITY_IMPACT_CALCULATED">CONTINUITY_IMPACT_CALCULATED</option>
                <option value="GUIDELINE_RECOMMENDATION_GENERATED">GUIDELINE_RECOMMENDATION_GENERATED</option>
              </select>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {isLoadingEvents ? (
            <Spinner size="lg" className="py-20" label="Verifying ledger records..." />
          ) : events.length === 0 ? (
            <EmptyState
              title="No Audit Records"
              description="No audit events matched the current filter."
            />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Event Type</TableHead>
                  <TableHead>Actor</TableHead>
                  <TableHead>Resource</TableHead>
                  <TableHead>Event Hash (SHA-256)</TableHead>
                  <TableHead>Timestamp</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {events.map((ev) => (
                  <TableRow key={ev.id}>
                    <TableCell>
                      <span className="text-xs font-mono font-semibold text-blue-400">
                        {ev.event_type}
                      </span>
                    </TableCell>
                    <TableCell className="text-xs text-slate-300">
                      <div className="flex items-center gap-1.5">
                        <User className="w-3.5 h-3.5 text-slate-500" />
                        <span>{ev.actor_email}</span>
                      </div>
                    </TableCell>
                    <TableCell className="text-xs font-mono text-slate-400">
                      {ev.resource_type ? `${ev.resource_type}:${ev.resource_id?.slice(0, 8)}` : '—'}
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1.5 font-mono text-xs text-slate-400">
                        <span className="truncate max-w-[120px]">{ev.event_hash}</span>
                      </div>
                    </TableCell>
                    <TableCell className="text-xs text-slate-400 font-mono">
                      {new Date(ev.created_at).toLocaleString()}
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        size="sm"
                        variant="secondary"
                        leftIcon={<Eye className="w-3.5 h-3.5" />}
                        onClick={() => setSelectedEvent(ev)}
                      >
                        Details
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* MODAL: Audit Event Detail & Hash Chain Proof */}
      <Modal
        isOpen={!!selectedEvent}
        onClose={() => setSelectedEvent(null)}
        title="Audit Event Cryptographic Proof"
        description={`Event ID: ${selectedEvent?.id}`}
        maxWidth="2xl"
        footer={
          <Button
            size="sm"
            variant="outline"
            leftIcon={copiedHash ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
            onClick={() => {
              if (selectedEvent) handleCopyHash(selectedEvent.event_hash);
            }}
          >
            {copiedHash ? 'Copied Hash' : 'Copy Hash'}
          </Button>
        }
      >
        {selectedEvent && (
          <div className="space-y-4 text-xs">
            <div className="grid grid-cols-2 gap-3 p-3 bg-slate-900 border border-slate-800 rounded-lg">
              <div>
                <span className="text-slate-500 block mb-0.5">Event Type</span>
                <span className="font-mono font-bold text-blue-400">{selectedEvent.event_type}</span>
              </div>
              <div>
                <span className="text-slate-500 block mb-0.5">Actor Identity</span>
                <span className="text-slate-200">{selectedEvent.actor_email}</span>
              </div>
            </div>

            <div className="space-y-2">
              <div>
                <span className="text-[10px] uppercase font-mono text-slate-500 block">
                  Ancestor Previous Hash (prev_hash)
                </span>
                <div className="p-2.5 bg-slate-950 font-mono text-[11px] text-slate-400 rounded border border-slate-800 truncate">
                  {selectedEvent.prev_hash || '0000000000000000000000000000000000000000000000000000000000000000 (GENESIS)'}
                </div>
              </div>

              <div>
                <span className="text-[10px] uppercase font-mono text-emerald-400 block">
                  Current Block Hash (event_hash)
                </span>
                <div className="p-2.5 bg-slate-950 font-mono text-[11px] text-emerald-400 rounded border border-emerald-500/30 truncate">
                  {selectedEvent.event_hash}
                </div>
              </div>
            </div>

            <div>
              <span className="text-[10px] uppercase font-mono text-slate-500 block mb-1">
                Deterministic Payload Diff (diff_json)
              </span>
              <pre className="p-3 bg-slate-950 border border-slate-800 rounded font-mono text-slate-300 overflow-x-auto max-h-48 leading-relaxed">
                {JSON.stringify(selectedEvent.diff_json || {}, null, 2)}
              </pre>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
};

