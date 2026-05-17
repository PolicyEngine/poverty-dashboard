"use client";

import type { CensusSpmReport, RegionResult } from "@/lib/types";
import { num, pct, shortDataset } from "@/lib/format";

type Props = {
  federal: RegionResult | undefined;
  year: number;
  census: CensusSpmReport | null;
};

function Stat({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div>
      <div className="text-xs uppercase tracking-wider text-secondary-500">{label}</div>
      <div className="mt-1 text-3xl font-semibold text-secondary-900">{value}</div>
      {sub && <div className="text-xs text-secondary-500">{sub}</div>}
    </div>
  );
}

const GROUPS: {
  key: "all" | "child" | "working_age" | "senior";
  label: string;
}[] = [
  { key: "all", label: "All people" },
  { key: "child", label: "Under 18" },
  { key: "working_age", label: "18 to 64" },
  { key: "senior", label: "65+" },
];

function policyEngineRate(
  federal: RegionResult | undefined,
  key: "all" | "child" | "working_age" | "senior",
): number | undefined {
  return federal?.rates[key];
}

function CensusComparison({
  census,
  federal,
  year,
}: {
  census: CensusSpmReport | null;
  federal: RegionResult | undefined;
  year: number;
}) {
  if (!census || year !== census.report_year) return null;

  return (
    <div className="mt-6 overflow-hidden rounded-md border border-secondary-200">
      <div className="flex flex-wrap items-baseline justify-between gap-2 border-b border-secondary-200 bg-secondary-100 px-4 py-3">
        <h3 className="text-sm font-semibold text-secondary-900">
          Census 2024 SPM comparison
        </h3>
        <a
          href={census.sources.tables_page}
          target="_blank"
          rel="noreferrer"
          className="text-xs font-medium text-primary-700 hover:text-primary-900"
        >
          Census tables
        </a>
      </div>
      <table className="min-w-full text-sm">
        <thead className="bg-white text-left">
          <tr>
            <th className="px-4 py-2 text-xs font-medium uppercase tracking-wider text-secondary-700">
              Group
            </th>
            <th className="px-4 py-2 text-right text-xs font-medium uppercase tracking-wider text-secondary-700">
              Census 2024
            </th>
            <th className="px-4 py-2 text-right text-xs font-medium uppercase tracking-wider text-secondary-700">
              PolicyEngine {year}
            </th>
            <th className="px-4 py-2 text-right text-xs font-medium uppercase tracking-wider text-secondary-700">
              Gap
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-secondary-200">
          {GROUPS.map((group) => {
            const censusRate = census.national[group.key].rate;
            const peRate = policyEngineRate(federal, group.key);
            const gap = peRate === undefined ? undefined : peRate - censusRate;
            return (
              <tr key={group.key}>
                <td className="px-4 py-2 font-medium text-secondary-900">
                  {group.label}
                </td>
                <td className="px-4 py-2 text-right tabular-nums">
                  {pct(censusRate)}
                </td>
                <td className="px-4 py-2 text-right tabular-nums">
                  {pct(peRate)}
                </td>
                <td className="px-4 py-2 text-right tabular-nums font-medium">
                  {gap === undefined ? "—" : `${(gap * 100).toFixed(1)} pp`}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export function FederalCard({ federal, year, census }: Props) {
  if (!federal) {
    return (
      <div className="rounded-lg border border-secondary-200 bg-white p-6 text-secondary-500 shadow-sm">
        <div>No federal baseline for {year} yet — run “Recompute {year}”.</div>
        <CensusComparison census={census} federal={federal} year={year} />
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-secondary-200 bg-white p-6 shadow-sm">
      <div className="flex items-baseline justify-between">
        <h2 className="text-xl font-semibold text-secondary-900">
          United States · {year} baseline
        </h2>
        <span className="font-mono text-xs text-secondary-500">
          {shortDataset(federal.dataset_path)}
        </span>
      </div>

      <div className="mt-6 grid grid-cols-2 gap-6 sm:grid-cols-4">
        <Stat label="Poverty rate" value={pct(federal.rates.all)} sub={`${num(federal.people)} people`} />
        <Stat label="Child poverty" value={pct(federal.rates.child)} sub={`${num(federal.child_count)} children`} />
        <Stat label="Working-age poverty" value={pct(federal.rates.working_age)} />
        <Stat label="Senior poverty" value={pct(federal.rates.senior)} />
      </div>

      <div className="mt-6 grid grid-cols-2 gap-6 border-t border-secondary-200 pt-6 sm:grid-cols-4">
        <Stat label="Deep poverty" value={pct(federal.deep_rates.all)} />
        <Stat label="Deep child poverty" value={pct(federal.deep_rates.child)} />
        <Stat label="Deep working-age" value={pct(federal.deep_rates.working_age)} />
        <Stat label="Deep senior" value={pct(federal.deep_rates.senior)} />
      </div>

      <CensusComparison census={census} federal={federal} year={year} />
    </div>
  );
}
