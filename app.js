import { initializeApp } from "https://www.gstatic.com/firebasejs/11.8.1/firebase-app.js";
import {
  GoogleAuthProvider,
  browserLocalPersistence,
  getAuth,
  onAuthStateChanged,
  setPersistence,
  signInWithPopup,
  signOut,
} from "https://www.gstatic.com/firebasejs/11.8.1/firebase-auth.js";
import {
  Timestamp,
  collection,
  deleteDoc,
  doc,
  getDoc,
  getFirestore,
  onSnapshot,
  orderBy,
  query,
  serverTimestamp,
  setDoc,
  writeBatch,
} from "https://www.gstatic.com/firebasejs/11.8.1/firebase-firestore.js";

const firebaseConfig = {
  apiKey: "AIzaSyBhcTOJQGsa4uAY2Y3IuI1rFpz_39wDTuY",
  authDomain: "livenote-app.firebaseapp.com",
  projectId: "livenote-app",
  storageBucket: "livenote-app.firebasestorage.app",
  messagingSenderId: "325304749270",
  appId: "1:325304749270:web:efd78aa9a0cb8dbd1dcd77",
  measurementId: "G-LQ35M4TPGQ",
};

const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
const db = getFirestore(app);
const googleProvider = new GoogleAuthProvider();

googleProvider.addScope("https://www.googleapis.com/auth/spreadsheets");
googleProvider.addScope("https://www.googleapis.com/auth/drive.file");
googleProvider.setCustomParameters({ prompt: "select_account" });

setPersistence(auth, browserLocalPersistence).catch(() => {});

const THEME_META = {
  食譜: { icon: "🍳", color: "#b14f35" },
  生活備忘: { icon: "🗂", color: "#2e6f6b" },
  工作: { icon: "💼", color: "#5671a6" },
  讀書: { icon: "📚", color: "#8b5e3c" },
  旅行: { icon: "✈️", color: "#5b7c8a" },
  學習: { icon: "🧠", color: "#7b5ea7" },
};

const FALLBACK_PALETTE = [
  { icon: "🗂", color: "#2e6f6b" },
  { icon: "🍳", color: "#b14f35" },
  { icon: "💼", color: "#5671a6" },
  { icon: "📚", color: "#8b5e3c" },
  { icon: "✈️", color: "#5b7c8a" },
  { icon: "🧠", color: "#7b5ea7" },
];

const content = document.querySelector("#content");
const pageTitle = document.querySelector("#pageTitle");
const crumbLabel = document.querySelector("#crumbLabel");
const backButton = document.querySelector("#backButton");
const searchInput = document.querySelector("#searchInput");
const drawer = document.querySelector("#drawer");
const editorModal = document.querySelector("#editorModal");
const editorForm = document.querySelector("#editorForm");
const advancedToggleButton = document.querySelector("#advancedToggleButton");
const advancedFields = document.querySelector("#advancedFields");
const themeSelect = document.querySelector("#themeSelect");
const categorySelect = document.querySelector("#categorySelect");
const themeCustomRow = document.querySelector("#themeCustomRow");
const categoryCustomRow = document.querySelector("#categoryCustomRow");
const themeCustomInput = document.querySelector("#themeCustomInput");
const categoryCustomInput = document.querySelector("#categoryCustomInput");
const editIdInput = document.querySelector("#editId");
const syncStatus = document.querySelector("#syncStatus");
const authStatus = document.querySelector("#authStatus");
const authProfile = document.querySelector("#authProfile");
const authAvatar = document.querySelector("#authAvatar");
const authName = document.querySelector("#authName");
const authEmail = document.querySelector("#authEmail");
const authUid = document.querySelector("#authUid");
const signInButton = document.querySelector("#signInButton");
const signOutButton = document.querySelector("#signOutButton");
const exportCsvButton = document.querySelector("#exportCsvButton");
const exportGoogleSheetButton = document.querySelector("#exportGoogleSheetButton");
const importInput = document.querySelector("#importInput");
const newItemButton = document.querySelector("#newItemButton");
const toolsButton = document.querySelector("#toolsButton");
const closeDrawerButton = document.querySelector("#closeDrawerButton");
const closeEditorButton = document.querySelector("#closeEditorButton");
const deleteButton = document.querySelector("#deleteButton");

