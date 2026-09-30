"use client";

import { BrainCircuit, Cloud, Cpu, Loader2, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useAnalyzeIncident, useIncident, useIncidents, useProvider } from "@/hooks/use-vaynex";
import { useRole } from "@/hooks/use-session";
import { errorMessage } from "@/lib/api/errors";
import { cn } from "@/lib/utils/cn";
import { shortId, timeAgo } from "@/lib/utils/format";
import { useUI } from "@/store/ui";
import type { AnalyzeIncidentResponse } from "@/types";
import { PageHeader } from "@/components/shell/page-header";
import { Panel } from "@/components/ui/panel";
import { Button } from "@/components/ui/button";
import { Badge, LevelBadge, StatusBadge } from "@/components/ui/badge";
import { EmptyState, ErrorState, LoadingState, QueryView } from "@/components/ui/states";
import { toast } from "@/components/ui/toast";
import { AIAnalysisView } from "@/components/intelligence/ai-analysis";
import { PipelineRail, type Stage } from "@/components/intelligence/pipeline-rail";
import { RecommendationCard } from "@/components/recommendations/recommendation-card";
import { RiskGauge } from "@/components/incidents/risk";

const AI_STAGES = [
  "EVENT_CREATED",
  "INFRASTRUCTURE_CONTEXT",
  "DEPENDENCIES_ANALYZED",
  "RISK_ASSESSED",
  "AI_ANALYSIS",
  "RECOMMENDATIONS",
  "HUMAN_DECISION",
  "AUDIT",
] as const;
const AI_INDEX = AI_STAGES.indexOf("AI_ANALYSIS");

