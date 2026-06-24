# LiveNote

LiveNote 是一個以 Firebase Authentication + Cloud Firestore 為核心的筆記系統。
目前專案是純 HTML / CSS / Vanilla JavaScript，沒有 React。

## 功能

- Google 登入
- 私有筆記 CRUD
- 主題 / 分類瀏覽
- 公開食譜社群
- 單篇食譜頁
- 星等評分 1~5
- 收藏 / 我的收藏
- 匯入 Excel / CSV
- 匯出 CSV

## 路由

- `/`：我的筆記
- `/theme/:theme`：主題
- `/theme/:theme/category/:category`：分類
- `/note/:id`：單篇私有筆記
- `/public`：公開食譜
- `/recipe/:id`：單篇公開食譜
- `/popular`：熱門排行
- `/favorites`：我的收藏
- `/groups`：我的群組

## Firestore 結構

### 使用者

`users/{uid}`

```json
{
  "displayName": "",
  "email": "",
  "photoURL": "",
  "createdAt": "",
  "lastLoginAt": ""
}
```

### 私有筆記

`users/{uid}/notes/{noteId}`

```json
{
  "title": "",
  "content": "",
  "theme": "",
  "category": "",
  "visibility": "private",
  "createdAt": "",
  "updatedAt": ""
}
```

### 公開食譜

`public_recipes/{recipeId}`

```json
{
  "title": "",
  "content": "",
  "ownerUid": "",
  "ownerName": "",
  "createdAt": "",
  "updatedAt": "",
  "avgRating": 0,
  "ratingCount": 0,
  "category": "",
  "visibility": "public"
}
```

### 評分

`public_recipes/{recipeId}/ratings/{uid}`

```json
{
  "uid": "",
  "rating": 5,
  "createdAt": "",
  "updatedAt": ""
}
```

### 收藏

`public_recipes/{recipeId}/favorites/{uid}`

```json
{
  "uid": "",
  "createdAt": ""
}
```

## 本機測試

用任何靜態伺服器開啟專案根目錄即可。

```powershell
python -m http.server 8080
```

然後開啟：

`http://localhost:8080/`

## Firebase 設定

1. 在 Firebase Console 啟用 Authentication。
2. 開啟 Google 登入。
3. 建立 Firestore Database。
4. 將 `firestore.rules` 部署到專案 `livenote-app`。
5. 使用 Hosting 部署這個前端。

## 匯入 / migration

### 舊 Google Sheet 匯入到 Firestore

這支腳本保留給舊資料搬遷使用：

```powershell
$env:GOOGLE_APPLICATION_CREDENTIALS="C:\path\to\service-account.json"
$env:FIREBASE_PROJECT_ID="livenote-app"
$env:TARGET_UID="your-firebase-auth-uid"
$env:LEGACY_SHEET_URL="https://script.google.com/macros/s/....../exec"
$env:LEGACY_SHEET_PASSCODE="3141"
npm run migrate:legacy
```

### 將已公開的筆記補進 public_recipes

```powershell
$env:GOOGLE_APPLICATION_CREDENTIALS="C:\path\to\service-account.json"
$env:FIREBASE_PROJECT_ID="livenote-app"
npm run migrate:public
```

## 部署

```powershell
npm run deploy:hosting
npm run deploy:rules
```

## 專案檔案

- `app.js`：前端 SPA 與 Firebase 邏輯
- `index.html`：畫面骨架
- `styles.css`：樣式
- `firestore.rules`：安全規則
- `scripts/migrate-legacy-sheet.mjs`：舊 Google Sheet 搬遷
- `scripts/migrate-public-recipes.mjs`：公開食譜回填
- `firebase.json`：Hosting / Firestore 設定