let currentUser = null;
let googleAccessToken = "";
let notes = [];
let notesLoaded = false;
let notesUnsubscribe = null;
let authReady = false;
let route = { view: "home", theme: "", category: "", id: "" };
let syncMessage = "請先登入 Google 帳號。";
let currentEditId = "";

function normalize(value) {
  return String(value ?? "").trim();
}

function escapeHtml(value) {
  return normalize(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function today() {
  return new Date().toISOString().slice(0, 10);
}

function slug(value) {
  return encodeURIComponent(normalize(value));
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

function formatDate(value) {
  const date = asDate(value);
  return date ? date.toISOString().slice(0, 10) : today();
}

function toTimestamp(value) {
  const date = asDate(value) || new Date(`${today()}T12:00:00`);
  return Timestamp.fromDate(date);
}

function summaryFromContent(content) {
  const text = normalize(content).replace(/\s+/g, " ");
  return text.length > 72 ? `${text.slice(0, 72)}…` : text || "沒有內容";
}

function themeMeta(theme) {
  const key = normalize(theme);
  if (THEME_META[key]) return THEME_META[key];
  const seed = [...key].reduce((sum, char) => sum + char.codePointAt(0), 0);
  return FALLBACK_PALETTE[seed % FALLBACK_PALETTE.length];
}

function userDocRef(uid) {
  return doc(db, "users", uid);
}

function notesCollection(uid) {
  return collection(db, "users", uid, "notes");
}

function noteDocRef(uid, noteId) {
  return doc(db, "users", uid, "notes", noteId);
}

function noteFromSnapshot(snapshot) {
  const data = snapshot.data() || {};
  return {
    id: snapshot.id,
    title: normalize(data.title),
    content: normalize(data.content),
    theme: normalize(data.theme) || "未分類",
    category: normalize(data.category) || "未分類",
    createdAt: data.createdAt || null,
    updatedAt: data.updatedAt || null,
  };
}

function buildVisibleNotes() {
  const queryText = normalize(searchInput.value).toLowerCase();
  const base = notes.slice();
  if (!queryText) return base;
  return base.filter((note) =>
    [note.theme, note.category, note.title, note.content].some((field) =>
      normalize(field).toLowerCase().includes(queryText),
    ),
  );
}

function groupBy(items, key) {
  return items.reduce((acc, item) => {
    const name = normalize(item[key]) || "未分類";
    if (!acc[name]) acc[name] = [];
    acc[name].push(item);
    return acc;
  }, {});
}

function uniqueSortedValues(key) {
  return [...new Set(notes.map((note) => normalize(note[key])).filter(Boolean))].sort((a, b) =>
    a.localeCompare(b, "zh-Hant"),
  );
}

function setSelectOptions(selectEl, values, currentValue) {
  if (!selectEl) return;
  const options = values.map((value) => `<option value="${escapeHtml(value)}">${escapeHtml(value)}</option>`).join("");
  selectEl.innerHTML = `${options}<option value="__custom__">+ 自訂</option>`;
  if (currentValue && values.includes(currentValue)) selectEl.value = currentValue;
  else if (currentValue) selectEl.value = "__custom__";
  else if (values.length > 0) selectEl.selectedIndex = 0;
  else selectEl.value = "__custom__";
}

function toggleCustomRow(selectEl, rowEl, inputEl, fallback = "") {
  if (!selectEl || !rowEl || !inputEl) return;
  const isCustom = selectEl.value === "__custom__";
  rowEl.classList.toggle("is-hidden", !isCustom);
  if (isCustom) {
    inputEl.value = fallback || inputEl.value || "";
  } else {
    inputEl.value = "";
  }
}

function collectChosenValue(selectEl, customInputEl, fallback = "") {
  if (!selectEl) return fallback;
  if (selectEl.value === "__custom__") return normalize(customInputEl?.value) || fallback;
  return normalize(selectEl.value) || fallback;
}

function setStatus(message) {
  syncMessage = message;
  if (syncStatus) syncStatus.textContent = message;
  if (currentUser) render();
}

function setAuthStatus(message) {
  if (authStatus) authStatus.textContent = message;
}

function readRoute() {
  const [view = "home", theme = "", category = "", id = ""] = location.hash.replace(/^#\/?/, "").split("/").map(decodeURIComponent);
  route = { view, theme, category, id };
}

function setRoute(nextRoute) {
  route = nextRoute;
  const parts = [nextRoute.view, nextRoute.theme, nextRoute.category, nextRoute.id].filter(Boolean).map(slug);
  location.hash = parts.join("/");
  render();
}

function openDrawer() {
  drawer.classList.add("is-open");
  drawer.setAttribute("aria-hidden", "false");
}

function closeDrawer() {
  drawer.classList.remove("is-open");
  drawer.setAttribute("aria-hidden", "true");
}

function closeEditor() {
  editorModal.classList.remove("is-open");
  editorModal.setAttribute("aria-hidden", "true");
}

function openEditor(note = null) {
  if (!currentUser) {
    setStatus("請先登入 Google 帳號後再新增或編輯筆記。");
    return;
  }

  const isEdit = Boolean(note);
  const existingTheme = route.theme || note?.theme || "";
  const existingCategory = route.category || note?.category || "";

  currentEditId = note?.id || randomId();
  editorForm.reset();
  editIdInput.value = currentEditId;

  document.querySelector("#editorModeLabel").textContent = isEdit ? "編輯" : "新增";
  document.querySelector("#editorTitle").textContent = isEdit ? normalize(note.title) || "編輯筆記" : "新增筆記";

  editorForm.elements.title.value = normalize(note?.title);
  editorForm.elements.content.value = normalize(note?.content);
  editorForm.elements.updated_at.value = formatDate(note?.updatedAt || new Date());

  setSelectOptions(themeSelect, uniqueSortedValues("theme"), normalize(existingTheme || note?.theme));
  setSelectOptions(categorySelect, uniqueSortedValues("category"), normalize(existingCategory || note?.category));
  toggleCustomRow(themeSelect, themeCustomRow, themeCustomInput, normalize(existingTheme || note?.theme));
  toggleCustomRow(categorySelect, categoryCustomRow, categoryCustomInput, normalize(existingCategory || note?.category));
  advancedFields?.classList.add("is-collapsed");
  if (advancedToggleButton) advancedToggleButton.textContent = "顯示進階欄位";
  deleteButton.style.visibility = isEdit ? "visible" : "hidden";
  editorModal.classList.add("is-open");
  editorModal.setAttribute("aria-hidden", "false");
}

function buildNotePayload(existing = null) {
  const data = Object.fromEntries(new FormData(editorForm).entries());
  const theme = collectChosenValue(themeSelect, themeCustomInput, route.theme || existing?.theme || "未分類");
  const category = collectChosenValue(categorySelect, categoryCustomInput, route.category || existing?.category || "未分類");
  const updatedAt = toTimestamp(data.updated_at || today());
  const createdAt = existing?.createdAt ? existing.createdAt : updatedAt;
  return {
    title: normalize(data.title),
    content: normalize(data.content),
    theme,
    category,
    createdAt,
    updatedAt,
  };
}

function noteMatchesRoute(note) {
  if (route.view === "theme") return normalize(note.theme) === normalize(route.theme);
  if (route.view === "category") {
    return normalize(note.theme) === normalize(route.theme) && normalize(note.category) === normalize(route.category);
  }
  if (route.view === "detail") return normalize(note.id) === normalize(route.id);
  return true;
}

function visibleNotes() {
  return buildVisibleNotes().filter(noteMatchesRoute);
}

function renderEmpty(message) {
  return `<div class="empty-state">${escapeHtml(message)}</div>`;
}

function renderHome() {
  pageTitle.textContent = "LiveNote";
  backButton.style.visibility = "hidden";
  crumbLabel.textContent = currentUser ? "我的筆記" : "請先登入";

  if (!currentUser) {
    content.innerHTML = renderEmpty("請先在右側登入 Google 帳號，才能讀取你的 Firestore 筆記。");
    return;
  }

  if (!notesLoaded) {
    content.innerHTML = renderEmpty("正在載入你的筆記...");
    return;
  }

  const rows = visibleNotes();
  if (rows.length === 0) {
    content.innerHTML = renderEmpty("目前沒有可顯示的筆記。");
    return;
  }

  const groups = groupBy(rows, "theme");
  const status = syncMessage ? `<div class="sync-banner">${escapeHtml(syncMessage)}</div>` : "";
  const cards = Object.entries(groups)
    .map(([theme, items]) => {
      const meta = themeMeta(theme);
      const categories = groupBy(items, "category");
      const summary = Object.entries(categories)
        .map(([name, list]) => `${escapeHtml(name)} (${list.length})`)
        .join(" | ");
      return `<button class="tile" type="button" style="--tile-color:${escapeHtml(meta.color)};" data-theme="${escapeHtml(theme)}">
        <div>
          <span class="tile-icon">${escapeHtml(meta.icon)}</span>
          <h2>${escapeHtml(theme)}</h2>
          <p>${summary}</p>
        </div>
        <div class="count-strip">
          ${Object.entries(categories)
            .slice(0, 4)
            .map(([name, list]) => {
              const width = Math.max(18, Math.round((list.length / items.length) * 100));
              return `<div class="bar" style="--tile-color:${escapeHtml(meta.color)};">
                <span>${escapeHtml(name)}</span>
                <span class="bar-track"><span class="bar-fill" style="--bar-width:${width}%"></span></span>
                <span>${list.length}</span>
              </div>`;
            })
            .join("")}
        </div>
      </button>`;
    })
    .join("");

  content.innerHTML = `${status}${cards ? `<div class="tile-grid">${cards}</div>` : renderEmpty("沒有找到可顯示的主題。")}`;
  content.querySelectorAll("[data-theme]").forEach((button) => {
    button.addEventListener("click", () => setRoute({ view: "theme", theme: button.dataset.theme, category: "", id: "" }));
  });
}

function renderTheme() {
  const rows = visibleNotes().filter((note) => normalize(note.theme) === normalize(route.theme));
  const meta = themeMeta(route.theme);
  pageTitle.textContent = route.theme || "主題";
  crumbLabel.textContent = "主題分類";
  backButton.style.visibility = "visible";

  if (rows.length === 0) {
    content.innerHTML = renderEmpty("這個主題目前沒有資料。");
    return;
  }

  const groups = groupBy(rows, "category");
  const cards = Object.entries(groups)
    .map(
      ([category, items]) => `<button class="tile" type="button" style="--tile-color:${escapeHtml(meta.color)};" data-category="${escapeHtml(category)}">
        <div>
          <span class="tile-icon">${escapeHtml(meta.icon)}</span>
          <h2>${escapeHtml(category)}</h2>
          <p>${items.length} 筆筆記</p>
        </div>
        <div class="count-strip">
          <div class="bar" style="--tile-color:${escapeHtml(meta.color)};">
            <span>筆記</span>
            <span class="bar-track"><span class="bar-fill" style="--bar-width:${Math.min(100, Math.round((items.length / rows.length) * 100))}%"></span></span>
            <span>${items.length}</span>
          </div>
        </div>
      </button>`,
    )
    .join("");

  content.innerHTML = cards ? `<div class="tile-grid">${cards}</div>` : renderEmpty("這個主題目前沒有分類。");
  content.querySelectorAll("[data-category]").forEach((button) => {
    button.addEventListener("click", () =>
      setRoute({ view: "category", theme: route.theme, category: button.dataset.category, id: "" }),
    );
  });
}

function renderCategory() {
  const rows = visibleNotes().filter(
    (note) => normalize(note.theme) === normalize(route.theme) && normalize(note.category) === normalize(route.category),
  );
  pageTitle.textContent = route.category || "分類";
  crumbLabel.textContent = route.theme || "主題";
  backButton.style.visibility = "visible";

  if (rows.length === 0) {
    content.innerHTML = renderEmpty("這個分類目前沒有資料。");
    return;
  }

  const cards = rows
    .map(
      (note) => `<button class="list-item" type="button" data-id="${escapeHtml(note.id)}">
        <h2>${escapeHtml(note.title)}</h2>
        <div class="meta-line">${escapeHtml(formatDate(note.updatedAt))} · ${escapeHtml(note.theme)} · ${escapeHtml(note.category)}</div>
        <p class="summary">${escapeHtml(summaryFromContent(note.content))}</p>
      </button>`,
    )
    .join("");

  content.innerHTML = `<div class="list-stack">${cards}</div>`;
  content.querySelectorAll("[data-id]").forEach((button) => {
    button.addEventListener("click", () =>
      setRoute({ view: "detail", theme: route.theme, category: route.category, id: button.dataset.id }),
    );
  });
}

function renderDetail() {
  const note = notes.find((item) => normalize(item.id) === normalize(route.id));
  pageTitle.textContent = note ? note.title : "找不到筆記";
  crumbLabel.textContent = note ? `${note.theme} / ${note.category}` : "內容";
  backButton.style.visibility = "visible";

  if (!note) {
    content.innerHTML = renderEmpty("這筆筆記不存在，或已經被刪除。");
    return;
  }

  content.innerHTML = `<article class="detail-card">
    <div class="detail-actions">
      <button class="secondary-action" id="editCurrentButton" type="button">編輯</button>
    </div>
    <h2>${escapeHtml(note.title)}</h2>
    <div class="meta-line">${escapeHtml(formatDate(note.updatedAt))} · ${escapeHtml(note.theme)} · ${escapeHtml(note.category)}</div>
    <p class="summary">${escapeHtml(summaryFromContent(note.content))}</p>
    <div class="content-block">${escapeHtml(note.content)}</div>
  </article>`;

  document.querySelector("#editCurrentButton").addEventListener("click", () => openEditor(note));
}

function renderLoggedOut() {
  pageTitle.textContent = "LiveNote";
  crumbLabel.textContent = "請先登入";
  backButton.style.visibility = "hidden";
  content.innerHTML = renderEmpty("請先用右側的 Google 登入，系統會把你的筆記存到 Firestore。");
}

function renderLoading() {
  pageTitle.textContent = "LiveNote";
  crumbLabel.textContent = "載入中";
  backButton.style.visibility = "hidden";
  content.innerHTML = renderEmpty("正在連線 Firebase...");
}

function render() {
  renderAuthPanel();
  if (!authReady) {
    renderLoading();
    return;
  }
  if (!currentUser) {
    renderLoggedOut();
    return;
  }
  if (!notesLoaded) {
    renderLoading();
    return;
  }

  if (route.view === "theme") renderTheme();
  else if (route.view === "category") renderCategory();
  else if (route.view === "detail") renderDetail();
  else renderHome();
}

function renderAuthPanel() {
  const loggedIn = Boolean(currentUser);
  authProfile.classList.toggle("is-hidden", !loggedIn);
  signInButton.textContent = loggedIn ? "重新登入" : "Google 登入";
  signOutButton.disabled = !loggedIn;

  if (!loggedIn) {
    authAvatar.removeAttribute("src");
    authName.textContent = "尚未登入";
    authEmail.textContent = "";
    authUid.textContent = "";
    setAuthStatus("請先用 Google 登入。");
    return;
  }

  authName.textContent = currentUser.displayName || "Google 使用者";
  authEmail.textContent = currentUser.email || "沒有 email";
  authUid.textContent = `UID: ${currentUser.uid}`;
  authAvatar.src = currentUser.photoURL || "";
  authAvatar.alt = currentUser.displayName || "Google 使用者";
  setAuthStatus(`已登入 ${currentUser.email || currentUser.uid}`);
}

async function ensureUserDocument(user) {
  const ref = userDocRef(user.uid);
  const snap = await getDoc(ref);
  const payload = {
    displayName: user.displayName || "",
    email: user.email || "",
    photoURL: user.photoURL || "",
    lastLoginAt: serverTimestamp(),
  };
  if (!snap.exists()) payload.createdAt = serverTimestamp();
  await setDoc(ref, payload, { merge: true });
}

function subscribeToNotes(uid) {
  if (notesUnsubscribe) notesUnsubscribe();
  notesLoaded = false;
  const noteQuery = query(notesCollection(uid), orderBy("updatedAt", "desc"));
  notesUnsubscribe = onSnapshot(
    noteQuery,
    (snapshot) => {
      notes = snapshot.docs.map(noteFromSnapshot);
      notesLoaded = true;
      render();
    },
    (error) => {
      notesLoaded = true;
      setStatus(`讀取 Firestore 失敗：${error.message}`);
    },
  );
}

async function signInWithGoogle() {
  const result = await signInWithPopup(auth, googleProvider);
  const credential = GoogleAuthProvider.credentialFromResult(result);
  googleAccessToken = credential?.accessToken || "";
}

async function signOutUser() {
  googleAccessToken = "";
  if (notesUnsubscribe) {
    notesUnsubscribe();
    notesUnsubscribe = null;
  }
  notes = [];
  notesLoaded = false;
  await signOut(auth);
  setStatus("已登出。");
}

function currentEditNote() {
  return notes.find((note) => normalize(note.id) === normalize(editIdInput.value));
}

async function saveNote(event) {
  event.preventDefault();
  if (!currentUser) return;

  const existing = currentEditNote();
  const payload = buildNotePayload(existing);
  const noteId = normalize(editIdInput.value) || currentEditId || randomId();
  const ref = noteDocRef(currentUser.uid, noteId);

  if (existing) {
    await setDoc(ref, payload, { merge: false });
    setStatus(`已更新「${payload.title}」。`);
  } else {
    await setDoc(ref, payload, { merge: false });
    setStatus(`已新增「${payload.title}」。`);
  }

  closeEditor();
  setRoute({ view: "detail", theme: payload.theme, category: payload.category, id: noteId });
}

async function deleteCurrentNote() {
  if (!currentUser) return;
  const existing = currentEditNote() || notes.find((note) => normalize(note.id) === normalize(route.id));
  if (!existing) return;
  const confirmed = window.confirm(`確定要刪除「${existing.title}」嗎？`);
  if (!confirmed) return;
  await deleteDoc(noteDocRef(currentUser.uid, existing.id));
  closeEditor();
  setStatus(`已刪除「${existing.title}」。`);
  setRoute({ view: "home", theme: "", category: "", id: "" });
}

async function importNotesFromFile(file) {
  if (!currentUser) {
    setStatus("請先登入後再匯入資料。");
    return;
  }
  if (!window.XLSX) throw new Error("SheetJS 尚未載入。");

  const ext = file.name.split(".").pop().toLowerCase();
  const workbook =
    ext === "csv"
      ? XLSX.read(await file.text(), { type: "string" })
      : XLSX.read(await file.arrayBuffer(), { type: "array" });

  const sheetName = workbook.SheetNames[0];
  const sheet = workbook.Sheets[sheetName];
  const rows = XLSX.utils.sheet_to_json(sheet, { defval: "" });
  const mapped = rows.map(normalizeImportedRow).filter((row) => row.title || row.content || row.theme || row.category);
  await writeRowsToFirestore(mapped);
  setStatus(`已匯入 ${mapped.length} 筆筆記。`);
}

function normalizeImportedRow(row) {
  const title = normalize(row.title || row["名稱"] || row["title"]);
  const content = normalize(row.content || row["內容"] || row["content"]);
  const theme = normalize(row.theme || row["主題"] || row["theme"]) || "未分類";
  const category = normalize(row.category || row["分類"] || row["category"]) || "未分類";
  const id = normalize(row.id || row["id"]) || randomId();
  const createdAt = toTimestamp(row.createdAt || row.created_at || row["created_at"] || row.updatedAt || row.updated_at);
  const updatedAt = toTimestamp(row.updatedAt || row.updated_at || row["updated_at"] || row.createdAt || row.created_at);
  return { id, title, content, theme, category, createdAt, updatedAt };
}

async function writeRowsToFirestore(rowsToWrite) {
  const chunkSize = 400;
  for (let index = 0; index < rowsToWrite.length; index += chunkSize) {
    const batch = writeBatch(db);
    const slice = rowsToWrite.slice(index, index + chunkSize);
    for (const row of slice) {
      const ref = noteDocRef(currentUser.uid, row.id);
      batch.set(ref, {
        title: row.title,
        content: row.content,
        theme: row.theme,
        category: row.category,
        createdAt: row.createdAt || toTimestamp(today()),
        updatedAt: row.updatedAt || toTimestamp(today()),
      });
    }
    await batch.commit();
  }
}

function buildExportRows() {
  return notes.map((note) => [
    note.id,
    note.title,
    note.content,
    note.theme,
    note.category,
    formatDate(note.createdAt),
    formatDate(note.updatedAt),
  ]);
}

function rowsToCsv(rowsInput) {
  return rowsInput
    .map((row) =>
      row
        .map((cell) => {
          const text = normalize(cell);
          return /[",\n\r]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
        })
        .join(","),
    )
    .join("\r\n");
}

function downloadText(filename, text, mimeType) {
  const blob = new Blob([text], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

function exportCsv() {
  if (!currentUser) {
    setStatus("請先登入後再匯出 CSV。");
    return;
  }
  const header = ["id", "title", "content", "theme", "category", "createdAt", "updatedAt"];
  const csv = rowsToCsv([header, ...buildExportRows()]);
  downloadText("livenote.csv", csv, "text/csv;charset=utf-8");
  setStatus("已下載 livenote.csv。");
}

async function ensureGoogleSheetsToken() {
  if (googleAccessToken) return googleAccessToken;
  const result = await signInWithPopup(auth, googleProvider);
  const credential = GoogleAuthProvider.credentialFromResult(result);
  googleAccessToken = credential?.accessToken || "";
  if (!googleAccessToken) {
    throw new Error("無法取得 Google Sheets 存取權限，請重新登入一次。");
  }
  return googleAccessToken;
}

async function exportToGoogleSheet() {
  if (!currentUser) {
    setStatus("請先登入後再匯出 Google Sheet。");
    return;
  }
  const token = await ensureGoogleSheetsToken();
  const title = `LiveNote export ${today()}`;
  const createResponse = await fetch("https://sheets.googleapis.com/v4/spreadsheets", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      properties: { title },
    }),
  });

  if (!createResponse.ok) {
    throw new Error(await createResponse.text());
  }

  const created = await createResponse.json();
  const values = [
    ["id", "title", "content", "theme", "category", "createdAt", "updatedAt"],
    ...buildExportRows(),
  ];
  const updateResponse = await fetch(`https://sheets.googleapis.com/v4/spreadsheets/${created.spreadsheetId}/values/Sheet1!A1?valueInputOption=RAW`, {
    method: "PUT",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ values }),
  });

  if (!updateResponse.ok) {
    throw new Error(await updateResponse.text());
  }

  setStatus(`已建立新的 Google Sheet：${created.spreadsheetUrl}`);
}

async function initUserSession(user) {
  currentUser = user;
  googleAccessToken = "";
  if (!user) {
    if (notesUnsubscribe) {
      notesUnsubscribe();
      notesUnsubscribe = null;
    }
    notes = [];
    notesLoaded = false;
    render();
    return;
  }

  await ensureUserDocument(user);
  subscribeToNotes(user.uid);
  render();
}

async function handleLoginState(user) {
  authReady = true;
  if (!user) {
    currentUser = null;
    notes = [];
    notesLoaded = false;
    render();
    return;
  }

  try {
    await initUserSession(user);
    setStatus(`已登入 ${user.email || user.uid}`);
  } catch (error) {
    setStatus(`登入後處理失敗：${error.message}`);
  }
}

function wireEvents() {
  backButton.addEventListener("click", () => {
    if (route.view === "detail") setRoute({ view: "category", theme: route.theme, category: route.category, id: "" });
    else if (route.view === "category") setRoute({ view: "theme", theme: route.theme, category: "", id: "" });
    else setRoute({ view: "home", theme: "", category: "", id: "" });
  });

  searchInput.addEventListener("input", render);
  toolsButton.addEventListener("click", openDrawer);
  closeDrawerButton.addEventListener("click", closeDrawer);
  closeEditorButton.addEventListener("click", closeEditor);
  newItemButton.addEventListener("click", () => {
    closeDrawer();
    if (!currentUser) {
      setStatus("請先登入 Google 帳號。");
      return;
    }
    openEditor();
  });
  deleteButton.addEventListener("click", deleteCurrentNote);

  drawer.addEventListener("click", (event) => {
    if (event.target === drawer) closeDrawer();
  });

  editorModal.addEventListener("click", (event) => {
    if (event.target === editorModal) closeEditor();
  });

  advancedToggleButton.addEventListener("click", () => {
    const collapsed = advancedFields.classList.toggle("is-collapsed");
    advancedToggleButton.textContent = collapsed ? "顯示進階欄位" : "隱藏進階欄位";
  });

  themeSelect.addEventListener("change", () => toggleCustomRow(themeSelect, themeCustomRow, themeCustomInput));
  categorySelect.addEventListener("change", () => toggleCustomRow(categorySelect, categoryCustomRow, categoryCustomInput));

  signInButton.addEventListener("click", async () => {
    try {
      setStatus("正在登入 Google...");
      await signInWithGoogle();
      setStatus("Google 登入完成。");
    } catch (error) {
      setStatus(`登入失敗：${error.message}`);
    }
  });

  signOutButton.addEventListener("click", async () => {
    try {
      await signOutUser();
    } catch (error) {
      setStatus(`登出失敗：${error.message}`);
    }
  });

  exportCsvButton.addEventListener("click", exportCsv);
  exportGoogleSheetButton.addEventListener("click", async () => {
    try {
      setStatus("正在建立新的 Google Sheet...");
      await exportToGoogleSheet();
    } catch (error) {
      setStatus(`匯出 Google Sheet 失敗：${error.message}`);
    }
  });

  importInput.addEventListener("change", async (event) => {
    const [file] = event.target.files || [];
    if (!file) return;
    try {
      setStatus(`正在匯入 ${file.name}...`);
      await importNotesFromFile(file);
      importInput.value = "";
    } catch (error) {
      setStatus(`匯入失敗：${error.message}`);
    }
  });

  editorForm.addEventListener("submit", saveNote);
  window.addEventListener("hashchange", () => {
    readRoute();
    render();
  });
}

document.addEventListener("DOMContentLoaded", () => {
  readRoute();
  wireEvents();

  onAuthStateChanged(auth, handleLoginState);
  render();
});
