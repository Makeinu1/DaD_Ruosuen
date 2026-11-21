"""仮曲『空に降る雪』v8 temp (75s, 64 BPM, D major).

Hit points follow v8_timeline.json:
  beat 18 浮上 / 30 視線（全休止）/ 39 点火 / 45 タイトル溜め / 48 離陸＝主題 / 64 退場 / 70 帰還 / 76 終幕
Renders to MIDI; audio is rendered with FluidSynth + FluidR3_GM afterwards.
"""
import random
import sys

import pretty_midi as pm

BPM = 64
SPB = 60.0 / BPM  # seconds per beat (0.9375)
random.seed(1223)

mid = pm.PrettyMIDI(initial_tempo=BPM)
INST = {}


def inst(name, program, is_drum=False):
    if name not in INST:
        INST[name] = pm.Instrument(program=program, is_drum=is_drum, name=name)
        mid.instruments.append(INST[name])
    return INST[name]


def n(name, program, pitch, beat, dur, vel, human=True):
    i = inst(name, program)
    p = pm.note_name_to_number(pitch) if isinstance(pitch, str) else pitch
    jitter = random.uniform(-0.012, 0.012) if human else 0.0
    v = max(1, min(127, int(vel + (random.randint(-4, 4) if human else 0))))
    s = max(0.0, beat * SPB + jitter)
    i.notes.append(pm.Note(velocity=v, pitch=p, start=s, end=s + dur * SPB))


def chord(name, program, pitches, beat, dur, vel, roll=0.0):
    for k, p in enumerate(pitches):
        n(name, program, p, beat + k * roll, dur - k * roll, vel)


PIANO, CELESTA, GLOCK, HARP = 0, 8, 9, 46
STR, STR_SLOW, VIOLIN, CBASS, TIMP = 48, 49, 40, 43, 47
CHOIR, PAD = 52, 89

# ---------- motif (piano) ----------
MOTIF = [(0, "F#5", 1), (1, "A5", 1), (2, "E5", 2), (4, "D5", 1), (5, "E5", 0.5), (5.5, "F#5", 0.5), (6, "A4", 2)]


def motif(at, vel=48, octave_shift=0):
    for b, p, d in MOTIF:
        nn = pm.note_name_to_number(p) + 12 * octave_shift
        n("piano", PIANO, nn, at + b, d + 0.6, vel)


# ---------- 0–12 intro: silence -> piano motif, open-fifth pad ----------
chord("pad", PAD, ["D4", "A4"], 2, 10, 34)
motif(1.0, vel=46)
chord("piano", PIANO, ["B4", "D5", "F#5"], 9, 3, 38, roll=0.25)

# ---------- 12–18 shadow: low drone ----------
n("cbass", CBASS, "D2", 12, 18, 52)
chord("strings_low", STR_SLOW, ["D3", "A3"], 13, 5, 40)
chord("pad", PAD, ["D4", "A4", "E5"], 12, 6, 30)

# ---------- 18–30 breach -> approach -> heigei: crescendo ----------
for k in range(16):  # soft timpani roll into the breach
    n("timpani", TIMP, "D2", 18 + k * 0.125, 0.12, 30 + k * 3)
prog_a = [(18, ["B2", "D3", "F#3", "B3"], 56), (22, ["G2", "D3", "G3", "B3"], 70), (26, ["F#2", "D3", "A3", "D4"], 88)]
for b, ps, v in prog_a:
    chord("strings", STR, ps, b, 4, v)
n("cbass", CBASS, "B1", 18, 4, 60); n("cbass", CBASS, "G1", 22, 4, 70); n("cbass", CBASS, "F#1", 26, 4, 84)
n("violin", VIOLIN, "F#5", 22, 4, 62)
n("violin", VIOLIN, "A5", 26, 3.6, 84)

# ---------- 30–34.5 eye: everything stops, one high line ----------
n("violin", VIOLIN, "A6", 30.15, 4.2, 40)
n("piano", PIANO, "D6", 31.0, 3.0, 36)

# ---------- 34.5–39 turn-back: suspended chord rising ----------
chord("strings_slow", STR_SLOW, ["A2", "E3", "A3", "D4"], 34.5, 4.5, 46)
chord("pad", PAD, ["A3", "D4", "E4"], 34.5, 4.5, 40)
for k, p in enumerate(["A2", "D3", "E3", "A3", "D4", "E4"]):
    n("harp", HARP, p, 35.5 + k * 0.5, 1.5, 44)

# ---------- 39 ignition ----------
for k, p in enumerate(["D6", "F#6", "A6", "D7"]):
    n("celesta", CELESTA, p, 39 + k * 0.25, 1.2, 78)
