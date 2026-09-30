"use client";

import { ShieldCheck, Zap } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { useIncidents } from "@/hooks/use-vaynex";
import { useRole } from "@/hooks/use-session";
import { formatDateTime, shortId } from "@/lib/utils/format";
import { riskTone, TONE_HEX } from "@/lib/utils/status";
import { INCIDENT_STATUSES, LEVELS, type IncidentFilters, type IncidentStatus, type Severity } from "@/types";
import { PageHeader } from "@/components/shell/page-header";
import { Panel } from "@/components/ui/panel";
import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/field";
import { LevelBadge, StatusBadge } from "@/components/ui/badge";
import { EmptyState, QueryView } from "@/components/ui/states";
import { CreateEventDialog } from "@/components/incidents/create-event-dialog";

export default function IncidentsPage() {
  const { canOperate } = useRole();
  const [status, setStatus] = useState<IncidentStatus | "">("");
  const [severity, setSeverity] = useState<Severity | "">("");
  const [activeOnly, setActiveOnly] = useState(false);
  const filters: IncidentFilters = { status, severity, active_only: activeOnly || undefined };
  const q = useIncidents(filters);

  return (
    <div className="p-4">
      <PageHeader
        code="02 · INCIDENTS"
        title="Incident Register"
        subtitle="Incidents detected by the event pipeline, with backend risk scores."
        actions={
          canOperate && (
            <CreateEventDialog
              trigger={(open) => (
                <Button variant="primary" onClick={open}>
                  <Zap className="h-3.5 w-3.5" /> Create Event
                </Button>
              )}
            />
          )
        }
      />
      <Panel
        title={q.data ? `${q.data.total} INCIDENT(S)` : "INCIDENTS"}
        code="IN"
        bodyClassName="p-0"
        actions={
          <div className="flex items-center gap-2">
            <Select value={status} onChange={(e) => setStatus(e.target.value as IncidentStatus | "")} className="h-7 w-36" aria-label="Status">
              <option value="">ALL STATUS</option>
              {INCIDENT_STATUSES.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </Select>
            <Select value={severity} onChange={(e) => setSeverity(e.target.value as Severity | "")} className="h-7 w-36" aria-label="Severity">
              <option value="">ALL SEVERITY</option>
              {LEVELS.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </Select>
            <label className="flex items-center gap-1.5 font-mono text-2xs text-muted">
              <input type="checkbox" className="accent-cyan" checked={activeOnly} onChange={(e) => setActiveOnly(e.target.checked)} />
              ACTIVE ONLY
            </label>
          </div>
        }
      >
        <QueryView
          query={q}
          loadingLabel="LOADING INCIDENTS"
          isEmpty={(d) => d.items.length === 0}
          empty={
            <EmptyState
              title={activeOnly || status || severity ? "NO MATCHING INCIDENTS" : "NO INCIDENTS"}
              hint="Run a simulation or create an event to trigger the pipeline."
              icon={<ShieldCheck className="h-5 w-5 text-green" />}
              className="py-16"
            />
          }
        >
          {(d) => (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-line">
                    {["ID", "TITLE", "SEVERITY", "STATUS", "RISK", "IMPACT", "CREATED"].map((h) => (
                      <th key={h} className="label px-3 py-2 font-normal">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {d.items.map((inc) => (
                    <tr key={inc.id} className="group border-b border-line/60 hover:bg-elevated">
                      <td className="px-3 py-2.5 font-mono text-2xs text-muted">
                        <Link href={`/command/incidents/${inc.id}`} className="hover:text-cyan">
                          INC-{shortId(inc.id)}
                        </Link>
                      </td>
                      <td className="max-w-[420px] px-3 py-2.5">
                        <Link href={`/command/incidents/${inc.id}`} className="block truncate text-ink group-hover:text-cyan">
                          {inc.title}
                        </Link>
                      </td>
                      <td className="px-3 py-2.5">
                        <LevelBadge level={inc.severity} />
                      </td>
                      <td className="px-3 py-2.5">
                        <StatusBadge status={inc.status} />
                      </td>
                      <td className="px-3 py-2.5">
                        {inc.risk ? (
                          <div className="flex items-center gap-2">
                            <span className="num w-7 text-right font-semibold" style={{ color: TONE_HEX[riskTone(inc.risk.score)] }}>
                              {inc.risk.score}
                            </span>
                            <div className="h-1 w-16 bg-elevated">
                              <div className="h-full" style={{ width: `${inc.risk.score}%`, background: TONE_HEX[riskTone(inc.risk.score)] }} />
                            </div>
                          </div>
                        ) : (
                          <span className="text-dim">—</span>
                        )}
                      </td>
                      <td className="px-3 py-2.5 font-mono text-2xs text-muted">
                        {inc.affected_infrastructure_count} INF · {inc.affected_services_count} SVC
                      </td>
                      <td className="px-3 py-2.5 font-mono text-2xs text-muted">{formatDateTime(inc.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </QueryView>
      </Panel>
    </div>
  );
}
