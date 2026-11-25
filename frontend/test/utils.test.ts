import { describe, expect, it } from "vitest";
import { formatClock, formatMinutes, splitLines, splitSteps, splitTags } from "../src/format";
import { translator } from "../src/i18n";
import { MAX_UPLOAD_DIMENSION, targetSize } from "../src/image";
import { parseRoute, routePath } from "../src/router";

describe("Router", () => {
  it.each([
    ["", { view: "list" }],
    ["/", { view: "list" }],
    ["/rezept/12", { view: "recipe", recipeId: 12 }],
    ["/rezept/abc", { view: "list" }],
    ["/entwuerfe", { view: "drafts" }],
    ["/entwurf/3", { view: "draft", draftId: 3 }],
    ["/entwurf/0", { view: "drafts" }],
    ["/import", { view: "import" }],
    ["/unbekannt", { view: "list" }],
  ])("%s", (path, route) => {
    expect(parseRoute(path)).toEqual(route);
  });

  it("baut Pfade zurück", () => {
    for (const path of ["/rezept/5", "/entwuerfe", "/entwurf/7", "/import", ""]) {
      expect(routePath(parseRoute(path))).toBe(path);
    }
  });
});

describe("Formatierung", () => {
  const de = translator("de");
  it("Minuten", () => {
    expect(formatMinutes(de, 45)).toBe("45 Min.");
    expect(formatMinutes(de, 60)).toBe("1 Std.");
    expect(formatMinutes(de, 95)).toBe("1 Std. 35 Min.");
    expect(formatMinutes(de, null)).toBe("");
  });
  it("Uhr", () => {
    expect(formatClock(65_000)).toBe("1:05");
    expect(formatClock(3_725_000)).toBe("1:02:05");
    expect(formatClock(-5)).toBe("0:00");
    expect(formatClock(1)).toBe("0:01"); // aufrunden, nie zu früh 0:00
  });
  it("Editor-Zeilen", () => {
    expect(splitLines(" 200 g Mehl \n\n1 Ei\n")).toEqual(["200 g Mehl", "1 Ei"]);
    expect(splitSteps("Teig kneten.\nRuhen lassen.\n\n  Backen. \n\n")).toEqual([
      "Teig kneten. Ruhen lassen.",
      "Backen.",
    ]);
    expect(splitTags("Sommer, Grillen,,Sommer ")).toEqual(["Sommer", "Grillen"]);
  });
});

describe("Bildverkleinerung", () => {
  it("behält kleine Bilder", () => {
    expect(targetSize(800, 600)).toEqual([800, 600]);
  });
  it("verkleinert die längere Kante auf das Maximum", () => {
    expect(targetSize(4000, 3000)).toEqual([MAX_UPLOAD_DIMENSION, 1800]);
    expect(targetSize(3000, 6000)).toEqual([1200, MAX_UPLOAD_DIMENSION]);
  });
});
