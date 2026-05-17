"use client";

import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";

import {
  fetchCensusSpm2024,
  fetchCommittedBaseline,
  fetchSpmGapDiagnostics,
  fetchVersions,
  recompute,
} from "@/lib/api";
import type { Baseline } from "@/lib/types";
import { FederalCard } from "@/components/FederalCard";
import { StateTable } from "@/components/StateTable";
import { VersionBar } from "@/components/VersionBar";
import { DownloadJSONButton } from "@/components/DownloadJSONButton";
import { CensusEffects } from "@/components/CensusEffects";
import { GapDiagnostics } from "@/components/GapDiagnostics";

const EMPTY_BASELINE: Baseline = {
  generated_at: null,
  year: 2026,
  versions: {},
  regions: {},
  errors: [],
};

const AVAILABLE_YEARS = [2024, 2025, 2026];

export default function Page() {
  const [selectedYear, setSelectedYear] = useState(2026);
  const committedQuery = useQuery({
    queryKey: ["committed-baseline"],
    queryFn: fetchCommittedBaseline,
    retry: false,
  });
  const [override, setOverride] = useState<Baseline | null>(null);
  const sourceBaseline = override ?? committedQuery.data ?? EMPTY_BASELINE;
  const baseline =
    sourceBaseline.year === selectedYear
      ? sourceBaseline
      : { ...EMPTY_BASELINE, year: selectedYear };

  const censusQuery = useQuery({
    queryKey: ["census-spm-2024"],
    queryFn: fetchCensusSpm2024,
    retry: false,
  });

  const diagnosticsQuery = useQuery({
    queryKey: ["spm-gap-diagnostics"],
    queryFn: fetchSpmGapDiagnostics,
    retry: false,
  });

  const versionsQuery = useQuery({
    queryKey: ["versions"],
    queryFn: () => fetchVersions(),
    enabled: false,
    retry: false,
  });

  const recomputeMut = useMutation({
    mutationFn: ({ upgrade, year }: { upgrade: boolean; year: number }) =>
      recompute({ upgrade, year }),
    onSuccess: (data) => setOverride(data),
  });

  const federal = baseline.regions["us"];
  const errorCount = baseline.errors?.length ?? 0;

  return (
    <main className="mx-auto max-w-7xl space-y-6 px-4 py-8 sm:px-6 lg:px-8">
      <VersionBar
        committed={baseline.versions}
        generatedAt={baseline.generated_at}
        selectedYear={selectedYear}
        availableYears={AVAILABLE_YEARS}
        live={versionsQuery.data ?? null}
        liveLoading={versionsQuery.isFetching}
        liveError={versionsQuery.error ? String(versionsQuery.error) : null}
        onYearChange={(year) => {
          setSelectedYear(year);
          setOverride(null);
        }}
        onRefreshVersions={() => versionsQuery.refetch()}
        onRecompute={() => recomputeMut.mutate({ upgrade: false, year: selectedYear })}
        onRecomputeUpgrade={() => recomputeMut.mutate({ upgrade: true, year: selectedYear })}
        recomputing={recomputeMut.isPending}
      />

      {recomputeMut.isError && (
        <div className="rounded-md border border-error/30 bg-error/5 px-4 py-3 text-sm text-error">
          Recompute failed: {String(recomputeMut.error)}
        </div>
      )}

      {override && (
        <div className="flex items-center justify-between rounded-md border border-primary-300 bg-primary-50 px-4 py-3 text-sm text-primary-800">
          <span>
            Showing freshly computed numbers (not yet committed). Generated{" "}
            {override.generated_at}.
          </span>
          <DownloadJSONButton baseline={override} />
        </div>
      )}

      <FederalCard
        federal={federal}
        year={selectedYear}
        census={censusQuery.data ?? null}
      />

      <GapDiagnostics diagnostics={diagnosticsQuery.data ?? null} />

      <CensusEffects
        census={censusQuery.data ?? null}
        diagnostics={diagnosticsQuery.data ?? null}
      />

      <section className="space-y-2">
        <div className="flex items-baseline justify-between">
          <h2 className="text-lg font-semibold text-secondary-900">By state</h2>
          {errorCount > 0 && (
            <span className="text-xs text-error">
              {errorCount} region{errorCount === 1 ? "" : "s"} failed
            </span>
          )}
        </div>
        <StateTable
          regions={baseline.regions}
          census={censusQuery.data ?? null}
        />
      </section>

      {errorCount > 0 && (
        <details className="rounded-md border border-error/30 bg-error/5 p-4 text-sm">
          <summary className="cursor-pointer font-medium text-error">
            Errors ({errorCount})
          </summary>
          <ul className="mt-2 space-y-1 font-mono text-xs">
            {baseline.errors.map((e) => (
              <li key={e.region_code}>
                <span className="font-bold">{e.region_code}:</span> {e.error}
              </li>
            ))}
          </ul>
        </details>
      )}
    </main>
  );
}
