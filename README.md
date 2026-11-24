# Video cưới — 24.12.2026

**Video:** [video-cuoi-24-12-2026.mp4](video-cuoi-24-12-2026.mp4)

Slideshow 1920×1080, 30fps, dựng từ 26 ảnh cưới (thư mục Google Drive `WEDDING/Vân Anh`) với nhạc nền
"NHẠC CÔ DÂU CHÚ RỂ LÊN SÂN KHẤU" (bài đầu tiên trong file mix). File `TINH-ANH.mp4` không được dùng.

Bố cục video (~2 phút 57 giây), có 8 kiểu chuyển cảnh: đẩy ngang, mở vòng tròn, zoom, lau chéo, chớp sáng, nhòe mờ, trượt lên, vệt nắng:
- **Intro**: "Save the Date — Chúng mình kết hôn — 24 . 12 . 2026 — Thứ Năm"
- **Ảnh**: theo thứ tự chụp, xen kẽ 3 kiểu cảnh: ảnh có khung trên nền mờ, ảnh cận cảnh tràn màn hình
  (lia máy chậm), và cảnh chia đôi có chữ ("Gặp gỡ", "Yêu thương", "Hẹn ước", "Ngày chung đôi").
  Ngày cưới hiển thị ở góc phải dưới suốt video.
- **Outro**: "Thank you — Hẹn gặp bạn trong ngày vui — 24 . 12 . 2026"

## Dựng lại

```bash
pip install pillow   # cần thêm ffmpeg
python3 render_video.py <thư_mục_media> video-cuoi.mp4
python3 render_video.py <thư_mục_media> preview_dir --preview   # chỉ xuất ảnh xem trước
```

`<thư_mục_media>` chứa `WEDDING/...` và `Nhạc Cưới/...` tải từ Drive.
Font (Google Fonts, giấy phép OFL) nằm trong `fonts/`.

## Website thiệp mời (GitHub Pages)

Mỗi khách có một trang riêng ghi tên mình, kèm video, đếm ngược, thông tin tiệc và album ảnh.

- `wedding.json`: tên cô dâu chú rể, giờ, địa chỉ và link bản đồ của nhà trai / nhà gái, link form xác nhận `rsvp_url` (trường nào để trống thì tự ẩn)
- `guests.csv`: danh sách khách, mỗi dòng gồm `xung_ho,ten,duong_dan` (cột `duong_dan` có thể bỏ trống, khi đó link được tạo tự động từ tên, ví dụ "Anh Nam" → `/anh-nam/`)

Sửa hai file trên rồi push, GitHub Actions sẽ tự dựng lại trang. Danh sách link của từng khách nằm ở mục
**Actions → lần chạy mới nhất → Summary**.

Bật lần đầu: **Settings → Pages → Source: GitHub Actions** (repo cần ở chế độ Public nếu dùng tài khoản miễn phí).

## Xác nhận tham dự → Google Sheet

Form trên thiệp (tên, lời nhắn, tham dự / bận / cân nhắc, số người) ghi vào Google Sheet qua Google Apps Script.
Hướng dẫn cài đặt nằm ở [`apps-script/HUONG-DAN.md`](apps-script/HUONG-DAN.md).
