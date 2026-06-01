import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const COOK_DIR = path.join(ROOT, "cook");
const OUTPUT_DIR = path.join(ROOT, "outputs");
const OUTPUT_XLSX = path.join(OUTPUT_DIR, "cook-classified.xlsx");
const GOOGLE_SCRIPT_URL =
  "https://script.google.com/macros/s/AKfycbwif1Vtd9mc1PfJyX33EMaenRNj2sg2j4-3dlP5Qw0wAh7XLJECFY9SgcdtLXZhay0DXg/exec";
const GOOGLE_PASSCODE = "3141";

const HEADERS = [
  "id",
  "status",
  "theme",
  "theme_icon",
  "theme_color",
  "category",
  "title",
  "summary",
  "content",
  "tags",
  "updated_at",
];

const THEME = {
  name: "食譜",
  icon: "🍳",
  color: "#b14f35",
};

const TITLE_RULES = [
  { test: /^(無標題|Untitled)/i, category: "中式" },
  { test: /日式|蕎麥|豚汁|味增|甘露煮|牛蒡|天婦羅|湯咖哩/, category: "日式" },
  {
    test: /ジェノベーゼ|pasta|義大利|意大利|燉飯|羅宋|奶酪|牛奶鍋|起司|烤鯖魚|烤起司鮭魚/,
    category: "西式",
  },
  { test: /綠咖哩/, category: "日式" },
  {
    test: /豆花|三杯|糖醋|紅燒|花雕|蔥油|魚香|清蒸|番茄炒蛋|烘蛋|炸雞|雞|魚|牛|豬|里肌|鱸|鯖|鮭|炒飯|蛋包飯|蒸蛋|高麗菜|青菜|海帶|金針菇|茄子|涼拌|醬拌|麻油|醃料|醬|胡麻|麵|乾麵|炒麵|涼麵|番茄麵/,
    category: "中式",
  },
];

function normalizeText(value) {
  return String(value ?? "").normalize("NFC").trim();
}

function slugify(value) {
  return normalizeText(value)
    .toLowerCase()
    .replace(/[^\p{L}\p{N}]+/gu, "-")
    .replace(/^-+|-+$/g, "");
}

function stripXmlTags(text) {
  return normalizeText(text)
    .replace(/<br\s*\/?>/gi, "\n")
    .replace(/<\/div>|<\/p>|<\/li>|<\/h\d>/gi, "\n")
    .replace(/<[^>]+>/g, "")
    .replace(/\r/g, "")
    .split("\n")
    .map((line) => line.replace(/\s+/g, " ").trim())
    .filter(Boolean)
    .join("\n")
    .trim();
}

function extractXmlValue(source, tagName) {
  const match = source.match(new RegExp(`<${tagName}>([\\s\\S]*?)</${tagName}>`, "i"));
  return match ? match[1].trim() : "";
}

function parseZnNote(buffer) {
  const start = buffer.indexOf(Buffer.from("<ZNote"));
  const xmlText = start >= 0 ? buffer.slice(start).toString("utf8") : buffer.toString("utf8");
  const titleFromMeta = extractXmlValue(xmlText, "ZTitle");
  const modifiedDate = extractXmlValue(xmlText, "ZModifiedDate");
  const contentMatch = xmlText.match(/<ZContent><!\[CDATA\[([\s\S]*?)\]\]><\/ZContent>/i);
  return {
    titleFromMeta: normalizeText(titleFromMeta),
    modifiedDate: normalizeText(modifiedDate),
    content: stripXmlTags(contentMatch ? contentMatch[1] : ""),
  };
}

function classifyTitle(title) {
  const clean = normalizeText(title);
  for (const rule of TITLE_RULES) {
    if (rule.test.test(clean)) return rule.category;
  }
  return "中式";
}

function inferredTags(title, category) {
  const tags = new Set(["自動分類", THEME.name, category]);
  const keywords = [
    "日式",
    "西式",
    "中式",
    "雞",
    "魚",
    "牛",
    "豬",
    "蛋",
    "飯",
    "麵",
    "湯",
    "鍋",
    "甜點",
    "咖哩",
    "配菜",
    "調味",
  ];
  for (const word of keywords) {
    if (title.includes(word)) tags.add(word);
  }
  return [...tags].join(",");
}

