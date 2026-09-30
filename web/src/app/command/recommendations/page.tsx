"use client";

import { Bot, ClipboardCheck, Cpu, ScrollText, UserCheck } from "lucide-react";
import { useState } from "react";
import { useRecommendations } from "@/hooks/use-vaynex";
import { useRole } from "@/hooks/use-session";
import { cn } from "@/lib/utils/cn";
import {
  LEVELS,
  RECOMMENDATION_STATUSES,
  type RecommendationPriority,
  type RecommendationSource,
  type RecommendationStatus,
} from "@/types";
import { PageHeader } from "@/components/shell/page-header";
import { Panel } from "@/components/ui/panel";
import { Select } from "@/components/ui/field";
import { EmptyState, QueryView } from "@/components/ui/states";
import { RecommendationCard } from "@/components/recommendations/recommendation-card";

const PRIORITY_ORDER: Record<string, number> = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3 };

export default function RecommendationsPage() {
  const { canOperate } = useRole();
  const [status, setStatus] = useState<RecommendationStatus | "">("PENDING");
  const [source, setSource] = useState<RecommendationSource | "">("");
  const [priority, setPriority] = useState<RecommendationPriority | "">("");
  const q = useRecommendations({ status, source, priority });
  const all = useRecommendations({});
  const counts = RECOMMENDATION_STATUSES.map((s) => ({
    s,
    n: all.data?.items.filter((r) => r.status === s).length ?? 0,
  }));

  return (
    <div className="flex flex-col gap-3 p-4">
      <PageHeader
        code="07 · RECOMMENDATIONS"
        title="Operator Decisions"
        subtitle="Rule-engine and AI recommendations. Nothing is executed automatically — an authorized operator accepts, rejects or completes each one, and every decision is audited."
      />

      <HumanLoop />

      <div className="flex flex-wrap items-center gap-2">
        {[{ s: "" as const, n: all.data?.total ?? 0 }, ...counts].map(({ s, n }) => (
          <button
            key={s || "ALL"}
            onClick={() => setStatus(s)}
            className={cn(
              "flex items-center gap-2 border px-3 py-1.5 font-mono text-2xs uppercase tracking-wider",
              status === s ? "border-cyan/60 bg-cyan/10 text-cyan" : "border-line text-muted hover:text-ink",
            )}
          >
            {s || "ALL"} <span className="num text-ink">{n}</span>
          </button>
        ))}
        <div className="ml-auto flex gap-2">
          <Select value={source} onChange={(e) => setSource(e.target.value as RecommendationSource | "")} className="h-8 w-40" aria-label="Source">
            <option value="">ALL SOURCES</option>
            <option value="RULE_ENGINE">RULE ENGINE</option>
            <option value="AI">AI</option>
          </Select>
          <Select value={priority} onChange={(e) => setPriority(e.target.value as RecommendationPriority | "")} className="h-8 w-40" aria-label="Priority">
            <option value="">ALL PRIORITIES</option>
            {LEVELS.map((l) => (
              <option key={l} value={l}>
                {l}
              </option>
            ))}
          </Select>
        </div>
      </div>

      {!canOperate && (
        <p className="border border-amber/40 bg-amber-soft/30 px-3 py-2 font-mono text-xs text-amber">
          VIEWER ROLE — decisions require OPERATOR or ADMIN.
        </p>
      )}

      <Panel title="QUEUE" code="Q" bodyClassName="p-3">
        <QueryView
          query={q}
          loadingLabel="LOADING RECOMMENDATIONS"
          isEmpty={(d) => d.items.length === 0}
          empty={
            <EmptyState
              title={status === "PENDING" ? "NO PENDING DECISIONS" : "NO RECOMMENDATIONS"}
              hint="Recommendations are generated when the pipeline detects an incident."
              icon={<ClipboardCheck className="h-5 w-5 text-green" />}
              className="py-12"
            />
          }
        >
          {(d) => (
            <div className="grid gap-2 xl:grid-cols-2">
              {[...d.items]
                .sort(
                  (a, b) =>
                    (PRIORITY_ORDER[a.priority] ?? 9) - (PRIORITY_ORDER[b.priority] ?? 9) ||
                    new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
                )
                .map((r) => (
                  <RecommendationCard key={r.id} rec={r} showIncident />
                ))}
            </div>
          )}
        </QueryView>
      </Panel>
    </div>
  );
}

function HumanLoop() {
  const steps = [
    { icon: Bot, t: "AI / RULE RECOMMENDATION", d: "Generated from risk, dependencies and AI analysis" },
    { icon: UserCheck, t: "HUMAN REVIEW", d: "Authorized operator evaluates context" },
    { icon: Cpu, t: "ACCEPT OR REJECT", d: "Decision + optional note; ACCEPTED → COMPLETED" },
    { icon: ScrollText, t: "AUDIT", d: "Decision, operator and time recorded" },
  ];
  return (
    <div className="grid gap-px border border-line bg-line md:grid-cols-4">
      {steps.map((s, i) => (
        <div key={s.t} className="flex items-start gap-3 bg-panel px-3 py-2.5">
          <span className="num text-2xs text-cyan/60">{String(i + 1).padStart(2, "0")}</span>
          <s.icon className="mt-0.5 h-4 w-4 shrink-0 text-cyan" />
          <div>
            <div className="font-mono text-2xs tracking-[0.16em] text-ink">{s.t}</div>
            <div className="text-2xs text-muted">{s.d}</div>
          </div>
        </div>
      ))}
    </div>
  );
}