export default function IntelligencePage() {
  const { canOperate } = useRole();
  const provider = useProvider();
  const incidents = useIncidents({ limit: 100 });
  const selectedId = useUI((s) => s.selectedIncidentId);
  const selectIncident = useUI((s) => s.selectIncident);
  const incident = useIncident(selectedId);
  const analyze = useAnalyzeIncident();
  const [fresh, setFresh] = useState<AnalyzeIncidentResponse | null>(null);
  const [animStep, setAnimStep] = useState<number | null>(null);

  // Default to the most recent active incident.
  useEffect(() => {
    if (selectedId || !incidents.data?.items.length) return;
    const first = incidents.data.items.find((i) => i.status !== "RESOLVED") ?? incidents.data.items[0];
    selectIncident(first.id);
  }, [incidents.data, selectedId, selectIncident]);

  // Illuminate stages up to AI ANALYSIS while the request is in flight.
  useEffect(() => {
    if (!analyze.isPending) return;
    setAnimStep(0);
    const id = setInterval(() => setAnimStep((s) => (s === null ? 0 : Math.min(AI_INDEX, s + 1))), 380);
    return () => clearInterval(id);
  }, [analyze.isPending]);

  const inc = incident.data;
  const analysis = fresh && fresh.incident_id === selectedId ? fresh.ai_analysis : inc?.ai_analysis ?? null;
  const pending = inc?.recommendations.filter((r) => r.status === "PENDING").length ?? 0;
  const decided = inc?.recommendations.some((r) => r.status !== "PENDING") ?? false;

  const stages: Stage[] = useMemo(() => {
    const doneUntil =
      analyze.isPending && animStep !== null
        ? animStep
        : !inc
          ? -1
          : !analysis
            ? AI_INDEX
            : pending > 0
              ? AI_STAGES.indexOf("HUMAN_DECISION")
              : AI_STAGES.length;
    return AI_STAGES.map((k, i) => ({
      key: k,
      label: "",
      status: i < doneUntil ? "done" : i === doneUntil ? "active" : "pending",
      detail:
        k === "HUMAN_DECISION" && inc
          ? pending > 0
            ? `${pending} recommendation(s) awaiting operator`
            : decided
              ? "Operator decisions recorded"
              : undefined
          : k === "AI_ANALYSIS" && analysis
            ? `${analysis.provider} · confidence ${Math.round(analysis.confidence * 100)}%`
            : k === "RISK_ASSESSED" && inc?.risk
              ? `${inc.risk.level} (${inc.risk.score}/100)`
              : undefined,
    }));
  }, [analyze.isPending, animStep, inc, analysis, pending, decided]);

  function run() {
    if (!selectedId) return;
    analyze.mutate(selectedId, {
      onSuccess: (res) => {
        setFresh(res);
        setAnimStep(null);
        toast.ok("AI analysis complete", `${res.new_recommendations.length} new recommendation(s)`);
      },
      onError: (e) => {
        setAnimStep(null);
        toast.error("AI analysis unavailable", errorMessage(e));
      },
    });
  }

  return (
    <div className="flex flex-col gap-3 p-4">
      <PageHeader
        code="04 · INTELLIGENCE"
        title="AI Intelligence"
        subtitle="AI analysis of incidents from sanitised operational context. Output is advisory only — recommendations always require a human decision."
      />

      <div className="grid gap-3 lg:grid-cols-[300px,1fr]">
        <div className="flex flex-col gap-3">
          <Panel title="AI PROVIDER" code="AP">
            {provider.isLoading ? (
              <LoadingState label="QUERYING PROVIDER" />
            ) : provider.isError || !provider.data ? (
              <ErrorState error={provider.error} title="AI ANALYSIS UNAVAILABLE" onRetry={() => void provider.refetch()} />
            ) : (
              <div className="space-y-2">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center border border-cyan/40 bg-cyan/10">
                    {provider.data.external ? <Cloud className="h-5 w-5 text-cyan" /> : <Cpu className="h-5 w-5 text-cyan" />}
                  </div>
                  <div>
                    <div className="font-mono text-sm uppercase tracking-wider text-ink">{provider.data.provider}</div>
                    <div className="font-mono text-2xs text-muted">MODEL {provider.data.model ?? "—"}</div>
                  </div>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  <Badge tone={provider.data.external ? "info" : "neutral"}>{provider.data.external ? "EXTERNAL LLM" : "LOCAL / DETERMINISTIC"}</Badge>
                  <Badge tone="warn">
                    <ShieldCheck className="h-3 w-3" /> ADVISORY ONLY
                  </Badge>
                </div>
              </div>
            )}
          </Panel>

          <Panel title="INCIDENTS" code="IN" bodyClassName="p-0 overflow-y-auto max-h-[520px]">
            <QueryView
              query={incidents}
              loadingLabel="LOADING INCIDENTS"
              isEmpty={(d) => d.items.length === 0}
              empty={<EmptyState title="NO INCIDENTS" hint="Run a simulation to generate one." className="py-10" />}
            >
              {(d) => (
                <ul className="divide-y divide-line">
                  {d.items.map((i) => (
                    <li key={i.id}>
                      <button
                        onClick={() => {
                          setFresh(null);
                          selectIncident(i.id);
                        }}
                        className={cn(
                          "w-full px-3 py-2 text-left hover:bg-elevated",
                          i.id === selectedId && "bg-cyan/5 shadow-[inset_2px_0_0_#22D3EE]",
                        )}
                      >
                        <div className="flex items-center gap-1.5">
                          <span className="font-mono text-2xs text-dim">INC-{shortId(i.id)}</span>
                          <span className="ml-auto font-mono text-2xs text-dim">{timeAgo(i.detected_at)}</span>
                        </div>
                        <p className="truncate text-sm text-ink">{i.title}</p>
                        <div className="mt-1 flex gap-1.5">
                          <LevelBadge level={i.severity} />
                          <StatusBadge status={i.status} />
                        </div>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </QueryView>
          </Panel>
        </div>

        <div className="flex min-w-0 flex-col gap-3">
          <Panel title="AI DECISION PIPELINE" code="PL" tone={analyze.isPending ? "accent" : "default"}>
            <PipelineRail stages={stages} orientation="horizontal" />
          </Panel>

          {!selectedId ? (
            <Panel>
              <EmptyState title="SELECT AN INCIDENT" className="py-16" />
            </Panel>
          ) : incident.isLoading ? (
            <Panel>
              <LoadingState label="LOADING INCIDENT CONTEXT" />
            </Panel>
          ) : incident.isError || !inc ? (
            <Panel>
              <ErrorState error={incident.error} onRetry={() => void incident.refetch()} />
            </Panel>
          ) : (
            <>
              <Panel
                title="INCIDENT CONTEXT"
                code="CX"
                actions={
                  canOperate &&
                  inc.status !== "RESOLVED" && (
                    <Button size="sm" variant="primary" onClick={run} disabled={analyze.isPending}>
                      {analyze.isPending ? <Loader2 className="h-3 w-3 animate-spin" /> : <BrainCircuit className="h-3 w-3" />}
                      {analyze.isPending ? "Analysing" : "Run AI analysis"}
                    </Button>
                  )
                }
              >
                <div className="flex flex-wrap items-center gap-4">
                  {inc.risk && <RiskGauge score={inc.risk.score} level={inc.risk.level} size={112} />}
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap gap-1.5">
                      <StatusBadge status={inc.status} />
                      <LevelBadge level={inc.severity} />
                    </div>
                    <Link href={`/command/incidents/${inc.id}`} className="mt-1 block text-lg font-semibold text-ink hover:text-cyan">
                      {inc.title}
                    </Link>
                    <p className="mt-1 font-mono text-2xs text-muted">
                      {inc.affected_infrastructure_count} INFRASTRUCTURE · {inc.affected_services_count} SERVICES · EVENT{" "}
                      {inc.event?.event_type ?? "—"}
                    </p>
                  </div>
                </div>
              </Panel>
              <Panel title="AI ASSESSMENT" code="AX" tone={analyze.isPending ? "accent" : "default"}>
                {analyze.isPending ? (
                  <LoadingState label="AI ANALYSIS IN PROGRESS" />
                ) : analysis ? (
                  <AIAnalysisView analysis={analysis} />
                ) : (
                  <EmptyState title="AI ANALYSIS UNAVAILABLE" hint={canOperate ? "Run an analysis for this incident." : undefined} />
                )}
              </Panel>
              {fresh && fresh.incident_id === selectedId && fresh.new_recommendations.length > 0 && (
                <Panel title={`NEW RECOMMENDATIONS (${fresh.new_recommendations.length})`} code="NR" bodyClassName="p-3 space-y-2">
                  {fresh.new_recommendations.map((r) => (
                    <RecommendationCard key={r.id} rec={inc.recommendations.find((x) => x.id === r.id) ?? r} />
                  ))}
                </Panel>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
