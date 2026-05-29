# Google Sheets 連線設定

## 1. 建立 Google Sheet

建立一個新的 Google 試算表，第一張工作表命名為 `notes`，第一列貼上欄位：

```text
id	status	theme	theme_icon	theme_color	category	title	summary	content	tags	updated_at
```

也可以先把網站下載的 `data.xlsx` 匯入 Google Sheets。

## 2. 建立 Apps Script

在 Google Sheet 裡選：

`擴充功能` -> `Apps Script`

把本專案的 `google-apps-script.js` 內容貼進去。

把這行改成你自己的寫入密碼：

```js
const PASSCODE = "change-this-passcode";
```

## 3. 部署 Web App

選：

`部署` -> `新增部署作業` -> 類型選 `網頁應用程式`

設定：

- 執行身分：`我`
- 誰可以存取：`任何人`

部署後複製 Web App URL，格式會像：

```text
https://script.google.com/macros/s/....../exec
```

## 4. 回到手機網頁設定

開網站右上角資料維護，貼上：

- Apps Script Web App URL
- 寫入密碼

按 `儲存設定`，再按 `同步資料`。

之後手機新增、編輯、封存都會送到 Google Sheets。若 Apps Script 重新部署，請貼新的 Web App URL。
