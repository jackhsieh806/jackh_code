const STORAGE_KEY = "language";
const DEFAULT_LANGUAGE = "zh-TW";
const SUPPORTED_LANGUAGES = ["zh-TW", "en", "ja", "ko"];

const LANGUAGE_NAMES = {
  "zh-TW": "繁體中文",
  en: "English",
  ja: "日本語",
  ko: "한국어",
};

const TRANSLATIONS = {
  "zh-TW": {
    appName: "LiveNote",
    appSubtitle: "筆記與料理",
    sidebarTitle: "工作區",
    newNote: "新增筆記",
    notesHome: "我的筆記",
    groups: "群組",
    publicNotes: "公開筆記",
    popular: "熱門",
    favorites: "收藏",
    account: "帳號",
    signInGoogle: "登入 Google",
    settings: "設定",
    signOut: "登出",
    language: "語言",
    languageAuto: "自動偵測",
    syncStatusLoading: "正在同步至 Firebase...",
    syncStatusReady: "已連線 Firebase",
    exportImport: "匯出 / 匯入",
    exportCsv: "匯出 CSV",
    importExcelCsv: "匯入 Excel / CSV",
    customOption: "+ 自訂",
    back: "返回",
    openSidebar: "開啟側欄",
    closeSidebar: "關閉側欄",
    closeEditor: "關閉編輯器",
    searchPrivate: "搜尋筆記、主題、分類或狀態",
    searchPublic: "搜尋公開筆記、作者或內容",
    editorDraft: "草稿",
    editorEdit: "編輯",
    editorNewTitle: "新增筆記",
    editorEditTitle: "編輯筆記",
    titleLabel: "標題",
    titlePlaceholder: "輸入標題",
    contentLabel: "內容",
    contentPlaceholder: "輸入內容",
    advancedOpen: "顯示進階欄位",
    advancedClose: "收合進階欄位",
    themeLabel: "主題",
    customThemeLabel: "自訂主題",
    customThemePlaceholder: "輸入主題",
    categoryLabel: "分類",
    customCategoryLabel: "自訂分類",
    customCategoryPlaceholder: "輸入分類",
    visibilityLabel: "可見性",
    visibilityPrivate: "私密",
    visibilityGroup: "群組",
    visibilityPublic: "公開",
    delete: "刪除",
    save: "儲存",
    emptyHome: "目前沒有任何筆記",
    emptyTheme: "這個主題還沒有筆記",
    emptyCategory: "這個分類還沒有筆記",
    emptyNote: "找不到這則筆記",
    emptyPublic: "目前沒有公開筆記",
    emptyRecipe: "目前沒有公開料理",
    emptyFavorites: "你還沒有收藏任何料理",
    emptyGroups: "目前沒有群組筆記",
    emptySearch: "沒有符合條件的結果",
    drawerHint: "側欄選單",
    settingsHint: "設定與語言",
    authMenuSettings: "設定",
    authMenuSignOut: "登出",
    authMenuSignIn: "登入",
    menuNotes: "我的筆記",
    menuGroups: "群組",
    menuPublic: "公開筆記",
    menuPopular: "熱門",
    menuFavorites: "收藏",
    statusSaved: "已儲存",
    statusDeleted: "已刪除",
    statusSignedIn: "已登入",
    statusSignedOut: "已登出",
    statusLanguageSaved: "語言設定已更新",
    statusLanguageLoaded: "已套用語言設定",
    statusSignInFailed: "Google 登入失敗",
    statusSignOutFailed: "登出失敗",
    statusImportFailed: "匯入失敗",
    statusExported: "已匯出 CSV",
    statusNoNotes: "目前沒有筆記可匯出",
    statusNoPublicData: "目前沒有公開資料",
    statusNoFavorites: "目前沒有收藏資料",
    statusSavedToFirestore: "已同步偏好設定",
    routeNotes: "我的筆記",
    routeGroups: "群組",
    routePublic: "公開筆記",
    routePopular: "熱門",
    routeFavorites: "收藏",
    routeTheme: "主題",
    routeCategory: "分類",
    routeNote: "筆記",
    routeRecipe: "料理",
  },
  en: {
    appName: "LiveNote",
    appSubtitle: "Notes and recipes",
    sidebarTitle: "Workspace",
    newNote: "New note",
    notesHome: "My notes",
    groups: "Groups",
    publicNotes: "Public notes",
    popular: "Popular",
    favorites: "Favorites",
    account: "Account",
    signInGoogle: "Sign in with Google",
    settings: "Settings",
    signOut: "Sign out",
    language: "Language",
    languageAuto: "Auto-detect",
    syncStatusLoading: "Syncing to Firebase...",
    syncStatusReady: "Connected to Firebase",
    exportImport: "Export / Import",
    exportCsv: "Export CSV",
    importExcelCsv: "Import Excel / CSV",
    customOption: "+ Custom",
    back: "Back",
    openSidebar: "Open sidebar",
    closeSidebar: "Close sidebar",
    closeEditor: "Close editor",
    searchPrivate: "Search notes, themes, categories, or status",
    searchPublic: "Search public notes, authors, or content",
    editorDraft: "Draft",
    editorEdit: "Edit",
    editorNewTitle: "New note",
    editorEditTitle: "Edit note",
    titleLabel: "Title",
    titlePlaceholder: "Enter title",
    contentLabel: "Content",
    contentPlaceholder: "Enter content",
    advancedOpen: "Show advanced fields",
    advancedClose: "Hide advanced fields",
    themeLabel: "Theme",
    customThemeLabel: "Custom theme",
    customThemePlaceholder: "Enter theme",
    categoryLabel: "Category",
    customCategoryLabel: "Custom category",
    customCategoryPlaceholder: "Enter category",
    visibilityLabel: "Visibility",
    visibilityPrivate: "Private",
    visibilityGroup: "Group",
    visibilityPublic: "Public",
    delete: "Delete",
    save: "Save",
    emptyHome: "No notes yet",
    emptyTheme: "No notes in this theme yet",
    emptyCategory: "No notes in this category yet",
    emptyNote: "This note could not be found",
    emptyPublic: "No public notes yet",
    emptyRecipe: "No public recipes yet",
    emptyFavorites: "You have no favorite recipes yet",
    emptyGroups: "No group notes yet",
    emptySearch: "No matching results",
    drawerHint: "Sidebar menu",
    settingsHint: "Settings and language",
    authMenuSettings: "Settings",
    authMenuSignOut: "Sign out",
    authMenuSignIn: "Sign in",
    menuNotes: "My notes",
    menuGroups: "Groups",
    menuPublic: "Public notes",
    menuPopular: "Popular",
    menuFavorites: "Favorites",
    statusSaved: "Saved",
    statusDeleted: "Deleted",
    statusSignedIn: "Signed in",
    statusSignedOut: "Signed out",
    statusLanguageSaved: "Language updated",
    statusLanguageLoaded: "Language applied",
    statusSignInFailed: "Google sign-in failed",
    statusSignOutFailed: "Sign-out failed",
    statusImportFailed: "Import failed",
    statusExported: "CSV exported",
    statusNoNotes: "No notes to export",
    statusNoPublicData: "No public data available",
    statusNoFavorites: "No favorite data available",
    statusSavedToFirestore: "Preferences synced",
    routeNotes: "My notes",
    routeGroups: "Groups",
    routePublic: "Public notes",
    routePopular: "Popular",
    routeFavorites: "Favorites",
    routeTheme: "Theme",
    routeCategory: "Category",
    routeNote: "Note",
    routeRecipe: "Recipe",
  },
  ja: {
    appName: "LiveNote",
    appSubtitle: "ノートとレシピ",
    sidebarTitle: "ワークスペース",
    newNote: "新規ノート",
    notesHome: "マイノート",
    groups: "グループ",
    publicNotes: "公開ノート",
    popular: "人気",
    favorites: "お気に入り",
    account: "アカウント",
    signInGoogle: "Google でログイン",
    settings: "設定",
    signOut: "ログアウト",
    language: "言語",
    languageAuto: "自動検出",
    syncStatusLoading: "Firebase に同期中...",
    syncStatusReady: "Firebase に接続しました",
    exportImport: "エクスポート / インポート",
    exportCsv: "CSV を出力",
    importExcelCsv: "Excel / CSV を取り込み",
    customOption: "+ カスタム",
    back: "戻る",
    openSidebar: "サイドバーを開く",
    closeSidebar: "サイドバーを閉じる",
    closeEditor: "エディタを閉じる",
    searchPrivate: "ノート、テーマ、カテゴリ、状態を検索",
    searchPublic: "公開ノート、作者、内容を検索",
    editorDraft: "下書き",
    editorEdit: "編集",
    editorNewTitle: "新規ノート",
    editorEditTitle: "ノートを編集",
    titleLabel: "タイトル",
    titlePlaceholder: "タイトルを入力",
    contentLabel: "内容",
    contentPlaceholder: "内容を入力",
    advancedOpen: "詳細項目を表示",
    advancedClose: "詳細項目を折りたたむ",
    themeLabel: "テーマ",
    customThemeLabel: "カスタムテーマ",
    customThemePlaceholder: "テーマを入力",
    categoryLabel: "カテゴリ",
    customCategoryLabel: "カスタムカテゴリ",
    customCategoryPlaceholder: "カテゴリを入力",
    visibilityLabel: "公開設定",
    visibilityPrivate: "非公開",
    visibilityGroup: "グループ",
    visibilityPublic: "公開",
    delete: "削除",
    save: "保存",
    emptyHome: "まだノートがありません",
    emptyTheme: "このテーマにはまだノートがありません",
    emptyCategory: "このカテゴリにはまだノートがありません",
    emptyNote: "このノートは見つかりませんでした",
    emptyPublic: "まだ公開ノートがありません",
    emptyRecipe: "まだ公開レシピがありません",
    emptyFavorites: "お気に入りのレシピはまだありません",
    emptyGroups: "まだグループノートがありません",
    emptySearch: "一致する結果がありません",
    drawerHint: "サイドバーメニュー",
    settingsHint: "設定と言語",
    authMenuSettings: "設定",
    authMenuSignOut: "ログアウト",
    authMenuSignIn: "ログイン",
    menuNotes: "マイノート",
    menuGroups: "グループ",
    menuPublic: "公開ノート",
    menuPopular: "人気",
    menuFavorites: "お気に入り",
    statusSaved: "保存しました",
    statusDeleted: "削除しました",
    statusSignedIn: "ログインしました",
    statusSignedOut: "ログアウトしました",
    statusLanguageSaved: "言語設定を更新しました",
    statusLanguageLoaded: "言語を適用しました",
    statusSignInFailed: "Google ログインに失敗しました",
    statusSignOutFailed: "ログアウトに失敗しました",
    statusImportFailed: "インポートに失敗しました",
    statusExported: "CSV を出力しました",
    statusNoNotes: "出力するノートがありません",
    statusNoPublicData: "公開データがありません",
    statusNoFavorites: "お気に入りデータがありません",
    statusSavedToFirestore: "設定を同期しました",
    routeNotes: "マイノート",
    routeGroups: "グループ",
    routePublic: "公開ノート",
    routePopular: "人気",
    routeFavorites: "お気に入り",
    routeTheme: "テーマ",
    routeCategory: "カテゴリ",
    routeNote: "ノート",
    routeRecipe: "レシピ",
  },
  ko: {
    appName: "LiveNote",
    appSubtitle: "메모와 레시피",
    sidebarTitle: "작업 공간",
    newNote: "새 메모",
    notesHome: "내 메모",
    groups: "그룹",
    publicNotes: "공개 메모",
    popular: "인기",
    favorites: "즐겨찾기",
    account: "계정",
    signInGoogle: "Google로 로그인",
    settings: "설정",
    signOut: "로그아웃",
    language: "언어",
    languageAuto: "자동 감지",
    syncStatusLoading: "Firebase에 동기화 중...",
    syncStatusReady: "Firebase에 연결됨",
    exportImport: "내보내기 / 가져오기",
    exportCsv: "CSV 내보내기",
    importExcelCsv: "Excel / CSV 가져오기",
    customOption: "+ 사용자 지정",
    back: "뒤로",
    openSidebar: "사이드바 열기",
    closeSidebar: "사이드바 닫기",
    closeEditor: "편집기 닫기",
    searchPrivate: "메모, 테마, 카테고리 또는 상태 검색",
    searchPublic: "공개 메모, 작성자 또는 내용 검색",
    editorDraft: "임시 저장",
    editorEdit: "편집",
    editorNewTitle: "새 메모",
    editorEditTitle: "메모 편집",
    titleLabel: "제목",
    titlePlaceholder: "제목 입력",
    contentLabel: "내용",
    contentPlaceholder: "내용 입력",
    advancedOpen: "고급 항목 표시",
    advancedClose: "고급 항목 접기",
    themeLabel: "테마",
    customThemeLabel: "사용자 테마",
    customThemePlaceholder: "테마 입력",
    categoryLabel: "카테고리",
    customCategoryLabel: "사용자 카테고리",
    customCategoryPlaceholder: "카테고리 입력",
    visibilityLabel: "공개 범위",
    visibilityPrivate: "비공개",
    visibilityGroup: "그룹",
    visibilityPublic: "공개",
    delete: "삭제",
    save: "저장",
    emptyHome: "아직 메모가 없습니다",
    emptyTheme: "이 테마에는 아직 메모가 없습니다",
    emptyCategory: "이 카테고리에는 아직 메모가 없습니다",
    emptyNote: "이 메모를 찾을 수 없습니다",
    emptyPublic: "아직 공개 메모가 없습니다",
    emptyRecipe: "아직 공개 레시피가 없습니다",
    emptyFavorites: "아직 즐겨찾기한 레시피가 없습니다",
    emptyGroups: "아직 그룹 메모가 없습니다",
    emptySearch: "일치하는 결과가 없습니다",
    drawerHint: "사이드바 메뉴",
    settingsHint: "설정 및 언어",
    authMenuSettings: "설정",
    authMenuSignOut: "로그아웃",
    authMenuSignIn: "로그인",
    menuNotes: "내 메모",
    menuGroups: "그룹",
    menuPublic: "공개 메모",
    menuPopular: "인기",
    menuFavorites: "즐겨찾기",
    statusSaved: "저장됨",
    statusDeleted: "삭제됨",
    statusSignedIn: "로그인됨",
    statusSignedOut: "로그아웃됨",
    statusLanguageSaved: "언어 설정이 업데이트되었습니다",
    statusLanguageLoaded: "언어가 적용되었습니다",
    statusSignInFailed: "Google 로그인 실패",
    statusSignOutFailed: "로그아웃 실패",
    statusImportFailed: "가져오기 실패",
    statusExported: "CSV가 내보내졌습니다",
    statusNoNotes: "내보낼 메모가 없습니다",
    statusNoPublicData: "공개 데이터가 없습니다",
    statusNoFavorites: "즐겨찾기 데이터가 없습니다",
    statusSavedToFirestore: "설정이 동기화되었습니다",
    routeNotes: "내 메모",
    routeGroups: "그룹",
    routePublic: "공개 메모",
    routePopular: "인기",
    routeFavorites: "즐겨찾기",
    routeTheme: "테마",
    routeCategory: "카테고리",
    routeNote: "메모",
    routeRecipe: "레시피",
  },
};

