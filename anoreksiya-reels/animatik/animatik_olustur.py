"""Anoreksiya Reels taslak videosu (animatik) üretir.

Çıktı: animatik.mp4 (1080x1920, 9:16, ~64 sn)
Gereksinim: python3, pillow, numpy, ffmpeg
Kullanım: python3 animatik_olustur.py
"""
import re
import subprocess
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
SRT = HERE.parent / "altyazi.srt"
OUT = HERE / "animatik.mp4"
WAV = HERE / "_muzik.wav"

W, H, FPS = 1080, 1920, 15
TOTAL = 64.0
FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_R = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

# (başlangıç, bitiş, sahne adı, görüntü açıklaması, renk üst, renk alt)
SCENES = [
    (0, 3, "1 · HOOK — Tartı", "Karanlık banyo. Çıplak ayaklar tartıya basıyor.\nRakam bulanık. Gözler kapanıyor.", (18, 24, 38), (6, 8, 14)),
    (3, 6, "2 · Ayna", "Avucunu karnına koyar,\naynada karnına bakar.", (40, 46, 60), (14, 16, 24)),
    (6, 12, "3 · Mutfak", "Koridordan mutfağa. Güneş, çay buharı,\nannenin koyduğu kahvaltı tabağı.", (92, 70, 44), (30, 22, 14)),
    (12, 16, "4 · Kahvaltı", "Zeytini tabakta gezdirir.\nTabağı yavaşça iter.", (98, 74, 46), (32, 24, 16)),
    (16, 23, "5 · Gün içinde", "Kampüs yolu, kafe. Arkadaşlarına yemek,\nona yalnızca sade kahve gelir.", (70, 66, 58), (24, 22, 20)),
    (23, 28, "6 · Kafe", "Ece çatalını bırakır, ona bakar.\nFincanı iki eliyle tutar.", (74, 64, 52), (26, 22, 18)),
    (28, 33, "7 · Akşam — Tartı", "Soğuk floresan ışık. Aynı tartı.\nKaşları çatılır, başını sallar.", (34, 52, 56), (10, 16, 18)),
    (33, 43, "8 · Yatak — Fotoğraflar", "Yüzünde yalnızca telefon ışığı.\nEski fotoğraflar; kendi yanağına zoom.", (20, 26, 48), (4, 6, 12)),
    (43, 49, "9 · Tavana bakış", "Telefonu göğsüne bırakır, ışık söner.\nÜstten plan: tavana bakıyor.", (14, 18, 32), (2, 3, 8)),
    (49, 59, "10 · Final — Ayna", "Aynanın karşısında. Kamera çok yavaş\nyüzüne yaklaşır. Önce sessizlik.", (26, 28, 36), (4, 4, 6)),
    (59, 64, "11 · Kapanış", "", (8, 8, 10), (0, 0, 0)),
]

HOOK_TEXT = "“Biraz daha kilo verirsem\nkendimi seveceğim.”"
CARD_MAIN = ("Yemekle, kilonla ve bedeninle\nkurduğun ilişki hayatını\nyönetmeye başladıysa\n"
             "bunu tek başına çözmek\nzorunda değilsin.")
CARD_SMALL = ("Anoreksiya nervoza tedavi gerektiren ciddi bir\nyeme bozukluğudur. "
              "Profesyonel destek almak önemlidir.")

# Hangi altyazı kime ait (anlatıcı = VO). Numara: SRT sıra no.
SPEAKER = {1: "", 2: "DEFNE", 5: "ANNE", 6: "DEFNE", 10: "ECE", 11: "DEFNE"}


def parse_srt(path):
    def t(s):
        h, m, rest = s.split(":")
        sec, ms = rest.split(",")
        return int(h) * 3600 + int(m) * 60 + int(sec) + int(ms) / 1000

    subs = []
    for block in path.read_text(encoding="utf-8").strip().split("\n\n"):
        lines = block.strip().splitlines()
        idx = int(lines[0])
        a, b = [x.strip() for x in lines[1].split("-->")]
        subs.append((idx, t(a), t(b), "\n".join(lines[2:])))
    return subs


