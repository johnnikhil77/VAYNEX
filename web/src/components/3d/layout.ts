import type { DependencyGraph, GraphEdge, GraphNode } from "@/types";

export interface PlacedNode {
  node: GraphNode;
  /** World position [x, y, z]. Infrastructure sits on y=0, services on an upper layer. */
  pos: [number, number, number];
  hostId: string | null;
  geo: boolean;
}

export interface NetworkLayout {
  nodes: PlacedNode[];
  byId: Map<string, PlacedNode>;
  edges: GraphEdge[];
  extent: number;
}

const SERVICE_Y = 2.4;
const RADIUS = 6;

/**
 * Positions infrastructure by its real latitude/longitude (normalised to the scene),
 * and floats each public service above the asset that hosts it (implicit hosting edge).
 * Nodes without coordinates are placed on an outer ring — no locations are invented.
 */
export function computeLayout(graph: DependencyGraph): NetworkLayout {
  const infra = graph.nodes.filter((n) => n.kind === "INFRASTRUCTURE");
  const services = graph.nodes.filter((n) => n.kind === "SERVICE");

  const geo = infra.filter((n) => typeof n.latitude === "number" && typeof n.longitude === "number");
  const lats = geo.map((n) => n.latitude as number);
  const lons = geo.map((n) => n.longitude as number);
  const latC = lats.length ? (Math.min(...lats) + Math.max(...lats)) / 2 : 0;
  const lonC = lons.length ? (Math.min(...lons) + Math.max(...lons)) / 2 : 0;
  // Correct longitude spacing for latitude so the shape is not distorted.
  const lonScale = Math.cos((latC * Math.PI) / 180);
  const span = Math.max(
    lats.length ? Math.max(...lats) - Math.min(...lats) : 0,
    lons.length ? (Math.max(...lons) - Math.min(...lons)) * lonScale : 0,
    1e-6,
  );
  const scale = (RADIUS * 2) / span;

  const placed = new Map<string, PlacedNode>();
  for (const n of geo) {
    const x = ((n.longitude as number) - lonC) * lonScale * scale;
    const z = -((n.latitude as number) - latC) * scale;
    placed.set(n.id, { node: n, pos: [x, 0, z], hostId: null, geo: true });
  }
  const nonGeo = infra.filter((n) => !placed.has(n.id));
  nonGeo.forEach((n, i) => {
    const a = (i / Math.max(1, nonGeo.length)) * Math.PI * 2;
    placed.set(n.id, { node: n, pos: [Math.cos(a) * (RADIUS + 2.5), 0, Math.sin(a) * (RADIUS + 2.5)], hostId: null, geo: false });
  });

  // Services: hosted ones hover above their host, fanned out when several share a host.
  const hostOf = new Map<string, string>();
  for (const e of graph.edges) if (e.implicit) hostOf.set(e.target, e.source);
  const siblings = new Map<string, GraphNode[]>();
  const floating: GraphNode[] = [];
  for (const s of services) {
    const host = hostOf.get(s.id);
    if (host && placed.has(host)) {
      const arr = siblings.get(host) ?? [];
      arr.push(s);
      siblings.set(host, arr);
    } else floating.push(s);
  }
  for (const [hostId, list] of siblings) {
    const h = placed.get(hostId)!;
    list.forEach((s, i) => {
      const a = (i / list.length) * Math.PI * 2 + 0.6;
      const r = list.length > 1 ? 1.1 : 0;
      placed.set(s.id, {
        node: s,
        pos: [h.pos[0] + Math.cos(a) * r, SERVICE_Y + i * 0.15, h.pos[2] + Math.sin(a) * r],
        hostId,
        geo: false,
      });
    });
  }
  floating.forEach((s, i) => {
    const a = (i / Math.max(1, floating.length)) * Math.PI * 2 + 0.3;
    placed.set(s.id, {
      node: s,
      pos: [Math.cos(a) * (RADIUS * 0.55), SERVICE_Y + 1.4, Math.sin(a) * (RADIUS * 0.55)],
      hostId: null,
      geo: false,
    });
  });

  const nodes = graph.nodes.map((n) => placed.get(n.id)).filter((p): p is PlacedNode => !!p);
  const extent = Math.max(RADIUS, ...nodes.map((p) => Math.hypot(p.pos[0], p.pos[2])));
  const edges = graph.edges.filter((e) => placed.has(e.source) && placed.has(e.target));
  return { nodes, byId: placed, edges, extent };
}

export type NodeVisualState = "normal" | "degraded" | "failed" | "origin" | "affected";

export interface HighlightInput {
  affected: Set<string>;
  origin: string | null;
  depthById: Record<string, number>;
  /** Only affected nodes with depth <= revealDepth are shown as impacted (propagation animation). */
  revealDepth: number;
}

export function nodeState(node: GraphNode, h: HighlightInput | null): NodeVisualState {
  if (h && h.affected.has(node.id)) {
    const depth = h.depthById[node.id] ?? 0;
    if (depth <= h.revealDepth) return node.id === h.origin ? "origin" : "affected";
  }
  if (node.status === "FAILED" || node.status === "DISRUPTED" || node.status === "SUSPENDED") return "failed";
  if (node.status === "DEGRADED") return "degraded";
  return "normal";
}

export const STATE_COLOR: Record<NodeVisualState, string> = {
  normal: "#22D3EE",
  degraded: "#F5A524",
  failed: "#FF4D5E",
  origin: "#FF4D5E",
  affected: "#FF7A45",
};

export const CRIT_SIZE: Record<string, number> = { LOW: 0.22, MEDIUM: 0.27, HIGH: 0.32, CRITICAL: 0.38 };
