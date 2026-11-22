#!/usr/bin/env python3
"""First-order geometric checks for the *unapproved* overland moonlight model.

Run from the GitHub repository root:
    python3 dm/episode-01/ending/v8/scripts/verify_overland_moonbeam_v02.py

No third-party modules. This checks a 2-D fissure roof plane and representative
whale/body points. It does NOT trace photons through thick, irregular rock,
verify a moving whale mesh, or prove a cinematic image is physically correct.
"""
from __future__ import annotations
import json
import math
from pathlib import Path

D = Path(__file__).resolve().parent.parent / "diagrams" / "overland-moonbeam-spatial-v02.json"
data = json.loads(D.read_text(encoding="utf-8"))
shore = data["shorelineControlPointsXY"]
slit = data["roofSingleFissureSectionsY_Xleft_Xright"]
stations = {p["id"]: p for p in data["whaleCenterline"]["stations"]}
places = data["locations"]
pc = places["adventurerProxy"]
flowers = places["S1MatureFlowerInstances"]
root_height = data["adoptedScale"]["fissureRimReferenceM"]
dy_over_dz = data["moon"]["toMoonPerMeterVertical"]["dy"]
checks = []


def interp(x, series, col):
    if x < series[0][0] or x > series[-1][0]:
        return None
    for left, right in zip(series, series[1:]):
        if left[0] <= x <= right[0]:
            t = (x - left[0]) / (right[0] - left[0])
            return left[col] + t * (right[col] - left[col])
    return series[-1][col]


def inland(point):
    boundary = interp(point["x"], shore, 1)
    return boundary is not None and point["y"] < boundary


def moon(point):
    x = point["x"]
    yy = point["y"] + (root_height - point["z"]) * dy_over_dz
    left = interp(yy, slit, 1)
    right = interp(yy, slit, 2)
    return left is not None and left <= x <= right


def distance(a, b):
    return math.dist((a["x"], a["y"], a["z"]), (b["x"], b["y"], b["z"]))


def case(name, condition):
    result = bool(condition)
    checks.append((name, result))
    print(f'{"PASS" if result else "FAIL"}: {name}')


def position(phi, z):
    a = math.radians(phi)
    return {"x": -20 + 70 * math.cos(a),
            "y": -15 + 70 * math.sin(a), "z": z}


def nose(phi, z):
    p = position(phi, z)
    a = math.radians(phi)
    return {"x": p["x"] - 11 * math.sin(a),
            "y": p["y"] + 11 * math.cos(a),
            "z": z - 4}


case("PC is on land", inland(pc))
case("Cam A is on land", inland(places["CamA"]))
case("P0 is on land", inland(places["P0YoungFlower"]))
case("E01 breach starts above water", not inland(stations["E01"]))
case("All six S1 sample patches are on land", all(inland(f) for f in flowers))
case("P0 receives the proposed lunar beam", moon(places["P0YoungFlower"]))
case("Cam A can see the proposed moon direction", moon(places["CamA"]))
case("PC starts in direct-moon shadow", not moon(pc))
case("S1 sample patches are outside direct lunar beam", all(not moon(f) for f in flowers))
case("Whale's nose before contact is in shadow", not moon(nose(255, 21)))
case("Whale's nose at E08 receives moonlight", moon(nose(260, 24)))
case("Whale's body center at E08 is still in shadow", not moon(stations["E08"]))

p = nose(235, 11.5)
head_skin_m = math.dist((p["x"], p["y"]), (pc["x"], pc["y"])) - 3.5
case("E05 near-pass face separation 3–5m using head proxy", 3 <= head_skin_m <= 5)
case("E05 approximate nose underside above local ground 2.5–3m",
     2.5 <= stations["E05"]["z"] - 3.2 - 2.85 - pc["z"] <= 3)
case("E05 approximate eye above local ground 4–5m",
     4 <= stations["E05"]["z"] - 4.5 - pc["z"] <= 5)
case("E10 illumination within tentative 65m of S1 base",
     distance(stations["E10"], flowers[0]) <= 65)
case("E14 illumination within tentative 65m of S1 tip",
     distance(stations["E14"], flowers[4]) <= 65)
case("First arc within normal approx 70–90m planar radius",
     data["whaleCenterline"]["geometry"][1]["radius"] == 70)
case("Second arc within normal approx 70–90m planar radius",
     data["whaleCenterline"]["geometry"][3]["radius"] == 80)
case("Average interstation proxy speeds less than 20m/s",
     all(s.get("fromPrevious", {}).get("approx3DAverageSpeedMps", 0) < 20
         for s in stations.values()))

# These checks use a very rough ORIENTED rectangle, not the whale's 3-D mesh.
for id_, phi in [("E20", 60), ("E21", 70), ("E22", 82)]:
    s = stations[id_]
    a = math.radians(phi)
    tx, ty = -math.sin(a), math.cos(a)
    lx, ly = math.cos(a), math.sin(a)
    margin = math.inf
    for length in [-12, 0, 12]:
        for fin in [-7.4, 0, 7.4]:
            x = s["x"] + tx * length + lx * fin
            y = s["y"] + ty * length + ly * fin
            left, right = interp(y, slit, 1), interp(y, slit, 2)
            margin = min(margin, x-left if left is not None else -math.inf,
                         right-x if right is not None else -math.inf)
    case(f"{id_}: rough planar whale body+fin box fits slit (margin {margin:.1f}m)",
         margin > 0)

# At E22 the body proxy is above the rim even when the tail points downhill.
# This uses an approximate rearward max drop of 12m + body half-thickness.
case("E22 complete emergence: crude min height > rim",
     stations["E22"]["z"] - 12 - 2.85 > root_height)
case("Provisional 70s edit: exit by 64 seconds",
     stations["E22"]["timeSec"] <= 64)
case("E01–E22 rough mean planar speed stays in 5–12m/s",
     5 <= data["firstOrderTests"]["centerlineMeanPlanarSpeedFromE01toE22"] <= 12)

print(f"{sum(ok for _, ok in checks)} / {len(checks)} checks passed")
if not all(ok for _, ok in checks):
    raise SystemExit(1)
print("Important: 3-D roof thickness, real whale mesh, camera lens projection,")
print("S1 photometric bloom threshold, and smooth acceleration are NOT VERIFIED.")
