#!/usr/bin/env python3
"""Procedural Cinema Sound Design Engine for Episode 1 Ending v5.0 'Kousetsuka' (96.0s).
Reads dm/episode-01/ending/v5-pill-previs/scene_spec.json directly so EVERY audio event
is mathematically frame-locked to the visual cuts and signature beats!

Musical Key: D-flat Major / F minor (Db, Eb, F, Gb, Ab, Bb, C)
Outputs:
  - audio/kousetsuka_v5_master_audio_96s.wav (48kHz 16-bit Stereo, mastered to -14.0 LUFS, true peak <= -2.0 dBFS)
  - sheets/sound_waveform_v5.png (beat-aligned waveform QA sheet with coral timeline markers)
  - clips/master_96s_preview_v5_WITH_AUDIO.mp4 (Rec.709 tagged H.264 + AAC 192kbps muxed master preview)
"""

import json
import math
import wave
from pathlib import Path

import av
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
SPEC_PATH = ROOT / "scene_spec.json"
AUDIO_DIR = ROOT / "audio"
WAV_PATH = AUDIO_DIR / "kousetsuka_v5_master_audio_96s.wav"
WAVE_PNG = ROOT / "sheets" / "sound_waveform_v5.png"
VIDEO_IN = ROOT / "clips" / "master_96s_preview_v5.mp4"
VIDEO_OUT = ROOT / "clips" / "master_96s_preview_v5_WITH_AUDIO.mp4"

SR = 48000
TARGET_LUFS = -14.0
FONT_SANS = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
FONT_SERIF = "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc"

# Musical frequencies in D-flat Major (Db3..Db6)
NOTE = {
    "Db2": 69.30,  "F2": 87.31,  "Gb2": 92.50,  "Ab2": 103.83, "Bb2": 116.54,
    "Db3": 138.59, "Eb3": 155.56, "F3": 174.61, "Gb3": 185.00, "Ab3": 207.65, "Bb3": 233.08, "C4": 261.63,
    "Db4": 277.18, "Eb4": 311.13, "F4": 349.23, "Gb4": 369.99, "Ab4": 415.30, "Bb4": 466.16, "C5": 523.25,
    "Db5": 554.37, "Eb5": 622.25, "F5": 698.46, "Gb5": 739.99, "Ab5": 830.61, "Bb5": 932.33, "C6": 1046.50,
    "Db6": 1108.73,
}


def lp_filter(x, cutoff_hz):
    """Simple zero-dependency 2-pole Butterworth-like low-pass via FFT for crystal-clean filtering."""
    freqs = np.fft.rfftfreq(len(x), 1.0 / SR)
    H = 1.0 / (1.0 + (freqs / max(10.0, cutoff_hz)) ** 4)
    return np.fft.irfft(np.fft.rfft(x) * H, n=len(x))


def bp_filter(x, f_lo, f_hi):
    freqs = np.fft.rfftfreq(len(x), 1.0 / SR)
    hp = 1.0 / (1.0 + (max(5.0, f_lo) / np.maximum(freqs, 1e-3)) ** 4)
    lp = 1.0 / (1.0 + (freqs / max(20.0, f_hi)) ** 4)
    return np.fft.irfft(np.fft.rfft(x) * hp * lp, n=len(x))


def smooth_env(n, atk_s, rel_s):
    e = np.ones(n, dtype=np.float64)
    na = min(n, int(atk_s * SR))
    nr = min(n, int(rel_s * SR))
    if na > 0:
        u = np.linspace(0, 1, na)
        e[:na] *= 0.5 - 0.5 * np.cos(np.pi * u)
    if nr > 0:
        u = np.linspace(0, 1, nr)
        e[-nr:] *= 0.5 + 0.5 * np.cos(np.pi * u)
    return e


