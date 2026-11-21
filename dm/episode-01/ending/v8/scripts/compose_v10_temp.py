"""仮曲 v10『空に降る雪』(80s, 60 BPM = 1 beat per second). Follows v10-shotlist.md.

Hit points: 14 浮上 / 21 接近(月光の遮り) / 28 一瞥=全休止 / 32 背面ロール=解放 / 37 点火
           44.5 花びら静止 / 47 向き直り / 48 主題 / 57 大渦 / 63 昇天 / 68 タイトル回収 / 73 静寂 / 77 最後の一枚
Whale motif: minor & low "question" D-F-E-A(down) on approach -> major & high "answer" D-F#-E-A(up) in free swim.
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


def gliss(name, program, notes, start, span, vel0, step=1):
    for k, p in enumerate(notes):
        n(name, program, p, start + k * (span / len(notes)), 1.0, vel0 + k * step)


PIANO, CELESTA, GLOCK, HARP, TIMP = 0, 8, 9, 46, 47
STR, STR_SLOW, TREM, VIOLIN, CELLO, CBASS = 48, 49, 44, 40, 42, 43
BRASS, HORN, TROMB, CHOIR, PAD = 61, 60, 57, 52, 89
DMAJ = ["D3", "E3", "F#3", "G3", "A3", "B3", "C#4", "D4", "E4", "F#4", "G4", "A4", "B4", "C#5", "D5", "E5", "F#5", "A5", "D6"]

# C02-C03 6-14 drone
n("cbass", CBASS, "D1", 6.5, 7.5, 48)
chord("trem", TREM, ["D2", "A2"], 8, 6, 32)

# C04-C05 14-21 breach & ascent
for k in range(16):
    n("timp", TIMP, "D2", 13 + k * 0.0625, 0.07, 30 + k * 4)
chord("tromb", TROMB, ["D2", "A2", "D3", "F3"], 14, 3.5, 90)
n("cbass", CBASS, "D1", 14, 7, 70)
n("horn", HORN, "F3", 16, 1.2, 68); n("horn", HORN, "E3", 17.2, 2.0, 60)
chord("str", STR, ["D3", "F3", "A3"], 18, 1.5, 58)
chord("str", STR, ["Bb2", "F3", "Bb3", "D4"], 19.5, 1.5, 64)

# C06-C07 21-28 approach: ambiguous harmony, motif, pulse, crescendo
AMB = [(21, ["D2", "A2", "D3", "F3"]), (23, ["Bb1", "F2", "Bb2", "D3"]), (25, ["G1", "D2", "Bb2", "E3"]), (27, ["A1", "E2", "A2", "Bb2", "D3"])]
for k, (b, ps) in enumerate(AMB):
    chord("str", STR, ps, b, 2, 62 + k * 9)
    n("cbass", CBASS, ps[0], b, 2, 68 + k * 8)
for k in range(14):
    b = 21 + k * 0.5
    n("timp", TIMP, "D2" if k % 4 != 3 else "A1", b, 0.3, 52 + k * 3)
    n("cello", CELLO, "D2", b, 0.22, 48 + k * 3)
for b, p in [(21, "D3"), (22, "F3"), (23, "E3"), (24, "A2")]:
    n("brass", BRASS, p, b, 1, 76)
for b, p in [(25, "E3"), (26, "G3"), (27, "F3")]:
    n("brass", BRASS, p, b, 1, 92)
for k in range(16):
    n("timp", TIMP, "A1", 27 + k * 0.0625, 0.07, 70 + k * 3)

# C08 28-32 glance: total stop, one unresolved high string
n("violin", VIOLIN, "E6", 28.2, 3.8, 34)

# C09-C10 32-37 roll -> release: bVI - bVII - I
chord("str", STR, ["Bb2", "F3", "Bb3", "D4"], 32, 1.6, 60)
chord("str", STR, ["C3", "G3", "C4", "E4"], 33.6, 1.6, 68)
chord("str", STR, ["D3", "A3", "D4", "F#4"], 35.2, 1.8, 78)
chord("horn", HORN, ["D3", "F#3", "A3"], 35.2, 1.8, 72)
n("cbass", CBASS, "Bb1", 32, 1.6, 62); n("cbass", CBASS, "C2", 33.6, 1.6, 66); n("cbass", CBASS, "D2", 35.2, 1.8, 72)
gliss("harp", HARP, DMAJ[:15], 32.2, 1.4, 46)
gliss("harp", HARP, DMAJ[:15], 35.3, 1.2, 50)

# C11 37-41 ignition
for k, p in enumerate(["D6", "F#6", "A6", "D7", "A6", "F#6"]):
    n("celesta", CELESTA, p, 37 + k * 0.25, 1.0, 76)
n("glock", GLOCK, "A6", 37, 1.5, 66)
chord("pad", PAD, ["D4", "E4", "A4"], 37, 4, 46)
chord("choir", CHOIR, ["D4", "F#4", "A4"], 38.5, 2.5, 54)

# C12 41-44.5 bloom sweep: warm strings, rolling harp
chord("str", STR, ["G2", "D3", "B3", "D4"], 41, 1.75, 62)
chord("str", STR, ["A2", "E3", "C#4", "E4"], 42.75, 1.75, 68)
for k in range(14):
    n("harp", HARP, ["D4", "F#4", "A4", "D5"][k % 4], 41 + k * 0.25, 0.8, 50)

# C13 44.5-47 hover: time suspended
chord("str_slow", STR_SLOW, ["A4", "D5", "E5"], 44.5, 2.5, 34)
for b, p in [(44.8, "A6"), (45.6, "E7"), (46.3, "D7")]:
    n("celesta", CELESTA, p, b, 1.0, 46)

# C14 47 turn -> 48 theme
chord("choir", CHOIR, ["A3", "D4", "E4", "A4"], 47, 1, 70)
gliss("harp", HARP, ["D4", "F#4", "A4", "D5", "F#5", "A5", "D6", "F#6"], 47, 1.0, 58, 3)
n("timp", TIMP, "D2", 48, 2, 84)
CH = [(48, "D2", ["D3", "A3", "F#4"]), (52, "B1", ["B2", "F#3", "D4"]), (56, "G1", ["G2", "D3", "B3"]), (60, "A1", ["A2", "E3", "C#4"])]
for b, bass, ps in CH:
    n("cbass", CBASS, bass, b, 4, 84)
    chord("str", STR, ps, b, 4, 80)
    chord("choir", CHOIR, ps, b, 4, 58 if b < 56 else 74)
n("timp", TIMP, "G1", 56, 2, 86)
MEL = [(48, "D5", 1), (49, "F#5", 1), (50, "E5", 1), (51, "A5", 1), (52, "B5", 2), (54, "A5", 1), (55, "F#5", 1),
       (56, "G5", 1), (57, "A5", 1), (58, "B5", 1), (59, "D6", 1), (60, "C#6", 2), (62, "A5", 1)]
for b, p, d in MEL:
    n("violin", VIOLIN, p, b, d, 94)
    n("piano", PIANO, pm.note_name_to_number(p) - 12, b, d, 60)
for bar0, ps in [(48, ["D4", "A4", "D5", "F#5"]), (52, ["B3", "F#4", "B4", "D5"]), (56, ["G3", "D4", "G4", "B4"]), (60, ["A3", "E4", "A4", "C#5"])]:
    for k in range(8):
        n("harp", HARP, ps[k % 4], bar0 + k * 0.5, 0.8, 50)

# C17 63-68 ascent: rising reprise
for b, bass, ps, v in [(63, "G1", ["G2", "D3", "B3", "D4"], 78), (65, "A1", ["A2", "E3", "C#4", "E4"], 84), (67, "B1", ["B2", "F#3", "D4", "F#4"], 88)]:
    n("cbass", CBASS, bass, b, 2, v)
    chord("str", STR, ps, b, 2, v)
    chord("choir", CHOIR, ps[1:], b, 2, v - 8)
for b, p, d in [(63, "D5", 1), (64, "F#5", 1), (65, "E5", 1), (66, "A5", 1), (67, "B5", 1)]:
    n("violin", VIOLIN, p, b, d, 92)
gliss("harp", HARP, DMAJ, 66.5, 1.4, 52)

# C18 68-73 title payoff: big D major, then fade
chord("str", STR, ["D3", "A3", "D4", "F#4", "A4"], 68, 4.5, 96)
chord("choir", CHOIR, ["D4", "F#4", "A4", "D5"], 68, 4.5, 84)
chord("horn", HORN, ["D3", "F#3", "A3"], 68, 3, 80)
n("cbass", CBASS, "D1", 68, 5, 90)
n("timp", TIMP, "D2", 68, 2.5, 96)
n("violin", VIOLIN, "D6", 68, 3, 96); n("violin", VIOLIN, "A5", 71, 2, 60)
for k, p in enumerate(["D7", "A6", "F#6", "D6", "A5"]):
    n("celesta", CELESTA, p, 69 + k * 0.6, 1.2, 60 - k * 5)

# C19 73-80: silence, one piano note, last petal chime, last chord
n("piano", PIANO, "A5", 74.5, 2.5, 36)
n("celesta", CELESTA, "E6", 77.4, 1.6, 42)
chord("piano", PIANO, ["D3", "A3", "E4", "F#4"], 78.0, 2.0, 30, roll=0.12)

out = sys.argv[1] if len(sys.argv) > 1 else "v10_temp.mid"
mid.write(out)
print("wrote", out, round(mid.get_end_time(), 2), "s")
