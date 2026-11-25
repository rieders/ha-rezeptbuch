/// <reference types="node" />
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { de } from "../src/i18n/de";
import { en } from "../src/i18n/en";
import { errorText, pickLanguage, translator } from "../src/i18n";

const placeholders = (text: string) => [...text.matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort();

function sourceFiles(dir: string): string[] {
  return readdirSync(dir).flatMap((name: string) => {
    const path = join(dir, name);
    return statSync(path).isDirectory() ? sourceFiles(path) : path.endsWith(".ts") ? [path] : [];
  });
}

describe("Übersetzungen", () => {
  it("de und en haben genau dieselben Schlüssel", () => {
    expect(Object.keys(en).sort()).toEqual(Object.keys(de).sort());
  });

  it("Platzhalter stimmen in beiden Sprachen überein", () => {
    for (const key of Object.keys(de) as (keyof typeof de)[]) {
      expect(placeholders(en[key]), key).toEqual(placeholders(de[key]));
    }
  });

  it("keine leeren Texte", () => {
    for (const [key, value] of [...Object.entries(de), ...Object.entries(en)]) {
      expect(value.trim(), key).not.toBe("");
    }
  });

  it("jeder im Code verwendete Schlüssel existiert", () => {
    const used = new Set<string>();
    for (const file of sourceFiles(fileURLToPath(new URL("../src", import.meta.url)))) {
      const code = readFileSync(file, "utf8");
      for (const m of code.matchAll(/\bt\(\s*"([a-z_]+\.[a-z_]+)"/g)) used.add(m[1]);
    }
    expect(used.size).toBeGreaterThan(50);
    const missing = [...used].filter((k) => !(k in de));
    expect(missing).toEqual([]);
  });

  it("wählt die Sprache nach hass.language", () => {
    expect(pickLanguage("de")).toBe("de");
    expect(pickLanguage("de-CH")).toBe("de");
    expect(pickLanguage("en-GB")).toBe("en");
    expect(pickLanguage("fr")).toBe("en");
    expect(pickLanguage(undefined)).toBe("en");
    expect(translator("de")("nav.recipes")).toBe("Rezepte");
    expect(translator("en")("nav.recipes")).toBe("Recipes");
  });

  it("ersetzt Platzhalter", () => {
    expect(translator("de")("list.count", { n: 3 })).toBe("3 Rezepte");
    expect(translator("en")("timer.done", { label: "Pasta" })).toBe("Done: Pasta");
  });

  it("übersetzt bekannte Fehlercodes, sonst Servermeldung", () => {
    const t = translator("de");
    expect(errorText(t, { code: "unauthorized", message: "x" })).toBe("Dafür sind Administratorrechte nötig.");
    expect(errorText(t, { code: "seltsam", message: "Kaputt" })).toBe("Fehler: Kaputt");
  });
});
