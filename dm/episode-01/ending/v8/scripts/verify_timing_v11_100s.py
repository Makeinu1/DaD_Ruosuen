#!/usr/bin/env python3
"""Validate proposed 100-second editorial timing against provisional whale geometry.

Run from any working directory:
    python3 dm/episode-01/ending/v8/scripts/verify_timing_v11_100s.py

This checks timeline integrity and approximate average segment speeds, not
collision meshes, instantaneous acceleration, moonlight onset, or scene lighting.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

V8 = Path(__file__).resolve().parent.parent
TIMING = V8 / "timing-v11-100s-proposal-2026-11-22.json"
GEOMETRY = V8 / "diagrams" / "c04-c18-geometry-v01.json"


def validate() -> dict:
    timing = json.loads(TIMING.read_text(encoding="utf-8"))
    geo = json.loads(GEOMETRY.read_text(encoding="utf-8"))
    shots = timing["shots"]
    stations = timing["pathStations"]
    shot_ids = [f"C{i:02d}" for i in range(1, 20)]
    assert [s["id"] for s in shots] == shot_ids, "C01–C19 shot list not complete"
    assert shots[0]["startS"] == 0
    assert shots[-1]["endS"] == timing["totalSeconds"] == 100
    assert timing["fps"] == 24
    assert timing["totalFrames"] == 2400
    prev = 0
    for s in shots:
        assert s["startS"] == prev, ("cut gap/overlap", s["id"], prev)
        assert s["endS"] - s["startS"] == s["durationS"], s["id"]
        assert 0 < s["durationS"] <= 7, ("cut over 7s", s["id"])
        assert s["startFrame"] == int(s["startS"] * 24)
        assert s["endFrameExclusive"] == int(s["endS"] * 24)
        prev = s["endS"]
        if s["pathStationTimeS"] is not None:
            assert s["startS"] <= s["pathStationTimeS"] < s["endS"], s["id"]
    assert sum(s["durationS"] for s in shots) == 100
    assert sum(s["deltaDurationS"] for s in shots) == 20

    assert stations[0]["id"] == "C04"
    assert stations[-1]["id"] == "EXIT"
    by_id = {s["id"]: s for s in shots}
    by_geo = {s["id"]: s for s in geo["cuts"]}
    speeds = []
    for i, s in enumerate(stations):
        assert s["horizontalPathDistanceM"] == by_geo[s["id"]]["routeDistanceM"]
        if s["id"] != "EXIT":
            assert by_id[s["id"]]["pathStationTimeS"] == s["timeS"]
        if i:
            p = stations[i - 1]
            dt = s["timeS"] - p["timeS"]
            ds = s["horizontalPathDistanceM"] - p["horizontalPathDistanceM"]
            dz = s["zAboveLakeM"] - p["zAboveLakeM"]
            assert dt > 0 and ds > 0, (p["id"], s["id"])
            speed = math.hypot(ds, dz) / dt
            assert 0 < speed < 12, (p["id"], s["id"], speed)
            speeds.append(speed)
    assert abs(stations[-1]["horizontalPathDistanceM"] - 456.07) < 0.1
    assert abs(stations[-1]["timeS"] - 93.0) < 0.01

    return {
        "shot_count": len(shots),
        "duration_s": timing["totalSeconds"],
        "frames": timing["totalFrames"],
        "max_cut_duration_s": max(s["durationS"] for s in shots),
        "delta_vs_prior_80s": sum(s["deltaDurationS"] for s in shots),
        "horizontal_path_distance_m": stations[-1]["horizontalPathDistanceM"],
        "mean_planar_speed_C04_to_EXIT_mps": round(
            stations[-1]["horizontalPathDistanceM"]
            / (stations[-1]["timeS"] - stations[0]["timeS"]), 2
        ),
        "min_interstation_3d_proxy_speed_mps": round(min(speeds), 2),
        "max_interstation_3d_proxy_speed_mps": round(max(speeds), 2),
        "moonlight_ingress_geometry_vs_cut": "OPEN — at approx 41.8s vs C11 cut 44.0s",
        "ascent_gradient_C13_C15": "OPEN — about 43–45 degrees",
        "mesh_and_collision": "NOT VERIFIED",
    }


if __name__ == "__main__":
    for key, value in validate().items():
        print(f"{key}: {value}")
