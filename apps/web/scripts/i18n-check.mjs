#!/usr/bin/env node

import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const messagesDir = path.resolve(__dirname, "../messages");
const referenceFile = path.join(messagesDir, "en.json");

if (!fs.existsSync(referenceFile)) {
  console.error("Reference translation file en.json not found!");
  process.exit(1);
}

const reference = JSON.parse(fs.readFileSync(referenceFile, "utf-8"));

function getKeys(obj, prefix = "") {
  let keys = [];
  for (const [key, value] of Object.entries(obj)) {
    const fullKey = prefix ? `${prefix}.${key}` : key;
    if (typeof value === "object" && value !== null) {
      keys = keys.concat(getKeys(value, fullKey));
    } else {
      keys.push({ key: fullKey, value });
    }
  }
  return keys;
}

function extractPlaceholders(str) {
  const matches = str.match(/\{([a-zA-Z0-9_]+)\}/g) || [];
  return matches.map((m) => m.slice(1, -1)).sort();
}

const refKeys = getKeys(reference);
const refKeyMap = new Map(refKeys.map((k) => [k.key, k.value]));

console.log("Checking i18n translation key parity across languages...");
console.log(`Reference (en.json): ${refKeys.length} total translation keys\n`);

let hasError = false;
const files = fs.readdirSync(messagesDir).filter((f) => f.endsWith(".json") && f !== "en.json");

for (const file of files) {
  const filePath = path.join(messagesDir, file);
  const data = JSON.parse(fs.readFileSync(filePath, "utf-8"));
  const currentKeys = getKeys(data);
  const currentKeyMap = new Map(currentKeys.map((k) => [k.key, k.value]));

  console.log(`Analyzing: ${file}...`);
  let missing = 0;
  let placeholderMismatches = 0;

  for (const [key, refVal] of refKeyMap.entries()) {
    if (!currentKeyMap.has(key)) {
      console.error(`  [MISSING KEY] ${key}`);
      missing++;
      hasError = true;
    } else {
      const curVal = currentKeyMap.get(key);
      if (typeof refVal === "string" && typeof curVal === "string") {
        const refPh = extractPlaceholders(refVal);
        const curPh = extractPlaceholders(curVal);
        if (refPh.join(",") !== curPh.join(",")) {
          console.error(
            `  [PLACEHOLDER MISMATCH] ${key}: Expected {${refPh.join(", ")}}, got {${curPh.join(", ")}}`
          );
          placeholderMismatches++;
          hasError = true;
        }
      }
    }
  }

  if (missing === 0 && placeholderMismatches === 0) {
    console.log(`  ✅ 100% key parity with en.json (${currentKeys.length} keys)\n`);
  } else {
    console.error(`  ❌ Errors: ${missing} missing, ${placeholderMismatches} placeholder mismatches\n`);
  }
}

if (hasError) {
  console.error("i18n parity check FAILED. Please resolve missing keys or placeholders.");
  process.exit(1);
} else {
  console.log("All translation files passed parity check successfully! 🎉");
  process.exit(0);
}
