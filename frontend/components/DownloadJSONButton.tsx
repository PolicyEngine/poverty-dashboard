"use client";

import type { Baseline } from "@/lib/types";

export function DownloadJSONButton({ baseline }: { baseline: Baseline }) {
  function download() {
    const blob = new Blob([JSON.stringify(baseline, null, 2) + "\n"], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "baseline.json";
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <button
      onClick={download}
      className="rounded-md border border-secondary-300 bg-white px-3 py-1.5 text-sm font-medium text-secondary-700 hover:bg-secondary-100"
    >
      Download JSON to commit
    </button>
  );
}