let currentLanguage = DEFAULT_LANGUAGE;

function normalizeLanguage(language) {
  const value = String(language || "").trim().replace("_", "-");
  if (!value) return "";
  const lower = value.toLowerCase();
  if (lower.startsWith("zh")) return "zh-TW";
  if (lower.startsWith("ja")) return "ja";
  if (lower.startsWith("ko")) return "ko";
  if (lower.startsWith("en")) return "en";
  return SUPPORTED_LANGUAGES.includes(value) ? value : "";
}

function getStoredLanguage() {
  try {
    return normalizeLanguage(localStorage.getItem(STORAGE_KEY));
  } catch {
    return "";
  }
}

function setStoredLanguage(language) {
  try {
    localStorage.setItem(STORAGE_KEY, normalizeLanguage(language) || DEFAULT_LANGUAGE);
  } catch {
    // Ignore storage failures.
  }
}

function getLanguage() {
  return currentLanguage;
}

function setLanguage(language) {
  const next = normalizeLanguage(language) || DEFAULT_LANGUAGE;
  currentLanguage = next;
  document.documentElement.lang = next;
  return next;
}

function getLanguageName(language = currentLanguage) {
  return LANGUAGE_NAMES[normalizeLanguage(language) || DEFAULT_LANGUAGE] || LANGUAGE_NAMES[DEFAULT_LANGUAGE];
}

