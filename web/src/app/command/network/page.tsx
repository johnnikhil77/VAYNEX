"use client";

import { Box, GitBranch } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Suspense, useMemo, useState } from "react";
import { useGraph, useInfrastructureDeps } from "@/hooks/use-vaynex";
import { cn } from "@/lib/utils/cn";
import { humanize } from "@/lib/utils/format";
import type { DependencyGraph, GraphNode } from "@/types";
import { PageHeader } from "@/components/shell/page-header";
import { Panel } from "@/components/ui/panel";
import { Badge, LevelBadge, StatusBadge } from "@/components/ui/badge";
import { EmptyState, LoadingState, QueryView } from "@/components/ui/states";
import { DependencyFlow } from "@/components/network/dependency-flow";
import { NetworkView } from "@/components/3d/network-view";
import { NetworkLegend } from "@/components/network/node-inspector";
import { ImpactList } from "@/components/incidents/impact-list";

export default function NetworkPage() {
  return (
    <Suspense fallback={<LoadingState label="LOADING NETWORK" />}>
      <NetworkScreen />
    </Suspense>
  );
}

function NetworkScreen() {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const selectedId = params.get("node");
  const [view, setView] = useState<"flow" | "3d">("flow");
  const graph = useGraph();

  const select = (id: string | null) => {
    router.replace(id ? `${pathname}?node=${id}` : pathname, { scroll: false });
  };

  const selected = graph.data?.nodes.find((n) => n.id === selectedId) ?? null;
  const deps = useInfrastructureDeps(selected?.kind === "INFRASTRUCTURE" ? selected.id : null);

  // Direct neighbours come straight from the graph's edges (target depends on source).
  const { upstream, downstream } = useMemo(() => neighbours(graph.data, selectedId), [graph.data, selectedId]);
  const affected = useMemo(
    () => new Set([...(deps.data?.affected_infrastructure ?? []), ...(deps.data?.affected_services ?? [])].map((n) => n.id)),
    [deps.data],
  );

  return (
    <div className="flex flex-col p-4">
      <PageHeader
        code="05 · NETWORK"
        title="Dependency Intelligence"
        subtitle="Every infrastructure asset and public service, and what depends on what. Select a node to trace upstream providers, downstream dependants and the cascade if it fails."
        actions={
          <div className="flex border border-line">
            {(
              [
                ["flow", "Graph", GitBranch],
                ["3d", "3D", Box],
              ] as const
            ).map(([k, label, Icon]) => (
              <button
                key={k}
                onClick={() => setView(k)}
                className={cn(
                  "flex h-8 items-center gap-1.5 px-3 font-mono text-2xs uppercase tracking-wider",
                  view === k ? "bg-cyan/10 text-cyan" : "text-muted hover:text-ink",
                )}
              >
                <Icon className="h-3.5 w-3.5" /> {label}
              </button>
            ))}
          </div>
        }
      />
      <div className="grid gap-3 xl:grid-cols-[1fr,400px]">
        <Panel
          title={view === "flow" ? "DEPENDENCY GRAPH" : "RESILIENCE NETWORK"}
          code={view === "flow" ? "DG" : "3D"}
          bodyClassName="relative p-0"
          className="h-[calc(100vh-230px)] min-h-[560px]"
          actions={
            graph.data && (
              <span className="font-mono text-2xs text-muted">
                {graph.data.nodes.length} NODES · {graph.data.edges.length} EDGES ({graph.data.edges.filter((e) => e.implicit).length} HOSTING)
              </span>
            )
          }
        >
          <div className="absolute inset-0">
            <QueryView
              query={graph}
              loadingLabel="MAPPING DEPENDENCIES"
              errorTitle="NETWORK UNAVAILABLE"
              isEmpty={(g) => g.nodes.length === 0}
              empty={<EmptyState title="NO NODES" hint="Seed the demo data on the backend." />}
            >
              {(g) =>
                view === "flow" ? (
                  <DependencyFlow
                    graph={g}
                    selectedId={selectedId}
                    onSelect={select}
                    upstream={upstream}
                    downstream={downstream}
                    affected={affected}
                  />
                ) : (
                  <NetworkView
                    graph={g}
                    selectedId={selectedId}
                    onSelect={select}
                    affected={selectedId ? [selectedId, ...affected] : undefined}
                    origin={selectedId}
                    showAllLabels
                  />
                )
              }
            </QueryView>
          </div>
          {view === "3d" && (
            <div className="pointer-events-none absolute left-3 top-3">
              <NetworkLegend />
            </div>
          )}
          {view === "flow" && (
            <div className="pointer-events-none absolute bottom-3 left-3 flex gap-3 border border-line bg-panel/90 px-2.5 py-1.5 font-mono text-[10px] text-muted">
              <span className="text-blue">■ UPSTREAM</span>
              <span className="text-amber">■ DOWNSTREAM</span>
              <span className="text-red">■ IMPACT PATH</span>
              <span>- - HOSTING</span>
            </div>
          )}
        </Panel>

        <Panel title="NODE INTELLIGENCE" code="NI" bodyClassName="p-0 overflow-y-auto" className="h-[calc(100vh-230px)] min-h-[560px]">
          {!selected ? (
            <EmptyState title="SELECT A NODE" hint="Click any infrastructure asset or service in the graph." className="h-full" />
          ) : (
            <NodeIntel
              node={selected}
              graph={graph.data!}
              upstream={upstream}
              downstream={downstream}
              deps={deps}
            />
          )}
        </Panel>
      </div>
    </div>
  );
}

