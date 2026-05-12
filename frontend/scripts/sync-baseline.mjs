// Copies the repo-root baseline.json into frontend/public so Next.js can serve it.
// Runs automatically before `next dev` / `next build`.

import { copyFileSync, existsSync, mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const src = resolve(here, "../../data/baseline.json");
const dest = resolve(here, "../public/baseline.json");

if (!existsSync(src)) {
  console.warn(`[sync-baseline] source missing: ${src}`);
  process.exit(0);
}

mkdirSync(dirname(dest), { recursive: true });
copyFileSync(src, dest);
console.log(`[sync-baseline] ${src} -> ${dest}`);
