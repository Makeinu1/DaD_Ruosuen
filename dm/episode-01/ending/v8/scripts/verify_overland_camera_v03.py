#!/usr/bin/env python3
"""Recalculate the overland moonlight ground-camera pinhole projection audit.

Run from repo root:
  python3 dm/episode-01/ending/v8/scripts/verify_overland_camera_v03.py

Uses only the standard library. Tests geometric *screen positions* for point and
rectangular whale proxies. It does not render a 3D scene, model lens distortion,
verify opaque rock thickness, or guarantee the art and anatomy on screen.
"""
from __future__ import annotations
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCENE = json.loads((ROOT / "diagrams/overland-moonbeam-spatial-v02.json").read_text(encoding="utf-8"))
AUDIT = json.loads((ROOT / "camera-overland-projection-audit-v03.json").read_text(encoding="utf-8"))
STATIONS = {s["id"]: s for s in SCENE["whaleCenterline"]["stations"]}
FLOWERS = {p["id"]: p for p in SCENE["locations"]["S1MatureFlowerInstances"]}
FISSURE = SCENE["roofSingleFissureSectionsY_Xleft_Xright"]
MOON = (0, math.cos(math.radians(43)), math.sin(math.radians(43)))
PASSED = 0


def check(title, condition):
    global PASSED
    ok = bool(condition)
    print(("PASS" if ok else "FAIL") + ": " + title)
    PASSED += int(ok)
    if not ok:
        raise AssertionError(title)


def point(camera, target, direction=False, yaw=None):
    yaw = math.radians(camera["yawDeg"] if yaw is None else yaw)
    pitch = math.radians(camera["pitchDeg"])
    v = (target if direction else
         tuple(target[k]-camera["pos"][k] for k in ("x", "y", "z")))
    front = (math.sin(yaw)*math.cos(pitch),
             math.cos(yaw)*math.cos(pitch), math.sin(pitch))
    right = (math.cos(yaw), -math.sin(yaw), 0)
    up = (-math.sin(yaw)*math.sin(pitch), -math.cos(yaw)*math.sin(pitch), math.cos(pitch))
    dot = lambda u: sum(a*b for a, b in zip(u, v))
    depth = dot(front)
    if depth <= 0:
        return None
    nx = dot(right)/depth*camera["focalMm"]/18
    ny = dot(up)/depth*camera["focalMm"]/10.125
    return nx, ny


def point_for(target):
    if target == "moon":
        return MOON
    if target == "P0":
        return SCENE["locations"]["P0YoungFlower"]
    return FLOWERS[target] if target.startswith("S1") else STATIONS[target]


def interp(y, col):
    if y < FISSURE[0][0] or y > FISSURE[-1][0]:
        return None
    for a, b in zip(FISSURE, FISSURE[1:]):
        if a[0] <= y <= b[0]:
            t = (y-a[0])/(b[0]-a[0])
            return a[col]+t*(b[col]-a[col])
    return FISSURE[-1][col]


def lunar_line(p):
    roof_y = p["y"]+(190-p["z"])*1.072
    a, b = interp(roof_y, 1), interp(roof_y, 2)
    return a is not None and a <= p["x"] <= b


def roof_line_to_target(camera, target):
    from_ = camera["pos"]
    if target["z"] <= 190:
        return True
    frac = (190-from_["z"])/(target["z"]-from_["z"])
    y = from_["y"]+(target["y"]-from_["y"])*frac
    x = from_["x"]+(target["x"]-from_["x"])*frac
    a, b = interp(y, 1), interp(y, 2)
    return a is not None and a <= x <= b


def proxy_box(station, phi):
    a = math.radians(phi)
    forward = (-math.sin(a), math.cos(a))
    lateral = (math.cos(a), math.sin(a))
    for ll in (-12, 12):
        for ww in (-7.4, 7.4):
            for dz in (-2.84, 2.84):
                yield {"x": station["x"] + forward[0]*ll + lateral[0]*ww,
                       "y": station["y"] + forward[1]*ll + lateral[1]*ww,
                       "z": station["z"]+dz}


