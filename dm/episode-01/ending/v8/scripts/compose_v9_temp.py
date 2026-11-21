"""仮曲 v9『空に降る雪』(80s, 60 BPM = 1 beat per second).

Emotion line v9:
  0-6   安堵   no music (water drops added in post)
  6-14  違和感 low drone
  14-22 驚愕   breach hit, swell
  22-30 警戒   ambiguous harmony, low brass motif, pulse, crescendo
  30-34 一瞥   TOTAL STOP; one high string note only
  34-40 反転   bVI-bVII-I lift into D major
  40-48 点火・開花 celesta, choir, harp, title hold
  48-64 自由遊泳 main theme = whale motif in major
  64-72 別れ   fragments, decrescendo
  72-80 静寂   piano motif, last chord, silence
Whale motif: minor/low "question" D-F-E-A(down) -> major/high "answer" D-F#-E-A(up).
"""
import random
import sys

import pretty_midi as pm

random.seed(1223)
mid = pm.PrettyMIDI(initial_tempo=60)
INST = {}


def n(name, program, pitch, beat, dur, vel, human=True):
    if name not in INST:
        INST[name] = pm.Instrument(program=program, name=name)
        mid.instruments.append(INST[name])
    p = pm.note_name_to_number(pitch) if isinstance(pitch, str) else pitch
    j = random.uniform(-0.01, 0.01) if human else 0.0
    v = max(1, min(127, int(vel + (random.randint(-3, 3) if human else 0))))
    s = max(0.0, beat + j)
    INST[name].notes.append(pm.Note(velocity=v, pitch=p, start=s, end=s + dur))


def chord(name, program, pitches, beat, dur, vel, roll=0.0):
    for k, p in enumerate(pitches):
        n(name, program, p, beat + k * roll, dur - k * roll, vel)


PIANO, CELESTA, GLOCK, HARP, TIMP = 0, 8, 9, 46, 47
STR, STR_SLOW, TREM, VIOLIN, CELLO, CBASS = 48, 49, 44, 40, 42, 43
BRASS, HORN, TROMB, CHOIR, PAD = 61, 60, 57, 52, 89

# 6-14 違和感: drone
n("cbass", CBASS, "D1", 7, 7.5, 50)
chord("trem", TREM, ["D2", "A2"], 8, 6.5, 34)

# 14-22 驚愕: breach
for k in range(16):
    n("timp", TIMP, "D2", 13 + k * 0.0625, 0.07, 30 + k * 4)
chord("tromb", TROMB, ["D2", "A2", "D3", "F3"], 14, 3.5, 92)
n("cbass", CBASS, "D1", 14, 8, 72)
n("horn", HORN, "F3", 16, 1.2, 70); n("horn", HORN, "E3", 17.2, 2.0, 62)   # low "call"
chord("str", STR, ["D3", "F3", "A3"], 18, 2, 60)
chord("str", STR, ["Bb2", "F3", "Bb3", "D4"], 20, 2, 66)

# 22-30 警戒: ambiguous harmony + low brass motif + pulse, crescendo
AMB = [(22, ["D2", "A2", "D3", "F3"]), (24, ["Bb1", "F2", "Bb2", "D3"]), (26, ["G1", "D2", "Bb2", "E3"]), (28, ["A1", "E2", "A2", "Bb2", "D3"])]
for k, (b, ps) in enumerate(AMB):
    chord("str", STR, ps, b, 2, 64 + k * 9)
    n("cbass", CBASS, ps[0], b, 2, 70 + k * 8)
for k in range(16):  # pulse in eighths: timpani + staccato cello
    b = 22 + k * 0.5
    n("timp", TIMP, "D2" if k % 4 != 3 else "A1", b, 0.3, 54 + k * 3)
    n("cello", CELLO, "D2", b, 0.22, 50 + k * 3)
MOTIF_MINOR = [(0, "D3", 1), (1, "F3", 1), (2, "E3", 1), (3, "A2", 1)]
for b, p, d in MOTIF_MINOR:
    n("brass", BRASS, p, 22 + b, d, 78)
for b, p, d in [(0, "E3", 1), (1, "G3", 1), (2, "F3", 1), (3, "Bb2", 1)]:
    n("brass", BRASS, p, 26 + b, d, 92)
for k in range(16):  # timpani roll into the cut
    n("timp", TIMP, "A1", 29 + k * 0.0625, 0.07, 70 + k * 3)

# 30-34 一瞥: everything stops; one high string, unresolved (E over nothing)
n("violin", VIOLIN, "E6", 30.25, 3.8, 34)

