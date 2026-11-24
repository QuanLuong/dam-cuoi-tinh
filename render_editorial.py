#!/usr/bin/env python3
"""Video cưới phong cách tạp chí (nền trắng, bố cục nhiều ảnh, chữ lớn, câu nói viết tay).

    python3 render_editorial.py <thư_mục_media> <file_ra.mp4> [--preview]
"""
import os
import sys
import glob
import math
import subprocess
from functools import lru_cache
from multiprocessing import Pool

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

import render_video as rv   # dùng lại hiệu ứng chuyển cảnh

W, H, FPS = 1920, 1080, 30
TR = 0.9                         # thời lượng chuyển cảnh giữa 2 cảnh
BG = (250, 248, 244)
INK = (46, 41, 38)
SOFT = (120, 108, 100)
HERE = os.path.dirname(os.path.abspath(__file__))
MEDIA = None

MUSIC_FILE = "Nhạc Cưới/NHẠC CÔ DÂU CHÚ RỂ LÊN SÂN KHẤU.mp3"
MUSIC_START = 1.15


def font(name, size):
    return ImageFont.truetype(os.path.join(HERE, "fonts", name), size)


SCRIPT = "DancingScript-Regular.ttf"
SCRIPT_B = "DancingScript-SemiBold.ttf"
FANCY = "GreatVibes-Regular.ttf"
BOLD = "Anton-Regular.ttf"
SERIF = "PlayfairDisplay-Regular.ttf"
CAPS = "Montserrat-Light.ttf"


def ease(t):
    t = min(max(t, 0.0), 1.0)
    return 1 - (1 - t) ** 3          # ease-out: vào nhanh, dừng êm


def smooth(t):
    t = min(max(t, 0.0), 1.0)
    return t * t * (3 - 2 * t)


# ---------------------------------------------------------------- tài nguyên

PHOTO_DIR = {}


@lru_cache(maxsize=64)
def photo(name):
    im = Image.open(os.path.join(MEDIA, PHOTO_DIR[name]))
    return ImageOps.exif_transpose(im).convert("RGB")


def cover_crop(name, w, h, fy=0.33, extra=1.08):
    """Cắt ảnh phủ kín khung w×h (dư thêm `extra` để zoom chậm), tâm dọc ở fy."""
    im = photo(name)
    tw, th = int(w * extra), int(h * extra)
    s = max(tw / im.width, th / im.height)
    rw, rh = round(im.width * s), round(im.height * s)
    im = im.resize((rw, rh), Image.LANCZOS)
    y = int(min(max(rh * fy - th / 2, 0), rh - th))
    x = (rw - tw) // 2
    return im.crop((x, y, x + tw, y + th))


