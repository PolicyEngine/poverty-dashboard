import type {
  Baseline,
  CensusSpmReport,
  SpmGapDiagnostics,
  Versions,
} from "./types";

const MODAL_BASE_URL = process.env.NEXT_PUBLIC_MODAL_BASE_URL || "";
const BASE_PATH = process.env.NEXT_PUBLIC_BASE_PATH || "";

/** Read the committed baseline.json that frontend/scripts/sync-baseline.mjs
 *  copies from data/baseline.json into public/ at dev/build time. */
export async function fetchCommittedBaseline(): Promise<Baseline> {
  const r = await fetch(`${BASE_PATH}/baseline.json`, { cache: "no-store" });
  if (!r.ok) throw new Error(`baseline.json fetch failed: ${r.status}`);
  return r.json();
}

export async function fetchCensusSpm2024(): Promise<CensusSpmReport> {
  const r = await fetch(`${BASE_PATH}/census_spm_2024.json`, { cache: "no-store" });
  if (!r.ok) throw new Error(`census_spm_2024.json fetch failed: ${r.status}`);
  return r.json();
}

export async function fetchSpmGapDiagnostics(): Promise<SpmGapDiagnostics> {
  const r = await fetch(`${BASE_PATH}/spm_gap_diagnostics.json`, { cache: "no-store" });
  if (!r.ok) throw new Error(`spm_gap_diagnostics.json fetch failed: ${r.status}`);
  return r.json();
}

export async function fetchVersions(opts: { upgrade?: boolean } = {}): Promise<Versions> {
  if (!MODAL_BASE_URL) throw new Error("NEXT_PUBLIC_MODAL_BASE_URL not set");
  const url = `${MODAL_BASE_URL}/versions?upgrade=${opts.upgrade ? "true" : "false"}`;
  const r = await fetch(url);
  if (!r.ok) throw new Error(`versions fetch failed: ${r.status}`);
  return r.json();
}

export async function recompute(opts: { upgrade?: boolean; year?: number } = {}): Promise<Baseline> {
  if (!MODAL_BASE_URL) throw new Error("NEXT_PUBLIC_MODAL_BASE_URL not set");
  const qs = new URLSearchParams({
    upgrade: opts.upgrade ? "true" : "false",
    year: String(opts.year ?? 2026),
  });
  const url = `${MODAL_BASE_URL}/recompute?${qs}`;
  const r = await fetch(url, { method: "POST" });
  if (!r.ok) throw new Error(`recompute failed: ${r.status}`);
  return r.json();
}

export const STATE_NAMES: Record<string, string> = {
  AL: "Alabama", AK: "Alaska", AZ: "Arizona", AR: "Arkansas",
  CA: "California", CO: "Colorado", CT: "Connecticut", DE: "Delaware",
  DC: "District of Columbia", FL: "Florida", GA: "Georgia",
  HI: "Hawaii", ID: "Idaho", IL: "Illinois", IN: "Indiana",
  IA: "Iowa", KS: "Kansas", KY: "Kentucky", LA: "Louisiana",
  ME: "Maine", MD: "Maryland", MA: "Massachusetts", MI: "Michigan",
  MN: "Minnesota", MS: "Mississippi", MO: "Missouri", MT: "Montana",
  NE: "Nebraska", NV: "Nevada", NH: "New Hampshire", NJ: "New Jersey",
  NM: "New Mexico", NY: "New York", NC: "North Carolina",
  ND: "North Dakota", OH: "Ohio", OK: "Oklahoma", OR: "Oregon",
  PA: "Pennsylvania", RI: "Rhode Island", SC: "South Carolina",
  SD: "South Dakota", TN: "Tennessee", TX: "Texas", UT: "Utah",
  VT: "Vermont", VA: "Virginia", WA: "Washington",
  WV: "West Virginia", WI: "Wisconsin", WY: "Wyoming",
};

export function regionLabel(code: string): string {
  if (code === "us") return "United States";
  const abbrev = code.split("/")[1]?.toUpperCase() ?? "";
  return STATE_NAMES[abbrev] ?? abbrev;
}

export function regionStateCode(code: string): string | null {
  if (code === "us") return null;
  return code.split("/")[1]?.toUpperCase() ?? null;
}
