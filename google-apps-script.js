const SHEET_NAME = "notes";
const PASSCODE = "3141";
// Leave blank when bound to a Google Sheet.
// If this is a standalone Apps Script project, paste the spreadsheet ID here.
const SPREADSHEET_ID = "";
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

function doGet(e) {
  const request = e && e.parameter ? e.parameter : {};
  const callback = String(request.callback || "").replace(/[^\w$.]/g, "");
  const payload = handleRequest({
    action: request.action || "list",
    passcode: request.passcode || "",
  });
  const body = callback ? `${callback}(${JSON.stringify(payload)});` : JSON.stringify(payload);
  return ContentService.createTextOutput(body).setMimeType(
    callback ? ContentService.MimeType.JAVASCRIPT : ContentService.MimeType.JSON,
  );
}

function doPost(e) {
  const data = JSON.parse((e && e.postData && e.postData.contents) || "{}");
  const payload = handleRequest(data);
  return ContentService.createTextOutput(JSON.stringify(payload)).setMimeType(ContentService.MimeType.JSON);
}

function handleRequest(data) {
  try {
    if (PASSCODE && data.passcode !== PASSCODE) {
      throw new Error("Passcode is incorrect.");
    }

    if (data.action === "ping") {
      return { ok: true, mode: "ping", rows: listRows().length };
    }

    if (data.action === "upsert") {
      return upsertRow(data.row || {});
    }

    return { ok: true, rows: listRows() };
  } catch (error) {
    return { ok: false, error: error.message };
  }
}

function getSpreadsheet_() {
  if (SPREADSHEET_ID) {
    return SpreadsheetApp.openById(SPREADSHEET_ID);
  }

  const spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
  if (!spreadsheet) {
    throw new Error("No active spreadsheet found. Either bind this script to the Sheet or set SPREADSHEET_ID.");
  }
  return spreadsheet;
}

function getSheet() {
  const spreadsheet = getSpreadsheet_();
  let sheet = spreadsheet.getSheetByName(SHEET_NAME);
  if (!sheet) sheet = spreadsheet.insertSheet(SHEET_NAME);
  const firstRow = sheet.getRange(1, 1, 1, HEADERS.length).getValues()[0];
  if (firstRow.join("") === "") {
    sheet.getRange(1, 1, 1, HEADERS.length).setValues([HEADERS]);
    sheet.setFrozenRows(1);
  }
  return sheet;
}

function listRows() {
  const sheet = getSheet();
  const values = sheet.getDataRange().getValues();
  if (values.length <= 1) return [];
  const headers = values[0].map(String);
  return values
    .slice(1)
    .filter((row) => row.some((cell) => cell !== ""))
    .map((row) => {
      const record = {};
      headers.forEach((header, index) => {
        if (HEADERS.includes(header)) record[header] = String(row[index] || "");
      });
      return record;
    });
}

function upsertRow(row) {
  const sheet = getSheet();
  const clean = {};
  HEADERS.forEach((header) => {
    clean[header] = String(row[header] || "");
  });
  if (!clean.id) throw new Error("Missing id.");

  const lastRow = Math.max(sheet.getLastRow(), 1);
  const ids =
    lastRow > 1
      ? sheet
          .getRange(2, 1, lastRow - 1, 1)
          .getValues()
          .flat()
          .map(String)
      : [];
  const foundIndex = ids.indexOf(clean.id);
  const targetRow = foundIndex >= 0 ? foundIndex + 2 : lastRow + 1;
  sheet.getRange(targetRow, 1, 1, HEADERS.length).setValues([HEADERS.map((header) => clean[header])]);
  return { ok: true, row: clean };
}
