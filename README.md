# LiveNote

LiveNote 是一個單頁筆記系統，前端使用 HTML、CSS 與 Vanilla JavaScript，資料層改為 Firebase Authentication + Cloud Firestore，並部署在 Firebase Hosting。

## 現在的資料流程

Google Login
→ Firebase Authentication
→ Cloud Firestore

每位使用者的資料都存放在自己的路徑下：

- `users/{uid}`
- `users/{uid}/notes/{noteId}`

## Firestore 資料結構

### 使用者資料

```json
{
  "displayName": "",
  "email": "",
  "photoURL": "",
  "createdAt": "",
  "lastLoginAt": ""
}
```

### 筆記資料

```json
{
  "title": "",
  "content": "",
  "theme": "",
  "category": "",
  "createdAt": "",
  "updatedAt": ""
}
```

## 本機開發

直接用本機伺服器開啟專案根目錄即可：

```powershell
python -m http.server 8080
```

然後開啟：

`http://localhost:8080/index.html`

## Firebase 設定步驟

1. 在 Firebase Console 啟用 Authentication。
2. 在 Sign-in method 中啟用 Google。
3. 建立 Firestore Database。
4. 套用 `firestore.rules`。
5. 建立 Web App，並使用以下設定初始化前端：

```json
{
  "apiKey": "AIzaSyBhcTOJQGsa4uAY2Y3IuI1rFpz_39wDTuY",
  "authDomain": "livenote-app.firebaseapp.com",
  "projectId": "livenote-app",
  "storageBucket": "livenote-app.firebasestorage.app",
  "messagingSenderId": "325304749270",
  "appId": "1:325304749270:web:efd78aa9a0cb8dbd1dcd77"
}
```

## 資料遷移

先準備 Firebase Admin 憑證，例如把 service account JSON 存成檔案並設定：

```powershell
$env:GOOGLE_APPLICATION_CREDENTIALS="C:\path\to\service-account.json"
$env:FIREBASE_PROJECT_ID="livenote-app"
$env:TARGET_UID="your-firebase-auth-uid"
$env:LEGACY_SHEET_URL="https://script.google.com/macros/s/....../exec"
$env:LEGACY_SHEET_PASSCODE="3141"
npm run migrate:legacy
```

如果你想同步建立使用者文件，可以另外帶：

```powershell
$env:TARGET_DISPLAY_NAME="Jack"
$env:TARGET_EMAIL="jack@example.com"
$env:TARGET_PHOTO_URL="https://..."
```

遷移完成後，前端就只會讀 Firestore，不再依賴 Google Sheet。

## 匯出功能

在右側工具面板可以：

- 匯出 `livenote.csv`
- 匯出成新的 Google Sheet
- 匯入 Excel / CSV

Google Sheet 匯出會在登入 Google 後，使用額外授權建立新試算表並寫入目前使用者的筆記。

## 部署

部署 Hosting：

```powershell
npm run deploy:hosting
```

部署 Firestore rules：

```powershell
npm run deploy:rules
```

## 專案檔案

- `app.js`：Firebase Auth + Firestore 前端
- `firestore.rules`：Firestore 安全規則
- `scripts/migrate-legacy-sheet.mjs`：舊 Google Sheet 匯入腳本
- `firebase.json`：Hosting / Firestore 設定