function t(key, params = {}) {
  const dict = TRANSLATIONS[currentLanguage] || TRANSLATIONS[DEFAULT_LANGUAGE];
  const fallback = TRANSLATIONS[DEFAULT_LANGUAGE];
  let value = dict[key] ?? fallback[key] ?? key;
  for (const [name, replacement] of Object.entries(params)) {
    value = value.replaceAll(`{{${name}}}`, String(replacement));
  }
  return value;
}

function languageFromNavigator() {
  const candidates = [];
  if (typeof navigator !== "undefined") {
    candidates.push(navigator.language, ...(Array.isArray(navigator.languages) ? navigator.languages : []));
  }
  for (const candidate of candidates) {
    const normalized = normalizeLanguage(candidate);
    if (normalized) return normalized;
  }
  return "";
}

function languageFromCountry(countryCode) {
  const code = String(countryCode || "").trim().toUpperCase();
  if (code === "TW" || code === "HK" || code === "MO") return "zh-TW";
  if (code === "JP") return "ja";
  if (code === "KR") return "ko";
  if (code) return "en";
  return "";
}

async function detectLanguageFromIp() {
  try {
    const controller = typeof AbortController !== "undefined" ? new AbortController() : null;
    const timeoutId = controller ? setTimeout(() => controller.abort(), 3500) : null;
    const response = await fetch("https://api.country.is/", {
      signal: controller?.signal,
      cache: "no-store",
    });
    if (timeoutId) clearTimeout(timeoutId);
    if (!response.ok) return "";
    const data = await response.json();
    return languageFromCountry(data?.country);
  } catch {
    return "";
  }
}

function resolveLanguagePreference() {
  const stored = getStoredLanguage();
  if (stored) return { language: stored, source: "storage" };
  const navigatorLanguage = languageFromNavigator();
  if (navigatorLanguage) return { language: navigatorLanguage, source: "navigator" };
  return { language: "", source: "ip" };
}

export {
  DEFAULT_LANGUAGE,
  LANGUAGE_NAMES,
  SUPPORTED_LANGUAGES,
  detectLanguageFromIp,
  getLanguage,
  getLanguageName,
  getStoredLanguage,
  languageFromCountry,
  languageFromNavigator,
  normalizeLanguage,
  resolveLanguagePreference,
  setLanguage,
  setStoredLanguage,
  t,
};