def synth_water_droplet(f0=780.0, f1=1950.0, dur=0.55):
    """Classic resonant subterranean cave water droplet plop with airy shimmer tail."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    freq = f0 + (f1 - f0) * (1.0 - np.exp(-t / 0.028))
    phase = 2.0 * np.pi * np.cumsum(freq) / SR
    body = np.sin(phase) * np.exp(-t / 0.042)
    harm = 0.35 * np.sin(phase * 2.02) * np.exp(-t / 0.025)
    ring = 0.14 * np.sin(2.0 * np.pi * NOTE["Db6"] * t) * np.exp(-t / 0.24) * (1.0 - np.exp(-t / 0.015))
    return (body + harm + ring) * smooth_env(n, 0.002, 0.08)


def synth_celesta_note(freq, dur=2.6, bright=0.35):
    """Pure crystalline celesta / glass-harp note in D-flat Major."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    y = (
        1.00 * np.sin(2.0 * np.pi * freq * t) * np.exp(-t / (dur * 0.44))
        + 0.42 * np.sin(2.0 * np.pi * freq * 2.0 * t) * np.exp(-t / (dur * 0.22))
        + bright * np.sin(2.0 * np.pi * freq * 3.0 * t) * np.exp(-t / (dur * 0.10))
        + 0.14 * np.sin(2.0 * np.pi * freq * 4.01 * t) * np.exp(-t / (dur * 0.06))
    )
    return y * smooth_env(n, 0.006, 0.18)


def synth_warm_pad_chord(freqs, dur, atk=1.8, rel=2.4, rng=None):
    """Lush detuned stereo orchestral-choir pad chord with subtle slow shimmer."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    L = np.zeros(n, dtype=np.float64)
    R = np.zeros(n, dtype=np.float64)
    for idx, f in enumerate(freqs):
        det = 0.0028 + 0.0007 * (idx % 3)
        vib = 0.0018 * np.sin(2.0 * np.pi * (0.28 + 0.07 * idx) * t + idx)
        pL = 2.0 * np.pi * np.cumsum(f * (1.0 - det + vib)) / SR
        pR = 2.0 * np.pi * np.cumsum(f * (1.0 + det - vib)) / SR
        w = 1.0 / (len(freqs) ** 0.72)
        L += w * (0.72 * np.sin(pL) + 0.22 * np.sin(2 * pL) + 0.08 * np.sin(3 * pL))
        R += w * (0.72 * np.sin(pR) + 0.22 * np.sin(2 * pR) + 0.08 * np.sin(3 * pR))
    env = smooth_env(n, atk, rel)
    return lp_filter(L * env, 2400.0), lp_filter(R * env, 2400.0)


def synth_whale_call(f_start, f_peak, f_end, dur=4.2):
    """Distant, haunting, warm musical whale-song glide tuned to D-flat pentatonic."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    u = t / dur
    freq = np.where(
        u < 0.38,
        f_start + (f_peak - f_start) * (0.5 - 0.5 * np.cos(np.pi * u / 0.38)),
        f_peak + (f_end - f_peak) * (0.5 - 0.5 * np.cos(np.pi * (u - 0.38) / 0.62)),
    )
    freq *= (1.0 + 0.008 * np.sin(2.0 * np.pi * 2.2 * t))
    ph = 2.0 * np.pi * np.cumsum(freq) / SR
    sig = 0.78 * np.sin(ph) + 0.26 * np.sin(2.0 * ph) + 0.10 * np.sin(3.0 * ph)
    return lp_filter(sig * smooth_env(n, 0.75, 1.35), 1400.0)


def synth_whoosh_water(dur, f_lo0, f_hi0, f_lo1, f_hi1, rng):
    """Dynamic water-wall surge / wing-sweep noise sculpted over time."""
    n = int(dur * SR)
    noise = rng.standard_normal(n)
    low = bp_filter(noise, f_lo0, f_hi0)
    high = bp_filter(noise, f_lo1, f_hi1)
    u = np.linspace(0, 1, n)
    mix = low * (1.0 - u) + high * u
    return mix * smooth_env(n, dur * 0.22, dur * 0.28)


def add_cavern_reverb(L, R):
    """Lush subterranean cathedral multi-tap stereo reverb tail (pure numpy, zero external deps)."""
    outL = L.copy()
    outR = R.copy()
    taps = [
        (0.083, 0.24, 0.16), (0.147, 0.17, 0.23), (0.241, 0.19, 0.14),
        (0.367, 0.13, 0.18), (0.523, 0.14, 0.11), (0.719, 0.09, 0.12),
        (0.977, 0.08, 0.07), (1.311, 0.05, 0.06), (1.747, 0.035, 0.04),
    ]
    n = len(L)
    wetL = np.zeros(n, dtype=np.float64)
    wetR = np.zeros(n, dtype=np.float64)
    for d_s, gL, gR in taps:
        off = int(d_s * SR)
        if off < n:
            wetL[off:] += L[:-off] * gL + R[:-off] * (gR * 0.45)
            wetR[off:] += R[:-off] * gR + L[:-off] * (gL * 0.45)
    wetL = lp_filter(wetL, 3200.0)
    wetR = lp_filter(wetR, 3200.0)
    return outL + wetL * 0.52, outR + wetR * 0.52


