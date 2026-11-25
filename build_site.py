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


def invite_html(cfg, who):
    """Thiệp mời: đếm ngược, bố mẹ hai bên, lời mời, các lễ."""
    def fam(key, label):
        f = cfg.get(key) or {}
        rows = "".join(f"<p>{t}: {esc(f[k])}</p>" for k, t in (("ong", "Ông"), ("ba", "Bà")) if f.get(k))
        return f'<div class="fam"><h3>{label}</h3>{rows}</div>'

    events = ""
    for ev in cfg.get("su_kien", []):
        d = date.fromisoformat(ev["ngay"])
        place = cfg.get(ev.get("tai", ""), {}) or {}
        where = {"nha_trai": "Tư gia nhà trai", "nha_gai": "Tư gia nhà gái"}.get(ev.get("tai"), ev.get("tai", ""))
        btn = (f'<a class="route" href="{esc(place["link_ban_do"])}" target="_blank" rel="noopener">'
               '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 2a7 7 0 0 0-7 7c0 5.2 7 13 7 13s7-7.8 7-13a7 7 0 0 0-7-7zm0 9.6A2.6 2.6 0 1 1 12 6.4a2.6 2.6 0 0 1 0 5.2z" fill="currentColor"/></svg>'
               'Xem chỉ đường</a>') if place.get("link_ban_do") else ""
        events += f'''<div class="event">
      <h3 class="ev-name">{esc(ev["ten"])}</h3>
      <p class="ev-when">Vào lúc:<br>{esc(ev.get("gio", ""))} - {esc(ev.get("thu", ""))}</p>
      <div class="ev-date"><span>Tháng {d.month}</span><b>{d.day:02d}</b><span>Năm {d.year}</span></div>
      {f'<p class="ev-lunar">( {esc(ev["am_lich"])} )</p>' if ev.get("am_lich") else ""}
      <p class="ev-at">Tại: {esc(where)}</p>
      {f'<p class="ev-addr">{esc(place["dia_chi"])}</p>' if place.get("dia_chi") else ""}
      {btn}
    </div>'''
    target = f"{cfg['ngay_cuoi']}T{cfg.get('gio_cuoi', '00:00')}:00+07:00"
    guest_line = esc(who) if who else "Quý khách"
    return f'''<section class="invite" id="thiep-moi">
    <p class="iv-script">Đếm ngược thời gian cùng chúng mình nha!</p>
    <div class="seg" data-date="{target}">
      <div><b id="d">00</b><span>Ngày</span></div><i>:</i>
      <div><b id="h">00</b><span>Giờ</span></div><i>:</i>
      <div><b id="m">00</b><span>Phút</span></div><i>:</i>
      <div><b id="s">00</b><span>Giây</span></div>
    </div>
    <div class="fams">{fam("nha_gai", "Nhà Gái")}{fam("nha_trai", "Nhà Trai")}</div>
    <p class="iv-invite">Trân trọng kính mời {guest_line}<br>tới dự bữa cơm thân mật mừng lễ thành hôn của hai con chúng tôi</p>
    <p class="iv-couple">{esc(cfg.get("chu_re", ""))}<span>&amp;</span>{esc(cfg.get("co_dau", ""))}</p>
    {events}
    <p class="iv-thanks">Rất hân hạnh được đón tiếp!</p>
  </section>'''


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
    rsvp_url = esc(cfg.get("rsvp_url", ""))
    gate = (f'''<div class="gate" role="dialog" aria-label="Mở thiệp mời">
  <div class="gate-card">
    <p class="eyebrow">Thiệp mời đám cưới</p>
    <p class="gate-to">Gửi</p>
    <p class="gate-name">{esc(who) if who else "Bạn thân mến"}</p>
    <button class="seal" type="button" aria-label="Mở thiệp"><span>♥</span></button>
    <p class="caps gate-hint">Chạm để mở thiệp</p>
    <p class="gate-date">{date_txt}</p>
  </div>
</div>'''
            if cfg.get("nhac_nen") else "")
    music = cfg.get("nhac_nen", "").strip()
    if music and not re.match(r"^https?://", music):
        music = base + music.lstrip("/")
    music_btn = (f'<button class="music" type="button" data-src="{esc(music)}" aria-label="Bật/tắt nhạc nền" aria-pressed="false">'
                 '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 17.5V6.2l10-2.2v11.3" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/>'
                 '<ellipse cx="6.6" cy="17.6" rx="2.6" ry="2.1" fill="currentColor"/><ellipse cx="16.6" cy="15.4" rx="2.6" ry="2.1" fill="currentColor"/></svg>'
                 '<span class="notes" aria-hidden="true"></span></button>') if music else ""
    guest_tag = esc(f"{guest['xung_ho']} {guest['ten']}".strip() if guest else "")
    n_img, n_show = 14, 6
    full_list = ",".join(f"{base}assets/img/g{i:02d}.jpg" for i in range(1, n_img + 1))
    gallery = ""
    for i in range(1, n_show + 1):
        more = (f'<span class="more">+{n_img - n_show}<small>ảnh</small></span>'
                if i == n_show and n_img > n_show else "")
        gallery += (f'<button class="ph" data-i="{i - 1}" aria-label="Xem album, ảnh {i}">'
                    f'<img src="{base}assets/img/t{i:02d}.jpg" alt="Ảnh cưới {i}" loading="lazy">{more}</button>')
    gallery = f'<div class="album" data-list="{full_list}">{gallery}</div>'
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
  {invite_html(cfg, who)}

  <section id="video" class="video">
    <h2 class="script">Our Story</h2>
    <div class="frame">
      <video controls playsinline preload="metadata" poster="{base}assets/img/poster.jpg">
        <source src="{base}assets/video/video-cuoi.mp4" type="video/mp4">
      </video>
    </div>
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
    {gallery}
  </section>

  <section class="thanks">
    <p class="msg">{loi_moi}</p>
    <p class="script big">Thank you</p>
    <p class="caps gold">Hẹn gặp {esc(who) if who else 'bạn'} trong ngày vui · {date_txt}</p>
  </section>
</main>

{gate}
{music_btn}
<div class="petals" aria-hidden="true"></div>
<dialog id="lb" aria-label="Album ảnh cưới">
  <div class="lb-bar"><i></i></div>
  <p class="lb-count"></p>
  <img alt="Ảnh cưới">
  <button class="lb-prev" aria-label="Ảnh trước">‹</button>
  <button class="lb-next" aria-label="Ảnh sau">›</button>
  <button class="x" aria-label="Đóng">×</button>
</dialog>
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
    # video 1080p chất lượng cao dùng chung với file trong repo (không nén lại)
    os.makedirs(os.path.join(out, "assets", "video"), exist_ok=True)
    shutil.copy2(os.path.join(HERE, "video-cuoi-24-12-2026.mp4"), os.path.join(out, "assets", "video", "video-cuoi.mp4"))
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