function toDateOnly(value, fallbackFile) {
  if (value) return value.slice(0, 10);
  return fallbackFile.toISOString().slice(0, 10);
}

function summarize(category) {
  return `自動分類：${THEME.name} / ${category}`;
}

function toRow(fileName, fileStat, parsed) {
  const title = normalizeText(fileName.replace(/\.znote$/i, "")) || "未命名";
  const category = classifyTitle(title);
  return {
    id: `cook-${slugify(title) || "note"}`,
    status: "active",
    theme: THEME.name,
    theme_icon: THEME.icon,
    theme_color: THEME.color,
    category,
    title,
    summary: summarize(category),
    content: parsed.content || summarize(category),
    tags: inferredTags(title, category),
    updated_at: toDateOnly(parsed.modifiedDate, fileStat.mtime),
  };
}

async function loadCookRows() {
  const files = (await fs.readdir(COOK_DIR)).filter((name) => name.toLowerCase().endsWith(".znote"));
  files.sort((a, b) => a.localeCompare(b, "zh-Hant"));
  const rows = [];
  for (const fileName of files) {
    const filePath = path.join(COOK_DIR, fileName);
    const [buffer, stat] = await Promise.all([fs.readFile(filePath), fs.stat(filePath)]);
    rows.push(toRow(fileName, stat, parseZnNote(buffer)));
  }
  return rows;
}

function countBy(rows, key) {
  return rows.reduce((acc, row) => {
    const value = normalizeText(row[key]) || "未分類";
    acc.set(value, (acc.get(value) || 0) + 1);
    return acc;
  }, new Map());
}

function buildAnalysisRows(rows) {
  const categoryCounts = countBy(rows, "category");
  return [
    ["metric", "value", ""],
    ["total_notes", rows.length, ""],
    ["recipes", rows.length, ""],
    ["", "", ""],
    ["category", "count", ""],
    ...[...categoryCounts.entries()]
      .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0], "zh-Hant"))
      .map(([category, count]) => [category, count, ""]),
  ];
}

async function updateWorkbook(rows) {
  const input = await FileBlob.load(path.join(ROOT, "data.xlsx"));
  const workbook = await SpreadsheetFile.importXlsx(input);
  const notesSheet = workbook.worksheets.getItem("notes");
  const values = [HEADERS, ...rows.map((row) => HEADERS.map((header) => row[header] ?? ""))];
  notesSheet.getRange(`A1:K${values.length}`).values = values;

  let analysisSheet;
  try {
    analysisSheet = workbook.worksheets.getItem("analysis");
  } catch {
    analysisSheet = workbook.worksheets.add("analysis");
  }
  analysisSheet.getRange(`A1:C${buildAnalysisRows(rows).length}`).values = buildAnalysisRows(rows);

  await fs.mkdir(OUTPUT_DIR, { recursive: true });
  const output = await SpreadsheetFile.exportXlsx(workbook);
  await output.save(OUTPUT_XLSX);
}

async function syncToGoogle(rows) {
  const scriptUrl = process.env.GOOGLE_SCRIPT_URL || GOOGLE_SCRIPT_URL;
  const passcode = process.env.GOOGLE_PASSCODE || GOOGLE_PASSCODE;

  let synced = 0;
  for (const row of rows) {
    const response = await fetch(scriptUrl, {
      method: "POST",
      headers: { "Content-Type": "text/plain;charset=utf-8" },
      body: JSON.stringify({
        action: "upsert",
        passcode,
        row,
      }),
    });
    if (!response.ok) {
      const body = await response.text().catch(() => "");
      throw new Error(`Google Sheets sync failed for ${row.id}: ${response.status} ${body}`);
    }
    synced += 1;
  }
  return synced;
}

async function main() {
  const rows = await loadCookRows();
  await updateWorkbook(rows);

  const shouldSync = process.argv.includes("--sync");
  const synced = shouldSync ? await syncToGoogle(rows) : 0;

  console.log(
    JSON.stringify(
      {
        rows: rows.length,
        output: OUTPUT_XLSX,
        synced,
        categoryCounts: [...countBy(rows, "category").entries()]
          .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0], "zh-Hant"))
          .map(([category, count]) => `${category}:${count}`)
          .join(", "),
      },
      null,
      2,
    ),
  );
}

await main();
