const DATA_FILE = "data.xlsx";
const CONFIG_KEY = "notebookGoogleSheetsConfig";
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

const fallbackRows = [
  {
    id: "recipe-zh-braised-pork",
    status: "active",
    theme: "食譜",
    theme_icon: "🍳",
    theme_color: "#b14f35",
    category: "中式",
    title: "家常滷肉",
    summary: "適合便當與拌飯的基礎滷肉。",
    content: "1. 五花肉切小塊，乾鍋煸出油香。\n2. 加入蒜、醬油、米酒、冰糖炒上色。\n3. 加水蓋過食材，小火燉 45 分鐘。\n4. 起鍋前試鹹度，可加水煮蛋一起滷。",
    tags: "便當,下飯",
    updated_at: "2026-05-29",
  },
  {
    id: "recipe-zh-tomato-egg",
    status: "active",
    theme: "食譜",
    theme_icon: "🍳",
    theme_color: "#b14f35",
    category: "中式",
    title: "番茄炒蛋",
    summary: "十分鐘完成的日常菜。",
    content: "1. 蛋加少許鹽打散，先炒至半熟盛起。\n2. 番茄切塊下鍋炒出汁。\n3. 加回蛋，補少許糖與鹽。\n4. 撒蔥花後起鍋。",
    tags: "快速,家常",
    updated_at: "2026-05-29",
  },
  {
    id: "recipe-west-pasta",
    status: "active",
    theme: "食譜",
    theme_icon: "🍳",
    theme_color: "#b14f35",
    category: "西式",
    title: "蒜香橄欖油義大利麵",
    summary: "材料少、很適合平日晚餐。",
    content: "1. 義大利麵煮到比包裝時間少 1 分鐘。\n2. 橄欖油小火煸香蒜片與辣椒。\n3. 加入麵與少量煮麵水乳化。\n4. 以鹽、黑胡椒與巴西里調味。",
    tags: "麵食,快速",
    updated_at: "2026-05-29",
  },
  {
    id: "recipe-jp-curry",
    status: "active",
    theme: "食譜",
    theme_icon: "🍳",
    theme_color: "#b14f35",
    category: "日式",
    title: "日式咖哩飯",
    summary: "可一次煮多份冷藏。",
    content: "1. 洋蔥炒到透明後加入肉塊煎香。\n2. 加紅蘿蔔、馬鈴薯與水燉煮。\n3. 關火放入咖哩塊，融化後再小火煮濃。\n4. 配白飯與福神漬。",
    tags: "備餐,飯食",
    updated_at: "2026-05-29",
  },
  {
    id: "life-cleaning",
    status: "active",
    theme: "生活備忘",
    theme_icon: "🗂",
    theme_color: "#2e6f6b",
    category: "家務",
    title: "週末整理清單",
    summary: "固定整理項目，避免漏掉。",
    content: "1. 更換床單與枕套。\n2. 清洗浴室排水孔。\n3. 檢查冰箱即期食材。\n4. 補充垃圾袋、洗碗精與衛生紙。",
    tags: "週末,清潔",
    updated_at: "2026-05-29",
  },
];

let rows = [];
let route = { view: "home" };
let dirty = false;
let syncMessage = "";
let config = loadConfig();

const content = document.querySelector("#content");
const pageTitle = document.querySelector("#pageTitle");
const crumbLabel = document.querySelector("#crumbLabel");
const backButton = document.querySelector("#backButton");
const searchInput = document.querySelector("#searchInput");
const drawer = document.querySelector("#drawer");
const editorModal = document.querySelector("#editorModal");
const editorForm = document.querySelector("#editorForm");
const googleUrlInput = document.querySelector("#googleScriptUrl");
const googlePasscodeInput = document.querySelector("#googlePasscode");
const syncStatus = document.querySelector("#syncStatus");

const normalize = (value) => String(value ?? "").trim();
const slug = (value) => encodeURIComponent(normalize(value));
const today = () => new Date().toISOString().slice(0, 10);
const activeRows = () => rows.filter((row) => normalize(row.status).toLowerCase() !== "archived");

function loadConfig() {
  try {
    return JSON.parse(localStorage.getItem(CONFIG_KEY) || "{}");
  } catch {
    return {};
  }
}

