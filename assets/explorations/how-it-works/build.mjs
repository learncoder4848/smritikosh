import { readFileSync, writeFileSync, readdirSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const assets = join(here, "..", "..");

// Derived from the existing assets/how-it-works-{light,dark}.svg pair, so the
// generated dark variant keeps exactly the palette that was already tuned.
const DARK = {
  "#FFFFFF": "#0B1020", "#F7F9FC": "#121A2E", "#F0FDFA": "#0F1F1C",
  "#0F172A": "#E6EAF2", "#64748B": "#9AA4BA", "#94A3B8": "#77839C",
  "#CBD5E1": "#3A4660",
  "#2563EB": "#4C8DFF", "#059669": "#34D399", "#0F766E": "#34D399",
  "#B45309": "#F59E0B", "#7C3AED": "#A78BFA", "#E11D48": "#FB7185",
  "#C3CCD9": "#26304A", "#BDC7D7": "#33415C", "#C0CAD9": "#33415C",
  "#C8D1DE": "#33415C", "#D3DBE6": "#33415C", "#99F6E4": "#14532D",
};

const toDark = (svg) => {
  const missing = new Set();
  const out = svg.replace(/#[0-9A-Fa-f]{6}/g, (hex) => {
    const key = hex.toUpperCase();
    if (!(key in DARK)) missing.add(key);
    return DARK[key] ?? hex;
  });
  if (missing.size) throw new Error(`unmapped colours: ${[...missing].join(" ")}`);
  return out;
};

// Self-check: the map must reproduce the committed dark file. The shipped pair
// differs in one hand-tweaked stroke-opacity, which is normalised away here.
const norm = (s) => s.replace(/stroke-opacity="0\.65"/g, 'stroke-opacity="0.7"');
const shipped = norm(toDark(readFileSync(join(assets, "how-it-works-light.svg"), "utf8")));
const expected = norm(readFileSync(join(assets, "how-it-works-dark.svg"), "utf8"));
console.log(
  shipped === expected
    ? "self-check: map reproduces the shipped dark file"
    : "self-check: FAILED - map does not reproduce the shipped dark file",
);

const drafts = readdirSync(here).filter((f) => f.endsWith("-light.svg")).sort();
for (const file of drafts) {
  const light = readFileSync(join(here, file), "utf8");
  writeFileSync(join(here, file.replace("-light.svg", "-dark.svg")), toDark(light));

  const name = file.replace("-light.svg", "");
  const dark = readFileSync(join(here, `${name}-dark.svg`), "utf8");
  writeFileSync(
    join(here, `${name}.preview.html`),
    `<!doctype html><meta charset="utf-8"><style>
    html,body{margin:0;background:#EEF1F5}
    .wrap{padding:16px;display:flex;flex-direction:column;gap:16px;width:960px}
    svg *{animation:none!important}
    </style><div class="wrap">${light}${dark}</div>`,
  );
}
console.log(`built ${drafts.length} dark variant(s) + preview page(s)`);
