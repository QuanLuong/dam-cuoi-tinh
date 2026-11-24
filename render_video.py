#!/usr/bin/env python3
"""Dựng video cưới từ ảnh + nhạc.

Cách dùng:
    python3 render_video.py <thư_mục_media> <file_ra.mp4> [--preview]

<thư_mục_media> chứa các thư mục con "WEDDING/..." (ảnh .jpg) và "Nhạc Cưới/..." (mp3).
"""
import os
import sys
import glob
import math
import subprocess
from functools import lru_cache
from multiprocessing import Pool

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps, ImageEnhance

W, H = 1920, 1080
FPS = 30
TRANS = 1.2           # thời lượng chuyển cảnh (giây)
SS = 1.25             # hệ số siêu mẫu cho ảnh nguồn
HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(HERE, "fonts")

WEDDING_DATE = "24 . 12 . 2026"
WEDDING_DAY = "THỨ NĂM"

MUSIC_FILE = "Nhạc Cưới/NHẠC CÔ DÂU CHÚ RỂ LÊN SÂN KHẤU.mp3"
MUSIC_START = 1.15    # bỏ đoạn im lặng đầu bài

IVORY = (250, 244, 234)
GOLD = (222, 196, 150)


def font(name, size):
    return ImageFont.truetype(os.path.join(FONT_DIR, name), size)


def spaced(draw, xy, text, fnt, fill, spacing, anchor="m"):
    """Vẽ chữ giãn cách ký tự, căn giữa theo x."""
    widths = [draw.textlength(c, font=fnt) for c in text]
    total = sum(widths) + spacing * (len(text) - 1)
    x, y = xy
    if anchor == "m":
        x -= total / 2
    elif anchor == "r":
        x -= total
    for c, w in zip(text, widths):
        draw.text((x, y), c, font=fnt, fill=fill, anchor="lm")
        x += w + spacing
    return total


# ---------------------------------------------------------------- tài nguyên

MEDIA = None


def load_photo(path):
    im = Image.open(os.path.join(MEDIA, path))
    im = ImageOps.exif_transpose(im).convert("RGB")
    return im


