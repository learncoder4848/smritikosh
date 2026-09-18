import { readFileSync, writeFileSync, readdirSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));

// light token -> dark token, matching the palette already used by assets/*-dark.svg
const DARK = {
  "#FFFFFF": "#0B1020", "#FDFDFD": "#0D1424", "#C3CCD9": "#26304A",
  "#BDC7D7": "#2B3653", "#D3DBE6": "#2B3653", "#C8D1DE": "#232D46",
  "#C0CAD9": "#202B44", "#E2E8F0": "#1E2740", "#E8EDF3": "#1C2539",
  "#EDF1F7": "#1A2237", "#F7F9FC": "#131A2E", "#D7DEE8": "#2A3450",
  "#B2BFD1": "#3A4665",
  "#0F172A": "#E6EAF2", "#334155": "#C7D0E2", "#64748B": "#9AA4BA",
  "#94A3B8": "#77839C",
  "#2563EB": "#4C8DFF", "#9EC0F5": "#2E4E85", "#DBEAFE": "#25406E",
  "#059669": "#34D399", "#047857": "#34D399", "#D8F3E8": "#12352C",
  "#F1FAF6": "#0F2B24", "#BFE3D3": "#1F4A3C",
  "#B45309": "#FBBF24", "#FBE8CE": "#3A2A10",
  "#7C3AED": "#A78BFA", "#EDE3FD": "#2A2149", "#C3AEEF": "#4B3A75",
  "#E11D48": "#FB7185", "#BE123C": "#FB7185", "#FDA4AF": "#9F1239",
  "#FFE4E6": "#3B1420", "#FEF2F3": "#21121A", "#F2C9CF": "#4A2230",
};

const drafts = readdirSync(here).filter((f) => f.endsWith("-light.svg")).sort();
const unmapped = new Set();

for (const file of drafts) {
  const light = readFileSync(join(here, file), "utf8");
  const dark = light.replace(/#[0-9A-Fa-f]{6}/g, (hex) => {
    const key = hex.toUpperCase();
    if (!(key in DARK)) unmapped.add(key);
    return DARK[key] ?? hex;
  });
  writeFileSync(join(here, file.replace("-light.svg", "-dark.svg")), dark);
}

if (unmapped.size) console.log("UNMAPPED:", [...unmapped].join(" "));

// one preview page per draft: light above, dark below, animations frozen at rest
for (const file of drafts) {
  const name = file.replace("-light.svg", "");
  const html = `<!doctype html><meta charset="utf-8"><style>
  html,body{margin:0;background:#EEF1F5}
  .wrap{padding:16px;display:flex;flex-direction:column;gap:16px;width:960px}
  svg *{animation:none!important}
  </style><div class="wrap">
  ${readFileSync(join(here, file), "utf8")}
  ${readFileSync(join(here, `${name}-dark.svg`), "utf8")}
  </div>`;
  writeFileSync(join(here, `${name}.preview.html`), html);
}

console.log(`built ${drafts.length} dark variants + preview pages`);