def text_img(text, fnt, fill=INK, spacing=0, stroke=0):
    """Ảnh RGBA vừa khít 1 dòng chữ (có giãn ký tự)."""
    d = ImageDraw.Draw(Image.new("L", (1, 1)))
    if spacing:
        ws = [d.textlength(c, font=fnt) for c in text]
        tw = sum(ws) + spacing * (len(text) - 1)
    else:
        tw = d.textlength(text, font=fnt)
    asc, desc = fnt.getmetrics()
    pad = int(fnt.size * 0.35)
    im = Image.new("RGBA", (int(tw) + 2 * pad, asc + desc + 2 * pad), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    if spacing:
        x = pad
        for c, w in zip(text, ws):
            dr.text((x, pad), c, font=fnt, fill=fill)
            x += w + spacing
    else:
        dr.text((pad, pad), text, font=fnt, fill=fill, stroke_width=stroke, stroke_fill=fill)
    return im


def heart_img(size, color=INK, outline=True):
    im = Image.new("RGBA", (size * 2, size * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    pts = []
    for i in range(120):
        t = math.pi * 2 * i / 120
        x = 16 * math.sin(t) ** 3
        y = -(13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t))
        pts.append((size + x * size / 18, size + y * size / 18))
    if outline:
        d.line(pts + [pts[0]], fill=color, width=max(2, size // 9), joint="curve")
    else:
        d.polygon(pts, fill=color)
    return im.resize((size, size), Image.LANCZOS)


# ---------------------------------------------------------------- phần tử

class El:
    """Một phần tử trong cảnh. kind: photo | img | mask."""

    def __init__(self, kind, x, y, t0=0.0, anim="fade", din=1.0, **kw):
        self.kind, self.x, self.y, self.t0, self.anim, self.din, self.kw = kind, x, y, t0, anim, din, kw


def P(name, x, y, w, h, t0=0.0, anim="fade", fy=0.33, kb="in", feather=None, din=1.1):
    return El("photo", x, y, t0, anim, din, name=name, w=w, h=h, fy=fy, kb=kb, feather=feather)


def T(text, fnt, size, x, y, t0=0.0, anim="up", fill=INK, spacing=0, anchor="mm", din=1.0):
    return El("img", x, y, t0, anim, din, make=("text", text, fnt, size, fill, spacing), anchor=anchor)


def LINES(text, fnt, size, x, y, t0, gap=None, fill=INK, anchor="mm", step=0.45, anim="up"):
    """Câu nói nhiều dòng, hiện lần lượt từng dòng."""
    gap = gap or int(size * 1.45)
    rows = text.split("\n")
    y0 = y - gap * (len(rows) - 1) / 2
    return [T(r, fnt, size, x, y0 + i * gap, t0 + i * step, anim, fill, 0, anchor) for i, r in enumerate(rows)]


def HEARTS(x, y, t0, n=3, size=34, gap=52):
    return [El("img", x + (i - (n - 1) / 2) * gap, y, t0 + i * 0.2, "pop", 0.7, make=("heart", size), anchor="mm")
            for i in range(n)]


def RULE(x1, x2, y, t0):
    return El("img", (x1 + x2) / 2, y, t0, "reveal", 1.2, make=("rule", int(x2 - x1)), anchor="mm")


def POLAROID(name, cx, cy, w, h, angle, t0, fy=0.3):
    return El("img", cx, cy, t0, "drop", 1.1, make=("polaroid", name, w, h, angle, fy), anchor="mm")


def MASK(word, size, cx, cy, name, t0=0.0, fy=0.35, spacing=0):
    return El("mask", cx, cy, t0, "fade", 1.4, word=word, size=size, name=name, fy=fy, spacing=spacing)


@lru_cache(maxsize=256)
def make_img(spec):
    kind = spec[0]
    if kind == "text":
        _, text, fnt, size, fill, spacing = spec
        im = text_img(text, font(fnt, size), fill, spacing)
        if fill == (255, 255, 255):          # chữ trắng trên ảnh: thêm bóng mờ cho dễ đọc
            a = im.getchannel("A").filter(ImageFilter.GaussianBlur(max(3, size // 7)))
            sh = Image.new("RGBA", im.size, (20, 14, 10, 0))
            sh.putalpha(a.point(lambda v: min(255, int(v * 1.6))))
            im = Image.alpha_composite(sh, im)
        return im
    if kind == "heart":
        return heart_img(spec[1])
    if kind == "rule":
        im = Image.new("RGBA", (spec[1], 6), (0, 0, 0, 0))
        ImageDraw.Draw(im).line([0, 3, spec[1], 3], fill=INK + (200,), width=2)
        return im
    if kind == "polaroid":
        _, name, w, h, angle, fy = spec
        b = int(w * 0.05)
        card = Image.new("RGB", (w + 2 * b, h + 2 * b), (255, 255, 255))
        card.paste(cover_crop(name, w, h, fy, 1.0), (b, b))
        pad = 50
        out = Image.new("RGBA", (card.width + 2 * pad, card.height + 2 * pad), (0, 0, 0, 0))
        sh = Image.new("L", out.size, 0)
        ImageDraw.Draw(sh).rectangle([pad + 6, pad + 12, pad + card.width + 6, pad + card.height + 12], fill=110)
        out.putalpha(sh.filter(ImageFilter.GaussianBlur(16)))
        out = Image.alpha_composite(Image.new("RGBA", out.size, (0, 0, 0, 0)), out)
        blk = Image.new("RGBA", out.size, (0, 0, 0, 0))
        blk.putalpha(out.getchannel("A"))
        blk.paste(card, (pad, pad))
        return blk.rotate(angle, resample=Image.BICUBIC, expand=True)
    raise ValueError(kind)


@lru_cache(maxsize=96)
def photo_src(name, w, h, fy):
    return cover_crop(name, w, h, fy, 1.08)


@lru_cache(maxsize=48)
def feather_mask(w, h, side):
    m = Image.new("L", (w, h), 255)
    d = ImageDraw.Draw(m)
    band = int(w * 0.28) if side in ("left", "right") else int(h * 0.3)
    for i in range(band):
        a = int(255 * smooth(i / band))
        if side == "left":
            d.line([i, 0, i, h], fill=a)
        elif side == "right":
            d.line([w - 1 - i, 0, w - 1 - i, h], fill=a)
        else:
            d.line([0, h - 1 - i, w, h - 1 - i], fill=a)
    return m


@lru_cache(maxsize=16)
def mask_layers(word, size, name, fy, spacing):
    fnt = font(BOLD, size)
    m = text_img(word, fnt, (255, 255, 255), spacing).getchannel("A")
    bbox = m.getbbox()
    m = m.crop(bbox)
    return m, photo_src(name, m.width, m.height, fy)


# ---------------------------------------------------------------- vẽ phần tử

def place(img, el, a):
    """Tính vị trí & độ mờ theo kiểu xuất hiện. Trả về (img, x, y, alpha)."""
    anchor = el.kw.get("anchor", "lt")
    x, y = el.x, el.y
    if anchor == "mm":
        x, y = x - img.width / 2, y - img.height / 2
    elif anchor == "lm":
        y = y - img.height / 2
    elif anchor == "rm":
        x, y = x - img.width, y - img.height / 2
    alpha = a
    if el.anim == "up":
        y += (1 - a) * 46
    elif el.anim == "down":
        y -= (1 - a) * 60
    elif el.anim == "left":
        x -= (1 - a) * 140
    elif el.anim == "right":
        x += (1 - a) * 140
    elif el.anim == "drop":
        y -= (1 - a) * 120
    elif el.anim == "rise":
        y += (1 - a) * (H * 0.6)
        alpha = min(1, a * 2.5)
    elif el.anim == "pop":
        s = 0.5 + 0.5 * a
        if s < 0.999:
            nw, nh = max(1, int(img.width * s)), max(1, int(img.height * s))
            x += (img.width - nw) / 2
            y += (img.height - nh) / 2
            img = img.resize((nw, nh), Image.BILINEAR)
    elif el.anim == "reveal":
        alpha = 1.0
        vis = int(img.width * a)
        img = img.crop((0, 0, max(1, vis), img.height))
    return img, int(round(x)), int(round(y)), alpha


def paste(canvas, img, x, y, alpha, mask=None):
    if img.mode == "RGBA":
        m = img.getchannel("A")
        if mask is not None:
            m = Image.composite(m, Image.new("L", m.size, 0), mask)
        if alpha < 0.999:
            m = m.point(lambda v: int(v * alpha))
        canvas.paste(img.convert("RGB"), (x, y), m)
    else:
        if mask is None and alpha >= 0.999:
            canvas.paste(img, (x, y))
        else:
            m = mask if mask is not None else Image.new("L", img.size, 255)
            if alpha < 0.999:
                m = m.point(lambda v: int(v * alpha))
            canvas.paste(img, (x, y), m)


def kb_frame(src, w, h, u, kb):
    """Zoom/pan chậm trong khung (u: 0..1 theo thời lượng cảnh)."""
    e = smooth(u)
    if kb == "out":
        z = 1.08 - 0.08 * e
    elif kb == "none":
        z = 1.0
    else:
        z = 1.0 + 0.08 * e
    s = (src.width / z) / w
    x0 = (src.width - w * s) / 2
    y0 = (src.height - h * s) / 2
    if kb == "pan":
        s = src.width / 1.08 / w
        x0 = (src.width - w * s) * e
        y0 = (src.height - h * s) / 2
    return src.transform((w, h), Image.AFFINE, (s, 0, x0, 0, s, y0), Image.BILINEAR)


def draw_el(canvas, el, t, dur):
    if t < el.t0:
        return
    a = ease((t - el.t0) / el.din)
    u = t / dur
    if el.kind == "photo":
        k = el.kw
        w, h = k["w"], k["h"]
        img = kb_frame(photo_src(k["name"], w, h, k["fy"]), w, h, u, k["kb"])
        mask = feather_mask(w, h, k["feather"]) if k["feather"] else None
        if el.anim == "reveal":
            vis = max(1, int(w * a))
            img = img.crop((0, 0, vis, h))
            mask = mask.crop((0, 0, vis, h)) if mask else None
            paste(canvas, img, int(el.x), int(el.y), 1.0, mask)
            return
        if el.anim == "zoom":
            s = 1.12 - 0.12 * a
            nw, nh = int(w * s), int(h * s)
            img = img.resize((nw, nh), Image.BILINEAR).crop(((nw - w) // 2, (nh - h) // 2, (nw - w) // 2 + w, (nh - h) // 2 + h))
            paste(canvas, img, int(el.x), int(el.y), a, mask)
            return
        el.kw.setdefault("anchor", "lt")
        img2, x, y, al = place(img, el, a)
        paste(canvas, img2, x, y, al, mask)
    elif el.kind == "img":
        img2, x, y, al = place(make_img(el.kw["make"]), el, a)
        paste(canvas, img2, x, y, al)
    elif el.kind == "mask":
        k = el.kw
        m, src = mask_layers(k["word"], k["size"], k["name"], k["fy"], k["spacing"])
        img = kb_frame(src, m.width, m.height, u, "in")
        x, y = int(el.x - m.width / 2), int(el.y - m.height / 2)
        # chữ hiện dần từ trái sang phải
        vis = max(1, int(m.width * a))
        mm = m.crop((0, 0, vis, m.height))
        canvas.paste(img.crop((0, 0, vis, m.height)), (x, y), mm)


# ---------------------------------------------------------------- kịch bản

class Scene:
    def __init__(self, dur, els, trans="fade", date=True):
        self.dur, self.els, self.trans, self.date = dur, els, trans, date


def corner_date():
    return T("24 . 12 . 2026", SERIF, 26, W - 70, H - 48, 0.6, "fade", SOFT, 3, "rm")


def build():
    S = []
    q = SCRIPT

    # 1. LOVE lồng ảnh
    S.append(Scene(7.5, [
        MASK("LOVE", 470, W / 2, H / 2 - 40, "BTT_2663.jpg", 0.3, 0.22, 10),
        T("SAVE THE DATE", CAPS, 30, W / 2, H / 2 + 250, 1.6, "up", INK, 14),
        T("24 . 12 . 2026", SERIF, 40, W / 2, H / 2 + 310, 2.0, "up", SOFT, 6),
    ], date=False))
    # 2. Tiêu đề + ảnh
    S.append(Scene(8.5, [
        P("@.jpg", 1010, 0, 910, H, 0.0, "right", 0.35),
        T("Our Wedding", FANCY, 150, 505, 400, 0.6, "up"),
        T("&", FANCY, 70, 505, 520, 1.0, "fade", SOFT),
        T("Chúng mình kết hôn", q, 64, 505, 610, 1.3, "up"),
        T("WELCOME TO OUR WEDDING!", CAPS, 26, 505, 730, 1.9, "fade", INK, 8),
    ], "push", date=False))
    # 3. Ba ảnh + số ngày
    els = []
    for i, (n, num) in enumerate([("BTT_2755.jpg", "24"), ("BTT_2809.jpg", "12"), ("BTT_2892.jpg", "26")]):
        x = 150 + i * 560
        els.append(P(n, x, 90, 500, 740, 0.2 + i * 0.35, "up", 0.3))
        els.append(T(num, SERIF, 190, x + 250, 900, 1.2 + i * 0.35, "up"))
    S.append(Scene(8.5, els, "fade", date=False))
    # 4. Hai ảnh, ảnh lớn mờ viền + câu nói
    S.append(Scene(8.5, [
        P("BTT_2877.jpg", 120, 170, 520, 760, 0.1, "left", 0.3),
        P("BTT_2663.jpg", 740, 0, 1180, H, 0.4, "fade", 0.2, "in", "left"),
        *LINES("Ngày gặp phút này,\nchúng ta vẫn yêu, và vẫn được yêu.", q, 46, 1330, 900, 1.8, fill=(255, 255, 255)),
    ], "iris", date=False))
    # 5. Lưới 4 ảnh + câu nói
    g = [("BTT_3068.jpg", 0.3), ("BTT_3093.jpg", 0.25), ("BTT_3104.jpg", 0.3), ("BTT_3134.jpg", 0.3)]
    els = [P(n, 140 + (i % 2) * 400, 70 + (i // 2) * 480, 380, 460, 0.15 * i, "fade", fy) for i, (n, fy) in enumerate(g)]
    els += LINES("Giữa hàng vạn người,\nta gặp được người mình nên gặp.\nKhông sớm một bước,\ncũng chẳng muộn một giây,\nvừa vặn tìm thấy nhau.", q, 50, 1390, 540, 1.0, step=0.55)
    S.append(Scene(9.5, els, "slide_up"))
    # 6. Ảnh lớn + Save the Date + ảnh nhỏ
    S.append(Scene(8.5, [
        P("BTT_2933.jpg", 0, 0, 900, H, 0.0, "fade", 0.25),
        T("Save The Date", SCRIPT_B, 92, 1410, 180, 0.7, "up"),
        P("BTT_3253.jpg", 1100, 290, 620, 640, 1.1, "up", 0.3),
    ], "wipe"))
    # 7. Ảnh tràn khung + câu nói
    S.append(Scene(8.5, [
        P("BTT_3457.jpg", 0, 0, W, H, 0.0, "fade", 0.2, "in"),
        *LINES("Tình yêu — đưa anh và em\ntrở thành “chúng ta”.\nBiến mọi “hôm nay”\nthành “ngày tuyệt vời nhất”.", q, 54, 1500, 560, 1.0, fill=INK, step=0.5),
    ], "fade", date=False))
    # 8. Polaroid nghiêng + câu nói
    S.append(Scene(8.5, [
        POLAROID("BTT_3143.jpg", 520, 470, 500, 680, 5, 0.2),
        POLAROID("BTT_3157.jpg", 820, 600, 460, 620, -6, 0.8),
        *HEARTS(1430, 380, 1.4),
        *LINES("Giữa muôn trùng thế giới,\nem là rung động duy nhất của anh.", q, 52, 1430, 560, 1.8),
    ], "push"))
    # 9. Ảnh dọc + chữ LOVE xếp dọc + ảnh nhỏ
    els = [P("BTT_3308.jpg", 0, 0, 700, H, 0.0, "left", 0.3)]
    for i, c in enumerate("LOVE"):
        els.append(T(c, BOLD, 170, 880, 170 + i * 235, 0.5 + i * 0.2, "up"))
    els += [P("BTT_3316.jpg", 1080, 90, 600, 600, 1.0, "fade", 0.25),
            *HEARTS(1380, 780, 1.8),
            *LINES("Tương lai sau này,\ncó Anh và Em.", q, 54, 1380, 900, 2.1)]
    S.append(Scene(9.5, els, "zoom"))
    # 10. Happiness + hai ảnh
    S.append(Scene(8.5, [
        RULE(180, 700, 130, 0.2), RULE(1220, 1740, 130, 0.2),
        T("Happiness", SCRIPT_B, 96, W / 2, 125, 0.4, "fade"),
        P("BTT_3324.jpg", 100, 240, 840, 780, 0.7, "up", 0.28),
        P("BTT_3339.jpg", 980, 240, 840, 780, 1.0, "up", 0.28),
    ], "fade"))
    # 11. ROMANTIC khổng lồ + dải ảnh
    S.append(Scene(9.5, [
        T("I love you", SCRIPT_B, 64, W / 2, 70, 0.3, "fade"),
        RULE(600, 800, 74, 0.3), RULE(1120, 1320, 74, 0.3),
        T("ROMANTIC", BOLD, 330, W / 2, 300, 0.2, "reveal", INK, 6),
        P("BTT_3374.jpg", 0, 430, W, 650, 0.9, "rise", 0.3, "pan"),
        P("BTT_3381.jpg", 1460, 640, 380, 380, 1.8, "up", 0.25),
        *LINES("Chỉ cần người ấy kề bên,\nmọi điều giản dị cũng trở nên tuyệt vời.", q, 40, 1080, 1000, 2.2, fill=(255, 255, 255), step=0.35),
    ], "slide_up", date=False))
    # 12. Ba dải ảnh dọc
    els = [P(n, 760 + i * 380, 0, 360, H, 0.15 + i * 0.3, "rise", 0.3) for i, n in enumerate(["BTT_3397.jpg", "BTT_3439.jpg", "BTT_2832.jpg"])]
    els += LINES("Hạnh phúc là được\nnắm tay nhau\nđi hết quãng đời còn lại.", q, 56, 370, 540, 1.3)
    S.append(Scene(8.5, els, "push", date=False))
    # 13. Ảnh trái + chữ phải
    S.append(Scene(8.5, [
        P("BTT_3284.jpg", 160, 80, 640, 920, 0.0, "reveal", 0.3),
        T("Always", FANCY, 170, 1340, 330, 0.6, "up"),
        *LINES("Cảm ơn anh đã đến,\ncảm ơn em đã ở lại.", q, 58, 1340, 600, 1.3),
        *HEARTS(1340, 800, 2.2, 1, 40),
    ], "light"))
    # 14. Ba ảnh: Anh & Em
    els = []
    for i, (n, w) in enumerate([("BTT_3093.jpg", "Anh"), ("BTT_3183.jpg", "&"), ("BTT_3143.jpg", "Em")]):
        x = 150 + i * 560
        els.append(P(n, x, 60, 500, 760, 0.2 + i * 0.3, "down", 0.25))
        els.append(T(w, FANCY, 140, x + 250, 920, 1.1 + i * 0.3, "up"))
    S.append(Scene(8.5, els, "fade", date=False))
    # 15. FOREVER lồng ảnh
    S.append(Scene(7.5, [
        T("together", FANCY, 110, W / 2, 230, 1.4, "fade", SOFT),
        MASK("FOREVER", 330, W / 2, H / 2 + 40, "BTT_3183.jpg", 0.2, 0.3, 6),
        T("24 . 12 . 2026", SERIF, 40, W / 2, H / 2 + 290, 2.0, "up", SOFT, 6),
    ], "iris", date=False))
    # 16. Lưới 4 ảnh (phải) + câu nói (trái)
    g = [("BTT_2755.jpg", 0.3), ("BTT_2877.jpg", 0.3), ("BTT_2933.jpg", 0.25), ("BTT_3253.jpg", 0.3)]
    els = [P(n, 1000 + (i % 2) * 400, 70 + (i // 2) * 480, 380, 460, 0.15 * i, "fade", fy) for i, (n, fy) in enumerate(g)]
    els += LINES("Một ánh nhìn, một nụ cười,\nvà thế là đủ\ncho cả một đời.", q, 58, 520, 540, 1.0)
    S.append(Scene(9.0, els, "wipe"))
    # 17. Ảnh tràn khung + câu nói trái
    S.append(Scene(8.5, [
        P("BTT_2663.jpg", 0, 0, W, H, 0.0, "zoom", 0.12, "out"),
        *LINES("Yêu là cùng nhau đi qua\nnhững ngày nắng,\nnhững ngày mưa.", q, 58, 420, 840, 1.2, fill=(255, 255, 255)),
    ], "blur", date=False))
    # 18. Polaroid 2
    S.append(Scene(8.5, [
        *LINES("Từ hôm nay,\nnhà mình có thêm\nmột người.", q, 60, 480, 520, 1.6),
        POLAROID("BTT_3316.jpg", 1150, 480, 480, 660, -5, 0.2),
        POLAROID("BTT_3068.jpg", 1470, 600, 440, 600, 7, 0.8),
    ], "push"))
    # 19. Together + hai ảnh
    S.append(Scene(8.5, [
        P("BTT_3134.jpg", 100, 60, 840, 780, 0.2, "down", 0.3),
        P("BTT_3104.jpg", 980, 60, 840, 780, 0.5, "down", 0.3),
        RULE(180, 700, 950, 1.0), RULE(1220, 1740, 950, 1.0),
        T("Together", SCRIPT_B, 96, W / 2, 945, 1.2, "fade"),
    ], "slide_up", date=False))
    # 20. Ba dải ảnh dọc (bên trái) + câu nói
    els = [P(n, 0 + i * 380, 0, 360, H, 0.15 + i * 0.3, "rise", 0.3) for i, n in enumerate(["BTT_2809.jpg", "BTT_3397.jpg", "BTT_3381.jpg"])]
    els += LINES("Yêu nhau\ntừ những điều nhỏ bé nhất.", q, 60, 1510, 540, 1.3)
    S.append(Scene(8.5, els, "fade"))
    # 21. WEDDING khổng lồ + ảnh
    S.append(Scene(9.0, [
        P("BTT_3183.jpg", 0, 380, W, 700, 0.6, "rise", 0.24, "pan"),
        T("WEDDING", BOLD, 330, W / 2, 230, 0.1, "reveal", INK, 10),
        T("Our", FANCY, 110, 260, 90, 1.0, "fade", SOFT),
        P("BTT_3324.jpg", 80, 640, 360, 380, 1.6, "up", 0.25),
    ], "push", date=False))
    # 22. Save the Date
    S.append(Scene(10.5, [
        P("@.jpg", 0, 0, 840, H, 0.0, "left", 0.35),
        T("Save the Date", FANCY, 140, 1380, 220, 0.6, "up"),
        RULE(1150, 1610, 340, 1.0),
        T("24 . 12 . 2026", SERIF, 120, 1380, 470, 1.3, "up", INK, 6),
        T("THỨ NĂM", CAPS, 34, 1380, 590, 1.8, "fade", SOFT, 14),
        *LINES("Hẹn gặp bạn\ntrong ngày vui của chúng mình!", q, 56, 1380, 790, 2.3),
    ], "wipe", date=False))
    # 23. Thank you
    S.append(Scene(8.0, [
        P("BTT_3339.jpg", 760, 120, 400, 560, 0.1, "fade", 0.25),
        T("Thank you", FANCY, 170, W / 2, 810, 0.8, "up"),
        *HEARTS(W / 2, 950, 1.6),
    ], "fade", date=False))

    t = 0.0
    for sc in S:
        sc.start = t
        if sc.date:
            sc.els.append(corner_date())
        t += sc.dur - TR
    return S, t + TR


# ---------------------------------------------------------------- dựng khung hình

SCENES, TOTAL = None, 0.0


def scene_frame(k, t):
    sc = SCENES[k]
    c = Image.new("RGB", (W, H), BG)
    for el in sc.els:
        draw_el(c, el, t, sc.dur)
    return c


def render(i):
    t = i / FPS
    act = [k for k, s in enumerate(SCENES) if s.start <= t < s.start + s.dur]
    if not act:
        return Image.new("RGB", (W, H), BG).tobytes()
    k = act[-1]
    fr = scene_frame(k, t - SCENES[k].start)
    if len(act) > 1:
        j = act[0]
        prev = scene_frame(j, t - SCENES[j].start)
        fr = rv.transition(SCENES[k].trans, prev, fr, smooth((t - SCENES[k].start) / TR))
    a = min(1.0, t / 1.0, (TOTAL - t) / 2.0)
    if a < 1:
        fr = Image.blend(Image.new("RGB", (W, H), BG), fr, max(a, 0))
    return fr.tobytes()


def init(media):
    global MEDIA, SCENES, TOTAL
    MEDIA = media
    for p in glob.glob(os.path.join(media, "WEDDING", "**", "*.jpg"), recursive=True):
        PHOTO_DIR[os.path.basename(p)] = os.path.relpath(p, media)
    SCENES, TOTAL = build()


def main():
    media, out = sys.argv[1], sys.argv[2]
    init(media)
    print(f"{len(SCENES)} cảnh, thời lượng {TOTAL:.1f}s")
    if "--preview" in sys.argv:
        os.makedirs(out, exist_ok=True)
        for k, s in enumerate(SCENES):
            fr = Image.frombytes("RGB", (W, H), render(int((s.start + s.dur - TR - 0.2) * FPS)))
            fr.resize((W // 2, H // 2), Image.LANCZOS).save(f"{out}/{k:02d}.jpg", quality=85)
            fr = Image.frombytes("RGB", (W, H), render(int((s.start + 1.0) * FPS)))
            fr.resize((W // 2, H // 2), Image.LANCZOS).save(f"{out}/{k:02d}a.jpg", quality=85)
        return
    n = int(TOTAL * FPS)
    music = os.path.join(media, MUSIC_FILE)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-stats",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-ss", str(MUSIC_START), "-t", f"{TOTAL:.3f}", "-i", music,
           "-filter_complex", f"[1:a]afade=t=in:d=1.0,afade=t=out:st={TOTAL - 5:.3f}:d=5[a]",
           "-map", "0:v", "-map", "[a]",
           "-c:v", "libx264", "-preset", "slow", "-crf", "19", "-tune", "film",
           "-pix_fmt", "yuv420p", "-profile:v", "high", "-c:a", "aac", "-b:a", "192k",
           "-movflags", "+faststart", "-shortest", out]
    ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    with Pool(os.cpu_count(), initializer=init, initargs=(media,)) as pool:
        for b in pool.imap(render, range(n), chunksize=FPS):
            ff.stdin.write(b)
    ff.stdin.close()
    sys.exit(ff.wait())


if __name__ == "__main__":
    main()
