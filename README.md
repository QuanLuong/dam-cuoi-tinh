# Video cưới — 24.12.2026

**Video:** [video-cuoi-24-12-2026.mp4](video-cuoi-24-12-2026.mp4)

Slideshow 1920×1080, 30fps, dựng từ 26 ảnh cưới (thư mục Google Drive `WEDDING/Vân Anh`) với nhạc nền
"NHẠC CÔ DÂU CHÚ RỂ LÊN SÂN KHẤU" (bài đầu tiên trong file mix). File `TINH-ANH.mp4` không được dùng.

Bố cục video (~2 phút 10 giây):
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