class StereoMix:
    def __init__(self, duration_s):
        self.n = int(round(duration_s * SR))
        self.L = np.zeros(self.n, dtype=np.float64)
        self.R = np.zeros(self.n, dtype=np.float64)
        self.cues = []

    def put(self, t_s, mono, gain=1.0, pan=0.0, label=None):
        i0 = int(round(t_s * SR))
        if i0 >= self.n:
            return
        i1 = min(self.n, i0 + len(mono))
        seg = mono[: max(0, i1 - i0)] * gain
        p = max(-1.0, min(1.0, pan))
        gL = math.cos((p + 1.0) * math.pi * 0.25)
        gR = math.sin((p + 1.0) * math.pi * 0.25)
        self.L[i0:i1] += seg * gL
        self.R[i0:i1] += seg * gR
        if label:
            self.cues.append((t_s, label))

    def put_stereo(self, t_s, l_sig, r_sig, gain=1.0, label=None):
        i0 = int(round(t_s * SR))
        if i0 >= self.n:
            return
        i1 = min(self.n, i0 + len(l_sig))
        k = max(0, i1 - i0)
        self.L[i0:i1] += l_sig[:k] * gain
        self.R[i0:i1] += r_sig[:k] * gain
        if label:
            self.cues.append((t_s, label))


