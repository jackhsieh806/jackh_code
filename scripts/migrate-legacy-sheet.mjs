import admin from "firebase-admin";

const projectId = process.env.FIREBASE_PROJECT_ID || "livenote-app";
const uid = normalize(process.env.TARGET_UID);
const sourceUrl = normalize(process.env.LEGACY_SHEET_URL);
const sourcePasscode = normalize(process.env.LEGACY_SHEET_PASSCODE);
const displayName = normalize(process.env.TARGET_DISPLAY_NAME);
const email = normalize(process.env.TARGET_EMAIL);
const photoURL = normalize(process.env.TARGET_PHOTO_URL);

if (!uid) {
  throw new Error("Missing TARGET_UID.");
}

if (!sourceUrl) {
  throw new Error("Missing LEGACY_SHEET_URL.");
}

if (!admin.apps.length) {
  admin.initializeApp({
    credential: admin.credential.applicationDefault(),
    projectId,
  });
}

const db = admin.firestore();

function normalize(value) {
  return String(value ?? "").trim();
}

function randomId() {
  return typeof crypto !== "undefined" && crypto.randomUUID ? crypto.randomUUID() : `note-${Date.now().toString(36)}`;
}

function asDate(value) {
  if (!value) return null;
  if (typeof value.toDate === "function") return value.toDate();
  if (value instanceof Date) return value;
  if (typeof value === "number") return new Date(value);
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

function timestampFrom(value) {
  const date = asDate(value) || new Date();
  return admin.firestore.Timestamp.fromDate(date);
}

function pick(row, keys) {
  for (const key of keys) {
    const value = normalize(row?.[key]);
    if (value) return value;
  }
  return "";
}

function normalizeLegacyRow(row) {
  const title = pick(row, ["title", "名稱", "name"]);
  const content = pick(row, ["content", "內容", "body"]);
  const theme = pick(row, ["theme", "主題"]) || "未分類";
  const category = pick(row, ["category", "分類"]) || "未分類";
  const id = pick(row, ["id", "ID"]) || randomId();
  const createdAt = timestampFrom(pick(row, ["createdAt", "created_at", "created_at"]));
  const updatedAt = timestampFrom(pick(row, ["updatedAt", "updated_at", "updated_at"]) || createdAt.toDate());
  return {
    id,
    title,
    content,
    theme,
    category,
    createdAt,
    updatedAt,
  };
}

async function fetchLegacyRows() {
  const url = new URL(sourceUrl);
  url.searchParams.set("action", "list");
  if (sourcePasscode) url.searchParams.set("passcode", sourcePasscode);

  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Legacy source request failed: ${response.status} ${response.statusText}`);
  }

  const payload = await response.json();
  const rows = Array.isArray(payload) ? payload : Array.isArray(payload?.rows) ? payload.rows : [];
  return rows.map(normalizeLegacyRow).filter((row) => row.title || row.content || row.theme || row.category);
}

async function ensureUserDocument() {
  const ref = db.collection("users").doc(uid);
  const snap = await ref.get();
  const payload = {
    displayName,
    email,
    photoURL,
    lastLoginAt: admin.firestore.FieldValue.serverTimestamp(),
  };
  if (!snap.exists) payload.createdAt = admin.firestore.FieldValue.serverTimestamp();
  await ref.set(payload, { merge: true });
}

async function importRows(rows) {
  const chunkSize = 400;
  for (let index = 0; index < rows.length; index += chunkSize) {
    const batch = db.batch();
    for (const row of rows.slice(index, index + chunkSize)) {
      const ref = db.collection(`users/${uid}/notes`).doc(row.id);
      batch.set(ref, {
        title: row.title,
        content: row.content,
        theme: row.theme,
        category: row.category,
        createdAt: row.createdAt,
        updatedAt: row.updatedAt,
      });
    }
    await batch.commit();
  }
}

async function main() {
  console.log(`Importing legacy rows into users/${uid}/notes ...`);
  await ensureUserDocument();
  const rows = await fetchLegacyRows();
  await importRows(rows);
  console.log(`Done. Imported ${rows.length} notes into Firestore project ${projectId}.`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