# 34-40 反転: bVI - bVII - I into D major
chord("str", STR, ["Bb2", "F3", "Bb3", "D4"], 34, 2, 58)
chord("str", STR, ["C3", "G3", "C4", "E4"], 36, 2, 68)
chord("str", STR, ["D3", "A3", "D4", "F#4"], 38, 2, 78)
chord("horn", HORN, ["D3", "F#3", "A3"], 38, 2, 74)
n("cbass", CBASS, "Bb1", 34, 2, 60); n("cbass", CBASS, "C2", 36, 2, 66); n("cbass", CBASS, "D2", 38, 2, 72)
gl = ["D3", "E3", "F#3", "G3", "A3", "B3", "C#4", "D4", "E4", "F#4", "G4", "A4", "B4", "C#5", "D5"]
for k, p in enumerate(gl):
    n("harp", HARP, p, 34.2 + k * (1.6 / len(gl)), 1.2, 46 + k)
for k, p in enumerate(gl):
    n("harp", HARP, p, 37.0 + k * (1.0 / len(gl)), 1.0, 50 + k)

# 40-48 点火・開花
for k, p in enumerate(["D6", "F#6", "A6", "D7", "A6", "F#6"]):
    n("celesta", CELESTA, p, 40 + k * 0.25, 1.0, 76)
n("glock", GLOCK, "A6", 40, 1.5, 66)
chord("pad", PAD, ["D4", "E4", "A4"], 40, 4.5, 46)
chord("choir", CHOIR, ["D4", "F#4", "A4"], 42, 2.5, 52)
chord("choir", CHOIR, ["G3", "D4", "A4"], 44.5, 3.5, 62)          # title hold: Gsus2
chord("str_slow", STR_SLOW, ["G2", "D3", "A3", "D4"], 44.5, 3.5, 58)
n("celesta", CELESTA, "A6", 45.0, 1.2, 52); n("celesta", CELESTA, "E7", 46.0, 1.0, 48)
for k, p in enumerate(["D4", "F#4", "A4", "D5", "F#5", "A5", "D6", "F#6"]):
    n("harp", HARP, p, 47 + k * 0.125, 1.0, 56 + k * 3)

# 48-64 自由遊泳: theme (whale motif in major, rising answer)
CH = [(48, "D2", ["D3", "A3", "F#4"]), (52, "B1", ["B2", "F#3", "D4"]), (56, "G1", ["G2", "D3", "B3"]), (60, "A1", ["A2", "E3", "C#4"]),
      ]
for b, bass, ps in CH:
    n("cbass", CBASS, bass, b, 4, 84)
    chord("str", STR, ps, b, 4, 80)
    chord("choir", CHOIR, ps, b, 4, 60 if b < 56 else 72)
for b in (48, 56):
    n("timp", TIMP, "D2" if b == 48 else "G1", b, 2, 84)
MEL = [(48, "D5", 1), (49, "F#5", 1), (50, "E5", 1), (51, "A5", 1),
       (52, "B5", 2), (54, "A5", 1), (55, "F#5", 1),
       (56, "G5", 1), (57, "A5", 1), (58, "B5", 1), (59, "D6", 1),
       (60, "C#6", 2), (62, "A5", 2)]
for b, p, d in MEL:
    n("violin", VIOLIN, p, b, d, 94)
    n("piano", PIANO, pm.note_name_to_number(p) - 12, b, d, 60)
for bar0, ps in [(48, ["D4", "A4", "D5", "F#5"]), (52, ["B3", "F#4", "B4", "D5"]), (56, ["G3", "D4", "G4", "B4"]), (60, ["A3", "E4", "A4", "C#5"])]:
    for k in range(8):
        n("harp", HARP, ps[k % 4], bar0 + k * 0.5, 0.8, 50)

# 64-72 別れ: fragments, decrescendo
for b, bass, ps, v in [(64, "G1", ["G2", "D3", "B3"], 66), (66, "F#1", ["F#2", "D3", "A3"], 56), (68, "E1", ["E2", "B2", "G3", "D4"], 46), (70, "A1", ["A2", "D3", "E3"], 36)]:
    n("cbass", CBASS, bass, b, 2, v)
    chord("str_slow", STR_SLOW, ps, b, 2, v)
for b, p, d, v in [(64, "D5", 1, 70), (65, "F#5", 1, 64), (66, "E5", 2, 58), (69, "A5", 2.5, 44)]:
    n("violin", VIOLIN, p, b, d, v)

# 72-80 静寂: piano motif, last chord, then silence
for b, p in [(73, "D5"), (74, "F#5"), (75, "E5"), (76, "A5")]:
    n("piano", PIANO, p, b, 1.8, 40)
chord("piano", PIANO, ["D3", "A3", "E4", "F#4"], 77, 2.6, 36, roll=0.15)
chord("pad", PAD, ["D4", "A4"], 72, 6.5, 26)

out = sys.argv[1] if len(sys.argv) > 1 else "v9_temp.mid"
mid.write(out)
print("wrote", out, round(mid.get_end_time(), 2), "s")
