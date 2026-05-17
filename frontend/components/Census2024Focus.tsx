"use client";

import type {
  CensusSpmReport,
  RawSpmResourceFormulaComponent,
  SpmGapDiagnostics,
  TotalIncomeLeafDiagnostics,
} from "@/lib/types";
import { dollars, num, pct, shortDataset } from "@/lib/format";

type Props = {
  census: CensusSpmReport | null;
  diagnostics: SpmGapDiagnostics | null;
};

type InputGapRow = {
  key: string;
  label: string;
  source: string;
  rawMean: number;
  peMean: number | null;
  difference: number | null;
  variables: string[];
};

function pp(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return `${(value * 100).toFixed(digits)} pp`;
}

function leafRow(
  totalIncome: TotalIncomeLeafDiagnostics | undefined,
  key: string,
): InputGapRow | null {
  const row = totalIncome?.component_mean_gaps.find((item) => item.key === key);
  if (!row) return null;
  return {
    key: row.key,
    label: row.label,
    source: row.raw_columns.join(" + "),
    rawMean: row.raw_mean,
    peMean: row.enhanced_mean,
    difference: row.difference,
    variables: row.enhanced_variables,
  };
}

function formulaRow(
  totalIncome: TotalIncomeLeafDiagnostics | undefined,
  key: string,
): InputGapRow | null {
  const row = totalIncome?.spm_resource_formula?.components.find(
    (item: RawSpmResourceFormulaComponent) => item.key === key,
  );
  if (!row) return null;
  return {
    key: row.key,
    label: row.label,
    source: row.raw_columns.join(" + "),
    rawMean: row.raw_mean,
    peMean: row.enhanced_mean,
    difference: row.difference,
    variables: row.enhanced_variables,
  };
}

function Stat({
  label,
  value,
  sub,
}: {
  label: string;
  value: string;
  sub?: string;
}) {
  return (
    <div className="bg-white p-4">
      <div className="text-xs uppercase tracking-wider text-secondary-500">
        {label}
      </div>
      <div className="mt-1 text-2xl font-semibold text-secondary-900">
        {value}
      </div>
      {sub ? <div className="text-xs text-secondary-500">{sub}</div> : null}
    </div>
  );
}

export function Census2024Focus({ census, diagnostics }: Props) {
  if (!census || !diagnostics) return null;

  const totalIncome = diagnostics.total_income_leaf_diagnostics;
  const gap = diagnostics.gap_accounting;
  const pe2024 = diagnostics.policyengine_2024_checks[0];
  const rawControl =
    diagnostics.source_replication_diagnostics?.sources.raw_cps_asec;
  const enhancedDataset =
    diagnostics.source_replication_diagnostics?.sources.enhanced_cps.dataset_path;
  const inputGapRows = [
    leafRow(totalIncome, "pension_income"),
    formulaRow(totalIncome, "housing_subsidy"),
    formulaRow(totalIncome, "energy_assistance"),
  ].filter((row): row is InputGapRow => row !== null);

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold text-secondary-900">
            2024 Census SPM comparison
          </h2>
          <div className="text-sm text-secondary-600">
            Main view for reconciling PolicyEngine 2024 SPM-like results with Census P60-287.
          </div>
        </div>
        <a
          href={census.sources.tables_page}
          target="_blank"
          rel="noreferrer"
          className="text-sm font-medium text-primary-700 hover:text-primary-900"
        >
          Census report tables
        </a>
      </div>

      {gap ? (
        <div className="overflow-hidden rounded-lg border border-secondary-200 bg-white shadow-sm">
          <div className="grid gap-px bg-secondary-200 text-sm md:grid-cols-4">
            <Stat
              label="Census SPM"
              value={pct(gap.census_rate)}
              sub={`${num(census.national.all.poverty_count)} people`}
            />
            <Stat
              label="PE modeled"
              value={pct(gap.policyengine_modeled_rate)}
              sub={`${pp(gap.policyengine_modeled_gap)} vs Census`}
            />
            <Stat
              label="PE + omitted rows"
              value={pct(gap.modeled_plus_omitted_rate)}
              sub={`${pp(gap.remaining_gap_after_omitted_resources)} gap remains`}
            />
            <Stat
              label="Raw CPS control"
              value={pct(gap.raw_cps_reported_rate)}
              sub={
                gap.raw_cps_reported_gap === null
                  ? undefined
                  : `${pp(gap.raw_cps_reported_gap)} vs Census`
              }
            />
          </div>
        </div>
      ) : (
        <div className="overflow-hidden rounded-lg border border-secondary-200 bg-white shadow-sm">
          <div className="grid gap-px bg-secondary-200 text-sm md:grid-cols-4">
            <Stat
              label="Census SPM"
              value={pct(census.national.all.rate)}
              sub={`${num(census.national.all.poverty_count)} people`}
            />
            <Stat label="PE modeled" value={pct(pe2024?.all)} />
          </div>
        </div>
      )}

      <div className="overflow-hidden rounded-lg border border-secondary-200 bg-white shadow-sm">
        <div className="border-b border-secondary-200 bg-secondary-100 px-4 py-3">
          <div className="text-sm font-semibold text-secondary-900">
            Current ECPS input gaps
          </div>
          <div className="text-xs text-secondary-600">
            Raw Census means compared with current PE ECPS inputs
            {enhancedDataset ? ` (${shortDataset(enhancedDataset)})` : ""}.
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="bg-white">
              <tr>
                <th className="px-4 py-2 text-left text-xs font-medium uppercase tracking-wider text-secondary-700">
                  Component
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium uppercase tracking-wider text-secondary-700">
                  Mapping
                </th>
                <th className="px-4 py-2 text-right text-xs font-medium uppercase tracking-wider text-secondary-700">
                  Raw Census
                </th>
                <th className="px-4 py-2 text-right text-xs font-medium uppercase tracking-wider text-secondary-700">
                  PE ECPS
                </th>
                <th className="px-4 py-2 text-right text-xs font-medium uppercase tracking-wider text-secondary-700">
                  Gap
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-secondary-200">
              {inputGapRows.map((row) => (
                <tr key={row.key}>
                  <td className="px-4 py-2">
                    <div className="font-medium text-secondary-900">
                      {row.label}
                    </div>
                  </td>
                  <td className="px-4 py-2">
                    <div className="font-mono text-xs text-secondary-500">
                      {row.source} -&gt; {row.variables.join(" + ")}
                    </div>
                  </td>
                  <td className="px-4 py-2 text-right tabular-nums">
                    {dollars(row.rawMean)}
                  </td>
                  <td className="px-4 py-2 text-right tabular-nums">
                    {dollars(row.peMean)}
                  </td>
                  <td className="px-4 py-2 text-right tabular-nums font-medium">
                    {dollars(row.difference)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="border-t border-secondary-200 px-4 py-3 text-xs text-secondary-600">
          These rows explain why pension, housing subsidy, and energy subsidy are currently
          near zero in the released ECPS-side comparison.
        </div>
      </div>

      {rawControl?.rates ? (
        <div className="rounded-lg border border-secondary-200 bg-white p-4 text-sm text-secondary-700 shadow-sm">
          Raw CPS with Census-reported SPM resources gives an all-person rate of{" "}
          <span className="font-semibold text-secondary-900">
            {pct(rawControl.rates.all)}
          </span>
          , so the remaining PE/Census gap is mainly upstream of the SPM formula comparison.
        </div>
      ) : null}
    </section>
  );
}
