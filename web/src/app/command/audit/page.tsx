"use client";

import { ChevronDown, ScrollText, ShieldAlert } from "lucide-react";
import { useState } from "react";
import { useAudit } from "@/hooks/use-vaynex";
import { useRole, useSession } from "@/hooks/use-session";
import { cn } from "@/lib/utils/cn";
import { formatDateTime, humanize, shortId } from "@/lib/utils/format";
import { AUDIT_ACTIONS, type AuditLog } from "@/types";
import { PageHeader } from "@/components/shell/page-header";
import { Panel } from "@/components/ui/panel";
import { Select } from "@/components/ui/field";
import { EmptyState, QueryView } from "@/components/ui/states";
import { Badge } from "@/components/ui/badge";
import type { Tone } from "@/lib/utils/status";

function actionTone(action: string): Tone {
  if (action.includes("FAILED") || action.includes("REJECTED") || action === "INCIDENT_CREATED") return "crit";
  if (action.includes("RESOLVED") || action.includes("ACCEPTED") || action.includes("COMPLETED")) return "ok";
  if (action.startsWith("AI_") || action === "RISK_CALCULATED") return "accent";
  if (action === "SIMULATION_RUN" || action === "EVENT_CREATED") return "warn";
  if (action.startsWith("RECOMMENDATION")) return "info";
  return "neutral";
}

export default function AuditPage() {
  const { canOperate } = useRole();
  const session = useSession();
  const [action, setAction] = useState("");
  const [entity, setEntity] = useState("");
  const q = useAudit({ action: action || undefined, entity_type: entity || undefined }, canOperate);

  return (
    <div className="flex flex-col gap-3 p-4">
      <PageHeader
        code="08 · AUDIT"
        title="Audit Trail"
        subtitle="Append-only record of every login, pipeline step, AI analysis, operator decision and simulation."
        actions={
          <>
            <Select value={action} onChange={(e) => setAction(e.target.value)} className="h-8 w-60" aria-label="Action">
              <option value="">ALL ACTIONS</option>
              {AUDIT_ACTIONS.map((a) => (
                <option key={a} value={a}>
                  {humanize(a)}
                </option>
              ))}
            </Select>
            <Select value={entity} onChange={(e) => setEntity(e.target.value)} className="h-8 w-44" aria-label="Entity">
              <option value="">ALL ENTITIES</option>
              {["user", "event", "incident", "risk", "recommendation", "simulation", "infrastructure", "service", "dependency", "organization"].map((t) => (
                <option key={t} value={t}>
                  {t.toUpperCase()}
                </option>
              ))}
            </Select>
          </>
        }
      />
      {!canOperate ? (
        <Panel>
          <EmptyState
            title="ACCESS RESTRICTED"
            hint="The audit trail requires the OPERATOR role or higher (backend rule)."
            icon={<ShieldAlert className="h-5 w-5 text-amber" />}
            className="py-16"
          />
        </Panel>
      ) : (
        <Panel title={q.data ? `${q.data.total} ENTRIES` : "ENTRIES"} code="AU" bodyClassName="p-0">
          <QueryView
            query={q}
            loadingLabel="LOADING AUDIT TRAIL"
            isEmpty={(d) => d.items.length === 0}
            empty={<EmptyState title="NO AUDIT ENTRIES" icon={<ScrollText className="h-5 w-5 text-muted" />} className="py-12" />}
          >
            {(d) => (
              <ol className="relative px-4 py-3">
                <span className="absolute bottom-3 left-[26px] top-3 w-px bg-line" />
                {d.items.map((a) => (
                  <AuditRow key={a.id} a={a} me={session?.user.id} meLabel={session?.user.email} />
                ))}
              </ol>
            )}
          </QueryView>
        </Panel>
      )}
    </div>
  );
}

function AuditRow({ a, me, meLabel }: { a: AuditLog; me?: string; meLabel?: string }) {
  const [open, setOpen] = useState(false);
  const tone = actionTone(a.action);
  const hasDetails = Object.keys(a.details ?? {}).length > 0;
  const summary = summarize(a.details);
  return (
    <li className="relative flex gap-3 py-1.5 pl-0">
      <span
        className={cn(
          "relative z-10 mt-2 h-2.5 w-2.5 shrink-0 translate-x-[5px] rotate-45 border",
          tone === "crit" && "border-red bg-red/40",
          tone === "ok" && "border-green bg-green/40",
          tone === "accent" && "border-cyan bg-cyan/40",
          tone === "warn" && "border-amber bg-amber/40",
          tone === "info" && "border-blue bg-blue/40",
          tone === "neutral" && "border-muted bg-elevated",
        )}
      />
      <div className="ml-3 min-w-0 flex-1 border border-line bg-panel/70 px-3 py-2">
        <button className="flex w-full flex-wrap items-center gap-2 text-left" onClick={() => hasDetails && setOpen((o) => !o)}>
          <span className="w-[150px] shrink-0 font-mono text-2xs text-muted">{formatDateTime(a.created_at)}</span>
          <Badge tone={tone}>{a.action}</Badge>
          <span className="font-mono text-2xs text-ink/70">
            {a.entity_type.toUpperCase()}
            {a.entity_id && <span className="text-dim"> · {shortId(a.entity_id)}</span>}
          </span>
          <span className="min-w-0 flex-1 truncate text-xs text-muted">{summary}</span>
          <span className="font-mono text-2xs text-dim">
            {a.user_id ? (a.user_id === me ? meLabel ?? "YOU" : `USER ${shortId(a.user_id)}`) : "SYSTEM"}
          </span>
          {hasDetails && <ChevronDown className={cn("h-3.5 w-3.5 text-dim transition-transform", open && "rotate-180")} />}
        </button>
        {open && (
          <pre className="mt-2 max-h-60 overflow-auto border border-line bg-bg/60 p-2 font-mono text-2xs text-muted">
            {JSON.stringify(a.details, null, 2)}
          </pre>
        )}
      </div>
    </li>
  );
}

function summarize(details: Record<string, unknown>): string {
  const keys = ["title", "scenario", "status", "risk_level", "level", "score", "risk_score", "priority", "provider", "note", "email"];
  const parts: string[] = [];
  for (const k of keys) {
    const v = details?.[k];
    if (v !== undefined && v !== null && v !== "" && typeof v !== "object") parts.push(`${k}: ${String(v)}`);
    if (parts.length >= 3) break;
  }
  return parts.join(" · ");
}
