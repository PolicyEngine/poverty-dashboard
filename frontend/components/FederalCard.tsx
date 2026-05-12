"use client";

import type { RegionResult } from "@/lib/types";
import { num, pct, shortDataset } from "@/lib/format";

type Props = { federal: RegionResult | undefined };

function Stat({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div>
      <div className="text-xs uppercase tracking-wider text-secondary-500">{label}</div>
      <div className="mt-1 text-3xl font-semibold text-secondary-900">{value}</div>
      {sub && <div className="text-xs text-secondary-500">{sub}</div>}
    </div>
  );
}

export function FederalCard({ federal }: Props) {
  if (!federal) {
    return (
      <div className="rounded-lg border border-secondary-200 bg-white p-6 text-secondary-500 shadow-sm">
        No federal baseline yet — run “Recompute”.
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-secondary-200 bg-white p-6 shadow-sm">
      <div className="flex items-baseline justify-between">
        <h2 className="text-xl font-semibold text-secondary-900">United States · 2026 baseline</h2>
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
    </div>
  );
}
