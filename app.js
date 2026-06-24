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
  collectionGroup,
  deleteDoc,
  doc,
  getDoc,
  getFirestore,
  onSnapshot,
  orderBy,
  query,
  runTransaction,
  serverTimestamp,
  setDoc,
  where,
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

googleProvider.setCustomParameters({ prompt: "select_account" });
setPersistence(auth, browserLocalPersistence).catch(() => {});

const DEFAULT_THEMES = ["中式", "西式", "日式", "甜點", "飲品", "其他"];
const DEFAULT_CATEGORIES = ["家常", "宴客", "便當", "湯品", "烘焙", "其他"];

const content = document.querySelector("#content");
const pageTitle = document.querySelector("#pageTitle");
const crumbLabel = document.querySelector("#crumbLabel");
const backButton = document.querySelector("#backButton");
const searchInput = document.querySelector("#searchInput");
const drawer = document.querySelector("#drawer");
const editorModal = document.querySelector("#editorModal");
const editorForm = document.querySelector("#editorForm");
const editorModeLabel = document.querySelector("#editorModeLabel");
const editorTitle = document.querySelector("#editorTitle");
const advancedToggleButton = document.querySelector("#advancedToggleButton");
const advancedFields = document.querySelector("#advancedFields");
const themeSelect = document.querySelector("#themeSelect");
const categorySelect = document.querySelector("#categorySelect");
const visibilitySelect = document.querySelector("#visibilitySelect");
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
const importInput = document.querySelector("#importInput");
const newItemButton = document.querySelector("#newItemButton");
const toolsButton = document.querySelector("#toolsButton");
const closeDrawerButton = document.querySelector("#closeDrawerButton");
const closeEditorButton = document.querySelector("#closeEditorButton");
const deleteButton = document.querySelector("#deleteButton");

let currentUser = null;
let notes = [];
let publicRecipes = [];
let favoriteRecipeIds = new Set();
let notesLoaded = false;
let publicLoaded = false;
let favoritesLoaded = false;
let authReady = false;
let publicSortMode = "latest";
let notesUnsubscribe = null;
let publicUnsubscribe = null;
let favoritesUnsubscribe = null;
let currentEditId = "";
let syncMessage = "正在連線 Firebase...";
let route = parseRoute(location.pathname);

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

function slugPath(value) {
  return encodeURIComponent(normalize(value));
}

