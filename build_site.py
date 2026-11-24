#!/usr/bin/env python3
"""Dựng website thiệp mời: 1 trang chung + 1 trang riêng cho mỗi khách trong guests.csv.

    python3 build_site.py [thư_mục_ra]      (mặc định: _site)

Biến môi trường SITE_URL (vd https://quanluong.github.io/dam-cuoi-tinh) dùng cho ảnh xem trước
khi gửi link qua Zalo/Messenger; GitHub Actions tự đặt biến này.
"""
import csv
import html
import json
import os
import re
import shutil
import sys
import unicodedata
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))


def slugify(text):
    text = text.replace("đ", "d").replace("Đ", "D")
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def esc(s):
    return html.escape(s or "", quote=True)


def load():
    with open(os.path.join(HERE, "wedding.json"), encoding="utf-8") as f:
        cfg = json.load(f)
    guests, seen = [], set()
    with open(os.path.join(HERE, "guests.csv"), encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            ten = (row.get("ten") or "").strip()
            if not ten:
                continue
            xung_ho = (row.get("xung_ho") or "").strip()
            slug = slugify((row.get("duong_dan") or "").strip() or f"{xung_ho} {ten}")
            base, n = slug, 2
            while slug in seen or slug == "assets":
                slug, n = f"{base}-{n}", n + 1
            seen.add(slug)
            guests.append({"xung_ho": xung_ho, "ten": ten, "slug": slug})
    return cfg, guests


def info_rows(cfg):
    d = date.fromisoformat(cfg["ngay_cuoi"])
    rows = [("Ngày", f"{cfg.get('thu', '')}, {d.day:02d} . {d.month:02d} . {d.year}".strip(", "))]
    if cfg.get("ngay_am_lich"):
        rows.append(("Âm lịch", cfg["ngay_am_lich"]))
    if cfg.get("gio_don_khach"):
        rows.append(("Đón khách", cfg["gio_don_khach"]))
    if cfg.get("gio_khai_tiec"):
        rows.append(("Khai tiệc", cfg["gio_khai_tiec"]))
    if cfg.get("lien_he"):
        rows.append(("Liên hệ", cfg["lien_he"]))
    return rows


def page(cfg, guest, base, site_url):
    d = date.fromisoformat(cfg["ngay_cuoi"])
    date_txt = f"{d.day:02d} . {d.month:02d} . {d.year}"
    couple = " & ".join(x for x in (cfg.get("chu_re"), cfg.get("co_dau")) if x)
    if guest:
        who = f"{guest['xung_ho']} {guest['ten']}".strip()
        title = f"Thiệp mời đám cưới — Gửi {who}"
        greet = f'<p class="eyebrow">Trân trọng kính mời</p><h1 class="guest">{esc(who)}</h1>'
        url = f"{site_url}/{guest['slug']}/" if site_url else ""
    else:
        who = ""
        title = "Thiệp mời đám cưới — Save the Date"
        greet = '<p class="eyebrow">Trân trọng kính mời</p><h1 class="guest">Bạn thân mến</h1>'
        url = f"{site_url}/" if site_url else ""
    couple_html = f'<p class="couple">{esc(couple)}</p>' if couple else ""
    desc = f"Tới dự lễ thành hôn{(' của ' + couple) if couple else ' của chúng mình'} — {date_txt}"
    rows = "".join(f"<div class=\"row\"><dt>{esc(k)}</dt><dd>{esc(v)}</dd></div>" for k, v in info_rows(cfg))
    places = ""
    for key, label in (("nha_trai", "Nhà Trai"), ("nha_gai", "Nhà Gái")):
        pl = cfg.get(key) or {}
        if not any(pl.values()):
            continue
        body = ""
        if pl.get("gio"):
            body += f'<p class="pl-time">{esc(pl["gio"])}</p>'
        if pl.get("dia_chi"):
            body += f'<p class="pl-addr">{esc(pl["dia_chi"])}</p>'
        if pl.get("link_ban_do"):
            body += (f'<a class="btn" href="{esc(pl["link_ban_do"])}" target="_blank" rel="noopener">'
                     f'Chỉ đường</a>')
        places += f'<div class="card place"><p class="caps gold">Tư gia</p><h3 class="script pl-name">{label}</h3>{body}</div>'
    rsvp_url = esc(cfg.get("rsvp_url", ""))
    music = cfg.get("nhac_nen", "").strip()
    if music and not re.match(r"^https?://", music):
        music = base + music.lstrip("/")
    music_btn = (f'<button class="music" type="button" data-src="{esc(music)}" aria-label="Bật/tắt nhạc nền" aria-pressed="false">'
                 '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 17.5V6.2l10-2.2v11.3" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/>'
                 '<ellipse cx="6.6" cy="17.6" rx="2.6" ry="2.1" fill="currentColor"/><ellipse cx="16.6" cy="15.4" rx="2.6" ry="2.1" fill="currentColor"/></svg>'
                 '<span class="notes" aria-hidden="true"></span></button>') if music else ""
    guest_tag = esc(f"{guest['xung_ho']} {guest['ten']}".strip() if guest else "")
    gallery = "".join(
        f'<button class="ph" data-full="{base}assets/img/g{i:02d}.jpg" aria-label="Xem ảnh {i}">'
        f'<img src="{base}assets/img/g{i:02d}.jpg" alt="Ảnh cưới {i}" loading="lazy"></button>'
        for i in range(1, 15))
    og_img = f"{site_url}/assets/img/og.jpg" if site_url else f"{base}assets/img/og.jpg"
    robots = '<meta name="robots" content="noindex">' if guest else ""
    loi_moi = esc(cfg.get("loi_moi", ""))
    iso = cfg["ngay_cuoi"]

    return f"""<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
{robots}
<meta property="og:type" content="website">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:image" content="{esc(og_img)}">
{f'<meta property="og:url" content="{esc(url)}">' if url else ''}
<meta name="theme-color" content="#1d1a17">
<link rel="stylesheet" href="{base}assets/style.css">
</head>
<body>
<header class="hero">
  <div class="hero-in">
    {greet}
    <p class="lead">tới dự lễ thành hôn của chúng mình</p>
    {couple_html}
    <div class="rule"><span></span></div>
    <p class="date">{date_txt}</p>
    <p class="caps">{esc(cfg.get('thu', ''))}</p>
  </div>
  <a class="scroll" href="#video" aria-label="Xem tiếp">⌄</a>
</header>

<main>
  <section class="count" aria-label="Đếm ngược">
    <p class="caps gold">Còn lại</p>
    <div class="cd" data-date="{iso}T00:00:00+07:00">
      <div><b id="d">–</b><span>ngày</span></div>
      <div><b id="h">–</b><span>giờ</span></div>
      <div><b id="m">–</b><span>phút</span></div>
      <div><b id="s">–</b><span>giây</span></div>
    </div>
  </section>

  <section id="video" class="video">
    <h2 class="script">Our Story</h2>
    <div class="frame">
      <video controls playsinline preload="metadata" poster="{base}assets/img/poster.jpg">
        <source src="{base}assets/video/video-cuoi-720p.mp4" type="video/mp4">
      </video>
    </div>
  </section>

  <section class="info">
    <h2 class="script">Save the Date</h2>
    <div class="card">
      <dl>{rows}</dl>
    </div>
    <div class="places">{places}</div>
  </section>

  <section id="rsvp" class="rsvp">
    <h2 class="script">Xác nhận tham dự</h2>
    <form class="rsvp-card" data-url="{rsvp_url}" data-guest="{guest_tag}" novalidate>
      <p class="rsvp-intro">Hãy xác nhận sự có mặt của bạn để chúng mình chuẩn bị đón tiếp một cách chu đáo nhất.<br>Trân trọng!</p>
      <input class="pill" name="ten" placeholder="Tên của bạn" value="{esc(who)}" required maxlength="80" autocomplete="name">
      <textarea class="pill" name="loi_nhan" placeholder="Lời nhắn của bạn đến cô dâu, chú rể" rows="2" maxlength="500"></textarea>
      <fieldset class="pill choices">
        <legend class="sr">Bạn có tham dự không?</legend>
        <label><input type="radio" name="tham_du" value="Sẽ tham dự" required> Mình sẽ tham dự</label>
        <label><input type="radio" name="tham_du" value="Bận mất rồi"> Thật tiếc mình bận mất rồi</label>
        <label><input type="radio" name="tham_du" value="Đang cân nhắc"> Mình đang cân nhắc</label>
      </fieldset>
      <select class="pill" name="so_nguoi" aria-label="Số người tham dự">
        <option value="" selected disabled>Bạn sẽ tham dự cùng mấy người?</option>
        <option>1 người (chỉ mình mình)</option>
        <option>2 người</option>
        <option>3 người</option>
        <option>4 người</option>
        <option>5 người trở lên</option>
      </select>
      <button class="send" type="submit">Gửi lời nhắn và xác nhận</button>
      <p class="rsvp-msg" role="status" aria-live="polite"></p>
    </form>
  </section>

  <section class="gallery">
    <h2 class="script">Khoảnh khắc</h2>
    <div class="grid">{gallery}</div>
  </section>

  <section class="thanks">
    <p class="msg">{loi_moi}</p>
    <p class="script big">Thank you</p>
    <p class="caps gold">Hẹn gặp {esc(who) if who else 'bạn'} trong ngày vui · {date_txt}</p>
  </section>
</main>

{music_btn}
<div class="petals" aria-hidden="true"></div>
<dialog id="lb"><img alt=""><button class="x" aria-label="Đóng">×</button></dialog>
<script src="{base}assets/app.js"></script>
</body>
</html>
"""


def main():
    out = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "_site"))
    site_url = os.environ.get("SITE_URL", "").rstrip("/")
    cfg, guests = load()
    if os.path.isdir(out):
        shutil.rmtree(out)
    shutil.copytree(os.path.join(HERE, "site"), out)
    with open(os.path.join(out, "index.html"), "w", encoding="utf-8") as f:
        f.write(page(cfg, None, "", site_url))
    links = []
    for g in guests:
        os.makedirs(os.path.join(out, g["slug"]))
        with open(os.path.join(out, g["slug"], "index.html"), "w", encoding="utf-8") as f:
            f.write(page(cfg, g, "../", site_url))
        links.append((f"{g['xung_ho']} {g['ten']}".strip(), f"{site_url}/{g['slug']}/"))
    open(os.path.join(out, ".nojekyll"), "w").close()

    print(f"Đã tạo trang chung + {len(guests)} trang khách tại {out}")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    lines = ["## Link thiệp mời", "", f"Trang chung: {site_url}/", "", "| Khách | Link |", "|---|---|"]
    lines += [f"| {n} | {u} |" for n, u in links]
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    else:
        print("\n".join(lines))


if __name__ == "__main__":
    main()
