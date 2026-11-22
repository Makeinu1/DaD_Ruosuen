#!/usr/bin/env python3
"""Overland flight v0.4: independent geometric sanity checks (Python stdlib).

From the repository root:
    python3 dm/episode-01/ending/v8/scripts/verify_overland_camera_v04.py

This is a 2.5D numerical test, NOT a Blender/3D scene and not proof of collision
avoidance against thick rock or articulated whale geometry.
"""
from __future__ import annotations
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
G = json.loads((ROOT / "diagrams/overland-moonbeam-spatial-v04.json").read_text(encoding="utf-8"))
C = json.loads((ROOT / "camera-overland-projection-audit-v04.json").read_text(encoding="utf-8"))
S = {s["id"]: s for s in G["whaleCenterline"]["stations"]}
CAM = {c["id"]: c for c in C["cameras"]}
FISSURE = G["roofSingleFissureSectionsY_Xleft_Xright"]
SHORE = G["shorelineControlPointsXY"]
DEG = math.pi/180
tests = []


def check(label, passed):
    ok = bool(passed)
    tests.append(ok)
    print(("PASS" if ok else "FAIL") + ": " + label)


def interpolate(coord, control_points, column):
    if coord < control_points[0][0] or coord > control_points[-1][0]:
        return None
    for a, b in zip(control_points, control_points[1:]):
        if a[0] <= coord <= b[0]:
            t = (coord-a[0]) / (b[0]-a[0])
            return a[column]*(1-t)+b[column]*t
    return control_points[-1][column]


def on_land(pt):
    shore = interpolate(pt["x"], SHORE, 1)
    return shore is not None and pt["y"] < shore


def lunar_margin(pt):
    y = pt["y"]+(190-pt["z"])*1.072
    left, right = interpolate(y, FISSURE, 1), interpolate(y, FISSURE, 2)
    return -math.inf if left is None else min(pt["x"]-left, right-pt["x"])


def eye_vec():
    return (0, math.cos(43*DEG), math.sin(43*DEG))


def projection(c, pt, *, direction=False, yaw=None):
    yaw = math.radians(c["yawDeg"] if yaw is None else yaw)
    pitch = math.radians(c["pitchDeg"])
    v = (tuple(pt) if direction else
         tuple(pt[k]-c["pos"][k] for k in ("x", "y", "z")))
    fwd = (math.sin(yaw)*math.cos(pitch),
           math.cos(yaw)*math.cos(pitch), math.sin(pitch))
    right = (math.cos(yaw), -math.sin(yaw), 0)
    up = (-math.sin(yaw)*math.sin(pitch),
          -math.cos(yaw)*math.sin(pitch), math.cos(pitch))
    dot = lambda a, b: sum(x*y for x, y in zip(a, b))
    depth = dot(v, fwd)
    if depth <= 0:
        return None
    return dot(v, right)/depth*c["focalMm"]/18, dot(v, up)/depth*c["focalMm"]/10.125


def target(key):
    if key == "moon":
        return eye_vec()
    if key == "P0":
        return G["locations"]["P0YoungFlower"]
    if key.startswith("S1"):
        return next(f for f in G["locations"]["S1MatureFlowerInstances"] if f["id"] == key)
    return S[key]


party = G["locations"]["adventurerProxy"]
check("party on land", on_land(party))
check("S1 mature flower sites all on land",
      all(on_land(f) for f in G["locations"]["S1MatureFlowerInstances"]))
check("P0 receives natural moonlight", lunar_margin(G["locations"]["P0YoungFlower"]) >= 0)
check("party remains in moon shadow", lunar_margin(party) < 0)
check("all S1 mature patches are shadowed from direct moon",
      all(lunar_margin(f) < 0 for f in G["locations"]["S1MatureFlowerInstances"]))

cx, cy = -20, -25
miss = abs(math.hypot(party["x"]-cx, party["y"]-cy)-70)
check("true-overhead track XY miss < 1 meter", miss < 1)
check("grazing head shadow E07 and E08 before lunar contact",
      all(lunar_margin(head) < 0 for head in (
         {"x":-20+70*math.cos(255*DEG)-11*math.sin(255*DEG)-3*math.cos(255*DEG),
          "y":cy+70*math.sin(255*DEG)+11*math.cos(255*DEG)-3*math.sin(255*DEG),
          "z":17},
         {"x":-20+70*math.cos(260*DEG)-11*math.sin(260*DEG)-3*math.cos(260*DEG),
          "y":cy+70*math.sin(260*DEG)+11*math.cos(260*DEG)-3*math.sin(260*DEG),
          "z":20})))
check("nose center reaches beam E08a", lunar_margin({
    "x":S["E08a"]["x"]-11*math.sin(262.316*DEG),
    "y":S["E08a"]["y"]+11*math.cos(262.316*DEG),
    "z":S["E08a"]["z"]-4}) > -.05)
check("S1 base < 65m from luminescent whale E10",
      math.dist(tuple(S["E10"][k] for k in ("x", "y", "z")),
                tuple(G["locations"]["S1MatureFlowerInstances"][0][k] for k in ("x", "y", "z"))) < 65)
check("S1 tip < 65m from luminescent whale E14",
      math.dist(tuple(S["E14"][k] for k in ("x", "y", "z")),
                tuple(G["locations"]["S1MatureFlowerInstances"][4][k] for k in ("x", "y", "z"))) < 65)
check("E22 total rough planar path ~509m",
      abs(S["E22"]["planDistanceFromE01M"]-509.41) < .02)
check("time keys monotonic",
      all(b["timeSec"] > a["timeSec"] for a,b in zip(G["whaleCenterline"]["stations"],
                                                    G["whaleCenterline"]["stations"][1:])))

for name, c in CAM.items():
    for key, saved in c["projection"].items():
        actual = projection(c, target(key), direction=(key=="moon"),
                            yaw=c.get("yawPanByStation",{}).get(key))
        check(f"camera {name}: projected {key} matches JSON", actual is not None and
              abs(actual[0]-saved["nx"]) < .003 and
              abs(actual[1]-saved["ny"]) < .003)
    check(f"camera {name}: moon roof ray", (lunar_margin(c["pos"])>=0)==c["lunarVisibility"]["visible"])

check("B intentional exit from frame", not CAM["B-near-zenith"]["projection"]["E06"]["onScreen"])
check("C all luminous full-body proxy from E09/E10 in frame",
      all(t["fullProxyWithin"] for t in C["bodyProjectionTests"]
          if t["cameraId"]=="C-ignite" and t["stationId"] in ("E09","E10")))
check("D full-body luminous whale fits S1 frame",
      all(t["fullProxyWithin"] for t in C["bodyProjectionTests"]
          if t["cameraId"]=="D-bloom"))
check("E high swim excludes S1 flower beds",
      all(not CAM["E-high"]["projection"][id]["onScreen"] for id in ("S1a","S1e")))
check("F exits above the slit according to camera sight ray",
      all(q["visible"] for q in C["exitSightline"].values()))

print(f"{sum(tests)}/{len(tests)} numerical tests passed")
if not all(tests):
    raise SystemExit(1)
print("NOTE: roof thickness, real whale mesh, camera art, image lighting and particle physics UNTESTED.")
