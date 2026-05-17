export function pct(x: number | null | undefined, digits = 1): string {
  if (x === null || x === undefined || Number.isNaN(x)) return "—";
  return `${(x * 100).toFixed(digits)}%`;
}

export function num(x: number | null | undefined): string {
  if (x === null || x === undefined || Number.isNaN(x)) return "—";
  return new Intl.NumberFormat("en-US").format(Math.round(x));
}

export function dollars(x: number | string | null | undefined): string {
  if (typeof x !== "number" || Number.isNaN(x)) return "—";
  if (x !== 0 && Math.abs(x) < 1) return `$${x.toFixed(2)}`;
  return `$${num(x)}`;
}

export function shortDataset(path: string | null | undefined): string {
  if (!path) return "—";
  return path.replace("hf://policyengine/policyengine-us-data/", "");
}

export function formatTimestamp(iso: string | null): string {
  if (!iso) return "never";
  const d = new Date(iso);
  const date = d.toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
  const time = d.toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
  return `${date} at ${time}`;
}
