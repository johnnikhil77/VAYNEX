"use client";

import { Activity, ArrowRight, Play, Zap } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo } from "react";
import { useDashboard, useGraph, useIncidents } from "@/hooks/use-vaynex";
import { useRole } from "@/hooks/use-session";
import { formatTime } from "@/lib/utils/format";
import { useUI } from "@/store/ui";
import { Button } from "@/components/ui/button";
import { Panel } from "@/components/ui/panel";
import { ErrorState, LoadingState, QueryView } from "@/components/ui/states";
import { LevelBadge } from "@/components/ui/badge";
import { NetworkView } from "@/components/3d/network-view";
import { MetricsStrip } from "@/components/command-center/metrics-strip";
import { LiveIncidents, RecentEvents } from "@/components/command-center/live-incidents";
import {
  InfrastructurePanel,
  RiskPanel,
  ServicesPanel,
  SystemStatusPanel,
} from "@/components/command-center/bottom-panels";
import { NetworkLegend, NodeInspectorCard } from "@/components/network/node-inspector";
import { CreateEventDialog } from "@/components/incidents/create-event-dialog";

export default function CommandCenterPage() {
  const router = useRouter();
  const { canOperate } = useRole();
  const dashboard = useDashboard();
  const graph = useGraph();
  const active = useIncidents({ active_only: true, limit: 20 });
  const selectedNodeId = useUI((s) => s.selectedNodeId);
  const selectNode = useUI((s) => s.selectNode);
  const lastSim = useUI((s) => s.lastSimulation);

  // Keep the last simulation's impact path lit only while its incident is still active.
  const simActive =
    !!lastSim?.incident && !!active.data?.items.some((i) => i.id === lastSim.incident?.id);
  const highlight = useMemo(() => {
    if (!simActive || !lastSim) return null;
    const nodes = [...lastSim.affected_infrastructure, ...lastSim.affected_services];
    return {
      affected: nodes.map((n) => n.id),
      origin: nodes.find((n) => n.relationship === "ORIGIN")?.id ?? lastSim.event.infrastructure_id,
      depthById: Object.fromEntries(nodes.map((n) => [n.id, n.depth])),
    };
  }, [simActive, lastSim]);

  const selectedNode = graph.data?.nodes.find((n) => n.id === selectedNodeId) ?? null;

  return (
    <div className="flex flex-col gap-3 p-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="font-mono text-2xs tracking-[0.3em] text-cyan/70">01 · COMMAND CENTER</div>
          <h1 className="mt-1 font-mono text-lg font-semibold uppercase tracking-[0.22em]">
            National Resilience Overview
          </h1>
        </div>
        <div className="flex items-center gap-2">
          {canOperate && (
            <CreateEventDialog
              trigger={(open) => (
                <Button variant="outline" onClick={open}>
                  <Zap className="h-3.5 w-3.5" /> Create Event
                </Button>
              )}
            />
          )}
          {canOperate && (
            <Button variant="solid" onClick={() => router.push("/command/simulation?demo=1")}>
              <Play className="h-3.5 w-3.5 fill-current" /> Run Vaynex Demo
            </Button>
          )}
        </div>
      </div>

      {dashboard.isLoading ? (
        <LoadingState label="CONNECTING TO VAYNEX" className="min-h-[76px]" />
      ) : dashboard.isError && !dashboard.data ? (
        <div className="border border-line bg-panel">
          <ErrorState error={dashboard.error} onRetry={() => void dashboard.refetch()} />
        </div>
      ) : dashboard.data ? (
        <MetricsStrip d={dashboard.data} />
      ) : null}

      {simActive && lastSim && (
        <div className="flex flex-wrap items-center gap-3 border border-red/40 bg-red-soft/30 px-3 py-2">
          <Activity className="h-4 w-4 text-red" />
          <span className="font-mono text-xs uppercase tracking-wider text-red">Simulation impact active</span>
          <span className="text-sm text-ink">{lastSim.incident?.title}</span>
          {lastSim.risk && <LevelBadge level={lastSim.risk.level} />}
          <span className="font-mono text-2xs text-muted">RUN {formatTime(lastSim.event.created_at)}</span>
          {lastSim.incident && (
            <Link
              href={`/command/incidents/${lastSim.incident.id}`}
              className="ml-auto flex items-center gap-1 font-mono text-2xs text-cyan hover:underline"
            >
              REVIEW & DECIDE <ArrowRight className="h-3 w-3" />
            </Link>
          )}
        </div>
      )}

      <div className="grid min-h-[520px] grid-cols-1 gap-3 lg:grid-cols-[1fr,340px]">
        <Panel
          title="VAYNEX RESILIENCE NETWORK"
          code="3D"
          bodyClassName="relative p-0"
          className="min-h-[520px]"
          actions={
            graph.data && (
              <span className="font-mono text-2xs text-muted">
                {graph.data.nodes.length} NODES · {graph.data.edges.length} LINKS
              </span>
            )
          }
        >
          <div className="absolute inset-0">
            <QueryView query={graph} loadingLabel="MAPPING DEPENDENCIES" errorTitle="NETWORK UNAVAILABLE">
              {(g) => (
                <NetworkView
                  graph={g}
                  affected={highlight?.affected}
                  origin={highlight?.origin ?? null}
                  depthById={highlight?.depthById}
                  selectedId={selectedNodeId}
                  onSelect={selectNode}
                />
              )}
            </QueryView>
          </div>
          <div className="pointer-events-none absolute left-3 top-3">
            <div className="pointer-events-auto">
              <NetworkLegend />
            </div>
          </div>
          {selectedNode && (
            <div className="absolute right-3 top-3">
              <NodeInspectorCard node={selectedNode} onClose={() => selectNode(null)} />
            </div>
          )}
          <div className="pointer-events-none absolute bottom-3 left-3 font-mono text-[10px] text-dim">
            DRAG TO ORBIT · SCROLL TO ZOOM · CLICK NODE TO INSPECT · POSITIONS FROM REAL COORDINATES
          </div>
        </Panel>
        <div className="grid min-h-0 grid-rows-[1fr,auto] gap-3">
          <LiveIncidents />
          {dashboard.data && (
            <div className="max-h-[220px] min-h-0">
              <RecentEvents events={dashboard.data.recent_events.slice(0, 6)} />
            </div>
          )}
        </div>
      </div>

      {dashboard.data && (
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 2xl:grid-cols-4">
          <SystemStatusPanel d={dashboard.data} />
          <RiskPanel d={dashboard.data} />
          <ServicesPanel />
          <InfrastructurePanel d={dashboard.data} />
        </div>
      )}
    </div>
  );
}
