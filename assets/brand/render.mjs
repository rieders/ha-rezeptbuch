// Rendert assets/brand/icon.svg in die Brand-Bilder der Integration.
// Aufruf (aus dem Repo-Root, @resvg/resvg-js muss erreichbar sein):
//   node assets/brand/render.mjs
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const require = createRequire(process.env.RESVG_FROM ? join(process.env.RESVG_FROM, "x.js") : import.meta.url);
const { Resvg } = require("@resvg/resvg-js");

const here = dirname(fileURLToPath(import.meta.url));
const svg = readFileSync(join(here, "icon.svg"), "utf8");
const out = join(here, "..", "..", "custom_components", "rezeptbuch", "brand");
mkdirSync(out, { recursive: true });

for (const [name, size] of [["icon.png", 256], ["icon@2x.png", 512]]) {
  const png = new Resvg(svg, { fitTo: { mode: "width", value: size }, background: "rgba(0,0,0,0)" })
    .render()
    .asPng();
  writeFileSync(join(out, name), png);
  console.log(`${name}: ${size}x${size}, ${png.length} Bytes`);
}
