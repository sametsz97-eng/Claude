import numpy as np, wave, sys
sys.path.insert(0, '.')
SR = 44100
DUR = 5.0
RINGS = [(0.30, 0.98), (1.70, 2.12), (2.95, 3.20)]
REACH = [0.24, 0.17, 0.12]
n = int(SR * DUR)
t = np.arange(n) / SR
out = np.zeros(n)
rng = np.random.default_rng(3)


def band(x, lo, hi):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR)
    X[(f < lo) | (f > hi)] = 0
    return np.fft.irfft(X, len(x))


# --- alarm: rapid bright "radar"-style pings in groups (classic annoying phone alarm feel)
def ping(dur):
    tt = np.arange(int(SR * dur)) / SR
    env = np.minimum(1, tt / 0.004) * np.exp(-tt / 0.045)
    fm = 1 + 0.004 * np.sin(2 * np.pi * 30 * tt)
    s = (np.sin(2 * np.pi * 2093 * fm * tt) * 0.6 + np.sin(2 * np.pi * 2637 * fm * tt) * 0.35
         + np.sin(2 * np.pi * 4186 * tt) * 0.12 + np.sin(2 * np.pi * 1046 * tt) * 0.2)
    return s * env

P = ping(0.11)
pattern = []  # offsets (s) inside a 0.62 s cycle: 4 quick pings then a gap
for g in range(1):
    for k in range(4):
        pattern.append(k * 0.085)
CYCLE = 0.50
alarm = np.zeros(n)
for tr, tc in RINGS:
    c = tr
    while c < tc:
        for off in pattern:
            st = c + off
            if st >= tc:
                break
            i = int(st * SR); seg = P[: max(0, min(len(P), int(tc * SR) - i))]
            alarm[i:i + len(seg)] += seg
        c += CYCLE
    # hard stop with a tiny fade at the tap
    i = int(tc * SR)
    alarm[i:i + 200] *= np.linspace(1, 0, 200)
    alarm[i + 200:i + int(0.05 * SR)] = 0
import wave as _w
_r = _w.open('ref_audio.wav'); REF = np.frombuffer(_r.readframes(_r.getnframes()), np.int16).reshape(-1, 2).astype(np.float64) / 32768
REF = REF.mean(1)
def seg(a, b): return REF[int(a * SR):int(b * SR)].copy()
XF = int(0.03 * SR)
alarm = np.zeros(n)
for tr, tc in RINGS:
    pre = seg(0.30, 0.30 + (tc - tr) - 0.03 + 0.03)      # alarm onset, as in the reference
    hit = seg(2.30, 2.62)                                # snooze tap + cut-off, as in the reference
    hit[-int(0.06 * SR):] *= np.linspace(1, 0, int(0.06 * SR))
    pre[-XF:] *= np.linspace(1, 0, XF); hit[:XF] *= np.linspace(0, 1, XF)
    i0 = int(tr * SR); alarm[i0:i0 + len(pre)] += pre[: n - i0]
    i1 = int((tc - 0.03) * SR); alarm[i1:i1 + len(hit)] += hit[: n - i1]
out += alarm * 1.0

# --- glass tap + soft thud at each contact
for tr, tc in RINGS:
    i = int(tc * SR); L = int(0.06 * SR)
    tt = np.arange(L) / SR
    click = band(rng.standard_normal(L), 2500, 9000) * np.exp(-tt / 0.006) * 0.9
    thud = np.sin(2 * np.pi * 140 * tt) * np.exp(-tt / 0.02) * 0.35
    pass

# --- cloth rustle when the arm moves (reach + return)
rust = band(rng.standard_normal(n), 300, 3500)
renv = np.zeros(n)
for (tr, tc), rd in zip(RINGS, REACH):
    for a, b, amp in [(tc - rd, tc, 0.25), (tc + 0.05, tc + 0.35, 0.16)]:
        m = (t >= a) & (t <= b)
        renv[m] = np.maximum(renv[m], amp * np.sin(np.pi * (t[m] - a) / (b - a)))
out += rust / np.abs(rust).max() * renv * 0.8

# --- breathing / little snore while asleep (quiet), silent while the alarm rings
breath = band(rng.standard_normal(n), 150, 1200)
breath /= np.abs(breath).max()
benv = 0.5 * (1 - np.cos(2 * np.pi * t / 2.6)) ** 2 / 4
snore = np.sin(2 * np.pi * 70 * t + 0.6 * np.sin(2 * np.pi * 35 * t)) * (0.5 + 0.5 * np.sign(np.sin(2 * np.pi * 70 * t)))
quiet = np.ones(n)
for tr, tc in RINGS:
    quiet[(t > tr - 0.05) & (t < tc + 0.4)] = 0
q = np.convolve(quiet, np.ones(2000) / 2000, 'same')
late = np.clip((t - 3.6) / 0.4, 0, 1)
out += breath * benv * 0.10 * q + snore * benv * 0.07 * q * late

# fade-out end
out *= np.clip((DUR - t) / 0.25, 0, 1)
out /= max(1e-9, np.abs(out).max()) / 0.9
pcm = (np.clip(out, -1, 1) * 32767).astype(np.int16)
st = np.stack([pcm, pcm], 1)
with wave.open('audio.wav', 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(st.tobytes())
print('ok')
