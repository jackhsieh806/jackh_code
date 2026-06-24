import admin from "firebase-admin";

const projectId = process.env.FIREBASE_PROJECT_ID || "livenote-app";

if (!admin.apps.length) {
  admin.initializeApp({
    credential: admin.credential.applicationDefault(),
    projectId,
  });
}

const db = admin.firestore();
const userCache = new Map();

function normalize(value) {
  return String(value ?? "").trim();
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

async function getOwnerName(uid, fallback = "") {
  if (userCache.has(uid)) return userCache.get(uid);
  const snap = await db.collection("users").doc(uid).get();
  const data = snap.data() || {};
  const ownerName = normalize(data.displayName) || normalize(data.email) || fallback || uid;
  userCache.set(uid, ownerName);
  return ownerName;
}

async function main() {
  console.log("Backfilling public_recipes from users/*/notes where visibility == public ...");
  const snapshot = await db.collectionGroup("notes").where("visibility", "==", "public").get();

  const rows = snapshot.docs.map((docSnap) => {
    const data = docSnap.data() || {};
    const noteId = docSnap.id;
    const ownerUid = docSnap.ref.parent.parent?.id || "";
    return {
      noteId,
      ownerUid,
      title: normalize(data.title),
      content: normalize(data.content),
      category: normalize(data.theme) || normalize(data.category) || "未分類",
      createdAt: timestampFrom(data.createdAt),
      updatedAt: timestampFrom(data.updatedAt || data.createdAt),
      avgRating: Number(data.avgRating || 0),
      ratingCount: Number(data.ratingCount || 0),
    };
  });

  const chunkSize = 350;
  for (let index = 0; index < rows.length; index += chunkSize) {
    const batch = db.batch();
    for (const row of rows.slice(index, index + chunkSize)) {
      const ownerName = await getOwnerName(row.ownerUid, row.ownerUid);
      const ref = db.collection("public_recipes").doc(row.noteId);
      batch.set(ref, {
        title: row.title,
        content: row.content,
        ownerUid: row.ownerUid,
        ownerName,
        category: row.category,
        createdAt: row.createdAt,
        updatedAt: row.updatedAt,
        avgRating: row.avgRating,
        ratingCount: row.ratingCount,
        visibility: "public",
      });
    }
    await batch.commit();
  }

  console.log(`Done. Mirrored ${rows.length} public notes into public_recipes in project ${projectId}.`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
