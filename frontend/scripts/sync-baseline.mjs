// Copies the repo-root baseline.json into frontend/public so Next.js can serve it.
// Runs automatically before `next dev` / `next build`.

import { copyFileSync, existsSync, mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const files = [
  ["../../data/baseline.json", "../public/baseline.json"],
  ["../../data/census_spm_2024.json", "../public/census_spm_2024.json"],
  ["../../data/spm_gap_diagnostics.json", "../public/spm_gap_diagnostics.json"],
];

for (const [srcPath, destPath] of files) {
  const src = resolve(here, srcPath);
  const dest = resolve(here, destPath);

  if (!existsSync(src)) {
    console.warn(`[sync-baseline] source missing: ${src}`);
    continue;
  }

  mkdirSync(dirname(dest), { recursive: true });
  copyFileSync(src, dest);
  console.log(`[sync-baseline] ${src} -> ${dest}`);
}
