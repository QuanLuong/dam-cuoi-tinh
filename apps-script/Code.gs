/**
 * Nhận form "Xác nhận tham dự" từ website thiệp mời và ghi vào Google Sheet.
 * Cách cài đặt: xem apps-script/HUONG-DAN.md
 */
var SHEET_ID = '1tWmuoBoZMuw362ov0vgesqSgMP4dcO6eDWKrAaS8Hmo';
var TAB_NAME = 'Xác nhận tham dự';
var HEADERS = ['Thời gian', 'Tên', 'Tham dự', 'Số người', 'Lời nhắn', 'Khách mời (link riêng)', 'Trang'];

function doPost(e) {
  var lock = LockService.getScriptLock();
  lock.waitLock(10000);
  try {
    var ss = SpreadsheetApp.openById(SHEET_ID);
    var sh = ss.getSheetByName(TAB_NAME) || ss.insertSheet(TAB_NAME);
    if (sh.getLastRow() === 0) {
      sh.appendRow(HEADERS);
      sh.getRange(1, 1, 1, HEADERS.length).setFontWeight('bold').setBackground('#f3d3cd');
      sh.setFrozenRows(1);
    }
    var p = (e && e.parameter) || {};
    sh.appendRow([
      new Date(),
      clean(p.ten, 80),
      clean(p.tham_du, 40),
      clean(p.so_nguoi, 40),
      clean(p.loi_nhan, 500),
      clean(p.khach_moi, 120),
      clean(p.trang, 300)
    ]);
    return ContentService.createTextOutput(JSON.stringify({ ok: true }))
      .setMimeType(ContentService.MimeType.JSON);
  } finally {
    lock.releaseLock();
  }
}

function doGet() {
  return ContentService.createTextOutput('RSVP đang hoạt động');
}

// Cắt độ dài và chặn công thức (=, +, -, @) để dữ liệu khách nhập không chạy như công thức trong Sheet
function clean(v, max) {
  v = String(v || '').trim().slice(0, max);
  return /^[=+\-@]/.test(v) ? "'" + v : v;
}