def gradient(top, bot):
    y = np.linspace(0, 1, H)[:, None, None]
    arr = (np.array(top)[None, None, :] * (1 - y) + np.array(bot)[None, None, :] * y)
    arr = np.broadcast_to(arr, (H, W, 3)).copy()
    # vinyet
    yy, xx = np.mgrid[0:H, 0:W]
    d = np.sqrt(((xx - W / 2) / (W / 1.2)) ** 2 + ((yy - H / 2) / (H / 1.3)) ** 2)
    arr *= np.clip(1.15 - d * 0.7, 0.35, 1)[:, :, None]
    return arr.astype(np.float32)


def text_center(draw, y, text, font, fill, spacing=14):
    bbox = draw.multiline_textbbox((0, 0), text, font=font, spacing=spacing, align="center")
    w = bbox[2] - bbox[0]
    draw.multiline_text(((W - w) / 2, y), text, font=font, fill=fill, spacing=spacing, align="center")
    return bbox[3] - bbox[1]


def fade(t, a, b, f=0.35):
    return max(0.0, min(1.0, (t - a) / f, (b - t) / f))


def make_music(path):
    sr = 44100
    n = int(TOTAL * sr)
    out = np.zeros(n, dtype=np.float64)

    def note(freq, start, dur, amp):
        s = int(start * sr)
        L = int(dur * sr)
        if s >= n:
            return
        L = min(L, n - s)
        tt = np.arange(L) / sr
        env = np.exp(-tt * 1.4) * np.minimum(1, tt / 0.01)
        tone = (np.sin(2 * np.pi * freq * tt) + 0.35 * np.sin(4 * np.pi * freq * tt)
                + 0.12 * np.sin(6 * np.pi * freq * tt))
        out[s:s + L] += amp * env * tone

    def hz(m):
        return 440 * 2 ** ((m - 69) / 12)

    # Am - F - C - G döngüsü, yavaş arpej (~64 BPM)
    chords = [[57, 60, 64], [53, 57, 60], [48, 55, 64], [55, 59, 62]]
    beat = 60 / 64
    t = 3.0
    note(hz(69), 3.0, 4, 0.18)  # giriş tek nota
    t = 4.0
    i = 0
    while t < 48.5:
        c = chords[(i // 4) % 4]
        if i % 4 == 0:
            note(hz(c[0] - 12), t, 4, 0.10)
        note(hz(c[i % 3] + 12), t, 2.5, 0.07)
        t += beat
        i += 1
    # 49'da müzik kesilir — tek uzun nota
    note(hz(69), 48.6, 3, 0.10)
    # kapanış akoru
    for m in [45, 57, 60, 64]:
        note(hz(m), 59.0, 5, 0.07)
    # tartı "bip"leri
    for bt in (0.6, 28.6):
        s = int(bt * sr)
        L = int(0.12 * sr)
        tt = np.arange(L) / sr
        out[s:s + L] += 0.12 * np.sin(2 * np.pi * 2000 * tt) * np.exp(-tt * 20)
    # basit yankı
    for delay, g in ((0.23, 0.30), (0.41, 0.18), (0.67, 0.10)):
        d = int(delay * sr)
        out[d:] += g * out[:-d]
    # VO alanlarında kısma (ducking simülasyonu yok; animatik sessiz)
    fade_out = np.ones(n)
    k = int(2 * sr)
    fade_out[-k:] = np.linspace(1, 0, k)
    out *= fade_out
    out = out / (np.max(np.abs(out)) + 1e-9) * 0.6
    pcm = (out * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(np.repeat(pcm[:, None], 2, axis=1).tobytes())


def main():
    subs = parse_srt(SRT)
    f_title = ImageFont.truetype(FONT_B, 46)
    f_desc = ImageFont.truetype(FONT_R, 38)
    f_hook = ImageFont.truetype(FONT_B, 62)
    f_sub = ImageFont.truetype(FONT_B, 50)
    f_spk = ImageFont.truetype(FONT_B, 30)
    f_card = ImageFont.truetype(FONT_B, 56)
    f_small = ImageFont.truetype(FONT_R, 30)
    f_tag = ImageFont.truetype(FONT_R, 28)

    bgs = [gradient(s[4], s[5]) for s in SCENES]
    rng = np.random.default_rng(1)

    make_music(WAV)
    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", str(WAV),
           "-c:v", "libx264", "-preset", "medium", "-crf", "27", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", str(OUT)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    nframes = int(TOTAL * FPS)
    for fi in range(nframes):
        t = fi / FPS
        si = next(i for i, s in enumerate(SCENES) if s[0] <= t < s[1] or i == len(SCENES) - 1)
        a, b, name, desc, _, _ = SCENES[si]
        bg = bgs[si]
        # sahne geçişlerinde siyaha yumuşak geçiş
        k = fade(t, a, b, 0.25) if si not in (0,) else min(1, (b - t) / 0.25)
        # final sahnesinde yavaş "push-in" hissi: hafif aydınlanma
        if si == 9:
            k *= 0.8 + 0.2 * (t - a) / (b - a)
        frame = bg * (0.25 + 0.75 * k)
        frame += rng.normal(0, 2.5, (H // 4, W // 4, 1)).repeat(4, 0).repeat(4, 1)  # film grain
        img = Image.fromarray(np.clip(frame, 0, 255).astype(np.uint8))
        dr = ImageDraw.Draw(img, "RGBA")

        al = int(255 * fade(t, a, b))
        # üst etiket
        dr.text((60, 70), "TASLAK · ANİMATİK", font=f_tag, fill=(255, 255, 255, 120))
        dr.text((W - 60 - dr.textlength(f"{int(t)//60}:{int(t)%60:02d}", font=f_tag), 70),
                f"{int(t)//60}:{int(t)%60:02d}", font=f_tag, fill=(255, 255, 255, 120))

        if si == 0:
            text_center(dr, 760, HOOK_TEXT, f_hook, (255, 255, 255, int(255 * fade(t, 0.15, 3.0, 0.4))), 22)
            dr.text((60, 150), name, font=f_title, fill=(255, 255, 255, 170))
            dr.multiline_text((60, 220), desc, font=f_desc, fill=(220, 220, 220, 150), spacing=12)
        elif si == len(SCENES) - 1:
            ca = int(255 * min(1, (t - a) / 0.8))
            text_center(dr, 640, CARD_MAIN, f_card, (255, 255, 255, ca), 20)
            text_center(dr, 1180, CARD_SMALL, f_small, (200, 200, 200, ca), 12)
        else:
            dr.text((60, 150), name, font=f_title, fill=(255, 255, 255, al))
            dr.multiline_text((60, 220), desc, font=f_desc, fill=(225, 225, 225, int(al * 0.85)), spacing=12)
            if si == 9 and t < 51:
                text_center(dr, 900, "( sessizlik )", f_desc, (255, 255, 255, int(140 * fade(t, 49, 51))))

        # altyazı (hook yazısı ekranda olduğu için 1 numara gösterilmez)
        for idx, sa, sb, txt in subs:
            if idx == 1 or not (sa <= t < sb):
                continue
            sal = fade(t, sa, sb, 0.15)
            spk = SPEAKER.get(idx, "ANLATICI")
            y0 = 1380
            bbox = dr.multiline_textbbox((0, 0), txt, font=f_sub, spacing=12, align="center")
            bw, bh = bbox[2] - bbox[0], bbox[3] - bbox[1]
            dr.rounded_rectangle(((W - bw) / 2 - 30, y0 - 20, (W + bw) / 2 + 30, y0 + bh + 34),
                                 18, fill=(0, 0, 0, int(110 * sal)))
            for dx, dy in ((3, 3),):
                bbox2 = dr.multiline_textbbox((0, 0), txt, font=f_sub, spacing=12, align="center")
                dr.multiline_text(((W - bw) / 2 + dx, y0 + dy), txt, font=f_sub, spacing=12,
                                  align="center", fill=(0, 0, 0, int(200 * sal)))
            text_center(dr, y0, txt, f_sub, (255, 255, 255, int(255 * sal)), 12)
            if spk:
                col = (150, 200, 255) if spk == "ANLATICI" else (255, 205, 150)
                text_center(dr, y0 - 64, spk, f_spk, col + (int(220 * sal),))

        # ilerleme çubuğu
        dr.rectangle((0, H - 8, W * t / TOTAL, H), fill=(255, 255, 255, 140))
        proc.stdin.write(img.convert("RGB").tobytes())

    proc.stdin.close()
    proc.wait()
    WAV.unlink(missing_ok=True)
    print("Hazır:", OUT)


if __name__ == "__main__":
    main()
