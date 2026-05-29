# Google Sheets 連線設定

這個版本已經把前端固定連到你提供的 Web App URL，密碼也固定為 `3141`。

## 1. Google Sheet

建立一個新的 Google 試算表，第一張工作表命名為 `notes`，第一列欄位如下：

```text
id	status	theme	theme_icon	theme_color	category	title	summary	content	tags	updated_at
```

也可以先把網站下載的 `data.xlsx` 匯入 Google Sheets。

## 2. Apps Script

在 Google Sheet 裡選：

`擴充功能` -> `Apps Script`

把本專案的 [google-apps-script.js](./google-apps-script.js) 內容貼進去。

如果你是從 Google Sheet 裡面開這個 Apps Script，通常 `SPREADSHEET_ID` 可以留空。

如果你是自己新建獨立專案，就把這行填成你的試算表 ID：

```js
const SPREADSHEET_ID = "your-spreadsheet-id";
```

## 3. 部署 Web App

選：

`部署` -> `新增部署作業` -> 類型選 `網頁應用程式`

設定：

- 執行身分：`我`
- 誰可以存取：`任何人`

部署後確認 URL 使用 `/exec`，不是 `/dev`。

## 4. 回到網站

現在網站右上角已經固定：

- Apps Script Web App URL
- 寫入密碼 `3141`

你只需要按 `同步資料`。

## 5. 如果還是讀不到

- 確認 Apps Script 已重新部署
- 確認是 `/exec`
- 確認 `SPREADSHEET_ID` 沒有留空
- 確認 Apps Script 與試算表有對到同一份資料