def blurred_bg(im, w, h, bright=0.5):
    bg = ImageOps.fit(im, (w // 4, h // 4), Image.LANCZOS)
    bg = bg.filter(ImageFilter.GaussianBlur(10))
    bg = ImageEnhance.Brightness(bg).enhance(bright)
    bg = ImageEnhance.Color(bg).enhance(0.8)
    return bg.resize((w, h), Image.BICUBIC)


def framed(im, height, border):
    """Ảnh có viền trắng mảnh + bóng đổ, trả về RGBA."""
    w = round(im.width * height / im.height)
    ph = im.resize((w, height), Image.LANCZOS)
    card = Image.new("RGB", (w + 2 * border, height + 2 * border), (252, 250, 246))
    card.paste(ph, (border, border))
    pad = 60
    sh = Image.new("L", (card.width + 2 * pad, card.height + 2 * pad), 0)
    ImageDraw.Draw(sh).rectangle([pad, pad + 14, pad + card.width, pad + card.height + 14], fill=150)
    sh = sh.filter(ImageFilter.GaussianBlur(24))
    out = Image.new("RGBA", sh.size, (0, 0, 0, 0))
    out.paste((0, 0, 0, 255), (0, 0), sh)
    out.paste(card, (pad, pad))
    return out, pad


def vignette(w, h, strength=170):
    m = Image.new("L", (w // 8, h // 8), 0)
    d = ImageDraw.Draw(m)
    mw, mh = m.size
    for i in range(40):
        f = i / 40
        a = int(strength * (1 - f) ** 2.2)
        d.ellipse([-mw * 0.35 + f * mw * 0.35, -mh * 0.45 + f * mh * 0.45,
                   mw * 1.35 - f * mw * 0.35, mh * 1.45 - f * mh * 0.45], outline=a, width=3)
    m = m.filter(ImageFilter.GaussianBlur(6)).resize((w, h), Image.BICUBIC)
    v = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    v.putalpha(m)
    return v


# --------------------------------------------------------------- lớp chữ

def date_badge():
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    f = font("CormorantGaramond-SemiBold.ttf", 34)
    x, y = W - 70, H - 62
    tw = spaced(d, (x, y), WEDDING_DATE, f, IVORY + (235,), 3, anchor="r")
    d.line([x - tw - 70, y + 2, x - tw - 18, y + 2], fill=GOLD + (220,), width=2)
    # quầng tối mềm phía sau để chữ đọc được trên ảnh sáng
    glow = Image.new("L", (W, H), 0)
    ImageDraw.Draw(glow).ellipse([x - tw - 140, y - 70, x + 90, y + 70], fill=120)
    glow = glow.filter(ImageFilter.GaussianBlur(40))
    shade = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    shade.putalpha(glow)
    return Image.alpha_composite(shade, lay)


def text_panel(lines, x_center, y_center):
    """lines: list of (kind, text). Trả về RGBA kích thước khung hình."""
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    styles = {
        "script": (font("GreatVibes-Regular.ttf", 120), IVORY, 0, 130),
        "script_s": (font("GreatVibes-Regular.ttf", 92), IVORY, 0, 105),
        "caps": (font("Montserrat-Light.ttf", 30), IVORY, 9, 62),
        "caps_s": (font("Montserrat-Medium.ttf", 24), GOLD, 7, 52),
        "date": (font("CormorantGaramond-SemiBold.ttf", 96), GOLD, 6, 120),
        "italic": (font("CormorantGaramond-Italic.ttf", 46), IVORY, 0, 62),
        "rule": (None, GOLD, 0, 46),
        "gap": (None, None, 0, 26),
    }
    total = sum(styles[k][3] for k, _ in lines)
    y = y_center - total / 2
    for kind, text in lines:
        fnt, col, sp, lh = styles[kind]
        cy = y + lh / 2
        if kind == "rule":
            d.line([x_center - 90, cy, x_center - 14, cy], fill=col + (230,), width=2)
            d.line([x_center + 14, cy, x_center + 90, cy], fill=col + (230,), width=2)
            d.regular_polygon((x_center, cy, 6), 4, fill=col + (240,))
        elif kind != "gap":
            if sp:
                spaced(d, (x_center, cy), text, fnt, col + (255,), sp)
            else:
                d.text((x_center, cy), text, font=fnt, fill=col + (255,), anchor="mm")
        y += lh
    # bóng chữ nhẹ để dễ đọc
    a = lay.getchannel("A").filter(ImageFilter.GaussianBlur(8))
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    shadow.putalpha(a.point(lambda v: int(v * 0.55)))
    return Image.alpha_composite(shadow, lay)


# --------------------------------------------------------------- kịch bản

def ease(t):
    t = min(max(t, 0.0), 1.0)
    return t * t * (3 - 2 * t)


class Slide:
    def __init__(self, kind, photo, dur, **kw):
        self.kind, self.photo, self.dur, self.kw = kind, photo, dur, kw


def build_script(photos):
    by = {os.path.basename(p): p for p in photos}
    cover = by.pop("@.jpg")
    order = sorted(by)  # theo số thứ tự chụp BTT_xxxx

    full = {"BTT_2663.jpg": 0.12, "BTT_2933.jpg": 0.15, "BTT_3093.jpg": 0.20,
            "BTT_3183.jpg": 0.10, "BTT_3457.jpg": 0.16}
    split = {
        "BTT_2832.jpg": ("right", [("caps_s", "CHƯƠNG MỘT"), ("script", "Gặp gỡ"), ("rule", ""),
                                   ("italic", "Một ánh nhìn, một nụ cười"),
                                   ("italic", "và thế là đủ cho cả một đời.")]),
        "BTT_3068.jpg": ("left", [("caps_s", "CHƯƠNG HAI"), ("script", "Yêu thương"), ("rule", ""),
                                  ("italic", "Cùng nhau đi qua"),
                                  ("italic", "những ngày nắng, những ngày mưa.")]),
        "BTT_3253.jpg": ("right", [("caps_s", "CHƯƠNG BA"), ("script", "Hẹn ước"), ("rule", ""),
                                   ("italic", "Nắm tay nhau,"),
                                   ("italic", "về chung một nhà.")]),
        "BTT_3439.jpg": ("left", [("caps_s", "NGÀY CHUNG ĐÔI"), ("script_s", "Save the Date"),
                                  ("rule", ""), ("gap", ""), ("date", WEDDING_DATE),
                                  ("caps", WEDDING_DAY)]),
    }
    slides = [Slide("intro", cover, 9.0)]
    flip = False
    for name in order:
        p = by[name]
        if name in full:
            slides.append(Slide("full", p, 5.6, y=full[name]))
        elif name in split:
            side, lines = split[name]
            slides.append(Slide("split", p, 6.8, side=side, lines=lines))
        else:
            flip = not flip
            slides.append(Slide("center", p, 5.4, drift=1 if flip else -1))
    slides.append(Slide("outro", by["BTT_3457.jpg"], 10.0))
    t = 0.0
    for s in slides:
        s.start = t
        t += s.dur - TRANS
    total = t + TRANS
    return slides, total


# ---------------------------------------------------------- dựng khung hình

@lru_cache(maxsize=3)
def prepare(idx):
    s = SLIDES[idx]
    im = load_photo(s.photo)
    sw, sh = int(W * SS), int(H * SS)
    overlays = []
    if s.kind in ("center", "split", "intro", "outro"):
        bright = 0.32 if s.kind in ("intro", "outro") else 0.5
        src = blurred_bg(im, sw, sh, bright).convert("RGBA")
        if s.kind in ("center", "split", "intro"):
            fh = int(sh * 0.86)
            card, pad = framed(im, fh, int(14 * SS))
            if s.kind == "center":
                cx = sw // 2
            else:
                side = s.kw.get("side", "right") if s.kind == "split" else "right"
                cx = int(sw * (0.30 if side == "left" else 0.70))
            src.alpha_composite(card, (cx - card.width // 2, (sh - card.height) // 2))
        src = src.convert("RGB")
        if s.kind == "center":
            overlays.append((date_badge(), 0.8, s.dur - 0.4))
        elif s.kind == "split":
            tx = int(W * (0.70 if s.kw["side"] == "left" else 0.30))
            overlays.append((text_panel(s.kw["lines"], tx, H // 2), 1.0, s.dur))
        elif s.kind == "intro":
            overlays.append((text_panel([("caps_s", "TRÂN TRỌNG BÁO TIN"), ("script", "Save the Date"),
                                         ("rule", ""), ("caps", "CHÚNG MÌNH KẾT HÔN")],
                                        int(W * 0.30), int(H * 0.40)), 1.2, s.dur))
            overlays.append((text_panel([("date", WEDDING_DATE), ("caps", WEDDING_DAY)],
                                        int(W * 0.30), int(H * 0.72)), 3.0, s.dur))
        else:  # outro
            overlays.append((text_panel([("script", "Thank you"), ("rule", ""), ("gap", ""),
                                         ("italic", "Sự hiện diện của bạn là niềm vinh hạnh"),
                                         ("italic", "cho gia đình chúng mình."), ("gap", ""),
                                         ("caps_s", "HẸN GẶP BẠN TRONG NGÀY VUI"), ("gap", ""),
                                         ("date", WEDDING_DATE), ("caps", WEDDING_DAY)],
                                        W // 2, H // 2), 1.0, s.dur))
    else:  # full: phủ kín khung hình, lia dọc
        src_w = sw
        src = im.resize((src_w, round(im.height * src_w / im.width)), Image.LANCZOS)
        overlays.append((date_badge(), 0.8, s.dur - 0.4))
    return src, overlays, vignette(W, H, 120 if s.kind == "full" else 90)


def camera(s, src, u):
    """Trả về (scale, x0, y0): khung xuất ánh xạ vào vùng nguồn."""
    e = ease(u)
    if s.kind == "full":
        scale = src.width / W * (1.0 - 0.05 * e)
        vh = H * scale
        y_c = src.height * (s.kw["y"] + 0.05 * e) + vh / 2
        y_c = min(max(y_c, vh / 2), src.height - vh / 2)
        x0 = (src.width - W * scale) / 2
        return scale, x0, y_c - vh / 2
    if s.kind in ("intro", "outro"):
        z = 1.0 + 0.06 * e
    elif s.kind == "split":
        z = 1.0 + 0.035 * e
    else:
        z = 1.0 + 0.07 * e
    scale = SS / z
    drift = s.kw.get("drift", 0) * 18 * SS * (e - 0.5)
    x0 = (src.width - W * scale) / 2 + drift
    y0 = (src.height - H * scale) / 2
    return scale, x0, y0


def fade_layer(layer, a):
    if a >= 0.999:
        return layer
    out = layer.copy()
    out.putalpha(layer.getchannel("A").point(lambda v: int(v * a)))
    return out


def slide_frame(idx, t_local):
    s = SLIDES[idx]
    src, overlays, vig = prepare(idx)
    scale, x0, y0 = camera(s, src, t_local / s.dur)
    fr = src.transform((W, H), Image.AFFINE, (scale, 0, x0, 0, scale, y0), Image.BICUBIC)
    fr = fr.convert("RGBA")
    fr.alpha_composite(vig)
    for layer, t_in, t_out in overlays:
        a = min(ease((t_local - t_in) / 1.2), ease((t_out - t_local) / 0.8))
        if a > 0.003:
            fr.alpha_composite(fade_layer(layer, a))
    return fr.convert("RGB")


def render(i):
    t = i / FPS
    act = [k for k, s in enumerate(SLIDES) if s.start <= t < s.start + s.dur]
    if not act:
        return Image.new("RGB", (W, H)).tobytes()
    k = act[-1]
    fr = slide_frame(k, t - SLIDES[k].start)
    if len(act) > 1:
        j = act[0]
        prev = slide_frame(j, t - SLIDES[j].start)
        fr = Image.blend(prev, fr, ease((t - SLIDES[k].start) / TRANS))
    # mở đầu từ đen, kết thúc về đen
    a = min(1.0, t / 1.5, (TOTAL - t) / 2.5)
    if a < 1:
        fr = Image.blend(Image.new("RGB", (W, H)), fr, max(a, 0))
    return fr.tobytes()


def init(media, slides, total):
    global MEDIA, SLIDES, TOTAL
    MEDIA, SLIDES, TOTAL = media, slides, total


def main():
    media, out = sys.argv[1], sys.argv[2]
    preview = "--preview" in sys.argv
    photos = sorted(os.path.relpath(p, media)
                    for p in glob.glob(os.path.join(media, "WEDDING", "**", "*.jpg"), recursive=True))
    slides, total = build_script(photos)
    init(media, slides, total)
    print(f"{len(photos)} ảnh, {len(slides)} cảnh, thời lượng {total:.1f}s")

    if preview:
        os.makedirs(out, exist_ok=True)
        for k, s in enumerate(slides):
            for name, tt in (("a", s.start + TRANS + 0.5), ("b", s.start + s.dur - TRANS - 0.1)):
                fr = Image.frombytes("RGB", (W, H), render(int(tt * FPS)))
                fr.resize((W // 2, H // 2), Image.LANCZOS).save(f"{out}/{k:02d}{name}.jpg", quality=85)
        return

    n = int(total * FPS)
    music = os.path.join(media, MUSIC_FILE)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-stats",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-ss", str(MUSIC_START), "-t", f"{total:.3f}", "-i", music,
           "-filter_complex", f"[1:a]afade=t=in:d=1.0,afade=t=out:st={total - 5:.3f}:d=5[a]",
           "-map", "0:v", "-map", "[a]",
           "-c:v", "libx264", "-preset", "slow", "-crf", "19", "-tune", "film",
           "-pix_fmt", "yuv420p", "-profile:v", "high", "-c:a", "aac", "-b:a", "192k",
           "-movflags", "+faststart", "-shortest", out]
    ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    with Pool(os.cpu_count(), initializer=init, initargs=(media, slides, total)) as pool:
        for b in pool.imap(render, range(n), chunksize=FPS):
            ff.stdin.write(b)
    ff.stdin.close()
    sys.exit(ff.wait())


if __name__ == "__main__":
    main()
