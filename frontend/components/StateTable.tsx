"use client";

import { useMemo, useState } from "react";

import type { RegionResult } from "@/lib/types";
import { num, pct, shortDataset } from "@/lib/format";
import { regionLabel, regionStateCode } from "@/lib/api";

type Props = { regions: Record<string, RegionResult> };

type SortKey =
  | "label"
  | "people"
  | "rates.all"
  | "rates.child"
  | "rates.senior"
  | "deep_rates.all"
  | "deep_rates.child"
  | "deep_rates.senior";

const COLUMNS: { key: SortKey; label: string; numeric: boolean }[] = [
  { key: "label", label: "State", numeric: false },
  { key: "people", label: "People", numeric: true },
  { key: "rates.all", label: "Poverty", numeric: true },
  { key: "rates.child", label: "Child poverty", numeric: true },
  { key: "rates.senior", label: "Senior poverty", numeric: true },
  { key: "deep_rates.all", label: "Deep poverty", numeric: true },
  { key: "deep_rates.child", label: "Deep child", numeric: true },
  { key: "deep_rates.senior", label: "Deep senior", numeric: true },
];

function pluck(r: RegionResult, key: SortKey): number | string {
  switch (key) {
    case "label": return regionLabel(r.region_code);
    case "people": return r.people;
    case "rates.all": return r.rates.all;
    case "rates.child": return r.rates.child;
    case "rates.senior": return r.rates.senior;
    case "deep_rates.all": return r.deep_rates.all;
    case "deep_rates.child": return r.deep_rates.child;
    case "deep_rates.senior": return r.deep_rates.senior;
  }
}

export function StateTable({ regions }: Props) {
  const [sortKey, setSortKey] = useState<SortKey>("rates.child");
  const [desc, setDesc] = useState(true);

  const rows = useMemo(() => {
    const states = Object.values(regions).filter((r) => r.region_code !== "us");
    return states.sort((a, b) => {
      const av = pluck(a, sortKey);
      const bv = pluck(b, sortKey);
      if (typeof av === "number" && typeof bv === "number") {
        return desc ? bv - av : av - bv;
      }
      return desc
        ? String(bv).localeCompare(String(av))
        : String(av).localeCompare(String(bv));
    });
  }, [regions, sortKey, desc]);

  if (rows.length === 0) {
    return (
      <div className="rounded-lg border border-secondary-200 bg-white p-6 text-secondary-500 shadow-sm">
        No state results yet — run “Recompute”.
      </div>
    );
  }

  function clickHeader(key: SortKey) {
    if (key === sortKey) {
      setDesc((d) => !d);
    } else {
      setSortKey(key);
      setDesc(true);
    }
  }

  return (
    <div className="overflow-hidden rounded-lg border border-secondary-200 bg-white shadow-sm">
      <table className="min-w-full text-sm">
        <thead className="bg-secondary-100 text-left">
          <tr>
            {COLUMNS.map((col) => (
              <th
                key={col.key}
                onClick={() => clickHeader(col.key)}
                className={`cursor-pointer px-4 py-3 text-xs font-medium uppercase tracking-wider text-secondary-700 hover:text-secondary-900 ${
                  col.numeric ? "text-right" : ""
                }`}
              >
                {col.label}
                {sortKey === col.key && (
                  <span className="ml-1 text-secondary-500">{desc ? "↓" : "↑"}</span>
                )}
              </th>
            ))}
            <th className="px-4 py-3 text-xs font-medium uppercase tracking-wider text-secondary-700">
              Dataset
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-secondary-200">
          {rows.map((r) => (
            <tr key={r.region_code} className="hover:bg-secondary-100/50">
              <td className="px-4 py-2 font-medium text-secondary-900">
                <span className="mr-2 inline-block w-8 font-mono text-xs text-secondary-500">
                  {regionStateCode(r.region_code)}
                </span>
                {regionLabel(r.region_code)}
              </td>
              <td className="px-4 py-2 text-right tabular-nums">{num(r.people)}</td>
              <td className="px-4 py-2 text-right tabular-nums">{pct(r.rates.all)}</td>
              <td className="px-4 py-2 text-right tabular-nums font-medium">{pct(r.rates.child)}</td>
              <td className="px-4 py-2 text-right tabular-nums font-medium">{pct(r.rates.senior)}</td>
              <td className="px-4 py-2 text-right tabular-nums">{pct(r.deep_rates.all)}</td>
              <td className="px-4 py-2 text-right tabular-nums">{pct(r.deep_rates.child)}</td>
              <td className="px-4 py-2 text-right tabular-nums">{pct(r.deep_rates.senior)}</td>
              <td className="px-4 py-2 font-mono text-xs text-secondary-500">
                {shortDataset(r.dataset_path)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
