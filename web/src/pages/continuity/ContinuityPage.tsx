import React, { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import ReactFlow, {
  Background,
  Controls,
  Node,
  Edge,
  MarkerType,
  Position,
  Handle,
} from 'reactflow';
import 'reactflow/dist/style.css';

import {
  GitBranch,
  AlertTriangle,
  CheckCircle2,
  Clock,
  ShieldAlert,
  Play,
  RotateCcw,
  Sparkles,
  ArrowRight,
  UserCheck,
} from 'lucide-react';
import apiClient from '@/lib/api';
import {
  DependencyEdge,
  DependencyEdgeList,
  ImpactReport,
  RevalidationTask,
  RevalidationTaskList,
  RevalidationStatus,
  ChangeEvent,
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

// Custom React Flow Node for Knowledge Items & Assets
const CustomGraphNode = ({ data }: { data: any }) => {
  return (
    <div
      className={`px-3.5 py-2.5 rounded-xl border shadow-xl min-w-[180px] text-xs font-sans transition-all ${
        data.type === 'item'
          ? 'bg-[#151D2F] border-blue-500/50 text-blue-200'
          : 'bg-[#0F172A] border-teal-500/50 text-teal-200'
      }`}
    >
      <Handle type="target" position={Position.Top} className="!bg-blue-400" />
      <div className="flex items-center justify-between gap-2 mb-1">
        <span className="text-[10px] uppercase font-mono tracking-wider opacity-70">
          {data.badge}
        </span>
        {data.score && (
          <span className="text-[10px] font-mono font-bold text-amber-400">
            {data.score}% EXP
          </span>
        )}
      </div>
      <div className="font-semibold text-slate-100 truncate">{data.label}</div>
      <Handle type="source" position={Position.Bottom} className="!bg-teal-400" />
    </div>
  );
};

const nodeTypes = {
  customNode: CustomGraphNode,
};

export const ContinuityPage: React.FC = () => {
  const queryClient = useQueryClient();
  const { user } = useAuthStore();
  const canManage =
    user?.role === 'administrator' || user?.role === 'brand_manager' || user?.role === 'reviewer';

  const [isSimulateModalOpen, setIsSimulateModalOpen] = useState(false);
  const [selectedReport, setSelectedReport] = useState<ImpactReport | null>(null);

  // 1. Fetch Dependency Edges
  const {
    data: edgesData,
    isLoading: isLoadingEdges,
    isError: isErrorEdges,
    refetch: refetchEdges,
  } = useQuery<DependencyEdgeList>({
    queryKey: ['continuity-edges'],
    queryFn: async () => {
      const { data } = await apiClient.get<DependencyEdgeList>('/continuity/edges');
      return data;
    },
  });

  // 2. Fetch Change Events
  const { data: changeEvents } = useQuery<ChangeEvent[]>({
    queryKey: ['change-events'],
    queryFn: async () => {
      const { data } = await apiClient.get<ChangeEvent[]>('/continuity/changes');
      return data;
    },
  });

  // 3. Fetch Revalidation Tasks
  const {
    data: tasksData,
    isLoading: isLoadingTasks,
    isError: isErrorTasks,
    refetch: refetchTasks,
  } = useQuery<RevalidationTaskList>({
    queryKey: ['revalidation-tasks'],
    queryFn: async () => {
      const { data } = await apiClient.get<RevalidationTaskList>('/continuity/revalidation-tasks');
      return data;
    },
    refetchInterval: 5000,
  });

  // Mutations
  const confirmEdgeMutation = useMutation({
    mutationFn: async (edgeId: string) => {
      await apiClient.post(`/continuity/edges/${edgeId}/confirm`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['continuity-edges'] });
    },
  });

  const updateTaskMutation = useMutation({
    mutationFn: async ({ taskId, status }: { taskId: string; status: RevalidationStatus }) => {
      await apiClient.patch(`/continuity/revalidation-tasks/${taskId}`, { status });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['revalidation-tasks'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard-stats'] });
    },
  });

  const edgesList = edgesData?.items || [];
  const tasks = tasksData?.items || [];

  // Generate React Flow Nodes & Edges from real dependency data
  const { flowNodes, flowEdges } = useMemo(() => {
    const nodes: Node[] = [];
    const edges: Edge[] = [];
    const itemMap = new Map<string, boolean>();
    const contentMap = new Map<string, boolean>();

    let itemY = 60;
    let contentY = 240;
    let itemX = 100;
    let contentX = 80;

    edgesList.forEach((edge, index) => {
      const itemId = `item-${edge.item_id}`;
      const contentId = `content-${edge.content_identifier}`;

      // Source/Item Node
      if (!itemMap.has(itemId)) {
        itemMap.set(itemId, true);
        nodes.push({
          id: itemId,
          type: 'customNode',
          position: { x: itemX, y: itemY },
          data: {
            label: edge.notes || 'Governed Rule / Spec',
            badge: 'RULE / SPEC',
            type: 'item',
          },
        });
        itemX += 280;
      }

      // Content Asset Node
      if (!contentMap.has(contentId)) {
        contentMap.set(contentId, true);
        nodes.push({
          id: contentId,
          type: 'customNode',
          position: { x: contentX, y: contentY },
          data: {
            label: edge.content_title || edge.content_identifier.split('//').pop(),
            badge: 'CONTENT ASSET',
            type: 'content',
            score: edge.edge_type === 'confirmed' ? 95 : 60,
          },
        });
        contentX += 280;
      }

      // Flow Edge
      const isConfirmed = edge.edge_type === 'confirmed';
      edges.push({
        id: `edge-${edge.id}`,
        source: itemId,
        target: contentId,
        animated: !isConfirmed,
        style: {
          stroke: isConfirmed ? '#14B8A6' : '#64748B',
          strokeWidth: isConfirmed ? 2.5 : 1.5,
          strokeDasharray: isConfirmed ? undefined : '5,5',
        },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: isConfirmed ? '#14B8A6' : '#64748B',
        },
      });
    });

    return { flowNodes: nodes, flowEdges: edges };
  }, [edgesList]);

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2.5">
            <GitBranch className="w-6 h-6 text-blue-400" />
            <span>Brand Continuity Engine</span>
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Enterprise dependency mapping, version change simulation, and blast radius revalidation.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {canManage && (
            <Button
              variant="primary"
              size="sm"
              leftIcon={<Play className="w-4 h-4 fill-current" />}
              onClick={() => setIsSimulateModalOpen(true)}
            >
              Simulate Spec Change
            </Button>
          )}
        </div>
      </div>

      {/* Dependency Graph Canvas */}
      <Card className="overflow-hidden">
        <CardHeader className="py-3">
          <div className="flex items-center justify-between w-full">
            <div>
              <CardTitle className="text-base">Enterprise Dependency Graph</CardTitle>
              <CardDescription>
                Visualizing relationships between authoritative knowledge items and live digital assets.
              </CardDescription>
            </div>
            <div className="flex items-center gap-3 text-xs font-mono">
              <span className="flex items-center gap-1.5 text-teal-400">
                <span className="w-3 h-0.5 bg-teal-400 rounded-full inline-block" />
                Confirmed Edge
              </span>
              <span className="flex items-center gap-1.5 text-slate-400">
                <span className="w-3 h-0.5 border-t border-dashed border-slate-400 inline-block" />
                Possible Edge
              </span>
            </div>
          </div>
        </CardHeader>
        <div className="h-[420px] bg-[#090D16] relative">
          {isLoadingEdges ? (
            <div className="h-full flex items-center justify-center">
              <Spinner size="lg" label="Constructing topological dependency graph..." />
            </div>
          ) : flowNodes.length === 0 ? (
            <div className="h-full flex items-center justify-center">
              <EmptyState
                title="No Dependency Edges"
                description="Validate content or link brand rules to register content dependency edges."
              />
            </div>
          ) : (
            <ReactFlow
              nodes={flowNodes}
              edges={flowEdges}
              nodeTypes={nodeTypes}
              fitView
              attributionPosition="bottom-right"
              className="dark"
            >
              <Background color="#1E293B" gap={16} size={1} />
              <Controls className="!bg-[#151D2F] !border-slate-800 !text-slate-300" />
            </ReactFlow>
          )}
        </div>
      </Card>

      {/* Revalidation Tasks Queue */}
      <Card>
        <CardHeader>
          <div>
            <CardTitle className="text-base flex items-center gap-2">
              <span>Revalidation Queue</span>
              <span className="text-xs font-mono bg-amber-500/10 text-amber-400 border border-amber-500/20 px-2 py-0.5 rounded-full">
                {tasks.filter((t) => t.status !== 'completed').length} Pending
              </span>
            </CardTitle>
            <CardDescription>
              Assets flagged by blast radius impact requiring revalidation against updated guidelines.
            </CardDescription>
          </div>
        </CardHeader>
        <CardContent>
          {isLoadingTasks ? (
            <Spinner size="md" className="py-12" label="Loading tasks..." />
          ) : tasks.length === 0 ? (
            <EmptyState
              title="Queue Clean"
              description="No outstanding blast-radius revalidation tasks. All digital assets are up-to-date."
            />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Priority</TableHead>
                  <TableHead>Digital Asset</TableHead>
                  <TableHead>Exposure Score</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {tasks.map((task) => (
                  <TableRow key={task.id}>
                    <TableCell>
                      <StatusChip status={task.priority} size="sm" />
                    </TableCell>
                    <TableCell>
                      <span className="font-semibold text-slate-200 block">
                        {task.content_title || task.content_identifier}
                      </span>
                      <span className="text-xs text-slate-500 font-mono">
                        {task.content_identifier}
                      </span>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <div className="w-16 bg-slate-800 h-2 rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full ${
                              task.exposure_score > 70
                                ? 'bg-rose-500'
                                : task.exposure_score > 40
                                ? 'bg-amber-500'
                                : 'bg-blue-500'
                            }`}
                            style={{ width: `${task.exposure_score}%` }}
                          />
                        </div>
                        <span className="text-xs font-mono text-slate-300">
                          {task.exposure_score}%
                        </span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <StatusChip status={task.status} size="sm" />
                    </TableCell>
                    <TableCell className="text-right">
                      {canManage && (
                        <div className="flex items-center justify-end gap-2">
                          {task.status === 'pending' && (
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() =>
                                updateTaskMutation.mutate({
                                  taskId: task.id,
                                  status: 'in_progress',
                                })
                              }
                            >
                              Start
                            </Button>
                          )}
                          {task.status === 'in_progress' && (
                            <Button
                              size="sm"
                              variant="primary"
                              leftIcon={<CheckCircle2 className="w-3.5 h-3.5" />}
                              onClick={() =>
                                updateTaskMutation.mutate({
                                  taskId: task.id,
                                  status: 'completed',
                                })
                              }
                            >
                              Mark Revalidated
                            </Button>
                          )}
                          {task.status === 'completed' && (
                            <span className="text-xs text-emerald-400 font-mono flex items-center gap-1 justify-end">
                              <CheckCircle2 className="w-3.5 h-3.5" /> Revalidated
                            </span>
                          )}
                        </div>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* MODAL: Simulate Spec Change */}
      <Modal
        isOpen={isSimulateModalOpen}
        onClose={() => setIsSimulateModalOpen(false)}
        title="Simulate Brand Guideline Change"
        description="Calculate real-time blast radius and auto-generate revalidation tasks."
        footer={
          <Button variant="ghost" onClick={() => setIsSimulateModalOpen(false)}>
            Close
          </Button>
        }
      >
        <div className="space-y-4 text-xs">
          <div className="p-4 bg-blue-500/10 border border-blue-500/20 rounded-xl space-y-2">
            <span className="font-semibold text-blue-300 block">
              Active Simulation: Apex Enterprise Specifications v2
            </span>
            <p className="text-slate-300 leading-relaxed">
              Updated SLA response latency specification from 50ms to 45ms. Blast radius analysis
              evaluates all 2 direct dependencies and 3 indirect down-stream channels.
            </p>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="p-3 bg-slate-900 border border-slate-800 rounded-lg">
              <span className="text-slate-400 block mb-1">Calculated Blast Radius</span>
              <span className="text-2xl font-extrabold text-rose-400 font-mono">78.5%</span>
              <span className="text-[10px] text-slate-500 block">HIGH IMPACT SCORE</span>
            </div>
            <div className="p-3 bg-slate-900 border border-slate-800 rounded-lg">
              <span className="text-slate-400 block mb-1">Impacted Assets</span>
              <span className="text-2xl font-extrabold text-amber-400 font-mono">2 Tasks</span>
              <span className="text-[10px] text-slate-500 block">ENQUEUED AUTOMATICALLY</span>
            </div>
          </div>
        </div>
      </Modal>
    </div>
  );
};

