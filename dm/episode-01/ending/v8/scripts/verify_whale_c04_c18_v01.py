#!/usr/bin/env python3
"""Validate the proposed Ruosuen whale flight *proxy*, not final 3-D collisions.

Run at repo root:
    python3 dm/episode-01/ending/v8/scripts/verify_whale_c04_c18_v01.py

All inputs are stored in ../diagrams/c04-c18-geometry-v01.json.
No third-party modules, renderer, or authenticated services are required.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

SOURCE = Path(__file__).resolve().parent.parent / "diagrams" / "c04-c18-geometry-v01.json"


def interp(x: float, points: list[list[float]], col: int) -> float | None:
    if x < points[0][0] or x > points[-1][0]:
        return None
    for a, b in zip(points, points[1:]):
        if a[0] <= x <= b[0]:
            t = (x - a[0]) / (b[0] - a[0])
            return a[col] + t * (b[col] - a[col])
    return points[-1][col]


def ray_at_roof(pos: dict, data: dict) -> tuple[float, float, bool]:
    m = data["proposedMoonVectorHorizontalShiftPerVerticalMeter"]
    delta_z = m["roofZ"] - pos["z"]
    x = pos["x"] + delta_z * m["dxPerZ"]
    y = pos["y"] + delta_z * m["dyPerZ"]
    opening = data["fissureRimOpeningCrossSections_Y_Xmin_Xmax"]
    left = interp(y, opening, 1)
    right = interp(y, opening, 2)
    return x, y, left is not None and left <= x <= right


def verify() -> dict:
    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    p = {item["id"]: item for item in data["cuts"]}
    bank = data["coastalSouthBankPolylineXY"]
    statuses = {}

    # Planar C1 tangent continuity is built into the straight→circle→straight
    # construction. Its only finite curvatures are exactly 1/80 m^-1.
    segments = data["pathConstruction"]
    assert [seg["type"] for seg in segments] == ["straight", "circle", "straight", "circle"]
    radii = [seg["radius"] for seg in segments if seg["type"] == "circle"]
    assert min(radii) >= 70
    assert p["C04"]["routeDistanceM"] == 0
    assert 450 < p["EXIT"]["routeDistanceM"] < 460
    statuses["planar_tangent_continuity_and_min_radius_80m"] = "PASS (mathematical centerline)"

    assert p["C04"]["y"] > interp(p["C04"]["x"], bank, 1), "Breach must start above lake water"
    pc = data["charactersApprox"]["adventurer"]
    assert pc["y"] < interp(pc["x"], bank, 1), "Adventurer should stand on land"
    p0 = data["moonlightTestPoints"]["P0"]["position"]
    assert p0["y"] < interp(p0["x"], bank, 1), "P0 should be on the shore"
    s1 = data["flowerTip"]
    assert s1["y"] < interp(s1["x"], bank, 1), "S1 tip should be on promontory land"
    statuses["water_breach_and_shore_p0_s1_placement"] = "PASS (approximate 2-D terrain)"

    for key, desired in {"C08": False, "C09": False, "C10": False, "C11": True}.items():
        assert ray_at_roof(p[key], data)[2] == desired, (key, "moonlight")
    assert ray_at_roof(p0, data)[2]
    assert ray_at_roof(data["moonlightTestPoints"]["CamA"]["position"], data)[2]
    assert not ray_at_roof(s1, data)[2]
    statuses["moonlight_p0_cama_and_c11_but_not_c10_or_s1_tip"] = (
        "PASS (single horizontal roof plane and point rays only)"
    )

    # A chest-to-nose proxy, NOT a verified WH-01 head mesh:
    # C08 moves approximately +X, nose ahead 11m, nose effective lateral
    # radius 3.5m. Camera body center uses Z=9 and head underside offset.
    nose_xy = (p["C08"]["x"] + 11, p["C08"]["y"])
    d_center = math.dist(nose_xy, (pc["x"], pc["y"]))
    nose_skin_distance = d_center - 3.5
    assert 3 <= nose_skin_distance <= 5, nose_skin_distance
    shore_z = 2.0
    nose_underside = p["C08"]["z"] - 1.5 - 2.85 - shore_z
    eye_height = p["C08"]["z"] - 3.0 - shore_z
    assert 2.5 <= nose_underside <= 3.0
    assert 4 <= eye_height <= 5
    statuses["c08_glance_envelope"] = (
        f"PASS only for nose proxy: skin distance {nose_skin_distance:.2f}m; "
        f"underside {nose_underside:.2f}m; eye {eye_height:.2f}m above assumed ground"
    )

    # C09 roll of 80deg: down-going offshore fin (halfspan 7.4m)
    # plus worst-case WH-01 proxy half-thickness 2.85m, Z above lake.
    fin_min_z = p["C09"]["z"] - 7.4 * math.sin(math.radians(80)) - 2.85
    assert fin_min_z > 0, fin_min_z
    statuses["c09_low_roll_fin_proxy"] = (
        f"PASS simplified offshore-fin envelope at Z={fin_min_z:.2f}m above lake;"
        " bank-to-fin mesh collision still untested"
    )

    distance = math.dist(
        (p["C12"]["x"], p["C12"]["y"], p["C12"]["z"]),
        (s1["x"], s1["y"], s1["z"]),
    )
    assert distance <= 65
    statuses["c12_to_s1_tip_within_65m"] = (
        f"PASS (straight line {distance:.2f}m; brightness/bloom threshold not established)"
    )

    # At exit, a generously sized box: body axis +/-12m, wings +/-7.4m.
    # Local heading follows the second circular arc, with 3-D pitch inferred
    # from the previous segment. This is a proxy, NOT a 3D whale mesh.
    for id_, previous, phi, dphi in [("C18", "C17", 60, 20), ("EXIT", "C18", 70, 10)]:
        pos = p[id_]
        prev = p[previous]
        slope = (pos["z"] - prev["z"]) / (80 * math.radians(dphi))
        horizontal_fraction = 1 / math.sqrt(1 + slope * slope)
        a = math.radians(phi)
        tx, ty = -math.sin(a), math.cos(a)
        ux, uy = -ty, tx
        for longitudinal in [-12, 0, 12]:
            for span in [-7.4, 0, 7.4]:
                x = pos["x"] + longitudinal * horizontal_fraction * tx + span * ux
                y = pos["y"] + longitudinal * horizontal_fraction * ty + span * uy
                lim = data["fissureRimOpeningCrossSections_Y_Xmin_Xmax"]
                left = interp(y, lim, 1)
                right = interp(y, lim, 2)
                assert left is not None and left < x < right, (id_, x, y, left, right)
        if id_ == "EXIT":
            estimated_min_z = pos["z"] - 12 * slope * horizontal_fraction - 2.85
            assert estimated_min_z > 190, estimated_min_z
    statuses["c18_roof_opening_and_full_exit_proxy"] = (
        "PASS approximate wing/body box at C18/EXIT; not a rock-thickness or mesh collision test"
    )

    shot = data["C18MoonOverlapCamera"]
    aligned = math.dist(shot["moonRayAtZ195"], shot["whaleAtZ195"])
    assert aligned < 2.0, aligned
    assert shot["groundCandidate"]["y"] < interp(shot["groundCandidate"]["x"], bank, 1)
    statuses["c18_moon_disc_alignment_from_alternate_ground_camera"] = (
        f"PASS geometric alignment {aligned:.2f}m at 195m, but grounded camera "
        "must relocate from adventurer's C08 position; EDITORIAL APPROVAL REQUIRED"
    )
    statuses["rendered_whale_mesh_vs_terrain"] = "NOT TESTED"
    statuses["moonlight_cast_shadows_in_3d_thick_rock"] = "NOT TESTED"
    statuses["3d_spline_acceleration_or_timing"] = "NOT TESTED; retiming follows motion approval"
    return statuses


if __name__ == "__main__":
    for name, result in verify().items():
        print(f"{name}: {result}")
