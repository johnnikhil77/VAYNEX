"use client";

import { Search } from "lucide-react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Suspense, useDeferredValue, useState } from "react";
import { useInfrastructureList, useOrganizations } from "@/hooks/use-vaynex";
import { cn } from "@/lib/utils/cn";
import { formatCoord, humanize } from "@/lib/utils/format";
import {
  INFRASTRUCTURE_STATUSES,
  INFRASTRUCTURE_TYPES,
  LEVELS,
  type Criticality,
  type InfrastructureStatus,
  type InfrastructureType,
} from "@/types";
import { PageHeader } from "@/components/shell/page-header";
import { Panel } from "@/components/ui/panel";
import { Input, Select } from "@/components/ui/field";
import { LevelBadge, StatusBadge } from "@/components/ui/badge";
import { EmptyState, LoadingState, QueryView } from "@/components/ui/states";
import { GeoGrid } from "@/components/infrastructure/geo-grid";
import { InfrastructureDetail } from "@/components/infrastructure/infrastructure-detail";

export default function InfrastructurePage() {
  return (
    <Suspense fallback={<LoadingState label="LOADING INFRASTRUCTURE" />}>
      <InfrastructureScreen />
    </Suspense>
  );
}

function InfrastructureScreen() {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const selectedId = params.get("id");

  const [org, setOrg] = useState("");
  const [type, setType] = useState<InfrastructureType | "">("");
  const [status, setStatus] = useState<InfrastructureStatus | "">("");
  const [criticality, setCriticality] = useState<Criticality | "">("");
  const [search, setSearch] = useState("");
  const deferredSearch = useDeferredValue(search.trim());

  const orgs = useOrganizations();
  const q = useInfrastructureList({ organization_id: org, type, status, criticality, search: deferredSearch || undefined });

  const select = (id: string | null) => {
    const sp = new URLSearchParams(params.toString());
    if (id) sp.set("id", id);
    else sp.delete("id");
    router.replace(`${pathname}${sp.toString() ? `?${sp}` : ""}`, { scroll: false });
  };

  return (
    <div className="p-4">
      <PageHeader
        code="03 · INFRASTRUCTURE"
        title="Infrastructure Registry"
        subtitle="Critical assets with live status, criticality and real coordinates. Select an asset for its dependency dossier."
      />
      <div className="mb-3 flex flex-wrap items-center gap-2 border border-line bg-panel/80 p-2">
        <div className="relative w-64">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-dim" />
          <Input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search name…" maxLength={100} className="pl-8" aria-label="Search" />
        </div>
        <Select value={org} onChange={(e) => setOrg(e.target.value)} className="w-56" aria-label="Organization">
          <option value="">ALL ORGANIZATIONS</option>
          {orgs.data?.items.map((o) => (
            <option key={o.id} value={o.id}>
              {o.name}
            </option>
          ))}
        </Select>
        <Select value={type} onChange={(e) => setType(e.target.value as InfrastructureType | "")} className="w-48" aria-label="Type">
          <option value="">ALL TYPES</option>
          {INFRASTRUCTURE_TYPES.map((t) => (
            <option key={t} value={t}>
              {humanize(t)}
            </option>
          ))}
        </Select>
        <Select value={status} onChange={(e) => setStatus(e.target.value as InfrastructureStatus | "")} className="w-40" aria-label="Status">
          <option value="">ALL STATUS</option>
          {INFRASTRUCTURE_STATUSES.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </Select>
        <Select value={criticality} onChange={(e) => setCriticality(e.target.value as Criticality | "")} className="w-40" aria-label="Criticality">
          <option value="">ALL CRITICALITY</option>
          {LEVELS.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </Select>
        {q.data && <span className="ml-auto font-mono text-2xs text-muted">{q.data.total} ASSET(S)</span>}
      </div>

      <div className={cn("grid gap-3", selectedId ? "xl:grid-cols-[1fr,440px]" : "grid-cols-1")}>
        <div className="flex min-w-0 flex-col gap-3">
          <Panel title="ASSETS" code="AS" bodyClassName="p-0">
            <QueryView
              query={q}
              loadingLabel="LOADING INFRASTRUCTURE"
              isEmpty={(d) => d.items.length === 0}
              empty={<EmptyState title="NO MATCHING INFRASTRUCTURE" className="py-12" />}
            >
              {(d) => (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead>
                      <tr className="border-b border-line">
                        {["NAME", "TYPE", "STATUS", "CRITICALITY", "LOCATION"].map((h) => (
                          <th key={h} className="label px-3 py-2 font-normal">
                            {h}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {d.items.map((i) => (
                        <tr
                          key={i.id}
                          onClick={() => select(i.id)}
                          className={cn(
                            "cursor-pointer border-b border-line/60 hover:bg-elevated",
                            selectedId === i.id && "bg-cyan/5",
                          )}
                        >
                          <td className="px-3 py-2.5 text-ink">
                            {selectedId === i.id && <span className="mr-2 inline-block h-2 w-[2px] bg-cyan align-middle" />}
                            {i.name}
                          </td>
                          <td className="px-3 py-2.5 font-mono text-2xs text-muted">{humanize(i.infrastructure_type)}</td>
                          <td className="px-3 py-2.5">
                            <StatusBadge status={i.status} />
                          </td>
                          <td className="px-3 py-2.5">
                            <LevelBadge level={i.criticality} />
                          </td>
                          <td className="px-3 py-2.5 font-mono text-2xs text-muted">{formatCoord(i.latitude, i.longitude)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </QueryView>
          </Panel>
          <Panel title="GEOSPATIAL GRID · WGS84" code="GEO" bodyClassName="p-2 h-[380px]">
            {q.data ? (
              <GeoGrid items={q.data.items} selectedId={selectedId} onSelect={(id) => select(id)} />
            ) : (
              <LoadingState label="PLOTTING COORDINATES" />
            )}
          </Panel>
        </div>
        {selectedId && (
          <div className="xl:sticky xl:top-4 xl:max-h-[calc(100vh-140px)]">
            <InfrastructureDetail id={selectedId} onClose={() => select(null)} />
          </div>
        )}
      </div>
    </div>
  );
}
