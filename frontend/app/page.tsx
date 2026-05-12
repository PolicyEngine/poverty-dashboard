"use client";

import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";

import { fetchCommittedBaseline, fetchVersions, recompute } from "@/lib/api";
import type { Baseline } from "@/lib/types";
import { FederalCard } from "@/components/FederalCard";
import { StateTable } from "@/components/StateTable";
import { VersionBar } from "@/components/VersionBar";
import { DownloadJSONButton } from "@/components/DownloadJSONButton";

const EMPTY_BASELINE: Baseline = {
  generated_at: null,
  year: 2026,
  versions: {},
  regions: {},
  errors: [],
};

export default function Page() {
  const committedQuery = useQuery({
    queryKey: ["committed-baseline"],
    queryFn: fetchCommittedBaseline,
    retry: false,
  });
  const [override, setOverride] = useState<Baseline | null>(null);
  const baseline = override ?? committedQuery.data ?? EMPTY_BASELINE;

  const versionsQuery = useQuery({
    queryKey: ["versions"],
    queryFn: () => fetchVersions(),
    enabled: false,
    retry: false,
  });

  const recomputeMut = useMutation({
    mutationFn: ({ upgrade }: { upgrade: boolean }) => recompute({ upgrade }),
    onSuccess: (data) => setOverride(data),
  });

  const federal = baseline.regions["us"];
  const errorCount = baseline.errors?.length ?? 0;

  return (
    <main className="mx-auto max-w-7xl space-y-6 px-4 py-8 sm:px-6 lg:px-8">
      <VersionBar
        committed={baseline.versions}
        generatedAt={baseline.generated_at}
        live={versionsQuery.data ?? null}
        liveLoading={versionsQuery.isFetching}
        liveError={versionsQuery.error ? String(versionsQuery.error) : null}
        onRefreshVersions={() => versionsQuery.refetch()}
        onRecompute={() => recomputeMut.mutate({ upgrade: false })}
        onRecomputeUpgrade={() => recomputeMut.mutate({ upgrade: true })}
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

      <FederalCard federal={federal} />

      <section className="space-y-2">
        <div className="flex items-baseline justify-between">
          <h2 className="text-lg font-semibold text-secondary-900">By state</h2>
          {errorCount > 0 && (
            <span className="text-xs text-error">
              {errorCount} region{errorCount === 1 ? "" : "s"} failed
            </span>
          )}
        </div>
        <StateTable regions={baseline.regions} />
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
