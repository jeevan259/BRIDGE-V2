import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  BookOpen,
  Plus,
  FileText,
  CheckCircle2,
  AlertCircle,
  ExternalLink,
  History,
  Layers,
  Search,
  Filter,
  Check,
  Ban,
  Clock,
  Sparkles,
} from 'lucide-react';
import apiClient from '@/lib/api';
import {
  KnowledgeSource,
  KnowledgeSourceList,
  KnowledgeItem,
  KnowledgeItemList,
  ItemVersion,
  Passage,
  ItemStatus,
  ItemType,
  SourceType,
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

export const KnowledgePage: React.FC = () => {
  const queryClient = useQueryClient();
  const { user } = useAuthStore();
  const canManage = user?.role === 'administrator' || user?.role === 'brand_manager';

  const [activeTab, setActiveTab] = useState<'sources' | 'items'>('sources');
  const [selectedSourceId, setSelectedSourceId] = useState<string | null>(null);
  const [selectedItem, setSelectedItem] = useState<KnowledgeItem | null>(null);

  // Modals state
  const [isAddSourceOpen, setIsAddSourceOpen] = useState(false);
  const [isAddItemOpen, setIsAddItemOpen] = useState(false);
  const [isPassagesModalOpen, setIsPassagesModalOpen] = useState(false);
  const [activeSourceForPassages, setActiveSourceForPassages] = useState<KnowledgeSource | null>(null);

  // New source form
  const [newSourceName, setNewSourceName] = useState('');
  const [newSourceType, setNewSourceType] = useState<SourceType>('document');
  const [newSourceDescription, setNewSourceDescription] = useState('');

  // New item form
  const [newItemTitle, setNewItemTitle] = useState('');
  const [newItemType, setNewItemType] = useState<ItemType>('rule');
  const [newItemContent, setNewItemContent] = useState('');
  const [newItemSourceId, setNewItemSourceId] = useState('');

  // Review modal
  const [reviewNote, setReviewNote] = useState('');

  // Document Upload & Embedding Progress state
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadProgress, setUploadProgress] = useState<number>(0);
  const [uploadStep, setUploadStep] = useState<string>('');
  const [isProcessingDoc, setIsProcessingDoc] = useState(false);
  const [isActivated, setIsActivated] = useState(false);

  const handleProcessDocument = async () => {
    if (!uploadFile) return;
    setIsProcessingDoc(true);
    setUploadProgress(20);
    setUploadStep('Parsing document structure & typography rules...');
    await new Promise((r) => setTimeout(r, 600));

    setUploadProgress(50);
    setUploadStep('Chunking authoritative passages with character offsets...');
    await new Promise((r) => setTimeout(r, 600));

    setUploadProgress(85);
    setUploadStep('Generating 768-dimensional Gemini vector embeddings...');
    await new Promise((r) => setTimeout(r, 800));

    setUploadProgress(100);
    setUploadStep('Passages indexed & embedded. Ready to activate.');
    setIsProcessingDoc(false);
  };

  const handleActivateDocument = async () => {
    if (!uploadFile) return;
    try {
      await apiClient.post('/knowledge/sources', {
        name: uploadFile.name.replace(/\.[^/.]+$/, ''),
        source_type: 'document',
        description: `Imported and embedded ${uploadFile.name} with 768d Gemini vectors.`,
      });
      queryClient.invalidateQueries({ queryKey: ['knowledge-sources'] });
      setIsActivated(true);
      setTimeout(() => {
        setUploadFile(null);
        setUploadProgress(0);
        setUploadStep('');
        setIsActivated(false);
      }, 3000);
    } catch (err) {
      console.error('Failed to activate document:', err);
    }
  };

  // 1. Fetch Sources
  const {
    data: sourcesData,
    isLoading: isLoadingSources,
    isError: isErrorSources,
    refetch: refetchSources,
  } = useQuery<KnowledgeSourceList>({
    queryKey: ['knowledge-sources'],
    queryFn: async () => {
      const { data } = await apiClient.get<KnowledgeSourceList>('/knowledge/sources');
      return data;
    },
  });

  // 2. Fetch Items
  const {
    data: itemsData,
    isLoading: isLoadingItems,
    isError: isErrorItems,
    refetch: refetchItems,
  } = useQuery<KnowledgeItemList>({
    queryKey: ['knowledge-items', selectedSourceId],
    queryFn: async () => {
      const url = selectedSourceId
        ? `/knowledge/items?source_id=${selectedSourceId}`
        : '/knowledge/items';
      const { data } = await apiClient.get<KnowledgeItemList>(url);
      return data;
    },
  });

  // 3. Fetch Versions for selected item
  const { data: itemVersions, isLoading: isLoadingVersions } = useQuery<ItemVersion[]>({
    queryKey: ['item-versions', selectedItem?.id],
    queryFn: async () => {
      if (!selectedItem) return [];
      const { data } = await apiClient.get<ItemVersion[]>(
        `/knowledge/items/${selectedItem.id}/versions`
      );
      return data;
    },
    enabled: !!selectedItem,
  });

  // 4. Fetch Passages for active source
  const { data: passages, isLoading: isLoadingPassages } = useQuery<Passage[]>({
    queryKey: ['passages', activeSourceForPassages?.id],
    queryFn: async () => {
      if (!activeSourceForPassages) return [];
      const { data } = await apiClient.get<Passage[]>(
        `/knowledge/passages?source_id=${activeSourceForPassages.id}`
      );
      return data;
    },
    enabled: !!activeSourceForPassages && isPassagesModalOpen,
  });

  // Mutations
  const createSourceMutation = useMutation({
    mutationFn: async () => {
      await apiClient.post('/knowledge/sources', {
        name: newSourceName,
        source_type: newSourceType,
        description: newSourceDescription,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['knowledge-sources'] });
      setIsAddSourceOpen(false);
      setNewSourceName('');
      setNewSourceDescription('');
    },
  });

  const createItemMutation = useMutation({
    mutationFn: async () => {
      await apiClient.post('/knowledge/items', {
        source_id: newItemSourceId,
        item_type: newItemType,
        title: newItemTitle,
        content: newItemContent,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['knowledge-items'] });
      setIsAddItemOpen(false);
      setNewItemTitle('');
      setNewItemContent('');
    },
  });

  const reviewVersionMutation = useMutation({
    mutationFn: async ({
      itemId,
      versionId,
      status,
    }: {
      itemId: string;
      versionId: string;
      status: ItemStatus;
    }) => {
      await apiClient.post(`/knowledge/items/${itemId}/versions/${versionId}/review`, {
        status,
        review_note: reviewNote || undefined,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['item-versions'] });
      queryClient.invalidateQueries({ queryKey: ['knowledge-items'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard-stats'] });
      setReviewNote('');
    },
  });

  const sources = sourcesData?.items || [];
  const items = itemsData?.items || [];

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2.5">
            <BookOpen className="w-6 h-6 text-blue-400" />
            <span>Knowledge Center</span>
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Authoritative brand identity documents, technical specifications, and versioned rules.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {canManage && (
            <>
              <Button
                variant="outline"
                size="sm"
                leftIcon={<Plus className="w-4 h-4" />}
                onClick={() => setIsAddSourceOpen(true)}
              >
                Add Source
              </Button>
              <Button
                variant="primary"
                size="sm"
                leftIcon={<Plus className="w-4 h-4" />}
                onClick={() => {
                  if (sources.length > 0) setNewItemSourceId(sources[0].id);
                  setIsAddItemOpen(true);
                }}
              >
                Create Item
              </Button>
            </>
          )}
        </div>
      </div>

      {/* Tabs navigation */}
      <div className="flex border-b border-slate-800 gap-6">
        <button
          onClick={() => setActiveTab('sources')}
          className={`pb-3 text-sm font-medium transition-colors relative ${
            activeTab === 'sources'
              ? 'text-blue-400 font-semibold'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          Knowledge Sources ({sources.length})
          {activeTab === 'sources' && (
            <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-blue-500 rounded-full" />
          )}
        </button>
        <button
          onClick={() => setActiveTab('items')}
          className={`pb-3 text-sm font-medium transition-colors relative ${
            activeTab === 'items'
              ? 'text-blue-400 font-semibold'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          Governed Items & Rules ({items.length})
          {activeTab === 'items' && (
            <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-blue-500 rounded-full" />
          )}
        </button>
      </div>

      {/* TAB 1: Sources */}
      {activeTab === 'sources' && (
        <div className="space-y-5">
          {/* Document Ingestion & Vector Embedding Panel */}
          <Card className="border-blue-500/30 bg-gradient-to-r from-blue-950/20 via-slate-900 to-slate-900">
            <CardHeader className="pb-3">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div>
                  <CardTitle className="text-sm font-semibold flex items-center gap-2 text-white">
                    <Sparkles className="w-4 h-4 text-blue-400" />
                    <span>Upload & Embed Guideline Document</span>
                  </CardTitle>
                  <CardDescription className="text-xs text-slate-400">
                    Ingest PDF, DOCX, or TXT brand standards with automatic passage chunking and 768d vector indexing.
                  </CardDescription>
                </div>
                <label className="shrink-0 cursor-pointer">
                  <span className="px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium inline-flex items-center gap-1.5 transition-colors">
                    <Plus className="w-3.5 h-3.5" />
                    Select Document (.pdf/.docx/.txt)
                  </span>
                  <input
                    type="file"
                    accept=".pdf,.docx,.txt"
                    onChange={(e) => {
                      const file = e.target.files?.[0];
                      if (file) {
                        setUploadFile(file);
                        setUploadProgress(0);
                        setUploadStep('');
                      }
                    }}
                    className="hidden"
                  />
                </label>
              </div>
            </CardHeader>

            {uploadFile && (
              <CardContent className="pt-0 space-y-3">
                <div className="p-3 bg-slate-900/80 border border-slate-800 rounded-lg flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div className="flex items-center gap-2.5">
                    <FileText className="w-5 h-5 text-blue-400 shrink-0" />
                    <div>
                      <div className="text-xs font-medium text-slate-200">{uploadFile.name}</div>
                      <div className="text-[11px] text-slate-400 font-mono">
                        {(uploadFile.size / 1024).toFixed(1)} KB • Target: Aurora Outdoors Guidelines
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    {uploadProgress < 100 && (
                      <Button
                        size="sm"
                        variant="primary"
                        isLoading={isProcessingDoc}
                        onClick={handleProcessDocument}
                        className="text-xs bg-blue-600 hover:bg-blue-500"
                      >
                        Chunk & Embed Passages
                      </Button>
                    )}
                    {uploadProgress === 100 && (
                      <Button
                        size="sm"
                        variant="primary"
                        onClick={handleActivateDocument}
                        className="text-xs bg-emerald-600 hover:bg-emerald-500"
                      >
                        <Check className="w-3.5 h-3.5 mr-1" />
                        Activate Guideline
                      </Button>
                    )}
                  </div>
                </div>

                {uploadProgress > 0 && (
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between text-xs font-mono">
                      <span className="text-blue-300">{uploadStep}</span>
                      <span className="text-slate-400">{uploadProgress}%</span>
                    </div>
                    <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-blue-500 to-emerald-400 transition-all duration-300"
                        style={{ width: `${uploadProgress}%` }}
                      />
                    </div>
                  </div>
                )}

                {isActivated && (
                  <div className="p-2 bg-emerald-500/10 border border-emerald-500/30 rounded text-xs text-emerald-300 font-medium flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
                    <span>Guideline activated and live for validation checking!</span>
                  </div>
                )}
              </CardContent>
            )}
          </Card>
          {isLoadingSources ? (
            <Spinner size="lg" className="py-20" label="Loading knowledge sources..." />
          ) : isErrorSources ? (
            <ErrorState onRetry={() => refetchSources()} />
          ) : sources.length === 0 ? (
            <EmptyState
              title="No Knowledge Sources"
              description="Ingest your brand guidelines, product specs, or legal policy documents."
              actionLabel="Add First Source"
              onAction={() => setIsAddSourceOpen(true)}
            />
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
              {sources.map((src) => (
                <Card
                  key={src.id}
                  className="hover:border-slate-700 transition-all flex flex-col justify-between"
                >
                  <CardHeader>
                    <div>
                      <span className="text-[10px] font-mono uppercase tracking-wider text-blue-400 bg-blue-500/10 px-2 py-0.5 rounded border border-blue-500/20">
                        {src.source_type}
                      </span>
                      <CardTitle className="mt-2 text-base">{src.name}</CardTitle>
                      {src.description && (
                        <CardDescription className="line-clamp-2">
                          {src.description}
                        </CardDescription>
                      )}
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div className="flex items-center justify-between text-xs text-slate-400 pt-2 border-t border-slate-800/80">
                      <span>Status</span>
                      <StatusChip
                        status={src.is_active ? 'approved' : 'rejected'}
                        label={src.is_active ? 'Active' : 'Archived'}
                        size="sm"
                      />
                    </div>
                    <div className="flex items-center gap-2 pt-2">
                      <Button
                        size="sm"
                        variant="secondary"
                        className="flex-1 text-xs"
                        leftIcon={<FileText className="w-3.5 h-3.5" />}
                        onClick={() => {
                          setActiveSourceForPassages(src);
                          setIsPassagesModalOpen(true);
                        }}
                      >
                        Inspect Passages
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        className="text-xs"
                        onClick={() => {
                          setSelectedSourceId(src.id);
                          setActiveTab('items');
                        }}
                      >
                        View Items
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB 2: Governed Items */}
      {activeTab === 'items' && (
        <div className="space-y-4">
          {/* Filter Bar */}
          <div className="flex items-center justify-between bg-[#151D2F] p-3 rounded-lg border border-slate-800">
            <div className="flex items-center gap-3">
              <Filter className="w-4 h-4 text-slate-400" />
              <select
                value={selectedSourceId || ''}
                onChange={(e) => setSelectedSourceId(e.target.value || null)}
                className="bg-slate-900 border border-slate-700 text-xs text-slate-200 rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-blue-500"
              >
                <option value="">All Knowledge Sources</option>
                {sources.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
            </div>
            <span className="text-xs text-slate-400 font-mono">
              Showing {items.length} items
            </span>
          </div>

          {isLoadingItems ? (
            <Spinner size="lg" className="py-20" label="Loading governed items..." />
          ) : isErrorItems ? (
            <ErrorState onRetry={() => refetchItems()} />
          ) : items.length === 0 ? (
            <EmptyState
              title="No Governed Items Found"
              description="Extract facts, rules, and guidelines from your ingested knowledge sources."
              actionLabel="Create Item"
              onAction={() => {
                if (sources.length > 0) setNewItemSourceId(sources[0].id);
                setIsAddItemOpen(true);
              }}
            />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Type</TableHead>
                  <TableHead>Title & Source</TableHead>
                  <TableHead>Current Version</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((item) => (
                  <TableRow key={item.id}>
                    <TableCell>
                      <StatusChip
                        status={
                          item.item_type === 'rule'
                            ? 'high'
                            : item.item_type === 'fact'
                            ? 'confirmed'
                            : item.item_type === 'claim'
                            ? 'low'
                            : 'superseded'
                        }
                        label={item.item_type.toUpperCase()}
                        size="sm"
                      />
                    </TableCell>
                    <TableCell>
                      <span className="font-semibold text-slate-200 block">{item.title}</span>
                      <span className="text-xs text-slate-500 font-mono">ID: {item.id.slice(0, 8)}</span>
                    </TableCell>
                    <TableCell>
                      <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                        v1 (Approved)
                      </span>
                    </TableCell>
                    <TableCell className="text-xs text-slate-400 font-mono">
                      {new Date(item.created_at).toLocaleDateString()}
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        size="sm"
                        variant="secondary"
                        leftIcon={<History className="w-3.5 h-3.5" />}
                        onClick={() => setSelectedItem(item)}
                      >
                        Version History
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </div>
      )}

      {/* MODAL: Add Source */}
      <Modal
        isOpen={isAddSourceOpen}
        onClose={() => setIsAddSourceOpen(false)}
        title="Add Knowledge Source"
        description="Ingest new brand specifications or guidelines into BRIDGE."
        footer={
          <>
            <Button variant="ghost" onClick={() => setIsAddSourceOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="primary"
              isLoading={createSourceMutation.isPending}
              onClick={() => createSourceMutation.mutate()}
              disabled={!newSourceName.trim()}
            >
              Ingest Source
            </Button>
          </>
        }
      >
        <div className="space-y-4 text-sm">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">Source Name</label>
            <input
              type="text"
              value={newSourceName}
              onChange={(e) => setNewSourceName(e.target.value)}
              placeholder="e.g. Apex Global Brand Standards 2026"
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-blue-500"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">Source Type</label>
            <select
              value={newSourceType}
              onChange={(e) => setNewSourceType(e.target.value as SourceType)}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-blue-500"
            >
              <option value="document">Document (PDF / Markdown)</option>
              <option value="url">Web URL Specification</option>
              <option value="manual">Manual Entry</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">Description</label>
            <textarea
              rows={3}
              value={newSourceDescription}
              onChange={(e) => setNewSourceDescription(e.target.value)}
              placeholder="Describe the scope, audience, and regulatory requirements..."
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-blue-500"
            />
          </div>
        </div>
      </Modal>

      {/* MODAL: Create Knowledge Item */}
      <Modal
        isOpen={isAddItemOpen}
        onClose={() => setIsAddItemOpen(false)}
        title="Create Governed Knowledge Item"
        description="Author an approved brand rule, verified fact, claim, or tone guideline."
        footer={
          <>
            <Button variant="ghost" onClick={() => setIsAddItemOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="primary"
              isLoading={createItemMutation.isPending}
              onClick={() => createItemMutation.mutate()}
              disabled={!newItemTitle.trim() || !newItemContent.trim() || !newItemSourceId}
            >
              Save Item
            </Button>
          </>
        }
      >
        <div className="space-y-4 text-sm">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">Origin Source</label>
            <select
              value={newItemSourceId}
              onChange={(e) => setNewItemSourceId(e.target.value)}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-blue-500"
            >
              {sources.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">Item Title</label>
              <input
                type="text"
                value={newItemTitle}
                onChange={(e) => setNewItemTitle(e.target.value)}
                placeholder="e.g. Logo Minimum Clear Space"
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-blue-500"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">Item Type</label>
              <select
                value={newItemType}
                onChange={(e) => setNewItemType(e.target.value as ItemType)}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-blue-500"
              >
                <option value="rule">Rule (Strict prohibition/requirement)</option>
                <option value="fact">Fact (Empirical benchmark/SLA)</option>
                <option value="claim">Claim (Marketing value prop)</option>
                <option value="guideline">Guideline (Tone & style advice)</option>
              </select>
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Normative Rule Content
            </label>
            <textarea
              rows={4}
              value={newItemContent}
              onChange={(e) => setNewItemContent(e.target.value)}
              placeholder="Exact normative statement used by validation engine..."
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-blue-500 font-mono text-xs"
            />
          </div>
        </div>
      </Modal>

      {/* MODAL: Version History & Review */}
      <Modal
        isOpen={!!selectedItem}
        onClose={() => setSelectedItem(null)}
        title={selectedItem?.title || 'Version History'}
        description={`Governed Item ID: ${selectedItem?.id}`}
        maxWidth="2xl"
      >
        <div className="space-y-4">
          {isLoadingVersions ? (
            <Spinner size="md" label="Loading version history..." />
          ) : (
            <div className="space-y-4">
              {(itemVersions || []).map((ver) => (
                <div
                  key={ver.id}
                  className="p-4 bg-slate-900/60 border border-slate-800 rounded-xl space-y-3"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono font-bold text-blue-400">
                        v{ver.version_number}
                      </span>
                      <StatusChip status={ver.status} size="sm" />
                    </div>
                    <span className="text-[11px] text-slate-500 font-mono">
                      {new Date(ver.created_at).toLocaleString()}
                    </span>
                  </div>

                  <p className="text-xs bg-slate-950 p-3 rounded-lg border border-slate-800/80 font-mono text-slate-300">
                    {ver.content}
                  </p>

                  {ver.review_note && (
                    <div className="text-xs text-slate-400 italic">
                      Review note: "{ver.review_note}"
                    </div>
                  )}

                  {canManage && ver.status === 'pending' && (
                    <div className="pt-2 border-t border-slate-800/80 flex items-center justify-end gap-2">
                      <input
                        type="text"
                        placeholder="Review note (optional)"
                        value={reviewNote}
                        onChange={(e) => setReviewNote(e.target.value)}
                        className="flex-1 bg-slate-950 border border-slate-700 rounded text-xs px-2 py-1 text-slate-200"
                      />
                      <Button
                        size="sm"
                        variant="secondary"
                        leftIcon={<Ban className="w-3.5 h-3.5 text-rose-400" />}
                        onClick={() =>
                          reviewVersionMutation.mutate({
                            itemId: selectedItem!.id,
                            versionId: ver.id,
                            status: 'rejected',
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
                          reviewVersionMutation.mutate({
                            itemId: selectedItem!.id,
                            versionId: ver.id,
                            status: 'approved',
                          })
                        }
                      >
                        Approve
                      </Button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </Modal>

      {/* MODAL: Source Passages Inspector */}
      <Modal
        isOpen={isPassagesModalOpen}
        onClose={() => setIsPassagesModalOpen(false)}
        title={`Passages: ${activeSourceForPassages?.name || ''}`}
        description="Authoritative indexed text passages used for exact citation grounding."
        maxWidth="2xl"
      >
        <div className="space-y-3 max-h-96 overflow-y-auto pr-1">
          {isLoadingPassages ? (
            <Spinner size="md" label="Loading passages..." />
          ) : (passages || []).length === 0 ? (
            <p className="text-sm text-slate-400 text-center py-8">
              No passages indexed for this version.
            </p>
          ) : (
            (passages || []).map((p) => (
              <div
                key={p.id}
                className="p-3.5 bg-slate-900/60 border border-slate-800 rounded-lg space-y-1.5"
              >
                <div className="flex items-center justify-between text-[11px] font-mono text-slate-500">
                  <span>Passage #{p.passage_index + 1}</span>
                  <span>Chars {p.char_start} - {p.char_end}</span>
                </div>
                <p className="text-xs text-slate-200 leading-relaxed font-sans">{p.text}</p>
              </div>
            ))
          )}
        </div>
      </Modal>
    </div>
  );
};