def margin_to_moonlit_region(q):
    yy = q["y"]+(190-q["z"])*1.072
    a, b = interp(yy, 1), interp(yy, 2)
    return -math.inf if a is None else min(q["x"]-a, b-q["x"])


def head_edge(phi, z):
    a = math.radians(phi)
    return {"x":-20+70*math.cos(a)-11*math.sin(a)-3*math.cos(a),
            "y":-15+70*math.sin(a)+11*math.cos(a)-3*math.sin(a),
            "z":z-4}


cam = {c["id"]: c for c in AUDIT["cameras"]}
check("Seven camera alternatives are provided", len(cam) == 7)
for camera in cam.values():
    for key, expected in camera["projected"].items():
        actual = point(camera, point_for(key), key=="moon",
                       camera.get("yawPanByStation", {}).get(key))
        check(f'{camera["id"]} {key} perspective point matches saved audit',
              actual is not None and
              abs(actual[0]-expected["nx"]) < .002 and
              abs(actual[1]-expected["ny"]) < .002)
    check(f'{camera["id"]} roof-plane moon visibility',
          lunar_line(camera["pos"]) == camera["moonDirectVisibility"]["visible"])

A = cam["A-revised"]; B = cam["B-overfly"]; C = cam["C-moon"]
D = cam["D-flower"]; E = cam["E-high"]; F = cam["F-exit"]
check("A Moon and P0 both inside 10 percent normalized margin",
      all(abs(A["projected"][q][axis]) < .9 for q in ("moon", "P0") for axis in ("nx", "ny")))
check("B Moon is physically blocked, even though its direction would fit",
      not lunar_line(B["pos"]))
check("C Moon is visible through model roof slit", lunar_line(C["pos"]))
check("C near first-contact & full body later center stay within frame",
      all(C["projected"][q]["onScreen"] for q in ("moon", "E08", "E09", "E10")))
check("D frames full S1 range and luminous whale centers",
      all(D["projected"][q]["onScreen"] for q in ("S1a", "S1e", "E11", "E14")))
check("E high flight keeps both S1 sample flower beds out of screen",
      not any(E["projected"][q]["onScreen"] for q in ("S1a", "S1e")))
check("F frames the true Moon and E20–E22",
      all(F["projected"][q]["onScreen"] for q in ("moon", "E20", "E21", "E22")))
check("F roof sight lines for high exit points",
      all(roof_line_to_target(F, STATIONS[q]) for q in ("E21", "E22")))

for cam_id, st_id, phi in [("B-overfly", "E05", 235), ("C-moon", "E08", 260),
                            ("C-moon", "E09", 290), ("C-moon", "E10", 294),
                            ("D-flower", "E11", 325), ("F-exit", "E21", 70)]:
    c = cam[cam_id]
    sample = next(t for t in AUDIT["whaleBoxTests"]
                  if t["cameraId"] == cam_id and t["stationId"] == st_id)
    xy = [point(c, q, False, c.get("yawPanByStation", {}).get(st_id))
          for q in proxy_box(STATIONS[st_id], phi)]
    check(f"{cam_id} / {st_id}: rough body box bounds reproduce",
          all(p is not None for p in xy) and
          abs(min(p[0] for p in xy)-sample["proxyScreenBounds"]["xmin"]) < .02 and
          abs(max(p[0] for p in xy)-sample["proxyScreenBounds"]["xmax"]) < .02)

check("E07 nose-right tip can receive light before center of nose at E08",
      margin_to_moonlit_region(head_edge(255, 21)) > 0 and
      margin_to_moonlit_region(head_edge(245, 16)) < 0)
print(f"{PASSED} checks passed. All calculations are first-order geometric checks.")
print("Warning: first light onset E07 head-right proxy is already moonlit.")
print("Unverified: rock volume, whale rig, precise eye/fin anatomy, real cinematography.")
