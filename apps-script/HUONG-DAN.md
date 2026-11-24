# Kết nối form "Xác nhận tham dự" với Google Sheet (làm 1 lần, ~3 phút)

1. Mở Google Sheet: https://docs.google.com/spreadsheets/d/1tWmuoBoZMuw362ov0vgesqSgMP4dcO6eDWKrAaS8Hmo/edit
2. Menu **Tiện ích mở rộng (Extensions) → Apps Script**.
3. Xoá hết code mẫu, dán toàn bộ nội dung file `apps-script/Code.gs`, bấm **Lưu** (biểu tượng đĩa mềm).
4. Bấm **Triển khai (Deploy) → Triển khai mới (New deployment)**:
   - Bấm bánh răng ⚙ → chọn **Ứng dụng web (Web app)**
   - *Thực thi dưới dạng (Execute as)*: **Tôi (Me)**
   - *Người có quyền truy cập (Who has access)*: **Bất kỳ ai (Anyone)**
   - Bấm **Triển khai**, cấp quyền khi được hỏi (chọn tài khoản → Nâng cao → Đi tới… → Cho phép).
5. Copy **URL ứng dụng web** (dạng `https://script.google.com/macros/s/.../exec`).
6. Dán URL vào `wedding.json` ở mục `"rsvp_url"` rồi push (hoặc gửi URL cho Claude để điền giúp).

Mỗi lượt khách bấm "Gửi lời nhắn và xác nhận" sẽ thêm 1 dòng vào tab **Xác nhận tham dự** trong Sheet:
Thời gian · Tên · Tham dự · Số người · Lời nhắn · Khách mời (link riêng) · Trang.
