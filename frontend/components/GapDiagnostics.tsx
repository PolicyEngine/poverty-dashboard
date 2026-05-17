"use client";

import { useState } from "react";

import type { SpmGapDiagnostics, ThresholdRatioDistribution } from "@/lib/types";
import { dollars, num, pct } from "@/lib/format";

type Props = {
  diagnostics: SpmGapDiagnostics | null;
};

const AGE_COLUMNS: {
  key: keyof ThresholdRatioDistribution;
  label: string;
  description: string;
}[] = [
  { key: "all", label: "All", description: "All people" },
  { key: "child", label: "Child", description: "Under 18" },
  { key: "working_age", label: "18-64", description: "Ages 18 to 64" },
  { key: "senior", label: "65+", description: "Ages 65 and older" },
];

function pp(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return `${(value * 100).toFixed(1)} pp`;
}

export function GapDiagnostics({ diagnostics }: Props) {
  const [ratioAgeGroup, setRatioAgeGroup] =
    useState<keyof ThresholdRatioDistribution>("all");

  if (!diagnostics) return null;

  const census = diagnostics.benchmarks.census_2024_spm.all.rate;
  const pe2024 = diagnostics.policyengine_2024_checks[0];
  const modeledPlusOmittedCheck = diagnostics.policyengine_2024_checks.find((check) =>
    check.label.startsWith("modeled"),
  );
  const sourceReplication = diagnostics.source_replication_diagnostics;
  const totalIncome = diagnostics.total_income_leaf_diagnostics;
  const rawReplication = sourceReplication?.sources.raw_cps_asec;
  const pe2026 = diagnostics.benchmarks.policyengine_2026_committed;
  const gap = diagnostics.gap_accounting;
  const thresholds = diagnostics.bls_2024_reference_thresholds.two_adults_two_children;
  const means = diagnostics.policyengine_2024_resource_means;
  const ratioDistribution = diagnostics.threshold_ratio_distribution;
  const negativeIncome = diagnostics.negative_income_diagnostics;
  const ratioAgeLabel =
    AGE_COLUMNS.find((column) => column.key === ratioAgeGroup)?.description ??
    "All people";

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <div>
          <h2 className="text-lg font-semibold text-secondary-900">
            Gap diagnostics
          </h2>
          <div className="text-sm text-secondary-600">
            Early checks on why PolicyEngine is above Census SPM.
          </div>
        </div>
        <div className="flex gap-3 text-xs">
          <a
            href={diagnostics.sources.tables_page}
            target="_blank"
            rel="noreferrer"
            className="font-medium text-primary-700 hover:text-primary-900"
          >
            Census P60-287
          </a>
          <a
            href={diagnostics.sources.table_b5}
            target="_blank"
            rel="noreferrer"
            className="font-medium text-primary-700 hover:text-primary-900"
          >
            Table B-5
          </a>
          <a
            href={diagnostics.sources.bls_2024_thresholds}
            target="_blank"
            rel="noreferrer"
            className="font-medium text-primary-700 hover:text-primary-900"
          >
            BLS thresholds
          </a>
        </div>
      </div>

      {gap ? (
        <div className="overflow-hidden rounded-lg border border-secondary-200 bg-white shadow-sm">
          <div className="border-b border-secondary-200 bg-secondary-100 px-4 py-3">
            <div className="text-sm font-semibold text-secondary-900">
              National gap accounting
            </div>
            <div className="text-xs text-secondary-600">
              All-person rate differences, percentage points, against Census 2024 SPM.
            </div>
          </div>
          <div className="grid gap-px bg-secondary-200 text-sm md:grid-cols-4">
            <div className="bg-white p-4">
              <div className="text-xs uppercase tracking-wider text-secondary-500">
                Modeled PE gap
              </div>
              <div className="mt-1 text-2xl font-semibold text-secondary-900">
                {pp(gap.policyengine_modeled_gap)}
              </div>
              <div className="text-xs text-secondary-500">
                {pct(gap.policyengine_modeled_rate)} vs {pct(gap.census_rate)}
              </div>
            </div>
            <div className="bg-white p-4">
              <div className="text-xs uppercase tracking-wider text-secondary-500">
                Closed by omitted rows
              </div>
              <div className="mt-1 text-2xl font-semibold text-secondary-900">
                {pp(gap.omitted_resources_gap_closure)}
              </div>
              <div className="text-xs text-secondary-500">
                {pct(gap.omitted_resources_share_of_gap)} of modeled gap
              </div>
            </div>
            <div className="bg-white p-4">
              <div className="text-xs uppercase tracking-wider text-secondary-500">
                Remaining after omitted
              </div>
              <div className="mt-1 text-2xl font-semibold text-secondary-900">
                {pp(gap.remaining_gap_after_omitted_resources)}
              </div>
              <div className="text-xs text-secondary-500">
                Child support + workers' comp added arithmetically
              </div>
            </div>
            <div className="bg-white p-4">
              <div className="text-xs uppercase tracking-wider text-secondary-500">
                Raw CPS reported gap
              </div>
              <div className="mt-1 text-2xl font-semibold text-secondary-900">
                {pp(gap.raw_cps_reported_gap)}
              </div>
              <div className="text-xs text-secondary-500">
                Validation-only Census resources control
              </div>
            </div>
          </div>
          <div className="border-t border-secondary-200 px-4 py-3 text-xs text-secondary-600">
            {gap.note}
          </div>
        </div>
      ) : null}

      <div className="grid gap-4 md:grid-cols-4">
        <div className="rounded-lg border border-secondary-200 bg-white p-4 shadow-sm">
          <div className="text-xs uppercase tracking-wider text-secondary-500">
            Census 2024 SPM
          </div>
          <div className="mt-1 text-2xl font-semibold text-secondary-900">
            {pct(census)}
          </div>
          <div className="text-xs text-secondary-500">
            {num(diagnostics.benchmarks.census_2024_spm.all.poverty_count)} people
          </div>
        </div>
        <div className="rounded-lg border border-secondary-200 bg-white p-4 shadow-sm">
          <div className="text-xs uppercase tracking-wider text-secondary-500">
            PolicyEngine 2024
          </div>
          <div className="mt-1 text-2xl font-semibold text-secondary-900">
            {pct(pe2024.all)}
          </div>
          <div className="text-xs text-error">
            {pp(pe2024.all - census)} above Census
          </div>
        </div>
        <div className="rounded-lg border border-secondary-200 bg-white p-4 shadow-sm">
          <div className="text-xs uppercase tracking-wider text-secondary-500">
            Raw CPS control
          </div>
          <div className="mt-1 text-2xl font-semibold text-secondary-900">
            {pct(rawReplication?.rates?.all)}
          </div>
          <div className="text-xs text-secondary-500">
            {rawReplication?.rates
              ? `${pp(rawReplication.rates.all - census)} vs Census`
              : "Validation-only replication"}
          </div>
        </div>
        <div className="rounded-lg border border-secondary-200 bg-white p-4 shadow-sm">
          <div className="text-xs uppercase tracking-wider text-secondary-500">
            PolicyEngine 2026
          </div>
          <div className="mt-1 text-2xl font-semibold text-secondary-900">
            {pct(pe2026.all)}
          </div>
          <div className="text-xs text-secondary-500">
            Current committed baseline
          </div>
        </div>
      </div>

      {sourceReplication ? (
        <div className="overflow-hidden rounded-lg border border-secondary-200 bg-white shadow-sm">
          <div className="border-b border-secondary-200 bg-secondary-100 px-4 py-3">
            <div className="text-sm font-semibold text-secondary-900">
              Resource distribution shape
            </div>
            <div className="text-xs text-secondary-600">
              Weighted person-level SPM resources and resource-to-threshold quantiles.
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="bg-white">
                  <th className="px-4 py-2 text-left text-xs font-medium uppercase tracking-wider text-secondary-700">
                    Source
                  </th>
                  <th className="px-4 py-2 text-right text-xs font-medium uppercase tracking-wider text-secondary-700">
                    P05 resource
                  </th>
                  <th className="px-4 py-2 text-right text-xs font-medium uppercase tracking-wider text-secondary-700">
                    P10 resource
                  </th>
                  <th className="px-4 py-2 text-right text-xs font-medium uppercase tracking-wider text-secondary-700">
                    Median resource
                  </th>
                  <th className="px-4 py-2 text-right text-xs font-medium uppercase tracking-wider text-secondary-700">
                    P90 resource
                  </th>
                  <th className="px-4 py-2 text-right text-xs font-medium uppercase tracking-wider text-secondary-700">
                    P10 ratio
                  </th>
                  <th className="px-4 py-2 text-right text-xs font-medium uppercase tracking-wider text-secondary-700">
                    &lt;= $0
                  </th>
                  <th className="px-4 py-2 text-right text-xs font-medium uppercase tracking-wider text-secondary-700">
                    &lt; threshold
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-secondary-200">
                {[
                  sourceReplication.sources.enhanced_cps,
                  sourceReplication.sources.raw_cps_asec,
                ].map((source) => {
                  const distribution = source.resource_distribution;
                  return (
                    <tr key={source.key}>
                      <td className="px-4 py-2">
                        <div className="font-medium text-secondary-900">
                          {source.label}
                        </div>
                        <div className="text-xs text-secondary-500">
                          {source.available
                            ? source.resource_variable
                            : source.error ?? source.note}
                        </div>
                      </td>
                      <td className="px-4 py-2 text-right tabular-nums">
                        {dollars(distribution?.resource_quantiles.p05)}
                      </td>
                      <td className="px-4 py-2 text-right tabular-nums">
                        {dollars(distribution?.resource_quantiles.p10)}
                      </td>
                      <td className="px-4 py-2 text-right tabular-nums">
                        {dollars(distribution?.resource_quantiles.p50)}
                      </td>
                      <td className="px-4 py-2 text-right tabular-nums">
                        {dollars(distribution?.resource_quantiles.p90)}
                      </td>
                      <td className="px-4 py-2 text-right tabular-nums">
                        {distribution
                          ? distribution.threshold_ratio_quantiles.p10.toFixed(2)
                          : "—"}
                      </td>
                      <td className="px-4 py-2 text-right tabular-nums">
                        {pct(distribution?.share_zero_or_below)}
                      </td>
                      <td className="px-4 py-2 text-right tabular-nums">
                        {pct(distribution?.share_below_threshold)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}

      <div className="overflow-hidden rounded-lg border border-secondary-200 bg-white shadow-sm">
        <div className="border-b border-secondary-200 bg-secondary-100 px-4 py-3">
          <div className="text-sm font-semibold text-secondary-900">
            Census SPM rate checks by age
          </div>
          <div className="text-xs text-secondary-600">
            Census 2024 report rates and Table B-5 deep-poverty shares vs PolicyEngine 2024.
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="bg-white">
                <th className="px-4 py-2 text-left text-xs font-medium uppercase tracking-wider text-secondary-700">
                  Group
                </th>
                <th className="px-4 py-2 text-right text-xs font-medium uppercase tracking-wider text-secondary-700">
                  Census SPM
                </th>
                <th className="px-4 py-2 text-right text-xs font-medium uppercase tracking-wider text-secondary-700">
                  PE modeled
                </th>
                <th className="px-4 py-2 text-right text-xs font-medium uppercase tracking-wider text-secondary-700">
                  PE + omitted
                </th>
                <th className="px-4 py-2 text-right text-xs font-medium uppercase tracking-wider text-secondary-700">
                  Raw CPS
                </th>
                <th className="px-4 py-2 text-right text-xs font-medium uppercase tracking-wider text-secondary-700">
                  Census &lt;0.50
                </th>
                <th className="px-4 py-2 text-right text-xs font-medium uppercase tracking-wider text-secondary-700">
                  PE &lt;0.50
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-secondary-200">
              {AGE_COLUMNS.map((column) => (
                <tr key={column.key}>
                  <td className="px-4 py-2">
                    <div className="font-medium text-secondary-900">
                      {column.description}
                    </div>
                    <div className="text-xs text-secondary-500">
                      {num(
                        diagnostics.benchmarks.census_2024_spm[column.key]
                          .poverty_count,
                      )}{" "}
                      Census SPM poor
                    </div>
                  </td>
                  <td className="px-4 py-2 text-right tabular-nums">
                    {pct(diagnostics.benchmarks.census_2024_spm[column.key].rate)}
                  </td>
                  <td className="px-4 py-2 text-right tabular-nums">
                    {pct(pe2024[column.key])}
                  </td>
                  <td className="px-4 py-2 text-right tabular-nums">
                    {pct(modeledPlusOmittedCheck?.[column.key])}
                  </td>
                  <td className="px-4 py-2 text-right tabular-nums">
                    {pct(rawReplication?.rates?.[column.key])}
                  </td>
                  <td className="px-4 py-2 text-right tabular-nums">
                    {pct(
                      ratioDistribution.census_2024_spm[column.key]
                        .less_than_0_50,
                    )}
                  </td>
                  <td className="px-4 py-2 text-right tabular-nums">
                    {pct(
                      ratioDistribution.policyengine_2024_modeled[column.key]
                        .less_than_0_50,
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {sourceReplication ? (
        <div className="grid gap-4 xl:grid-cols-[1fr_1fr]">
          <div className="overflow-hidden rounded-lg border border-secondary-200 bg-white shadow-sm">
            <div className="border-b border-secondary-200 bg-secondary-100 px-4 py-3">
              <div className="text-sm font-semibold text-secondary-900">
                Raw CPS replication control
              </div>
              <div className="text-xs text-secondary-600">
                Census-reported SPM resources are used only as a raw-data validation check.
              </div>
            </div>
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="bg-white">
                    <th className="px-4 py-2 text-left text-xs font-medium uppercase tracking-wider text-secondary-700">
                      Source
                    </th>
                    <th className="px-4 py-2 text-right text-xs font-medium uppercase tracking-wider text-secondary-700">
                      All
                    </th>
                    <th className="px-4 py-2 text-right text-xs font-medium uppercase tracking-wider text-secondary-700">
                      Child
                    </th>
                    <th className="px-4 py-2 text-right text-xs font-medium uppercase tracking-wider text-secondary-700">
                      65+
                    </th>
                    <th className="px-4 py-2 text-right text-xs font-medium uppercase tracking-wider text-secondary-700">
                      Mean resource
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-secondary-200">
                  {[
                    sourceReplication.sources.enhanced_cps,
                    sourceReplication.sources.raw_cps_asec,
                  ].map((source) => (
                    <tr key={source.key}>
                      <td className="px-4 py-2">
                        <div className="font-medium text-secondary-900">
                          {source.label}
                        </div>
                        <div className="text-xs text-secondary-500">
                          {source.available
                            ? source.resource_variable
                            : source.error ?? source.note}
                        </div>
                      </td>
                      <td className="px-4 py-2 text-right tabular-nums">
                        {pct(source.rates?.all)}
                      </td>
                      <td className="px-4 py-2 text-right tabular-nums">
                        {pct(source.rates?.child)}
                      </td>
                      <td className="px-4 py-2 text-right tabular-nums">
                        {pct(source.rates?.senior)}
                      </td>
                      <td className="px-4 py-2 text-right tabular-nums">
                        {dollars(source.mean_resource)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="border-t border-secondary-200 px-4 py-3 text-xs text-secondary-600">
              {sourceReplication.note}
            </div>
          </div>

          <div className="overflow-hidden rounded-lg border border-secondary-200 bg-white shadow-sm">
            <div className="border-b border-secondary-200 bg-secondary-100 px-4 py-3">
              <div className="text-sm font-semibold text-secondary-900">
                ECPS minus raw CPS means
              </div>
              <div className="text-xs text-secondary-600">
                Weighted person averages after mapping components to people.
              </div>
            </div>
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="bg-white">
                    <th className="px-4 py-2 text-left text-xs font-medium uppercase tracking-wider text-secondary-700">
                      Component
                    </th>
                    <th className="px-4 py-2 text-right text-xs font-medium uppercase tracking-wider text-secondary-700">
                      ECPS
                    </th>
                    <th className="px-4 py-2 text-right text-xs font-medium uppercase tracking-wider text-secondary-700">
                      Raw
                    </th>
                    <th className="px-4 py-2 text-right text-xs font-medium uppercase tracking-wider text-secondary-700">
                      Diff
                    </th>
                    <th className="px-4 py-2 text-right text-xs font-medium uppercase tracking-wider text-secondary-700">
                      Diff below threshold
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-secondary-200">
                  {sourceReplication.component_mean_gaps
                    .filter((row) => row.available)
                    .slice(0, 8)
                    .map((row) => (
                      <tr key={row.variable}>
                        <td className="px-4 py-2">
                          <div className="font-medium text-secondary-900">
                            {row.label}
                          </div>
                          <div className="font-mono text-xs text-secondary-500">
                            {row.variable}
                          </div>
                        </td>
                        <td className="px-4 py-2 text-right tabular-nums">
                          {dollars(row.enhanced_mean)}
                        </td>
                        <td className="px-4 py-2 text-right tabular-nums">
                          {dollars(row.raw_mean)}
                        </td>
                        <td className="px-4 py-2 text-right tabular-nums">
                          {dollars(row.difference)}
                        </td>
                        <td className="px-4 py-2 text-right tabular-nums">
                          {dollars(row.below_threshold_difference)}
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      ) : null}

      {totalIncome ? (
        <div className="overflow-hidden rounded-lg border border-secondary-200 bg-white shadow-sm">
          <div className="border-b border-secondary-200 bg-secondary-100 px-4 py-3">
            <div className="text-sm font-semibold text-secondary-900">
              SPM total income leaves
            </div>
            <div className="text-xs text-secondary-600">
              Raw ASEC SPM_TOTVAL reconstructed from person-level money-income leaves.
            </div>
          </div>
          <div className="grid gap-px bg-secondary-200 text-sm md:grid-cols-4">
            {[
              ["PTOTVAL from leaves", totalIncome.ptotval_from_person_leaves],
              ["SPM_TOTVAL from PTOTVAL", totalIncome.spm_totval_from_ptotval],
              ["SPM_TOTVAL from leaves", totalIncome.spm_totval_from_person_leaves],
              ...(totalIncome.spm_resource_formula
                ? [
                    [
                      "SPM_RESOURCES formula",
                      totalIncome.spm_resource_formula.spm_resources_from_formula,
                    ],
                  ]
                : []),
            ].map(([label, metrics]) => (
              <div key={label as string} className="bg-white p-4">
                <div className="text-xs uppercase tracking-wider text-secondary-500">
                  {label as string}
                </div>
                <div className="mt-1 text-lg font-semibold text-secondary-900">
                  {pct((metrics as typeof totalIncome.ptotval_from_person_leaves).exact_share)}
                </div>
                <div className="text-xs text-secondary-500">
                  Mean abs error{" "}
                  {dollars(
                    (metrics as typeof totalIncome.ptotval_from_person_leaves)
                      .weighted_mean_abs_error,
                  )}
                </div>
              </div>
            ))}
          </div>
          {totalIncome.spm_resource_formula ? (
            <div className="overflow-x-auto border-t border-secondary-200">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="bg-white">
                    <th className="px-4 py-2 text-left text-xs font-medium uppercase tracking-wider text-secondary-700">
                      Census SPM formula component
                    </th>
                    <th className="px-4 py-2 text-left text-xs font-medium uppercase tracking-wider text-secondary-700">
                      Treatment
                    </th>
                    <th className="px-4 py-2 text-right text-xs font-medium uppercase tracking-wider text-secondary-700">
                      Raw Census
                    </th>
                    <th className="px-4 py-2 text-right text-xs font-medium uppercase tracking-wider text-secondary-700">
                      PE
                    </th>
                    <th className="px-4 py-2 text-right text-xs font-medium uppercase tracking-wider text-secondary-700">
                      Diff
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-secondary-200">
                  {totalIncome.spm_resource_formula.components.map((row) => (
                    <tr key={row.key}>
                      <td className="px-4 py-2">
                        <div className="font-medium text-secondary-900">
                          {row.label}
                        </div>
                        <div className="font-mono text-xs text-secondary-500">
                          {row.raw_columns.join(" + ")}
                          {row.enhanced_variables.length
                            ? ` -> ${row.enhanced_variables.join(" + ")}`
                            : " -> no PE equivalent"}
                        </div>
                        {row.note ? (
                          <div className="max-w-lg text-xs text-secondary-500">
                            {row.note}
                          </div>
                        ) : null}
                      </td>
                      <td className="px-4 py-2 text-secondary-700">
                        {row.section === "addition" ? "Resource" : "Subtraction"}
                      </td>
                      <td className="px-4 py-2 text-right tabular-nums">
                        {dollars(row.raw_mean)}
                      </td>
                      <td className="px-4 py-2 text-right tabular-nums">
                        {dollars(row.enhanced_mean)}
                      </td>
                      <td className="px-4 py-2 text-right tabular-nums">
                        {dollars(row.difference)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div className="border-t border-secondary-200 px-4 py-3 text-xs text-secondary-600">
                {totalIncome.spm_resource_formula.note}
              </div>
            </div>
          ) : null}
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="bg-white">
                  <th className="px-4 py-2 text-left text-xs font-medium uppercase tracking-wider text-secondary-700">
                    Raw CPS leaf
                  </th>
                  <th className="px-4 py-2 text-right text-xs font-medium uppercase tracking-wider text-secondary-700">
                    Raw
                  </th>
                  <th className="px-4 py-2 text-right text-xs font-medium uppercase tracking-wider text-secondary-700">
                    ECPS
                  </th>
                  <th className="px-4 py-2 text-right text-xs font-medium uppercase tracking-wider text-secondary-700">
                    Diff
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-secondary-200">
                {totalIncome.component_mean_gaps.map((row) => (
                  <tr key={row.key}>
                    <td className="px-4 py-2">
                      <div className="font-medium text-secondary-900">
                        {row.label}
                      </div>
                      <div className="font-mono text-xs text-secondary-500">
                        {row.raw_columns.join(" + ")}
                        {row.enhanced_variables.length
                          ? ` -> ${row.enhanced_variables.join(" + ")}`
                          : " -> no ECPS equivalent"}
                      </div>
                    </td>
                    <td className="px-4 py-2 text-right tabular-nums">
                      {dollars(row.raw_mean)}
                    </td>
                    <td className="px-4 py-2 text-right tabular-nums">
                      {dollars(row.enhanced_mean)}
                    </td>
                    <td className="px-4 py-2 text-right tabular-nums">
                      {dollars(row.difference)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="border-t border-secondary-200 px-4 py-3 text-xs text-secondary-600">
            {totalIncome.note}
          </div>
        </div>
      ) : null}

      <div className="grid gap-4 xl:grid-cols-[1.4fr_1fr]">
        <div className="overflow-hidden rounded-lg border border-secondary-200 bg-white shadow-sm">
          <div className="border-b border-secondary-200 bg-secondary-100 px-4 py-3 text-sm font-semibold text-secondary-900">
            PolicyEngine 2024 cross-checks
          </div>
          <table className="min-w-full text-sm">
            <thead>
              <tr className="bg-white">
                <th className="px-4 py-2 text-left text-xs font-medium uppercase tracking-wider text-secondary-700">
                  Check
                </th>
                {AGE_COLUMNS.map((column) => (
                  <th
                    key={column.key}
                    className="px-4 py-2 text-right text-xs font-medium uppercase tracking-wider text-secondary-700"
                  >
                    {column.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-secondary-200">
              {diagnostics.policyengine_2024_checks.map((check) => (
                <tr key={check.label}>
                  <td className="px-4 py-2">
                    <div className="font-medium text-secondary-900">{check.label}</div>
                    <div className="text-xs text-secondary-500">{check.note}</div>
                  </td>
                  {AGE_COLUMNS.map((column) => (
                    <td key={column.key} className="px-4 py-2 text-right tabular-nums">
                      {pct(check[column.key])}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="space-y-4">
          <div className="rounded-lg border border-secondary-200 bg-white p-4 shadow-sm">
            <div className="text-sm font-semibold text-secondary-900">
              Working interpretation
            </div>
            <ul className="mt-3 space-y-2 text-sm text-secondary-700">
              {diagnostics.summary.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>

          <div className="rounded-lg border border-secondary-200 bg-white p-4 shadow-sm">
            <div className="text-sm font-semibold text-secondary-900">
              Threshold and resource context
            </div>
            <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
              <dt className="text-secondary-600">BLS renter threshold</dt>
              <dd className="text-right font-medium tabular-nums">
                {dollars(thresholds.renter)}
              </dd>
              <dt className="text-secondary-600">BLS owner w/ mortgage</dt>
              <dd className="text-right font-medium tabular-nums">
                {dollars(thresholds.owner_with_mortgage)}
              </dd>
              <dt className="text-secondary-600">PE mean threshold</dt>
              <dd className="text-right font-medium tabular-nums">
                {dollars(means.spm_unit_spm_threshold)}
              </dd>
              <dt className="text-secondary-600">PE mean modeled resources</dt>
              <dd className="text-right font-medium tabular-nums">
                {dollars(means.spm_unit_net_income)}
              </dd>
              <dt className="text-secondary-600">PE mean market income</dt>
              <dd className="text-right font-medium tabular-nums">
                {dollars(means.spm_unit_market_income)}
              </dd>
              <dt className="text-secondary-600">PE mean medical expenses</dt>
              <dd className="text-right font-medium tabular-nums">
                {dollars(means.spm_unit_medical_out_of_pocket_expenses)}
              </dd>
            </dl>
          </div>
        </div>
      </div>

      <div className="overflow-hidden rounded-lg border border-secondary-200 bg-white shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-secondary-200 bg-secondary-100 px-4 py-3">
          <div>
            <div className="text-sm font-semibold text-secondary-900">
              SPM threshold-ratio distribution
            </div>
            <div className="text-xs text-secondary-600">
              {ratioAgeLabel}, Census Table B-5 vs PolicyEngine 2024.
            </div>
          </div>
          <div className="flex rounded-md border border-secondary-300 bg-white p-0.5">
            {AGE_COLUMNS.map((column) => {
              const active = column.key === ratioAgeGroup;
              return (
                <button
                  key={column.key}
                  type="button"
                  aria-pressed={active}
                  onClick={() => setRatioAgeGroup(column.key)}
                  className={`min-w-12 rounded px-2.5 py-1 text-xs font-medium ${
                    active
                      ? "bg-primary-700 text-white"
                      : "text-secondary-700 hover:bg-secondary-100"
                  }`}
                >
                  {column.label}
                </button>
              );
            })}
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="bg-white">
                <th className="px-4 py-2 text-left text-xs font-medium uppercase tracking-wider text-secondary-700">
                  Income/resources to threshold
                </th>
                <th className="px-4 py-2 text-right text-xs font-medium uppercase tracking-wider text-secondary-700">
                  Census
                </th>
                <th className="px-4 py-2 text-right text-xs font-medium uppercase tracking-wider text-secondary-700">
                  PE modeled
                </th>
                <th className="px-4 py-2 text-right text-xs font-medium uppercase tracking-wider text-secondary-700">
                  PE + omitted resources
                </th>
                <th className="px-4 py-2 text-right text-xs font-medium uppercase tracking-wider text-secondary-700">
                  Raw CPS reported
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-secondary-200">
              {ratioDistribution.bins.map((bin) => (
                <tr key={bin.key}>
                  <td className="px-4 py-2 font-medium text-secondary-900">
                    {bin.label}
                  </td>
                  <td className="px-4 py-2 text-right tabular-nums">
                    {pct(ratioDistribution.census_2024_spm[ratioAgeGroup][bin.key])}
                  </td>
                  <td className="px-4 py-2 text-right tabular-nums">
                    {pct(
                      ratioDistribution.policyengine_2024_modeled[ratioAgeGroup][
                        bin.key
                      ],
                    )}
                  </td>
                  <td className="px-4 py-2 text-right tabular-nums">
                    {pct(
                      ratioDistribution
                        .policyengine_2024_modeled_plus_omitted_resources[
                        ratioAgeGroup
                      ][
                        bin.key
                      ],
                    )}
                  </td>
                  <td className="px-4 py-2 text-right tabular-nums">
                    {pct(
                      rawReplication?.threshold_ratio_distribution?.[ratioAgeGroup]?.[
                        bin.key
                      ],
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {negativeIncome ? (
        <div className="overflow-hidden rounded-lg border border-secondary-200 bg-white shadow-sm">
          <div className="border-b border-secondary-200 bg-secondary-100 px-4 py-3">
            <div className="text-sm font-semibold text-secondary-900">
              Negative income tail
            </div>
            <div className="text-xs text-secondary-600">
              ECPS vs raw CPS ASEC, using the first available SPM resource measure.
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="bg-white">
                  <th className="px-4 py-2 text-left text-xs font-medium uppercase tracking-wider text-secondary-700">
                    Source
                  </th>
                  <th className="px-4 py-2 text-right text-xs font-medium uppercase tracking-wider text-secondary-700">
                    People below $0
                  </th>
                  <th className="px-4 py-2 text-right text-xs font-medium uppercase tracking-wider text-secondary-700">
                    Share
                  </th>
                  <th className="px-4 py-2 text-right text-xs font-medium uppercase tracking-wider text-secondary-700">
                    Negative mass
                  </th>
                  <th className="px-4 py-2 text-right text-xs font-medium uppercase tracking-wider text-secondary-700">
                    Min income
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-secondary-200">
                {[
                  negativeIncome.sources.enhanced_cps,
                  negativeIncome.sources.raw_cps_asec,
                ].map((source) => (
                  <tr key={source.key}>
                    <td className="px-4 py-2">
                      <div className="font-medium text-secondary-900">
                        {source.label}
                      </div>
                      <div className="text-xs text-secondary-500">
                        {source.available
                          ? source.income_variable
                          : source.note}
                      </div>
                    </td>
                    <td className="px-4 py-2 text-right tabular-nums">
                      {num(source.negative_person_count)}
                    </td>
                    <td className="px-4 py-2 text-right tabular-nums">
                      {pct(source.negative_person_share)}
                    </td>
                    <td className="px-4 py-2 text-right tabular-nums">
                      {dollars(source.negative_income_abs_mass)}
                    </td>
                    <td className="px-4 py-2 text-right tabular-nums">
                      {dollars(source.minimum_spm_unit_income)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="border-t border-secondary-200 px-4 py-3 text-xs text-secondary-600">
            {negativeIncome.comparison.available
              ? `ECPS minus raw CPS ASEC: ${pp(
                  negativeIncome.comparison.negative_person_share_difference ?? 0,
                )} negative-income prevalence, ${dollars(
                  negativeIncome.comparison.negative_income_abs_mass_difference,
                )} negative-income mass.`
              : negativeIncome.comparison.note}
          </div>
        </div>
      ) : null}

      <div className="overflow-hidden rounded-lg border border-secondary-200 bg-white shadow-sm">
        <div className="border-b border-secondary-200 bg-secondary-100 px-4 py-3">
          <div className="text-sm font-semibold text-secondary-900">
            Administrative calibration targets
          </div>
          <div className="text-xs text-secondary-600">
            Candidate non-survey targets for weak SPM resource rows.
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="bg-white">
                <th className="px-4 py-2 text-left text-xs font-medium uppercase tracking-wider text-secondary-700">
                  Element
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium uppercase tracking-wider text-secondary-700">
                  Variables
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium uppercase tracking-wider text-secondary-700">
                  Source
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium uppercase tracking-wider text-secondary-700">
                  Target
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-secondary-200">
              {diagnostics.admin_calibration_targets.map((target) => (
                <tr key={target.element}>
                  <td className="px-4 py-2 font-medium text-secondary-900">
                    {target.element}
                  </td>
                  <td className="px-4 py-2 font-mono text-xs text-secondary-700">
                    {target.variables.join(", ")}
                  </td>
                  <td className="px-4 py-2 text-secondary-700">
                    {target.source}
                  </td>
                  <td className="px-4 py-2">
                    <div className="text-secondary-900">{target.target}</div>
                    <div className="mt-1 text-xs text-secondary-500">
                      {target.implementation_note}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
