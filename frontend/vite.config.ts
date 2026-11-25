import { defineConfig } from "vitest/config";

// Ein einziges ES-Modul ohne externe Abhängigkeiten (keine CDNs, keine Webfonts),
// direkt in den Integrationsordner – von dort liefert HA es über panel_custom aus.
export default defineConfig({
  build: {
    target: "es2021",
    outDir: "../custom_components/rezeptbuch/frontend",
    emptyOutDir: true,
    sourcemap: false,
    minify: true,
    reportCompressedSize: true,
    lib: {
      entry: "src/rezeptbuch-panel.ts",
      formats: ["es"],
      fileName: () => "rezeptbuch-panel.js",
    },
    rolldownOptions: {
      output: { codeSplitting: false },
    },
  },
  test: {
    environment: "node",
    include: ["test/**/*.test.ts"],
  },
});