n("glock", GLOCK, "A6", 39, 1.5, 70)
chord("strings", STR, ["D3", "A3", "D4", "F#4"], 39, 6, 58)
n("cbass", CBASS, "D2", 39, 6, 58)
scale = ["D3", "E3", "F#3", "G3", "A3", "B3", "C#4", "D4", "E4", "F#4", "G4", "A4", "B4", "C#5", "D5", "E5", "F#5", "A5", "D6"]
for k, p in enumerate(scale):  # harp glissando 41–43
    n("harp", HARP, p, 41 + k * (2.0 / len(scale)), 1.2, 50 + k)
for k, p in enumerate(["E4", "G4", "B4", "D5", "A4", "C#5", "E5", "A5"]):  # rising arpeggio 43–45
    n("piano", PIANO, p, 43 + k * 0.25, 1.0, 50 + k * 2)

# ---------- 45–48 title: Gsus2 hold, then upward run ----------
chord("strings_slow", STR_SLOW, ["G2", "D3", "A3", "D4"], 45, 3, 52)
chord("pad", PAD, ["G3", "A3", "D4"], 45, 3, 44)
n("celesta", CELESTA, "A6", 45.5, 1.5, 54)
n("celesta", CELESTA, "D7", 46.5, 1.0, 50)
for k, p in enumerate(["D4", "F#4", "A4", "D5", "F#5", "A5", "D6", "F#6"]):
    n("harp", HARP, p, 47 + k * 0.125, 1.0, 56 + k * 3)

# ---------- 48–64 climax theme ----------
CHORDS = [(48, "D2", ["D3", "A3", "F#4", "A4"]), (52, "C#2", ["C#3", "A3", "E4", "A4"]),
          (56, "B1", ["B2", "F#3", "D4", "A4"]), (60, "G1", ["G2", "D3", "B3", "D4"]), (62, "A1", ["A2", "E3", "C#4", "E4"])]
for b, bass, ps in CHORDS:
    d = 2 if b >= 60 else 4
    n("cbass", CBASS, bass, b, d, 90)
    chord("strings", STR, ps, b, d, 86)
    if b >= 56:
        chord("choir", CHOIR, ps[1:], b, d, 70)
for b in (48, 56):
    n("timpani", TIMP, "D2" if b == 48 else "B1", b, 2, 92)
MELODY = [(48, "D5", 1), (49, "F#5", 1), (50, "A5", 2), (52, "E5", 1), (53, "A5", 1), (54, "C#6", 2),
          (56, "D6", 2), (58, "B5", 1), (59, "A5", 1), (60, "G5", 1), (61, "F#5", 1), (62, "E5", 1), (63, "A5", 1)]
for b, p, d in MELODY:
    n("violin", VIOLIN, p, b, d, 96)
    n("piano", PIANO, p, b, d, 70)
    n("piano", PIANO, pm.note_name_to_number(p) - 12, b, d, 58)
for bar0, ps in [(48, ["D4", "A4", "D5", "F#5"]), (52, ["C#4", "A4", "C#5", "E5"]), (56, ["B3", "F#4", "B4", "D5"]), (60, ["G3", "D4", "G4", "B4"])]:
    for k in range(8):  # eighth-note piano arpeggio
        n("piano", PIANO, ps[k % 4], bar0 + k * 0.5, 0.6, 52)

# ---------- 64–70 exit: fragments, decrescendo ----------
for b, bass, ps, v in [(64, "F#1", ["F#2", "D3", "A3"], 70), (66, "G1", ["G2", "D3", "B3"], 56), (68, "E1", ["E2", "B2", "G3", "D4"], 44)]:
    n("cbass", CBASS, bass, b, 2, v)
    chord("strings_slow", STR_SLOW, ps, b, 2, v)
chord("choir", CHOIR, ["F#3", "D4", "A4"], 64, 2.5, 52)
for b, p, d, v in [(64, "F#5", 2, 72), (66, "E5", 2, 60), (68, "D5", 2, 48)]:
    n("violin", VIOLIN, p, b, d, v)

# ---------- 70–76 aftermath: motif returns ----------
chord("pad", PAD, ["D4", "A4"], 70, 6, 34)
chord("strings_slow", STR_SLOW, ["G2", "D3", "B3"], 70, 3, 30)
chord("strings_slow", STR_SLOW, ["D3", "A3", "F#4"], 73, 3, 30)
motif(70.5, vel=44)

# ---------- 76–80 end card: Dadd9 fades ----------
chord("piano", PIANO, ["D3", "A3", "E4", "F#4", "A4"], 76, 4, 46, roll=0.12)
chord("pad", PAD, ["D4", "E4", "A4"], 76, 4, 30)
n("celesta", CELESTA, "E6", 77, 2.5, 40)

out = sys.argv[1] if len(sys.argv) > 1 else "v8_temp.mid"
mid.write(out)
print("wrote", out, "length", round(mid.get_end_time(), 2), "s")