function saveConfig() {
  config = {
    scriptUrl: normalize(googleUrlInput.value),
    passcode: normalize(googlePasscodeInput.value),
  };
  localStorage.setItem(CONFIG_KEY, JSON.stringify(config));
  setSyncStatus(config.scriptUrl ? "Google Sheets 連線設定已儲存。" : "尚未設定 Google Sheets。");
}

function setSyncStatus(message) {
  syncMessage = message;
  if (syncStatus) syncStatus.textContent = message;
  if (route.view === "home") render();
}

function escapeHtml(value) {
  return normalize(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function groupBy(items, key) {
  return items.reduce((groups, item) => {
    const name = normalize(item[key]) || "未分類";
    groups[name] = groups[name] || [];
    groups[name].push(item);
    return groups;
  }, {});
}

function getFilteredRows() {
  const query = normalize(searchInput.value).toLowerCase();
  if (!query) return activeRows();
  return activeRows().filter((row) => {
    return ["theme", "category", "title", "summary", "content", "tags"].some((key) =>
      normalize(row[key]).toLowerCase().includes(query),
    );
  });
}

function setRoute(nextRoute) {
  route = nextRoute;
  const parts = [nextRoute.view, nextRoute.theme, nextRoute.category, nextRoute.id].filter(Boolean).map(slug);
  location.hash = parts.join("/");
  render();
}

function readRoute() {
  const [view = "home", theme, category, id] = location.hash.replace(/^#\/?/, "").split("/").map(decodeURIComponent);
  route = { view, theme, category, id };
}

function summaryForTheme(items) {
  const categories = groupBy(items, "category");
  return Object.entries(categories)
    .map(([name, list]) => `${escapeHtml(name)} (${list.length})`)
    .join(" | ");
}

function barsForTheme(items, color) {
  const categories = groupBy(items, "category");
  const max = Math.max(...Object.values(categories).map((list) => list.length), 1);
  return Object.entries(categories)
    .slice(0, 4)
    .map(([name, list]) => {
      const width = Math.round((list.length / max) * 100);
      return `<div class="bar" style="--tile-color:${escapeHtml(color)};">
        <span>${escapeHtml(name)}</span>
        <span class="bar-track"><span class="bar-fill" style="--bar-width:${width}%"></span></span>
        <span>${list.length}</span>
      </div>`;
    })
    .join("");
}

function renderHome() {
  const themes = groupBy(getFilteredRows(), "theme");
  pageTitle.textContent = "生活記事本";
  crumbLabel.textContent = dirty ? "有尚未同步的修改" : config.scriptUrl ? "Google Sheets 已連線" : "個人資料庫";
  backButton.style.visibility = "hidden";

  const notice = syncMessage ? `<div class="sync-banner">${escapeHtml(syncMessage)}</div>` : "";
  const html = Object.entries(themes)
    .map(([theme, items]) => {
      const first = items[0] || {};
      const color = normalize(first.theme_color) || "#2e6f6b";
      return `<button class="tile" type="button" style="--tile-color:${escapeHtml(color)};" data-theme="${escapeHtml(theme)}">
        <div>
          <span class="tile-icon">${escapeHtml(first.theme_icon) || "□"}</span>
          <h2>${escapeHtml(theme)}</h2>
          <p>${summaryForTheme(items)}</p>
        </div>
        <div class="count-strip">${barsForTheme(items, color)}</div>
      </button>`;
    })
    .join("");

  content.innerHTML = notice + (html ? `<div class="tile-grid">${html}</div>` : empty("找不到符合的記事。"));
  content.querySelectorAll("[data-theme]").forEach((button) => {
    button.addEventListener("click", () => setRoute({ view: "theme", theme: button.dataset.theme }));
  });
}

function renderTheme() {
  const themeRows = getFilteredRows().filter((row) => normalize(row.theme) === route.theme);
  const categories = groupBy(themeRows, "category");
  const first = themeRows[0] || {};
  const color = normalize(first.theme_color) || "#2e6f6b";
  pageTitle.textContent = route.theme || "主題";
  crumbLabel.textContent = "分類";
  backButton.style.visibility = "visible";

  const html = Object.entries(categories)
    .map(([category, items]) => `<button class="tile" type="button" style="--tile-color:${escapeHtml(color)};" data-category="${escapeHtml(category)}">
      <div>
        <span class="tile-icon">${escapeHtml(first.theme_icon) || "□"}</span>
        <h2>${escapeHtml(category)}</h2>
        <p>${items.length} 筆記事</p>
      </div>
      <div class="count-strip">${barsForTheme(items, color)}</div>
    </button>`)
    .join("");

  content.innerHTML = html ? `<div class="tile-grid">${html}</div>` : empty("這個主題目前沒有資料。");
  content.querySelectorAll("[data-category]").forEach((button) => {
    button.addEventListener("click", () => setRoute({ view: "category", theme: route.theme, category: button.dataset.category }));
  });
}

function renderCategory() {
  const list = getFilteredRows().filter(
    (row) => normalize(row.theme) === route.theme && normalize(row.category) === route.category,
  );
  pageTitle.textContent = route.category || "分類";
  crumbLabel.textContent = route.theme || "主題";
  backButton.style.visibility = "visible";

  const html = list
    .map((row) => `<button class="list-item" type="button" data-id="${escapeHtml(row.id)}">
      <h2>${escapeHtml(row.title)}</h2>
      <div class="meta-line">${escapeHtml(row.updated_at)} · ${escapeHtml(row.tags)}</div>
      <p class="summary">${escapeHtml(row.summary)}</p>
    </button>`)
    .join("");

  content.innerHTML = html ? `<div class="list-stack">${html}</div>` : empty("這個分類目前沒有資料。");
  content.querySelectorAll("[data-id]").forEach((button) => {
    button.addEventListener("click", () =>
      setRoute({ view: "detail", theme: route.theme, category: route.category, id: button.dataset.id }),
    );
  });
}

function renderDetail() {
  const item = activeRows().find((row) => normalize(row.id) === route.id);
  pageTitle.textContent = item ? normalize(item.title) : "找不到記事";
  crumbLabel.textContent = item ? `${normalize(item.theme)} / ${normalize(item.category)}` : "內容";
  backButton.style.visibility = "visible";

  if (!item) {
    content.innerHTML = empty("這筆資料不存在，或已經被封存。");
    return;
  }

  const tags = normalize(item.tags)
    .split(",")
    .map((tag) => tag.trim())
    .filter(Boolean)
    .map((tag) => `<span class="tag">${escapeHtml(tag)}</span>`)
    .join("");

  content.innerHTML = `<article class="detail-card">
    <div class="detail-actions">
      <button class="secondary-action" id="editCurrentButton" type="button">編輯</button>
    </div>
    <h2>${escapeHtml(item.title)}</h2>
    <div class="meta-line">${escapeHtml(item.updated_at)} · ${escapeHtml(item.theme)} · ${escapeHtml(item.category)}</div>
    <p class="summary">${escapeHtml(item.summary)}</p>
    <div class="content-block">${escapeHtml(item.content)}</div>
    <div class="tag-row">${tags}</div>
  </article>`;

  document.querySelector("#editCurrentButton").addEventListener("click", () => openEditor(item));
}

function empty(message) {
  return `<div class="empty-state">${escapeHtml(message)}</div>`;
}

function render() {
  if (route.view === "theme") renderTheme();
  else if (route.view === "category") renderCategory();
  else if (route.view === "detail") renderDetail();
  else renderHome();
}

function openEditor(item = null) {
  const isEdit = Boolean(item);
  document.querySelector("#editorModeLabel").textContent = isEdit ? "編輯" : "新增";
  document.querySelector("#editorTitle").textContent = isEdit ? normalize(item.title) : "記事";
  editorForm.reset();

  const defaults = {
    id: "",
    status: "active",
    theme: route.theme || "食譜",
    theme_icon: "🍳",
    theme_color: "#b14f35",
    category: route.category || "",
    title: "",
    summary: "",
    content: "",
    tags: "",
    updated_at: today(),
    ...item,
  };

  HEADERS.forEach((key) => {
    if (editorForm.elements[key]) editorForm.elements[key].value = normalize(defaults[key]);
  });
  document.querySelector("#archiveButton").style.visibility = isEdit ? "visible" : "hidden";
  editorModal.classList.add("is-open");
  editorModal.setAttribute("aria-hidden", "false");
}

function closeEditor() {
  editorModal.classList.remove("is-open");
  editorModal.setAttribute("aria-hidden", "true");
}

function makeId(values) {
  const base = `${values.theme}-${values.category}-${values.title}`
    .toLowerCase()
    .replace(/[^\p{L}\p{N}]+/gu, "-")
    .replace(/^-+|-+$/g, "");
  const stamp = Date.now().toString(36);
  return `${base || "note"}-${stamp}`;
}

function formValues() {
  const data = Object.fromEntries(new FormData(editorForm).entries());
  const values = {};
  HEADERS.forEach((key) => {
    values[key] = normalize(data[key]);
  });
  values.status = values.status || "active";
  values.theme_icon = values.theme_icon || "□";
  values.theme_color = values.theme_color || "#2e6f6b";
  values.updated_at = values.updated_at || today();
  values.id = values.id || makeId(values);
  return values;
}

async function saveForm(event) {
  event.preventDefault();
  const values = formValues();
  upsertLocal(values);
  closeEditor();
  setRoute({ view: "detail", theme: values.theme, category: values.category, id: values.id });
  await syncRow(values);
}

function upsertLocal(values) {
  const index = rows.findIndex((row) => normalize(row.id) === values.id);
  if (index >= 0) rows[index] = { ...rows[index], ...values };
  else rows.push(values);
  dirty = true;
}

async function archiveCurrent() {
  const id = normalize(editorForm.elements.id.value);
  const index = rows.findIndex((row) => normalize(row.id) === id);
  if (index < 0) return;
  rows[index].status = "archived";
  rows[index].updated_at = today();
  dirty = true;
  const archived = { ...rows[index] };
  closeEditor();
  setRoute({ view: "home" });
  await syncRow(archived);
}

function downloadWorkbook() {
  if (!window.XLSX) {
    alert("Excel 套件尚未載入，請稍後再試。");
    return;
  }
  const cleanRows = rows.map(normalizeRow);
  const workbook = XLSX.utils.book_new();
  const notes = XLSX.utils.json_to_sheet(cleanRows, { header: HEADERS });
  XLSX.utils.book_append_sheet(workbook, notes, "notes");
  const guide = XLSX.utils.aoa_to_sheet([
    ["欄位", "說明"],
    ["id", "唯一代號，不要重複。"],
    ["status", "active 顯示；archived 隱藏，建議不要刪資料。"],
    ["theme", "大主題，例如食譜、生活備忘。"],
    ["theme_icon", "主題圖示。"],
    ["theme_color", "主題色碼。"],
    ["category", "分類，例如中式、西式、日式。"],
    ["title", "記事或食譜名稱。"],
    ["summary", "列表摘要。"],
    ["content", "內頁內容，可換行。"],
    ["tags", "半形逗號分隔。"],
    ["updated_at", "更新日期。"],
  ]);
  XLSX.utils.book_append_sheet(workbook, guide, "guide");
  XLSX.writeFile(workbook, `data-updated-${today()}.xlsx`);
  dirty = false;
  render();
}

function normalizeRow(row) {
  const clean = {};
  HEADERS.forEach((key) => {
    clean[key] = normalize(row[key]);
  });
  return clean;
}

function googleParams(extra = {}) {
  const params = new URLSearchParams(extra);
  if (config.passcode) params.set("passcode", config.passcode);
  return params;
}

function loadGoogleRows() {
  return new Promise((resolve, reject) => {
    if (!config.scriptUrl) {
      reject(new Error("Google Apps Script URL is missing."));
      return;
    }
    const callback = `notebookCallback_${Date.now()}_${Math.random().toString(36).slice(2)}`;
    const params = googleParams({ action: "list", callback });
    const script = document.createElement("script");
    const timer = window.setTimeout(() => {
      cleanup();
      reject(new Error("Google Sheets 同步逾時。"));
    }, 15000);

    function cleanup() {
      window.clearTimeout(timer);
      delete window[callback];
      script.remove();
    }

    window[callback] = (payload) => {
      cleanup();
      if (!payload || payload.ok === false) {
        reject(new Error(payload?.error || "Google Sheets 回傳錯誤。"));
        return;
      }
      resolve((payload.rows || []).map(normalizeRow));
    };

    script.onerror = () => {
      cleanup();
      reject(new Error("無法讀取 Google Sheets。"));
    };
    script.src = `${config.scriptUrl}?${params.toString()}`;
    document.body.appendChild(script);
  });
}

async function syncRow(row) {
  if (!config.scriptUrl) {
    setSyncStatus("已儲存在目前頁面，尚未設定 Google Sheets。");
    return;
  }
  try {
    setSyncStatus("正在寫入 Google Sheets...");
    await fetch(config.scriptUrl, {
      method: "POST",
      mode: "no-cors",
      headers: { "Content-Type": "text/plain;charset=utf-8" },
      body: JSON.stringify({
        action: "upsert",
        passcode: config.passcode || "",
        row: normalizeRow(row),
      }),
    });
    dirty = false;
    setSyncStatus("已送出到 Google Sheets。請按同步確認最新資料。");
  } catch (error) {
    setSyncStatus(`Google Sheets 寫入失敗：${error.message}`);
  }
}

async function syncFromGoogle() {
  saveConfig();
  if (!config.scriptUrl) {
    setSyncStatus("請先貼上 Apps Script Web App URL。");
    return;
  }
  try {
    setSyncStatus("正在從 Google Sheets 同步...");
    rows = await loadGoogleRows();
    dirty = false;
    readRoute();
    setSyncStatus(`已從 Google Sheets 載入 ${rows.length} 筆資料。`);
    render();
  } catch (error) {
    setSyncStatus(`Google Sheets 同步失敗：${error.message}`);
  }
}

async function loadWorkbookFromArrayBuffer(buffer) {
  if (!window.XLSX) throw new Error("SheetJS library is unavailable.");
  const workbook = XLSX.read(buffer, { type: "array" });
  const sheet = workbook.Sheets.notes || workbook.Sheets[workbook.SheetNames[0]];
  rows = XLSX.utils.sheet_to_json(sheet, { defval: "" }).map(normalizeRow);
  dirty = false;
  readRoute();
  render();
}

async function loadDefaultData() {
  googleUrlInput.value = config.scriptUrl || "";
  googlePasscodeInput.value = config.passcode || "";
  if (config.scriptUrl) {
    try {
      await syncFromGoogle();
      return;
    } catch {
      // syncFromGoogle already reports the error.
    }
  }
  try {
    const response = await fetch(DATA_FILE, { cache: "no-store" });
    if (!response.ok) throw new Error("data.xlsx not found");
    await loadWorkbookFromArrayBuffer(await response.arrayBuffer());
  } catch (error) {
    rows = fallbackRows.map(normalizeRow);
    readRoute();
    render();
  }
}

backButton.addEventListener("click", () => {
  if (route.view === "detail") setRoute({ view: "category", theme: route.theme, category: route.category });
  else if (route.view === "category") setRoute({ view: "theme", theme: route.theme });
  else setRoute({ view: "home" });
});

searchInput.addEventListener("input", render);
window.addEventListener("hashchange", () => {
  readRoute();
  render();
});

document.querySelector("#toolsButton").addEventListener("click", () => {
  drawer.classList.add("is-open");
  drawer.setAttribute("aria-hidden", "false");
});

document.querySelector("#closeDrawerButton").addEventListener("click", () => {
  drawer.classList.remove("is-open");
  drawer.setAttribute("aria-hidden", "true");
});

drawer.addEventListener("click", (event) => {
  if (event.target === drawer) {
    drawer.classList.remove("is-open");
    drawer.setAttribute("aria-hidden", "true");
  }
});

document.querySelector("#excelInput").addEventListener("change", async (event) => {
  const [file] = event.target.files;
  if (!file) return;
  await loadWorkbookFromArrayBuffer(await file.arrayBuffer());
});

document.querySelector("#newItemButton").addEventListener("click", () => {
  drawer.classList.remove("is-open");
  drawer.setAttribute("aria-hidden", "true");
  openEditor();
});

document.querySelector("#downloadCurrentButton").addEventListener("click", downloadWorkbook);
document.querySelector("#saveGoogleConfigButton").addEventListener("click", saveConfig);
document.querySelector("#syncGoogleButton").addEventListener("click", syncFromGoogle);
document.querySelector("#closeEditorButton").addEventListener("click", closeEditor);
document.querySelector("#archiveButton").addEventListener("click", archiveCurrent);
editorForm.addEventListener("submit", saveForm);
editorModal.addEventListener("click", (event) => {
  if (event.target === editorModal) closeEditor();
});

loadDefaultData();