function neighbours(graph: DependencyGraph | undefined, id: string | null) {
  const upstream = new Set<string>();
  const downstream = new Set<string>();
  if (!graph || !id) return { upstream, downstream };
  for (const e of graph.edges) {
    if (e.target === id) upstream.add(e.source);
    if (e.source === id) downstream.add(e.target);
  }
  return { upstream, downstream };
}

function NodeIntel({
  node,
  graph,
  upstream,
  downstream,
  deps,
}: {
  node: GraphNode;
  graph: DependencyGraph;
  upstream: Set<string>;
  downstream: Set<string>;
  deps: ReturnType<typeof useInfrastructureDeps>;
}) {
  const byId = new Map(graph.nodes.map((n) => [n.id, n]));
  const hosted = graph.edges.filter((e) => e.implicit && e.source === node.id).map((e) => byId.get(e.target)).filter(Boolean) as GraphNode[];
  const list = (ids: Set<string>) => [...ids].map((i) => byId.get(i)).filter(Boolean) as GraphNode[];

  return (
    <div className="divide-y divide-line">
      <div className="p-3">
        <div className="flex flex-wrap items-center gap-1.5">
          <Badge tone={node.kind === "INFRASTRUCTURE" ? "accent" : "info"}>{node.kind}</Badge>
          <StatusBadge status={node.status} />
          <LevelBadge level={node.criticality} />
        </div>
        <h2 className="mt-2 text-lg font-semibold text-ink">{node.name}</h2>
        <p className="font-mono text-2xs text-muted">{humanize(node.type)}</p>
        {node.kind === "INFRASTRUCTURE" && (
          <Link href={`/command/infrastructure?id=${node.id}`} className="mt-2 inline-block font-mono text-2xs text-cyan hover:underline">
            ASSET DOSSIER →
          </Link>
        )}
      </div>
      <NodeGroup title="UPSTREAM · PROVIDERS" nodes={list(upstream)} />
      <NodeGroup title="DOWNSTREAM · DEPENDANTS" nodes={list(downstream)} />
      {node.kind === "INFRASTRUCTURE" && <NodeGroup title="HOSTED SERVICES" nodes={hosted} />}
      {node.kind === "INFRASTRUCTURE" ? (
        deps.isLoading ? (
          <LoadingState label="COMPUTING CASCADE" />
        ) : deps.data ? (
          <>
            <div className="p-3">
              <span className="label text-red/80">AFFECTED INFRASTRUCTURE IF FAILED ({deps.data.affected_infrastructure.length})</span>
              <ImpactList nodes={deps.data.affected_infrastructure} />
            </div>
            <div className="p-3">
              <span className="label text-red/80">AFFECTED SERVICES IF FAILED ({deps.data.affected_services.length})</span>
              <ImpactList nodes={deps.data.affected_services} />
            </div>
          </>
        ) : null
      ) : (
        <p className="p-3 text-xs text-muted">
          Cascade analysis (<span className="font-mono">/infrastructure/&#123;id&#125;/dependencies</span>) is available for infrastructure nodes.
        </p>
      )}
    </div>
  );
}

function NodeGroup({ title, nodes }: { title: string; nodes: GraphNode[] }) {
  return (
    <div className="p-3">
      <span className="label">
        {title} ({nodes.length})
      </span>
      {nodes.length === 0 ? (
        <p className="mt-1 text-xs text-muted">None.</p>
      ) : (
        <ul className="mt-1.5 space-y-1">
          {nodes.map((n) => (
            <li key={n.id} className="flex items-center gap-2 border border-line bg-bg/40 px-2 py-1.5">
              <span className="min-w-0 flex-1 truncate text-xs text-ink">{n.name}</span>
              <StatusBadge status={n.status} />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