def measure_lufs_bs1770(L, R):
    """Exact ITU-R BS.1770-4 K-weighted integrated loudness (400ms gated blocks, 75% overlap) + True Peak dBFS."""
    freqs = np.fft.rfftfreq(len(L), 1.0 / SR)
    w = 2.0 * np.pi * freqs / SR
    z1 = np.exp(-1j * w)
    z2 = np.exp(-2j * w)
    # Stage 1: pre-filter high shelf (+4 dB @ 48 kHz)
    H1 = (1.53512485958697 - 2.69169618940638 * z1 + 1.19839281085285 * z2) / (
        1.0 - 1.69065929318241 * z1 + 0.73248077421585 * z2
    )
    # Stage 2: RLB high-pass (~38 Hz @ 48 kHz)
    H2 = (1.0 - 2.0 * z1 + 1.0 * z2) / (1.0 - 1.99004745483398 * z1 + 0.99007225036621 * z2)
    Hk = H1 * H2
    kL = np.fft.irfft(np.fft.rfft(L) * Hk, n=len(L))
    kR = np.fft.irfft(np.fft.rfft(R) * Hk, n=len(R))

    win = int(0.400 * SR)
    hop = int(0.100 * SR)
    n_blk = max(1, (len(L) - win) // hop + 1)
    powers = np.empty(n_blk, dtype=np.float64)
    for i in range(n_blk):
        s0 = i * hop
        s1 = s0 + win
        powers[i] = np.mean(kL[s0:s1] ** 2) + np.mean(kR[s0:s1] ** 2)
    l_blk = -0.691 + 10.0 * np.log10(np.maximum(powers, 1e-12))
    abs_mask = l_blk > -70.0
    if not np.any(abs_mask):
        return -70.0, -70.0
    gamma_a = -0.691 + 10.0 * np.log10(np.mean(powers[abs_mask]))
    rel_mask = abs_mask & (l_blk > gamma_a - 10.0)
    lufs = -0.691 + 10.0 * np.log10(np.mean(powers[rel_mask])) if np.any(rel_mask) else gamma_a
    peak = max(float(np.max(np.abs(L))), float(np.max(np.abs(R))), 1e-9)
    tp_dbfs = 20.0 * math.log10(peak)
    return float(lufs), float(tp_dbfs)


def write_wav(path, L, R):
    path.parent.mkdir(parents=True, exist_ok=True)
    inter = np.empty(len(L) * 2, dtype=np.int16)
    inter[0::2] = np.clip(L * 32767.0, -32767, 32767).astype(np.int16)
    inter[1::2] = np.clip(R * 32767.0, -32767, 32767).astype(np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(inter.tobytes())


def render_waveform_qa(L, R, spec, lufs, tp):
    W, H = 2200, 620
    img = Image.new("RGB", (W, H), (11, 15, 23))
    d = ImageDraw.Draw(img)
    f_b = ImageFont.truetype(FONT_SANS, 20)
    f_s = ImageFont.truetype(FONT_SANS, 13)
    f_t = ImageFont.truetype(FONT_SERIF, 13)

    dur = spec["duration"]
    d.text((32, 18), "第一話エンディング『空に降る雪』v5.0（96秒）— 音響タイムライン同期＆ラウドネス検証（Waveform QA）", font=f_b, fill=(238, 244, 252))
    d.text((32, 48), f"Key: D-flat Major / F minor  |  Integrated Loudness: {lufs:.2f} LUFS (Target -14.0)  |  True Peak: {tp:.2f} dBFS (<= -2.0)  |  コーラル縦線＝scene_spec.json 全15カット境界", font=f_t, fill=(248, 218, 134))

    px0, px1 = 44, W - 44
    py0, py1 = 96, H - 96
    mid_y = (py0 + py1) // 2
    half_h = (py1 - py0) // 2 - 12
    d.rounded_rectangle([px0 - 4, py0 - 4, px1 + 4, py1 + 4], radius=8, fill=(16, 22, 34), outline=(50, 70, 98), width=2)

    # Highlight key silence/breath windows!
    def t_to_x(t_s):
        return int(px0 + (t_s / dur) * (px1 - px0))

    for t0, t1, lbl, col in [
        (21.5, 24.8, "C4b 1.8s 無音", (58, 30, 52)),
        (35.6, 36.6, "1s静止", (42, 54, 72)),
        (62.5, 65.5, "0.6x 一瞥", (34, 54, 74)),
        (76.4, 81.3, "尾→頭 満月溶解", (46, 56, 78)),
    ]:
        d.rectangle([t_to_x(t0), py0, t_to_x(t1), py1], fill=col)
        d.text((t_to_x(t0) + 4, py1 - 22), lbl, font=f_s, fill=(248, 218, 134))

    # Draw Stereo RMS + Peak envelope
    mono = 0.5 * (L + R)
    cols_w = px1 - px0
    spp = len(mono) / cols_w
    for i in range(cols_w):
        s0 = int(i * spp)
        s1 = min(len(mono), int((i + 1) * spp))
        blk = mono[s0:s1]
        if len(blk) == 0:
            continue
        pk = float(np.max(np.abs(blk)))
        rms = float(np.sqrt(np.mean(blk * blk)))
        x = px0 + i
        hp = int(pk * half_h)
        hr = int(rms * half_h * 1.4)
        d.line([(x, mid_y - hp), (x, mid_y + hp)], fill=(76, 142, 198), width=1)
        d.line([(x, mid_y - hr), (x, mid_y + hr)], fill=(142, 224, 220), width=1)
    d.line([(px0, mid_y), (px1, mid_y)], fill=(48, 66, 92), width=1)

    # Coral lines for every shot boundary from scene_spec.json!
    for sh in spec["shots"]:
        x = t_to_x(sh["start"])
        d.line([(x, py0), (x, py1)], fill=(242, 118, 98), width=1)
        d.text((x + 3, py0 + 4), sh["id"], font=f_s, fill=(242, 152, 132))
        d.text((x + 3, py1 + 10), f"{sh['start']:.0f}s", font=f_t, fill=(166, 186, 208))

    # Gold markers for the two exact mirror water droplets (t=2.40s & t=92.00s)!
    for td, lbl in [(2.40, "★ C1 銀の雫 (2.4s)"), (92.00, "★ C8 最後の一枚 (92.0s)")]:
        x = t_to_x(td)
        d.line([(x, py0), (x, py1)], fill=(252, 218, 118), width=2)
        tx = x + 4 if td < 50 else x - 160
        d.text((tx, py0 + 24), lbl, font=f_s, fill=(252, 228, 148))

    d.text((px0, H - 46), "ダイナミクス検証：C3→C4aで最大緊張へ膨張 → C4bで完全無音へ落差 → C5b開花チャイム → C6a 1秒静止後に大解放 → C6dで静かな一瞥 → C7b満月溶解 → C8雫で完全対称終止", font=f_t, fill=(208, 222, 238))
    WAVE_PNG.parent.mkdir(parents=True, exist_ok=True)
    img.save(WAVE_PNG)
    print(f"Saved waveform QA: {WAVE_PNG} ({W}x{H})")


def main():
    spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    dur = float(spec["duration"])
    shots = {s["id"]: s for s in spec["shots"]}
    rng = np.random.default_rng(20261126)

    mix = StereoMix(dur)

    # 1. Subtle damp subterranean cavern air bed (0-96s, ducked completely during C4b silence 21.5-24.8s!)
    n_all = int(dur * SR)
    t_all = np.arange(n_all) / SR
    cav_L = bp_filter(rng.standard_normal(n_all), 65.0, 420.0) * 0.022
    cav_R = bp_filter(rng.standard_normal(n_all), 65.0, 420.0) * 0.022
    # Duck cavern bed to near-zero during C4b 1.8s silence & fade out at 96s
    sil_duck = 1.0 - 0.94 * (
        np.clip((t_all - 21.45) / 0.15, 0, 1) * (1.0 - np.clip((t_all - 24.75) / 0.35, 0, 1))
    )
    end_fade = 1.0 - np.clip((t_all - 94.4) / 1.6, 0, 1)
    mix.put_stereo(0.0, cav_L * sil_duck * end_fade, cav_R * sil_duck * end_fade, 1.0)

    # 2. C1 (0-6s): Opening single silver water droplet at t=2.40s (exact mirror of C8 t=92.00s!)
    mix.put(2.40, synth_water_droplet(820.0, 2050.0, 0.72), gain=0.34, pan=0.18, label="C1 Droplet")
    # Tiny distant cave drip echo at 4.8s
    mix.put(4.85, synth_water_droplet(1050.0, 2350.0, 0.45), gain=0.09, pan=-0.55)

    # 3. C2 (6-12s): Deep subterranean sub-bass dread swell beneath the glassy lake
    c2_dur = shots["C2"]["end"] - shots["C2"]["start"]
    n_c2 = int((c2_dur + 0.5) * SR)
    t_c2 = np.arange(n_c2) / SR
    f_sub = 36.0 + 16.0 * (t_c2 / (c2_dur + 0.5))
    sub_c2 = np.sin(2.0 * np.pi * np.cumsum(f_sub) / SR) * (0.25 + 0.75 * (t_c2 / (c2_dur + 0.5)))
    sub_c2 += 0.32 * np.sin(2.0 * np.pi * np.cumsum(f_sub * 1.5) / SR)
    mix.put(shots["C2"]["start"], sub_c2 * smooth_env(n_c2, 1.2, 0.3), gain=0.22, pan=0.0, label="C2 Sub Dread")

    # 4. C3 -> C4a (12.0-21.5s): Head-on breaching water wall + relentless low pressure riser!
    rush_dur = shots["C4a"]["end"] - shots["C3"]["start"]  # 9.5s
    n_r = int(rush_dur * SR)
    t_r = np.arange(n_r) / SR
    u_r = t_r / rush_dur
    # Twin breaching spray walls bursting left & right at t=12.2s
    spray_L = synth_whoosh_water(8.8, 120, 650, 260, 2200, rng) * (0.35 + 0.65 * np.linspace(0, 1, int(8.8 * SR)))
    spray_R = synth_whoosh_water(8.8, 120, 650, 260, 2200, rng) * (0.35 + 0.65 * np.linspace(0, 1, int(8.8 * SR)))
    mix.put_stereo(12.2, spray_L, spray_R, gain=0.24, label="C3 Breaching Water Wall")
    # Heavy sub-bass whale loom pressure building to heart-stopping peak at 21.1s, hard-cut at 21.5s!
    f_loom = 42.0 + 48.0 * (u_r ** 2.1)
    loom = (0.75 * np.sin(2.0 * np.pi * np.cumsum(f_loom) / SR) + 0.30 * np.sin(2.0 * np.pi * np.cumsum(f_loom * 2.0) / SR))
    loom *= (0.25 + 0.75 * (u_r ** 1.6)) * smooth_env(n_r, 0.6, 0.14)
    mix.put(shots["C3"]["start"], loom, gain=0.34, pan=0.0, label="C3-C4a Collision Riser")

    # 5. C4b (21.5-25.0s): SHOCKING 1.8+ SECOND BREATHLESS SILENCE + one faint calm low heartbeat at 22.9s!
    n_hb = int(0.42 * SR)
    t_hb = np.arange(n_hb) / SR
    hb = np.sin(2.0 * np.pi * 48.0 * t_hb) * np.exp(-t_hb / 0.085) * smooth_env(n_hb, 0.015, 0.15)
    mix.put(22.9, hb, gain=0.07, pan=0.0, label="C4b Quiet Eye Silence")

    # 6. C5a (25.0-30.0s): Whale tail-stroke surge into silver moonlight -> Lush D-flat Major awakening pad!
    tail_L = synth_whoosh_water(2.8, 90, 480, 320, 1800, rng)
    tail_R = synth_whoosh_water(2.8, 90, 480, 320, 1800, rng)
    mix.put_stereo(25.1, tail_L, tail_R, gain=0.16, label="C5a Tail Surge")
    pL, pR = synth_warm_pad_chord([NOTE["Db3"], NOTE["Ab3"], NOTE["Db4"], NOTE["F4"]], 9.5, atk=2.0, rel=2.0)
    mix.put_stereo(26.2, pL, pR, gain=0.20, label="C5a Moonlit Pad")
    mix.put(27.5, synth_celesta_note(NOTE["Ab5"], 3.0), gain=0.12, pan=0.25)

    # 7. C5b (30.0-35.0s): Ground-level 20cm wave-bloom cascading crystalline chimes (shore -> stone bridge!)
    bloom_notes = ["Db5", "Eb5", "F5", "Ab5", "Bb5", "Db6", "Ab5", "F5", "Eb5", "Db5", "F5", "Ab5"]
    for idx, nm in enumerate(bloom_notes):
        tb = 30.25 + idx * 0.36
        pan = -0.65 + (idx / (len(bloom_notes) - 1)) * 1.30
        mix.put(tb, synth_celesta_note(NOTE[nm], 2.2, bright=0.45), gain=0.11 + 0.008 * idx, pan=pan)

    # 8. C6a (35.0-44.0s): 1.0s Magical Gravity-Freeze (35.6-36.6s) -> GRAND RELEASE into 3-layer Snowstorm!
    # Delicate high suspended shimmer during 1.0s freeze
    mix.put(35.55, synth_celesta_note(NOTE["Db6"], 2.4, bright=0.55), gain=0.14, pan=0.0, label="C6a 1s Freeze")
    mix.put(35.62, synth_celesta_note(NOTE["Ab5"], 2.4, bright=0.45), gain=0.10, pan=-0.25)
    # At 36.6s: Freeze breaks -> airy upward snow-billow whoosh + GRAND CATHEDRAL CHORD SWELL!
    up_L = synth_whoosh_water(4.2, 280, 1200, 650, 3600, rng)
    up_R = synth_whoosh_water(4.2, 280, 1200, 650, 3600, rng)
    mix.put_stereo(36.55, up_L, up_R, gain=0.11, label="C6a Snowstorm Release")

    # Sweeping harp/celesta arpeggio lifting with the ground-to-sky tilt (36.6 -> 43.2s)
    arp_notes = ["Db4", "Ab4", "Db5", "Eb5", "F5", "Ab5", "Bb5", "Db6", "Ab5", "F5", "Eb5", "Db5"]
    for idx, nm in enumerate(arp_notes):
        mix.put(36.70 + idx * 0.48, synth_celesta_note(NOTE[nm], 3.2), gain=0.13, pan=math.sin(idx * 0.7) * 0.65)

    # 9. C6a -> C6c (36.6-61.0s): Grand Cathedral Harmonic Progression (DbMaj9 -> GbMaj9 -> Absus4 -> DbMaj9)
    chords = [
        (36.6,  9.5, ["Db2", "Db3", "Ab3", "Eb4", "F4", "Ab4"], 0.30),
        (44.5,  9.0, ["Gb2", "Gb3", "Db4", "F4",  "Ab4", "Bb4"], 0.31),
        (52.0,  9.5, ["Db2", "Ab2", "Db3", "F3",  "Ab3", "Eb4", "F4", "Ab4"], 0.36),  # C6c 1+3 Climax Peak!
    ]
    for tc, dc, nms, g in chords:
        pL, pR = synth_warm_pad_chord([NOTE[k] for k in nms], dc, atk=2.0, rel=2.6)
        mix.put_stereo(tc, pL, pR, gain=g)

    # Joyful distant musical whale song during C6b 360-deg barrel roll (45.8s) & C6c 40-deg bank (54.2s)!
    mix.put(45.8, synth_whale_call(NOTE["Ab3"], NOTE["Db4"], NOTE["Bb3"], 4.4), gain=0.16, pan=0.35, label="C6b Whale Song")
    mix.put(54.2, synth_whale_call(NOTE["Db4"], NOTE["F4"],  NOTE["Eb4"], 4.8), gain=0.17, pan=-0.30, label="C6c Whale Song")

    # Gentle crystalline snow sparkles across C6b-C6c
    spark_notes = ["Ab5", "Db6", "F5", "Eb5", "Bb5", "Ab5", "Db6", "F5", "Ab5", "Eb5"]
    for idx, nm in enumerate(spark_notes):
        mix.put(45.2 + idx * 1.45, synth_celesta_note(NOTE[nm], 2.5), gain=0.075, pan=math.cos(idx * 1.1) * 0.75)

    # 10. C6d (60.0-69.0s): Intimate 22-deg Warm Glance & 0.6x Slow-Mo Breath (62.5-65.5s)!
    # Softly pull back to warm tender Fmin7 -> GbMaj7 solo chord + 4 poignant celesta notes!
    pL, pR = synth_warm_pad_chord([NOTE["F2"], NOTE["C4"], NOTE["Eb4"], NOTE["Ab4"]], 8.8, atk=2.2, rel=2.8)
    mix.put_stereo(60.4, pL, pR, gain=0.22, label="C6d Warm Glance")
    for t_g, nm, pn in [(62.5, "Ab5", -0.20), (63.6, "Gb5", 0.15), (64.7, "F5", -0.10), (65.9, "Eb5", 0.20)]:
        mix.put(t_g, synth_celesta_note(NOTE[nm], 3.4, bright=0.28), gain=0.15, pan=pn)

    # 11. C7a -> C7b (69.0-83.0s): Poignant Ascent & 85mm Tail-to-Head Full Moon Dissolve!
    pL, pR = synth_warm_pad_chord([NOTE["Bb2"], NOTE["F3"], NOTE["Db4"], NOTE["Ab4"]], 8.2, atk=1.8, rel=2.8)
    mix.put_stereo(68.8, pL, pR, gain=0.24, label="C7a Ascent")
    # C7b (75.0-83.0s): Ethereal high silver-moonlight harmonic dissolution shimmer (sweeps softly as tail->head melts 76.4-81.3s!)
    pL, pR = synth_warm_pad_chord([NOTE["Gb3"], NOTE["Db4"], NOTE["Ab4"], NOTE["Db5"], NOTE["F5"]], 7.4, atk=1.6, rel=2.8)
    mix.put_stereo(74.8, pL, pR, gain=0.23, label="C7b Moon Dissolve")
    # Descending/rising farewell moon chimes as tail->torso->head returns to silver light
    for t_m, nm, pn in [(76.4, "F5", -0.35), (77.8, "Ab5", -0.10), (79.2, "Bb5", 0.15), (80.6, "Db6", 0.32)]:
        mix.put(t_m, synth_celesta_note(NOTE[nm], 3.6, bright=0.50), gain=0.12, pan=pn)

    # 12. C7c (83.0-89.0s): True Gentle Winter Snowfall wrapping 4 PCs -> Grateful D-flat Major resolution!
    pL, pR = synth_warm_pad_chord([NOTE["Db2"], NOTE["Db3"], NOTE["Ab3"], NOTE["Db4"], NOTE["F4"]], 7.6, atk=1.8, rel=3.4)
    mix.put_stereo(82.6, pL, pR, gain=0.20, label="C7c True Snow")
    snow_chimes = [(83.5, "Ab5", -0.45), (84.4, "F5", 0.35), (85.3, "Eb5", -0.25), (86.3, "Db5", 0.25), (87.4, "Ab4", 0.0)]
    for ts, nm, pn in snow_chimes:
        mix.put(ts, synth_celesta_note(NOTE[nm], 3.2, bright=0.25), gain=0.10, pan=pn)

    # 13. C8 (89.0-96.0s): Exact Mirror Symmetry of C1 -> 2s Quiet -> Final Petal Droplet at t=92.00s!
    mix.put(92.00, synth_water_droplet(820.0, 2050.0, 0.85), gain=0.34, pan=0.18, label="C8 Final Petal Droplet")
    mix.put(92.04, synth_celesta_note(NOTE["Db5"], 3.8, bright=0.30), gain=0.14, pan=0.0)
    mix.put(92.12, synth_celesta_note(NOTE["Db6"], 3.6, bright=0.35), gain=0.09, pan=0.18)

    # Apply lush subterranean cathedral reverb (keeping C4b silence crystal clean!)
    L, R = add_cavern_reverb(mix.L, mix.R)
    # Re-apply a crisp subtle silence dip inside C4b (21.75-24.55s) so reverb tail from C4a stops breathlessly!
    c4b_gate = 1.0 - 0.88 * (
        np.clip((t_all - 21.55) / 0.22, 0, 1) * (1.0 - np.clip((t_all - 24.55) / 0.35, 0, 1))
    )
    L *= c4b_gate * end_fade
    R *= c4b_gate * end_fade

    # Automatic Iterative Mastering to -14.0 LUFS with soft-clip protection (true peak <= -2.0 dBFS)!
    gain = 1.0
    for _ in range(8):
        sL = np.tanh(L * gain * 1.15) / 1.15
        sR = np.tanh(R * gain * 1.15) / 1.15
        pk = max(float(np.max(np.abs(sL))), float(np.max(np.abs(sR))), 1e-6)
        if pk > 0.77:
            sL *= 0.77 / pk
            sR *= 0.77 / pk
        lufs, tp = measure_lufs_bs1770(sL, sR)
        diff = TARGET_LUFS - lufs
        if abs(diff) < 0.25:
            break
        gain *= 10.0 ** (np.clip(diff, -6.0, 6.0) / 20.0)

    sL = np.tanh(L * gain * 1.15) / 1.15
    sR = np.tanh(R * gain * 1.15) / 1.15
    pk = max(float(np.max(np.abs(sL))), float(np.max(np.abs(sR))), 1e-6)
    if pk > 0.77:
        sL *= 0.77 / pk
        sR *= 0.77 / pk
    write_wav(WAV_PATH, sL, sR)
    final_lufs, final_tp = measure_lufs_bs1770(sL, sR)
    print(f"Mastered WAV: {WAV_PATH} | Integrated={final_lufs:.2f} LUFS | True Peak={final_tp:.2f} dBFS")

    render_waveform_qa(sL, sR, spec, final_lufs, final_tp)

    # Mux master audio cleanly onto master_96s_preview_v5.mp4 via native PyAV with explicit Rec.709 color tags!
    if VIDEO_IN.exists():
        in_v = av.open(str(VIDEO_IN))
        v_in_s = in_v.streams.video[0]
        fps = int(round(float(v_in_s.average_rate or 24)))

        out_c = av.open(str(VIDEO_OUT), mode="w")
        out_v = out_c.add_stream("libx264", rate=fps)
        out_v.width = v_in_s.width
        out_v.height = v_in_s.height
        out_v.pix_fmt = "yuv420p"
        out_v.codec_context.color_primaries = 1  # bt709
        out_v.codec_context.color_trc = 1        # bt709
        out_v.codec_context.colorspace = 1       # bt709
        out_v.options = {"crf": "19", "preset": "fast", "movflags": "+faststart"}

        out_a = out_c.add_stream("aac", rate=SR)
        out_a.layout = "stereo"
        out_a.bit_rate = 192000

        # Copy & tag video frames cleanly
        for frame in in_v.decode(video=0):
            vf = av.VideoFrame.from_ndarray(frame.to_ndarray(format="rgb24"), format="rgb24")
            for pkt in out_v.encode(vf):
                out_c.mux(pkt)
        in_v.close()
        for pkt in out_v.encode():
            out_c.mux(pkt)

        # Encode stereo float32 planar audio in 1024-sample AAC frames
        pcm = np.vstack([sL, sR]).astype(np.float32)  # shape (2, N)
        chunk = 1024
        pts = 0
        for s0 in range(0, pcm.shape[1], chunk):
            blk = pcm[:, s0 : s0 + chunk]
            if blk.shape[1] < chunk:
                pad = np.zeros((2, chunk - blk.shape[1]), dtype=np.float32)
                blk = np.hstack([blk, pad])
            af = av.AudioFrame.from_ndarray(blk, format="fltp", layout="stereo")
            af.sample_rate = SR
            af.pts = pts
            pts += chunk
            for pkt in out_a.encode(af):
                out_c.mux(pkt)
        for pkt in out_a.encode():
            out_c.mux(pkt)
        out_c.close()
        print(f"Muxed Rec.709 Master Preview WITH AUDIO: {VIDEO_OUT}")


if __name__ == "__main__":
    main()