function randomId() {
  return typeof crypto !== "undefined" && crypto.randomUUID
    ? crypto.randomUUID()
    : `id-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
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
  return date ? date.toISOString().slice(0, 10) : "";
}

function formatDateTime(value) {
  const date = asDate(value);
  if (!date) return "";
  return new Intl.DateTimeFormat("zh-Hant-TW", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

function toTimestamp(value) {
  const date = asDate(value) || new Date();
  return Timestamp.fromDate(date);
}

function summaryFromContent(content) {
  const text = normalize(content).replace(/\s+/g, " ");
  if (!text) return "尚未輸入內容";
  return text.length > 88 ? `${text.slice(0, 88)}…` : text;
}

function themeMeta(theme) {
  const metaMap = {
    中式: { icon: "🍜", color: "#b14f35" },
    西式: { icon: "🥗", color: "#2e6f6b" },
    日式: { icon: "🍣", color: "#5671a6" },
    甜點: { icon: "🍰", color: "#8b5e3c" },
    飲品: { icon: "☕", color: "#5b7c8a" },
    其他: { icon: "📝", color: "#7b5ea7" },
  };
  const key = normalize(theme);
  if (metaMap[key]) return metaMap[key];
  const seed = [...key].reduce((sum, char) => sum + char.codePointAt(0), 0);
  const palette = [
    { icon: "🍲", color: "#2e6f6b" },
    { icon: "🥘", color: "#b14f35" },
    { icon: "🥪", color: "#5671a6" },
    { icon: "🥙", color: "#8b5e3c" },
    { icon: "🍱", color: "#5b7c8a" },
    { icon: "🧁", color: "#7b5ea7" },
  ];
  return palette[seed % palette.length];
}

function parseRoute(pathname) {
  const segments = normalize(pathname)
    .replace(/\/+$/, "")
    .replace(/^\/+/, "")
    .split("/")
    .filter(Boolean);

  const [head = ""] = segments;
  if (!head || head === "notes") return { view: "notes" };
  if (head === "theme") {
    const theme = decodeURIComponent(segments[1] || "");
    const maybeCategory = segments[2] === "category" ? decodeURIComponent(segments[3] || "") : "";
    if (theme && maybeCategory) return { view: "category", theme, category: maybeCategory };
    if (theme) return { view: "theme", theme };
    return { view: "notes" };
  }
  if (head === "note") return { view: "note", id: decodeURIComponent(segments[1] || "") };
  if (head === "public") return { view: "public" };
  if (head === "recipe") return { view: "recipe", id: decodeURIComponent(segments[1] || "") };
  if (head === "popular") return { view: "popular" };
  if (head === "favorites") return { view: "favorites" };
  if (head === "groups") return { view: "groups" };
  return { view: "notes" };
}

function routePath(nextRoute) {
  switch (nextRoute.view) {
    case "notes":
      return "/";
    case "theme":
      return `/theme/${slugPath(nextRoute.theme)}`;
    case "category":
      return `/theme/${slugPath(nextRoute.theme)}/category/${slugPath(nextRoute.category)}`;
    case "note":
      return `/note/${slugPath(nextRoute.id)}`;
    case "public":
      return "/public";
    case "recipe":
      return `/recipe/${slugPath(nextRoute.id)}`;
    case "popular":
      return "/popular";
    case "favorites":
      return "/favorites";
    case "groups":
      return "/groups";
    default:
      return "/";
  }
}

function navigate(nextRoute) {
  route = nextRoute;
  history.pushState({}, "", routePath(nextRoute));
  render();
}

function navigateToPath(path) {
  const nextRoute = parseRoute(path);
  route = nextRoute;
  history.pushState({}, "", routePath(nextRoute));
  render();
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

function publicRecipeRef(recipeId) {
  return doc(db, "public_recipes", recipeId);
}

function publicRatingRef(recipeId, uid) {
  return doc(db, "public_recipes", recipeId, "ratings", uid);
}

function publicFavoriteRef(recipeId, uid) {
  return doc(db, "public_recipes", recipeId, "favorites", uid);
}

function noteFromSnapshot(snapshot) {
  const data = snapshot.data() || {};
  return {
    id: snapshot.id,
    title: normalize(data.title),
    content: normalize(data.content),
    theme: normalize(data.theme) || "未分類",
    category: normalize(data.category) || "未分類",
    visibility: normalize(data.visibility) || "private",
    createdAt: data.createdAt || null,
    updatedAt: data.updatedAt || null,
  };
}

function recipeFromSnapshot(snapshot) {
  const data = snapshot.data() || {};
  return {
    id: snapshot.id,
    title: normalize(data.title),
    content: normalize(data.content),
    ownerUid: normalize(data.ownerUid),
    ownerName: normalize(data.ownerName) || "匿名",
    category: normalize(data.category) || "未分類",
    avgRating: Number(data.avgRating || 0),
    ratingCount: Number(data.ratingCount || 0),
    createdAt: data.createdAt || null,
    updatedAt: data.updatedAt || null,
    visibility: normalize(data.visibility) || "public",
  };
}

function uniqueSortedValues(key) {
  return [...new Set(notes.map((note) => normalize(note[key])).filter(Boolean))].sort((a, b) =>
    a.localeCompare(b, "zh-Hant"),
  );
}

function setSelectOptions(selectEl, values, currentValue) {
  if (!selectEl) return;
  const options = values
    .map((value) => `<option value="${escapeHtml(value)}">${escapeHtml(value)}</option>`)
    .join("");
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
  if (isCustom) inputEl.value = fallback || inputEl.value || "";
  else inputEl.value = "";
}

function collectChosenValue(selectEl, customInputEl, fallback = "") {
  if (!selectEl) return fallback;
  if (selectEl.value === "__custom__") return normalize(customInputEl?.value) || fallback;
  return normalize(selectEl.value) || fallback;
}

function visiblePrivateNotes() {
  const queryText = normalize(searchInput?.value).toLowerCase();
  const items = notes.slice();
  if (!queryText) return items;
  return items.filter((note) =>
    [note.title, note.content, note.theme, note.category, note.visibility].some((field) =>
      normalize(field).toLowerCase().includes(queryText),
    ),
  );
}

function visiblePublicRecipes() {
  const queryText = normalize(searchInput?.value).toLowerCase();
  let items = publicRecipes.slice();
  if (route.view === "favorites") {
    items = items.filter((recipe) => favoriteRecipeIds.has(recipe.id));
  }
  if (queryText) {
    items = items.filter((recipe) =>
      [recipe.title, recipe.content, recipe.category, recipe.ownerName].some((field) =>
        normalize(field).toLowerCase().includes(queryText),
      ),
    );
  }
  const sortMode = route.view === "popular" ? "hot" : route.view === "favorites" ? "latest" : publicSortMode;
  return sortPublicRecipes(items, sortMode);
}

function sortPublicRecipes(items, sortMode) {
  const list = items.slice();
  if (sortMode === "rating") {
    list.sort((a, b) => {
      if (b.avgRating !== a.avgRating) return b.avgRating - a.avgRating;
      if (b.ratingCount !== a.ratingCount) return b.ratingCount - a.ratingCount;
      return asDate(b.createdAt) - asDate(a.createdAt);
    });
    return list;
  }
  if (sortMode === "hot") {
    list.sort((a, b) => {
      const hotA = a.avgRating * Math.log10((a.ratingCount || 0) + 1);
      const hotB = b.avgRating * Math.log10((b.ratingCount || 0) + 1);
      if (hotB !== hotA) return hotB - hotA;
      return asDate(b.createdAt) - asDate(a.createdAt);
    });
    return list;
  }
  list.sort((a, b) => asDate(b.createdAt) - asDate(a.createdAt));
  return list;
}

function setStatus(message) {
  syncMessage = message;
  if (syncStatus) syncStatus.textContent = message;
}

function setAuthStatus(message) {
  if (authStatus) authStatus.textContent = message;
}

function isLoggedIn() {
  return Boolean(currentUser);
}

function ensureCurrentUserNote(noteId) {
  return notes.find((note) => note.id === noteId) || null;
}

function getCurrentRecipe(recipeId) {
  return publicRecipes.find((recipe) => recipe.id === recipeId) || null;
}

function updateChrome() {
  const labels = {
    notes: ["我的筆記", "LiveNote"],
    theme: [route.theme || "主題", "我的筆記"],
    category: [route.category || "分類", route.theme || "我的筆記"],
    note: ["筆記詳情", "我的筆記"],
    public: ["公開食譜", "社群"],
    recipe: ["食譜詳情", "公開食譜"],
    popular: ["熱門排行", "公開食譜"],
    favorites: ["我的收藏", "公開食譜"],
    groups: ["我的群組", "我的筆記"],
  };
  const [title, crumb] = labels[route.view] || ["LiveNote", ""];
  pageTitle.textContent = title;
  crumbLabel.textContent = crumb;
  backButton.setAttribute("aria-label", "返回上一頁");
  searchInput.placeholder =
    route.view === "public" || route.view === "recipe" || route.view === "popular" || route.view === "favorites"
      ? "搜尋公開食譜、作者、分類"
      : "搜尋標題、內容、主題、分類";
}

function renderMenuState() {
  document.querySelectorAll("[data-route]").forEach((button) => {
    const target = normalize(button.dataset.route);
    button.classList.toggle("is-active", target === routePath(route));
  });
}

function renderEmpty(message, extra = "") {
  return `
    <div class="empty-state">
      <strong>${escapeHtml(message)}</strong>
      ${extra ? `<p>${escapeHtml(extra)}</p>` : ""}
    </div>
  `;
}

function renderThemeTiles() {
  const items = visiblePrivateNotes();
  const grouped = items.reduce((acc, note) => {
    const theme = note.theme || "未分類";
    if (!acc[theme]) acc[theme] = [];
    acc[theme].push(note);
    return acc;
  }, {});
  const themes = Object.keys(grouped).sort((a, b) => a.localeCompare(b, "zh-Hant"));
  if (!themes.length) return renderEmpty("目前沒有可顯示的筆記。", "按下左側「新增筆記」開始建立內容。");
  const cards = themes
    .map((theme) => {
      const meta = themeMeta(theme);
      const list = grouped[theme].slice().sort((a, b) => asDate(b.updatedAt) - asDate(a.updatedAt));
      const categories = [...new Set(list.map((note) => note.category || "未分類"))].slice(0, 3);
      return `
        <button class="tile" type="button" data-route="${escapeHtml(routePath({ view: "theme", theme }))}" style="--tile-color:${meta.color}">
          <div class="tile-icon" aria-hidden="true">${meta.icon}</div>
          <div>
            <h2>${escapeHtml(theme)}</h2>
            <p>${escapeHtml(categories.join(" · ") || "未分類")}</p>
          </div>
          <p>${list.length} 篇筆記</p>
        </button>
      `;
    })
    .join("");
  return `<div class="tile-grid">${cards}</div>`;
}

function renderThemeView() {
  const rows = visiblePrivateNotes().filter((note) => normalize(note.theme) === normalize(route.theme));
  const meta = themeMeta(route.theme);
  if (!route.theme) return renderEmpty("找不到這個主題。");
  if (!rows.length) {
    return `
      <div class="detail-card">
        <div class="detail-actions">
          <button class="secondary-action" type="button" data-route="${escapeHtml(routePath({ view: "notes" }))}">返回</button>
        </div>
        <h2>${escapeHtml(route.theme)}</h2>
        <p class="summary">這個主題目前沒有筆記。</p>
      </div>
    `;
  }
  const grouped = rows.reduce((acc, note) => {
    const category = note.category || "未分類";
    if (!acc[category]) acc[category] = [];
    acc[category].push(note);
    return acc;
  }, {});
  const cards = Object.keys(grouped)
    .sort((a, b) => a.localeCompare(b, "zh-Hant"))
    .map((category) => {
      const list = grouped[category].slice().sort((a, b) => asDate(b.updatedAt) - asDate(a.updatedAt));
      return `
        <button class="tile" type="button" data-route="${escapeHtml(routePath({ view: "category", theme: route.theme, category }))}" style="--tile-color:${meta.color}">
          <div class="tile-icon" aria-hidden="true">${meta.icon}</div>
          <div>
            <h2>${escapeHtml(category)}</h2>
            <p>${escapeHtml(list[0]?.title || "尚未命名")}</p>
          </div>
          <p>${list.length} 篇筆記</p>
        </button>
      `;
    })
    .join("");
  return `
    <div class="sync-banner">
      ${escapeHtml(route.theme)} 底下共有 ${rows.length} 篇筆記。
    </div>
    <div class="tile-grid">${cards}</div>
  `;
}

function renderCategoryView() {
  const rows = visiblePrivateNotes().filter(
    (note) => normalize(note.theme) === normalize(route.theme) && normalize(note.category) === normalize(route.category),
  );
  if (!route.theme || !route.category) return renderEmpty("找不到這個分類。");
  if (!rows.length) {
    return `
      <div class="detail-card">
        <div class="detail-actions">
          <button class="secondary-action" type="button" data-route="${escapeHtml(routePath({ view: "theme", theme: route.theme }))}">返回</button>
        </div>
        <h2>${escapeHtml(route.category)}</h2>
        <p class="summary">這個分類目前沒有筆記。</p>
      </div>
    `;
  }
  const items = rows
    .slice()
    .sort((a, b) => asDate(b.updatedAt) - asDate(a.updatedAt))
    .map(
      (note) => `
        <button class="list-item" type="button" data-route="${escapeHtml(routePath({ view: "note", id: note.id }))}">
          <h2>${escapeHtml(note.title || "尚未命名")}</h2>
          <p class="meta-line">${escapeHtml(note.visibility === "public" ? "公開" : note.visibility === "group" ? "群組" : "私密")} · ${escapeHtml(
        formatDateTime(note.updatedAt) || "尚未更新",
      )}</p>
          <p class="summary">${escapeHtml(summaryFromContent(note.content))}</p>
        </button>
      `,
    )
    .join("");
  return `
    <div class="sync-banner">
      ${escapeHtml(route.theme)} / ${escapeHtml(route.category)} 底下共有 ${rows.length} 篇筆記。
    </div>
    <div class="list-stack">${items}</div>
  `;
}

function renderNoteDetailView() {
  const note = ensureCurrentUserNote(route.id);
  if (!note) return renderEmpty("這篇筆記不存在，或已被刪除。");
  const visibilityLabel = note.visibility === "public" ? "公開" : note.visibility === "group" ? "群組" : "私密";
  return `
    <div class="detail-card">
      <div class="detail-actions">
        <button class="secondary-action" type="button" data-action="edit-note" data-note-id="${escapeHtml(note.id)}">編輯</button>
        <button class="secondary-action" type="button" data-action="toggle-note-public" data-note-id="${escapeHtml(note.id)}">
          ${note.visibility === "public" ? "取消公開" : "公開分享"}
        </button>
      </div>
      <h2>${escapeHtml(note.title || "尚未命名")}</h2>
      <p class="meta-line">${escapeHtml(note.theme)} · ${escapeHtml(note.category)} · ${escapeHtml(visibilityLabel)}</p>
      <p class="meta-line">建立：${escapeHtml(formatDateTime(note.createdAt) || "未知")}｜更新：${escapeHtml(formatDateTime(note.updatedAt) || "未知")}</p>
      <div class="content-block">${escapeHtml(note.content || "")}</div>
    </div>
  `;
}

function renderNotesHome() {
  if (!isLoggedIn()) {
    return renderEmpty("請先登入 Google 帳號，再讀取你的私有筆記。");
  }
  if (!notesLoaded) {
    return renderEmpty("正在載入你的筆記...");
  }
  return renderThemeTiles();
}

function renderPublicList(mode = "public") {
  const items = visiblePublicRecipes();
  const label = mode === "popular" ? "熱門排行" : mode === "favorites" ? "我的收藏" : "公開食譜";
  const showSort = mode === "public";
  const controls = `
    <div class="public-toolbar">
      <div class="toolbar-chip">共 ${items.length} 筆</div>
      ${showSort ? `
        <label class="toolbar-select">
          <span>排序</span>
          <select data-public-sort>
            <option value="latest" ${publicSortMode === "latest" ? "selected" : ""}>最新</option>
            <option value="rating" ${publicSortMode === "rating" ? "selected" : ""}>星數</option>
            <option value="hot" ${publicSortMode === "hot" ? "selected" : ""}>熱門</option>
          </select>
        </label>
      ` : ""}
    </div>
  `;
  if (!publicLoaded) {
    return `
      ${controls}
      ${renderEmpty("正在載入公開食譜...")}
    `;
  }
  if (!items.length) {
    return `
      ${controls}
      ${renderEmpty(
        mode === "favorites" ? "你還沒有收藏任何公開食譜。" : "目前沒有符合條件的公開食譜。",
        mode === "public" ? "把筆記設成「公開」後，就會出現在這裡。" : "",
      )}
    `;
  }
  const cards = items
    .map(
      (recipe) => `
        <button class="list-item recipe-item" type="button" data-route="${escapeHtml(routePath({ view: "recipe", id: recipe.id }))}">
          <div class="recipe-head">
            <h2>${escapeHtml(recipe.title || "尚未命名")}</h2>
            <span class="recipe-rating">★ ${escapeHtml(recipe.avgRating ? recipe.avgRating.toFixed(1) : "0.0")}</span>
          </div>
          <p class="meta-line">${escapeHtml(recipe.category)} · ${escapeHtml(recipe.ownerName)} · ${recipe.ratingCount} 則評分</p>
          <p class="summary">${escapeHtml(summaryFromContent(recipe.content))}</p>
        </button>
      `,
    )
    .join("");
  return `
    ${controls}
    <div class="list-stack">${cards}</div>
  `;
}

function renderRecipeDetailView() {
  const recipe = getCurrentRecipe(route.id);
  if (!recipe) return renderEmpty("找不到這份公開食譜。");
  const isOwner = currentUser && recipe.ownerUid === currentUser.uid;
  const isFavorited = favoriteRecipeIds.has(recipe.id);
  return `
    <div class="detail-card">
      <div class="detail-actions">
        ${isOwner ? `<button class="secondary-action" type="button" data-action="edit-note" data-note-id="${escapeHtml(recipe.id)}">編輯原筆記</button>` : ""}
        <button class="secondary-action" type="button" data-action="favorite-toggle" data-recipe-id="${escapeHtml(recipe.id)}">
          ${isFavorited ? "取消收藏" : "加入收藏"}
        </button>
      </div>
      <h2>${escapeHtml(recipe.title || "尚未命名")}</h2>
      <p class="meta-line">${escapeHtml(recipe.category)} · ${escapeHtml(recipe.ownerName)} · ${recipe.ratingCount} 則評分</p>
      <p class="meta-line">平均星數：${escapeHtml(recipe.avgRating ? recipe.avgRating.toFixed(1) : "0.0")}</p>
      <div class="star-row" data-star-row>
        ${[1, 2, 3, 4, 5]
          .map((rating) => {
            const active = recipe.avgRating >= rating ? "is-active" : "";
            return `<button class="star-button ${active}" type="button" data-action="rate-recipe" data-recipe-id="${escapeHtml(
              recipe.id,
            )}" data-rating="${rating}" aria-label="${rating} 星">★</button>`;
          })
          .join("")}
      </div>
      <div class="content-block">${escapeHtml(recipe.content || "")}</div>
    </div>
  `;
}

function renderGroupsView() {
  if (!isLoggedIn()) {
    return renderEmpty("請先登入後使用群組功能。");
  }
  const groupNotes = visiblePrivateNotes().filter((note) => note.visibility === "group");
  if (!groupNotes.length) {
    return renderEmpty("目前還沒有群組筆記。", "你可以先把筆記存成「群組」可見，之後再接上成員權限。");
  }
  const items = groupNotes
    .slice()
    .sort((a, b) => asDate(b.updatedAt) - asDate(a.updatedAt))
    .map(
      (note) => `
        <button class="list-item" type="button" data-route="${escapeHtml(routePath({ view: "note", id: note.id }))}">
          <h2>${escapeHtml(note.title || "尚未命名")}</h2>
          <p class="meta-line">${escapeHtml(note.theme)} · ${escapeHtml(note.category)}</p>
          <p class="summary">${escapeHtml(summaryFromContent(note.content))}</p>
        </button>
      `,
    )
    .join("");
  return `<div class="list-stack">${items}</div>`;
}

function render() {
  route = parseRoute(location.pathname);
  updateChrome();
  renderMenuState();
  renderAuthPanel();
  setStatus(syncMessage);

  if (!authReady) {
    content.innerHTML = renderEmpty("正在連線 Firebase...");
    return;
  }

  if (
    (route.view === "notes" ||
      route.view === "theme" ||
      route.view === "category" ||
      route.view === "note" ||
      route.view === "groups" ||
      route.view === "favorites") &&
    !currentUser
  ) {
    content.innerHTML = renderEmpty("請先登入後才能查看你的筆記。");
    return;
  }

  if ((route.view === "notes" || route.view === "theme" || route.view === "category" || route.view === "note" || route.view === "groups") && !notesLoaded) {
    content.innerHTML = renderEmpty("正在載入你的筆記...");
    return;
  }

  if ((route.view === "public" || route.view === "recipe" || route.view === "popular" || route.view === "favorites") && !publicLoaded) {
    content.innerHTML = renderEmpty("正在載入公開食譜...");
    return;
  }

  if (route.view === "favorites" && currentUser && !favoritesLoaded) {
    content.innerHTML = renderEmpty("正在載入你的收藏...");
    return;
  }

  if (route.view === "notes") content.innerHTML = renderNotesHome();
  else if (route.view === "theme") content.innerHTML = renderThemeView();
  else if (route.view === "category") content.innerHTML = renderCategoryView();
  else if (route.view === "note") content.innerHTML = renderNoteDetailView();
  else if (route.view === "public") content.innerHTML = renderPublicList("public");
  else if (route.view === "recipe") content.innerHTML = renderRecipeDetailView();
  else if (route.view === "popular") content.innerHTML = renderPublicList("popular");
  else if (route.view === "favorites") content.innerHTML = renderPublicList("favorites");
  else if (route.view === "groups") content.innerHTML = renderGroupsView();
  else content.innerHTML = renderNotesHome();
}

function renderAuthPanel() {
  if (!authProfile || !authAvatar || !authName || !authEmail || !authUid) return;
  const user = currentUser;
  const signedIn = Boolean(user);
  authProfile.classList.toggle("is-hidden", !signedIn);
  signInButton.classList.toggle("is-hidden", signedIn);
  signOutButton.classList.toggle("is-hidden", !signedIn);
  if (signedIn) {
    authAvatar.src = user.photoURL || "";
    authAvatar.alt = user.displayName || user.email || "使用者頭像";
    authName.textContent = user.displayName || "未命名使用者";
    authEmail.textContent = user.email || "";
    authUid.textContent = user.uid;
    setAuthStatus("已登入 Google 帳號。");
  } else {
    authAvatar.removeAttribute("src");
    authAvatar.alt = "";
    authName.textContent = "";
    authEmail.textContent = "";
    authUid.textContent = "";
    setAuthStatus("請先登入 Google 帳號。");
  }
}

async function ensureUserDocument(user) {
  const ref = userDocRef(user.uid);
  const snapshot = await getDoc(ref);
  const payload = {
    displayName: user.displayName || "",
    email: user.email || "",
    photoURL: user.photoURL || "",
    lastLoginAt: serverTimestamp(),
  };
  if (!snapshot.exists()) payload.createdAt = serverTimestamp();
  await setDoc(ref, payload, { merge: true });
}

function subscribeToPrivateNotes(uid) {
  if (notesUnsubscribe) notesUnsubscribe();
  const noteQuery = query(notesCollection(uid), orderBy("updatedAt", "desc"));
  notesUnsubscribe = onSnapshot(
    noteQuery,
    (snapshot) => {
      notes = snapshot.docs.map(noteFromSnapshot);
      notesLoaded = true;
      render();
    },
    (error) => {
      console.error(error);
      setStatus("讀取筆記失敗。");
    },
  );
}

function subscribeToPublicRecipes() {
  if (publicUnsubscribe) publicUnsubscribe();
  const recipeQuery = query(collection(db, "public_recipes"), orderBy("createdAt", "desc"));
  publicUnsubscribe = onSnapshot(
    recipeQuery,
    (snapshot) => {
      publicRecipes = snapshot.docs.map(recipeFromSnapshot);
      publicLoaded = true;
      render();
    },
    (error) => {
      console.error(error);
      setStatus("讀取公開食譜失敗。");
    },
  );
}

function subscribeToFavorites(uid) {
  if (favoritesUnsubscribe) favoritesUnsubscribe();
  const favoriteQuery = query(collectionGroup(db, "favorites"), where("uid", "==", uid));
  favoritesUnsubscribe = onSnapshot(
    favoriteQuery,
    (snapshot) => {
      favoriteRecipeIds = new Set(
        snapshot.docs
          .map((docSnap) => docSnap.ref.parent.parent?.id)
          .filter(Boolean),
      );
      favoritesLoaded = true;
      render();
    },
    (error) => {
      console.error(error);
      setStatus("讀取收藏失敗。");
    },
  );
}

async function signInWithGoogle() {
  try {
    await signInWithPopup(auth, googleProvider);
  } catch (error) {
    console.error(error);
    setStatus("Google 登入失敗。");
  }
}

async function signOutUser() {
  try {
    await signOut(auth);
  } catch (error) {
    console.error(error);
    setStatus("登出失敗。");
  }
}

function currentEditorNote() {
  return currentEditId ? notes.find((note) => note.id === currentEditId) : null;
}

function openDrawer() {
  drawer.classList.add("is-open");
  drawer.setAttribute("aria-hidden", "false");
}

function closeDrawer() {
  drawer.classList.remove("is-open");
  drawer.setAttribute("aria-hidden", "true");
}

function openEditor(note = null) {
  if (!currentUser) {
    setStatus("請先登入後再新增或編輯筆記。");
    return;
  }
  const existing = note || currentEditorNote() || null;
  currentEditId = existing?.id || "";
  editIdInput.value = currentEditId;
  if (editorModeLabel) editorModeLabel.textContent = existing ? "編輯筆記" : "新增筆記";
  if (editorTitle) editorTitle.textContent = existing ? "修改內容" : "新增筆記";
  editorForm.elements.title.value = existing?.title || "";
  editorForm.elements.content.value = existing?.content || "";

  const themeValues = [...new Set([...DEFAULT_THEMES, ...uniqueSortedValues("theme")])];
  const categoryValues = [...new Set([...DEFAULT_CATEGORIES, ...uniqueSortedValues("category")])];
  setSelectOptions(themeSelect, themeValues, existing?.theme || "");
  setSelectOptions(categorySelect, categoryValues, existing?.category || "");
  if (visibilitySelect) {
    visibilitySelect.innerHTML = `
      <option value="private">私密</option>
      <option value="group">群組</option>
      <option value="public">公開</option>
    `;
    visibilitySelect.value = existing?.visibility || "private";
  }
  toggleCustomRow(themeSelect, themeCustomRow, themeCustomInput, existing?.theme || "");
  toggleCustomRow(categorySelect, categoryCustomRow, categoryCustomInput, existing?.category || "");
  advancedFields.classList.add("is-collapsed");
  advancedToggleButton.textContent = "顯示更多設定";
  deleteButton.classList.toggle("is-hidden", !existing);
  editorModal.classList.add("is-open");
  editorModal.setAttribute("aria-hidden", "false");
  editorForm.elements.title.focus();
}

function closeEditor() {
  currentEditId = "";
  editorForm.reset();
  editIdInput.value = "";
  advancedFields.classList.add("is-collapsed");
  advancedToggleButton.textContent = "顯示更多設定";
  editorModal.classList.remove("is-open");
  editorModal.setAttribute("aria-hidden", "true");
}

function buildNotePayload(existing = null) {
  const title = normalize(editorForm.elements.title.value);
  const content = normalize(editorForm.elements.content.value);
  const theme = collectChosenValue(themeSelect, themeCustomInput, existing?.theme || "未分類");
  const category = collectChosenValue(categorySelect, categoryCustomInput, existing?.category || "未分類");
  const visibility = normalize(visibilitySelect?.value) || existing?.visibility || "private";
  return {
    title,
    content,
    theme,
    category,
    visibility,
    createdAt: existing?.createdAt || serverTimestamp(),
    updatedAt: serverTimestamp(),
  };
}

async function syncPublicRecipe(note, owner) {
  const ref = publicRecipeRef(note.id);
  if (note.visibility !== "public") {
    await deleteDoc(ref).catch(() => {});
    return;
  }

  const existing = await getDoc(ref);
  const current = existing.exists() ? existing.data() || {} : {};
  const payload = {
    title: note.title,
    content: note.content,
    ownerUid: owner.uid,
    ownerName: owner.displayName || owner.email || "匿名",
    category: note.theme || note.category || "未分類",
    createdAt: current.createdAt || note.createdAt || serverTimestamp(),
    avgRating: Number(current.avgRating || 0),
    ratingCount: Number(current.ratingCount || 0),
    visibility: "public",
    updatedAt: serverTimestamp(),
  };
  await setDoc(ref, payload, { merge: true });
}

async function saveNote(event) {
  event.preventDefault();
  if (!currentUser) return;

  const existing = currentEditorNote();
  const noteId = currentEditId || randomId();
  const ref = noteDocRef(currentUser.uid, noteId);
  const payload = buildNotePayload(existing);

  await setDoc(ref, payload);
  await syncPublicRecipe({ id: noteId, ...payload }, currentUser);
  await ensureUserDocument(currentUser);
  closeEditor();
  setStatus("已儲存。");
}

async function deleteCurrentNote() {
  if (!currentUser) return;
  const existing = currentEditorNote();
  if (!existing) return;
  await deleteDoc(noteDocRef(currentUser.uid, existing.id));
  await deleteDoc(publicRecipeRef(existing.id)).catch(() => {});
  closeEditor();
  if (route.view === "note" && route.id === existing.id) navigate({ view: "notes" });
  setStatus("已刪除。");
}

async function toggleNotePublic(noteId) {
  if (!currentUser) return;
  const note = ensureCurrentUserNote(noteId);
  if (!note) return;
  const nextVisibility = note.visibility === "public" ? "private" : "public";
  await setDoc(
    noteDocRef(currentUser.uid, noteId),
    {
      visibility: nextVisibility,
      updatedAt: serverTimestamp(),
    },
    { merge: true },
  );
  await syncPublicRecipe({ ...note, visibility: nextVisibility }, currentUser);
  setStatus(nextVisibility === "public" ? "已公開分享。" : "已取消公開。");
}

async function rateRecipe(recipeId, rating) {
  if (!currentUser) {
    setStatus("請先登入後再評分。");
    return;
  }
  const recipeRef = publicRecipeRef(recipeId);
  const ratingRef = publicRatingRef(recipeId, currentUser.uid);

  await runTransaction(db, async (transaction) => {
    const recipeSnap = await transaction.get(recipeRef);
    if (!recipeSnap.exists()) {
      throw new Error("recipe-not-found");
    }
    const recipeData = recipeSnap.data() || {};
    const currentRatingSnap = await transaction.get(ratingRef);
    const previousRating = currentRatingSnap.exists() ? Number(currentRatingSnap.data()?.rating || 0) : 0;
    const ratingCount = Number(recipeData.ratingCount || 0);
    const avgRating = Number(recipeData.avgRating || 0);
    const hasPrevious = currentRatingSnap.exists();
    const nextCount = hasPrevious ? ratingCount : ratingCount + 1;
    const total = avgRating * ratingCount - previousRating + rating;
    const nextAverage = nextCount > 0 ? Number((total / nextCount).toFixed(2)) : 0;

    transaction.set(
      ratingRef,
      {
        uid: currentUser.uid,
        rating,
        createdAt: currentRatingSnap.exists() ? currentRatingSnap.data()?.createdAt || serverTimestamp() : serverTimestamp(),
        updatedAt: serverTimestamp(),
      },
      { merge: true },
    );
    transaction.update(recipeRef, {
      avgRating: nextAverage,
      ratingCount: nextCount,
      updatedAt: serverTimestamp(),
    });
  });

  setStatus(`已評分 ${rating} 星。`);
}

async function toggleFavorite(recipeId) {
  if (!currentUser) {
    setStatus("請先登入後再收藏。");
    return;
  }
  const ref = publicFavoriteRef(recipeId, currentUser.uid);
  const snap = await getDoc(ref);
  if (snap.exists()) {
    await deleteDoc(ref);
    setStatus("已移除收藏。");
  } else {
    await setDoc(
      ref,
      {
        uid: currentUser.uid,
        createdAt: serverTimestamp(),
      },
      { merge: true },
    );
    setStatus("已加入收藏。");
  }
}

function downloadText(filename, text, mimeType = "text/plain;charset=utf-8") {
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

function rowsToCsv(rows) {
  const headers = ["id", "title", "content", "theme", "category", "visibility", "createdAt", "updatedAt"];
  const escapeCsv = (value) => {
    const text = normalize(value).replaceAll('"', '""');
    return /[",\n]/.test(text) ? `"${text}"` : text;
  };
  return [headers.join(","), ...rows.map((row) => headers.map((header) => escapeCsv(row[header])).join(","))].join("\n");
}

function buildExportRows() {
  return notes.map((note) => ({
    id: note.id,
    title: note.title,
    content: note.content,
    theme: note.theme,
    category: note.category,
    visibility: note.visibility,
    createdAt: formatDate(note.createdAt),
    updatedAt: formatDate(note.updatedAt),
  }));
}

function exportCsv() {
  if (!notes.length) {
    setStatus("目前沒有可匯出的筆記。");
    return;
  }
  downloadText("livenote.csv", rowsToCsv(buildExportRows()), "text/csv;charset=utf-8");
  setStatus("已匯出 livenote.csv。");
}

async function writeRowsToFirestore(rows) {
  if (!currentUser) return;
  const batchSize = 380;
  for (let index = 0; index < rows.length; index += batchSize) {
    const batch = writeBatch(db);
    for (const row of rows.slice(index, index + batchSize)) {
      const noteId = normalize(row.id) || randomId();
      const ref = noteDocRef(currentUser.uid, noteId);
      batch.set(ref, {
        title: normalize(row.title),
        content: normalize(row.content),
        theme: normalize(row.theme) || "未分類",
        category: normalize(row.category) || "未分類",
        visibility: normalize(row.visibility) || "private",
        createdAt: row.createdAt ? toTimestamp(row.createdAt) : serverTimestamp(),
        updatedAt: row.updatedAt ? toTimestamp(row.updatedAt) : serverTimestamp(),
      });
    }
    await batch.commit();
  }
}

function normalizeImportedRow(row) {
  return {
    id: normalize(row.id || row.ID || ""),
    title: normalize(row.title || row["標題"] || row["名稱"] || row["name"]),
    content: normalize(row.content || row["內容"] || row["摘要"] || row["body"]),
    theme: normalize(row.theme || row["主題"] || row["分類"] || row["theme"]),
    category: normalize(row.category || row["子分類"] || row["category"]),
    visibility: normalize(row.visibility || row["visibility"]) || "private",
    createdAt: normalize(row.createdAt || row["createdAt"] || row["建立時間"]),
    updatedAt: normalize(row.updatedAt || row["updatedAt"] || row["更新時間"]),
  };
}

async function importNotesFromFile(event) {
  const file = event.target.files?.[0];
  event.target.value = "";
  if (!file || !currentUser) return;
  if (typeof XLSX === "undefined") {
    setStatus("找不到 XLSX 套件，無法匯入。");
    return;
  }

  const ext = file.name.split(".").pop().toLowerCase();
  let rows = [];
  if (ext === "csv") {
    const text = await file.text();
    const workbook = XLSX.read(text, { type: "string" });
    rows = XLSX.utils.sheet_to_json(workbook.Sheets[workbook.SheetNames[0]] || {});
  } else {
    const buffer = await file.arrayBuffer();
    const workbook = XLSX.read(buffer, { type: "array" });
    rows = XLSX.utils.sheet_to_json(workbook.Sheets[workbook.SheetNames[0]] || {});
  }

  const normalizedRows = rows.map(normalizeImportedRow).filter((row) => row.title || row.content);
  if (!normalizedRows.length) {
    setStatus("匯入檔案沒有可用資料。");
    return;
  }

  await writeRowsToFirestore(normalizedRows);
  setStatus(`已匯入 ${normalizedRows.length} 筆資料。`);
}

function bindContentActions() {
  content.addEventListener("click", async (event) => {
    const routeButton = event.target.closest("[data-route]");
    if (routeButton) {
      event.preventDefault();
      navigateToPath(routeButton.dataset.route);
      return;
    }

    const actionButton = event.target.closest("[data-action]");
    if (!actionButton) return;

    const action = actionButton.dataset.action;
    const noteId = normalize(actionButton.dataset.noteId);
    const recipeId = normalize(actionButton.dataset.recipeId);
    const rating = Number(actionButton.dataset.rating || 0);

    try {
      if (action === "edit-note") {
        const note = ensureCurrentUserNote(noteId) || getCurrentRecipe(noteId);
        openEditor(note && note.content !== undefined ? note : currentEditId ? currentEditorNote() : note);
      } else if (action === "toggle-note-public") {
        await toggleNotePublic(noteId);
      } else if (action === "rate-recipe") {
        await rateRecipe(recipeId, rating);
      } else if (action === "favorite-toggle") {
        await toggleFavorite(recipeId);
      }
    } catch (error) {
      console.error(error);
      setStatus("操作失敗，請稍後再試。");
    }
  });

  content.addEventListener("change", (event) => {
    const select = event.target.closest("[data-public-sort]");
    if (select) {
      publicSortMode = normalize(select.value) || "latest";
      render();
    }
  });
}

function wireEvents() {
  backButton.addEventListener("click", () => history.back());
  toolsButton.addEventListener("click", () => {
    if (drawer.classList.contains("is-open")) closeDrawer();
    else openDrawer();
  });
  closeDrawerButton.addEventListener("click", closeDrawer);
  signInButton.addEventListener("click", signInWithGoogle);
  signOutButton.addEventListener("click", signOutUser);
  newItemButton.addEventListener("click", () => openEditor());
  closeEditorButton.addEventListener("click", closeEditor);
  deleteButton.addEventListener("click", deleteCurrentNote);
  exportCsvButton.addEventListener("click", exportCsv);
  importInput.addEventListener("change", importNotesFromFile);
  searchInput.addEventListener("input", render);
  advancedToggleButton.addEventListener("click", () => {
    const collapsed = advancedFields.classList.toggle("is-collapsed");
    advancedToggleButton.textContent = collapsed ? "顯示更多設定" : "收合進階設定";
  });
  editorForm.addEventListener("submit", saveNote);
  themeSelect.addEventListener("change", () => toggleCustomRow(themeSelect, themeCustomRow, themeCustomInput));
  categorySelect.addEventListener("change", () =>
    toggleCustomRow(categorySelect, categoryCustomRow, categoryCustomInput),
  );
  window.addEventListener("popstate", render);
  bindContentActions();
}

async function handleAuthState(user) {
  currentUser = user || null;
  notesLoaded = false;
  favoritesLoaded = false;
  notes = [];
  favoriteRecipeIds = new Set();

  if (notesUnsubscribe) {
    notesUnsubscribe();
    notesUnsubscribe = null;
  }
  if (favoritesUnsubscribe) {
    favoritesUnsubscribe();
    favoritesUnsubscribe = null;
  }

  if (currentUser) {
    try {
      await ensureUserDocument(currentUser);
    } catch (error) {
      console.error(error);
    }
    subscribeToPrivateNotes(currentUser.uid);
    subscribeToFavorites(currentUser.uid);
    setStatus("已登入並同步個人資料。");
  } else {
    notesLoaded = false;
    favoritesLoaded = true;
    setStatus("請登入 Google 帳號以開始使用。");
  }
  render();
}

function init() {
  wireEvents();
  subscribeToPublicRecipes();
  onAuthStateChanged(auth, (user) => {
    authReady = true;
    handleAuthState(user);
  });
  render();
}

init();
