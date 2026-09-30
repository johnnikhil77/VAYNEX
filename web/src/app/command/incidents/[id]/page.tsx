"use client";

import { ArrowLeft, BrainCircuit, CheckCircle2, Loader2, RefreshCw, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { useAnalyzeIncident, useIncident, useIncidentRisk, useRecalculateRisk } from "@/hooks/use-vaynex";
import { useRole } from "@/hooks/use-session";
import { errorMessage } from "@/lib/api/errors";
import { formatCoord, formatDateTime, humanize, shortId } from "@/lib/utils/format";
import { Badge, LevelBadge, StatusBadge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Panel } from "@/components/ui/panel";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/states";
import { toast } from "@/components/ui/toast";
import { RiskBlock } from "@/components/incidents/risk";
import { RiskHistoryChart } from "@/components/incidents/risk-history";
import { ImpactList } from "@/components/incidents/impact-list";
import { ResolveDialog } from "@/components/incidents/resolve-dialog";
import { AIAnalysisView } from "@/components/intelligence/ai-analysis";
import { RecommendationCard } from "@/components/recommendations/recommendation-card";

export default function IncidentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { canOperate } = useRole();
  const q = useIncident(id);
  const risk = useIncidentRisk(id);
  const analyze = useAnalyzeIncident();
  const recalc = useRecalculateRisk();
  const [resolveOpen, setResolveOpen] = useState(false);

  if (q.isLoading) return <LoadingState label="LOADING INCIDENT" className="h-[60vh]" />;
  if (q.isError || !q.data)
    return (
      <div className="p-4">
        <BackLink />
        <Panel className="mt-3">
          <ErrorState error={q.error} onRetry={() => void q.refetch()} title={undefined} />
        </Panel>
      </div>
    );

  const inc = q.data;
  const resolved = inc.status === "RESOLVED";
  const latestRisk = risk.data?.latest ?? inc.risk_assessment;
  const pending = inc.recommendations.filter((r) => r.status === "PENDING").length;

  return (
    <div className="flex flex-col gap-3 p-4">
      <BackLink />
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-mono text-2xs tracking-[0.3em] text-cyan/70">INC-{shortId(inc.id)}</span>
            <StatusBadge status={inc.status} />
            <LevelBadge level={inc.severity} />
          </div>
          <h1 className="mt-1.5 text-xl font-semibold text-ink">{inc.title}</h1>
          {inc.description && <p className="mt-1 max-w-3xl text-sm text-muted">{inc.description}</p>}
          <p className="mt-1.5 font-mono text-2xs text-dim">
            DETECTED {formatDateTime(inc.detected_at)}
            {inc.resolved_at && ` · RESOLVED ${formatDateTime(inc.resolved_at)}`} · {inc.affected_infrastructure_count} INFRASTRUCTURE ·{" "}
            {inc.affected_services_count} SERVICES
          </p>
        </div>
        {canOperate && !resolved && (
          <div className="flex flex-wrap gap-2">
            <Button
              variant="outline"
              disabled={recalc.isPending}
              onClick={() =>
                recalc.mutate(inc.id, {
                  onSuccess: (r) => toast.ok("Risk recalculated", `${r.level} (${r.score}/100)`),
                  onError: (e) => toast.error("Recalculation failed", errorMessage(e)),
                })
              }
            >
              {recalc.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
              Recalculate risk
            </Button>
            <Button
              variant="outline"
              disabled={analyze.isPending}
              onClick={() =>
                analyze.mutate(inc.id, {
                  onSuccess: (r) =>
                    toast.ok("AI analysis refreshed", `${r.new_recommendations.length} new recommendation(s)`),
                  onError: (e) => toast.error("AI analysis unavailable", errorMessage(e)),
                })
              }
            >
              {analyze.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <BrainCircuit className="h-3.5 w-3.5" />}
              Re-run AI
            </Button>
            <Button variant="success" onClick={() => setResolveOpen(true)}>
              <CheckCircle2 className="h-3.5 w-3.5" /> Resolve incident
            </Button>
          </div>
        )}
      </div>

      {resolved && (
        <div className="flex items-center gap-3 border border-green/40 bg-green-soft/30 px-3 py-2">
          <ShieldCheck className="h-4 w-4 text-green" />
          <span className="font-mono text-xs tracking-wider text-green">INCIDENT RESOLVED</span>
          {inc.resolution_note && <span className="text-sm text-ink/80">“{inc.resolution_note}”</span>}
          <span className="ml-auto font-mono text-2xs text-muted">Affected asset statuses restored by the backend.</span>
        </div>
      )}

      <div className="grid gap-3 xl:grid-cols-[1.2fr,1fr]">
        <Panel title="RISK ASSESSMENT" code="RK" tone={latestRisk && latestRisk.score >= 80 && !resolved ? "crit" : "default"}>
          {latestRisk ? (
            <div className="space-y-4">
              <RiskBlock risk={latestRisk} />
              {risk.data && risk.data.history.length > 1 && (
                <div>
                  <span className="label">RISK HISTORY ({risk.data.history.length})</span>
                  <RiskHistoryChart history={risk.data.history} />
                </div>
              )}
            </div>
          ) : risk.isLoading ? (
            <LoadingState label="LOADING RISK" />
          ) : (
            <EmptyState title="NO RISK ASSESSMENT" />
          )}
        </Panel>
        <Panel title="TRIGGER EVENT" code="EV">
          {inc.event ? (
            <dl className="grid grid-cols-[120px,1fr] gap-x-3 gap-y-2 text-sm">
              <Dt>TYPE</Dt>
              <dd>
                <Badge tone="accent">{humanize(inc.event.event_type)}</Badge>
              </dd>
              <Dt>SEVERITY</Dt>
              <dd>
                <LevelBadge level={inc.event.severity} />
              </dd>
              <Dt>TITLE</Dt>
              <dd className="text-ink">{inc.event.title}</dd>
              <Dt>SOURCE</Dt>
              <dd className="font-mono text-xs text-ink/80">{inc.event.source}</dd>
              <Dt>OCCURRED</Dt>
              <dd className="font-mono text-xs text-ink/80">{formatDateTime(inc.event.occurred_at)}</dd>
              <Dt>LOCATION</Dt>
              <dd className="font-mono text-xs text-ink/80">{formatCoord(inc.event.latitude, inc.event.longitude)}</dd>
              {inc.event.description && (
                <>
                  <Dt>DESCRIPTION</Dt>
                  <dd className="text-xs text-muted">{inc.event.description}</dd>
                </>
              )}
              {Object.keys(inc.event.payload ?? {}).length > 0 && (
                <>
                  <Dt>PAYLOAD</Dt>
                  <dd>
                    <pre className="max-h-40 overflow-auto border border-line bg-bg/60 p-2 font-mono text-2xs text-muted">
                      {JSON.stringify(inc.event.payload, null, 2)}
                    </pre>
                  </dd>
                </>
              )}
            </dl>
          ) : (
            <EmptyState title="EVENT UNAVAILABLE" />
          )}
        </Panel>
      </div>

      <div className="grid gap-3 lg:grid-cols-2">
        <Panel title={`AFFECTED INFRASTRUCTURE (${inc.affected_infrastructure.length})`} code="AI" bodyClassName="px-3 py-1">
          <ImpactList nodes={inc.affected_infrastructure} />
        </Panel>
        <Panel title={`AFFECTED SERVICES (${inc.affected_services.length})`} code="AS" bodyClassName="px-3 py-1">
          <ImpactList nodes={inc.affected_services} />
        </Panel>
      </div>

      <div className="grid gap-3 xl:grid-cols-[1fr,1.1fr]">
        <Panel title="AI ANALYSIS" code="AX">
          {inc.ai_analysis ? (
            <AIAnalysisView analysis={inc.ai_analysis} />
          ) : (
            <EmptyState title="AI ANALYSIS UNAVAILABLE" hint={canOperate ? "Use “Re-run AI” to request an analysis." : undefined} />
          )}
        </Panel>
        <Panel
          title={`HUMAN DECISION · RECOMMENDATIONS (${inc.recommendations.length})`}
          code="HD"
          tone={pending && !resolved ? "warn" : "default"}
          actions={pending > 0 && <Badge tone="warn">{pending} PENDING</Badge>}
          bodyClassName="p-3 space-y-2"
        >
          {inc.recommendations.length === 0 ? (
            <EmptyState title="NO RECOMMENDATIONS" />
          ) : (
            [...inc.recommendations]
              .sort((a, b) => Number(b.status === "PENDING") - Number(a.status === "PENDING"))
              .map((r) => <RecommendationCard key={r.id} rec={r} />)
          )}
        </Panel>
      </div>

      {canOperate && <ResolveDialog incident={inc} open={resolveOpen} onOpenChange={setResolveOpen} />}
    </div>
  );
}

function Dt({ children }: { children: React.ReactNode }) {
  return <dt className="label pt-0.5">{children}</dt>;
}

function BackLink() {
  return (
    <Link href="/command/incidents" className="inline-flex items-center gap-1.5 font-mono text-2xs text-muted hover:text-cyan">
      <ArrowLeft className="h-3 w-3" /> INCIDENTS
    </Link>
  );
}
