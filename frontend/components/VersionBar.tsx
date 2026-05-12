"use client";

import type { Versions } from "@/lib/types";
import { relativeTime } from "@/lib/format";

type Props = {
  committed: Versions;
  generatedAt: string | null;
  live: Versions | null;
  liveLoading: boolean;
  liveError: string | null;
  onRefreshVersions: () => void;
  onRecompute: () => void;
  onRecomputeUpgrade: () => void;
  recomputing: boolean;
};

const KEY_PACKAGES = ["policyengine-us", "policyengine-us-data", "policyengine"];

function isStale(committed: string | null | undefined, live: string | null | undefined) {
  if (!live || !committed) return false;
  return committed !== live;
}

export function VersionBar(props: Props) {
  const {
    committed, generatedAt, live, liveLoading, liveError,
    onRefreshVersions, onRecompute, onRecomputeUpgrade, recomputing,
  } = props;

  return (
    <div className="rounded-lg border border-secondary-200 bg-white p-4 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-1">
          <div className="text-xs uppercase tracking-wider text-secondary-500">
            Baseline generated {relativeTime(generatedAt)}
          </div>
          <div className="flex flex-wrap gap-x-6 gap-y-1 text-sm">
            {KEY_PACKAGES.map((pkg) => {
              const c = committed[pkg];
              const l = live?.[pkg];
              const stale = isStale(c, l);
              return (
                <div key={pkg} className="flex items-baseline gap-2">
                  <span className="font-mono text-secondary-700">{pkg}</span>
                  <span className="font-mono font-medium">{c ?? "—"}</span>
                  {l && stale && (
                    <span className="rounded bg-warning/10 px-1.5 py-0.5 font-mono text-xs text-warning">
                      latest {l}
                    </span>
                  )}
                  {l && !stale && (
                    <span className="text-xs text-success">up to date</span>
                  )}
                </div>
              );
            })}
          </div>
          {liveError && (
            <div className="text-xs text-error">{liveError}</div>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={onRefreshVersions}
            disabled={liveLoading}
            className="rounded-md border border-secondary-300 bg-white px-3 py-1.5 text-sm font-medium text-secondary-700 hover:bg-secondary-100 disabled:opacity-50"
          >
            {liveLoading ? "Checking…" : "Check latest"}
          </button>
          <button
            onClick={onRecompute}
            disabled={recomputing}
            className="rounded-md border border-primary-600 bg-white px-3 py-1.5 text-sm font-medium text-primary-700 hover:bg-primary-50 disabled:opacity-50"
          >
            {recomputing ? "Recomputing…" : "Recompute (current)"}
          </button>
          <button
            onClick={onRecomputeUpgrade}
            disabled={recomputing}
            className="rounded-md bg-primary-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
          >
            {recomputing ? "Recomputing…" : "Upgrade & recompute"}
          </button>
        </div>
      </div>
    </div>
  );
}
