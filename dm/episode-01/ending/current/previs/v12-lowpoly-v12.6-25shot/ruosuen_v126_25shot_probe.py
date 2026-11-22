#!/usr/bin/env python3
"""v12.6 experimental 25-cut storyboard. NON-APPROVED 6 insert shots.

Run from this directory or next to the v12.5 four-file renderer:
  python ruosuen_v126_25shot_probe.py --out ./output --videos

The original 19-shot edit is not changed. All shots share the v12.5 source-time
24m low-poly whale trajectory and world coordinate system. The 80s variant
uniformly retimes 70 source seconds, NOT a validated new whale motion.
"""
import argparse
import json
import math
import subprocess
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'v12-lowpoly-v12.5-cut-test'))
import ruosuen_v12_5_cut_compare as ref

b = ref.b
PREVIOUS_CAMERA = b.camera
CAMERAS = {
    # Establish scale after N04B, ahead of N05.
    "BRIDGE_BREACH": ((-64, -48, 5.2), -53, 16, 26),
    # Between the approaching whale and the fixed overhead camera B.
    "BRIDGE_PC": ((-60, -80, 4.2), -55, 37, 20),
    # Can the whale's emission and S1 base occupy one continuous world view?
    "BRIDGE_LIGHT": ((8, -130, 7.0), 10, 13, 24),
    # Flowering wave -> macro; do not invent a giant flower.
    "BRIDGE_FLOWER": ((55, -38, 5.5), 23, -4, 40),
    # Wide environmental whale -> telephoto eye trace.
    "BRIDGE_SWIM": ((-33, -75, 7.0), 26, 28, 48),
    # Spatially establish the single fissure before closer departure shot.
    "BRIDGE_EXIT": ((-10, -108, 5.0), 6, 33, 32),
}
NEW = [
    ("N04.5", "BRIDGE_BREACH", "水面突破から岸への距離"),
    ("N05.5", "BRIDGE_PC", "岸と冒険者の関係"),
    ("N08.5", "BRIDGE_LIGHT", "鯨から花への光の因果"),
    ("N10.5", "BRIDGE_FLOWER", "開花の波から一輪へ"),
    ("N13.5", "BRIDGE_SWIM", "大空間から鯨へ"),
    ("N15.5", "BRIDGE_EXIT", "裂け目へ向かう方向"),
]
def added_camera(name, t):
    return CAMERAS[name] if name in CAMERAS else PREVIOUS_CAMERA(name, t)
b.camera = added_camera
for sid, name, label in NEW:
    b.SHOTS.append((sid, 0, 70, label, name, 35))

# Draw actual v12.5 surrogate features in new shots while retaining their
# own independently selectable cameras. These are diagnostic projections,
# not a physically correct moonlight raytrace / flower-size proof.
SURROGATE = {
    "N04.5": "N05", "N05.5": "N06",
    "N08.5": "N09", "N10.5": "N10",
    "N13.5": "N13", "N15.5": "N16",
}
for function_name in ("draw_roof_and_moon", "draw_water_marks",
                      "draw_points", "draw_diagnostic"):
    fn = getattr(b, function_name)
    if function_name == "draw_roof_and_moon":
        # Ensure N08.5 can show the environmental opening and tiny moon
        # under the same v12.3 visibility test, never make a fake light beam.
        def wrapper(img, cam, shot, t, fn=fn):
            alias = "N08" if shot == "N08.5" else SURROGATE.get(shot, shot)
            return fn(img, cam, alias, t)
    elif function_name == "draw_water_marks":
        def wrapper(img, cam, t, shot, fn=fn):
            return fn(img, cam, t, SURROGATE.get(shot, shot))
    elif function_name == "draw_points":
        def wrapper(img, cam, t, shot, fn=fn):
            return fn(img, cam, t, SURROGATE.get(shot, shot))
    else:
        def wrapper(img, cam, shot, t, fn=fn):
            return fn(img, cam, SURROGATE.get(shot, shot), t)
    setattr(b, function_name, wrapper)

# 25 shots / 70 source seconds. New shots borrow time from their neighbors.
# Do not claim that insert length, new cameras, or the resulting rhythm is
# author approved. This comparison intentionally exposes overcrowded edits.
CUTS25 = [
    ("N01", 0.00, 3.00, "A"),
    ("N02", 3.00, 5.50, "RIPPLE"),
    ("N03", 5.50, 7.50, "SUB"),
    ("N04A", 7.50, 9.05, "BREACH_FRONT"),
    ("N04B", 9.05, 10.20, "BREACH_THREEQ"),
    ("N04.5", 10.20, 11.55, "BRIDGE_BREACH"),
    ("N05", 11.55, 13.10, "APPROACH"),
    ("N05.5", 13.10, 14.70, "BRIDGE_PC"),
    ("N06", 14.70, 18.00, "B"),
    ("N07", 18.00, 19.45, "BEHIND"),
    ("N07.5", 19.45, 20.50, "MOON_ESTABLISH"),
    ("N08", 20.50, 25.10, "C"),
    ("N08.5", 25.10, 26.65, "BRIDGE_LIGHT"),
    ("N09", 26.65, 31.00, "D"),
    ("N10", 31.00, 35.90, "FLOWERWIDE"),
    ("N10.5", 35.90, 37.15, "BRIDGE_FLOWER"),
    ("N11", 37.15, 40.00, "MACRO"),
    ("N12", 40.00, 43.00, "PLUME"),
    ("N13", 43.00, 46.15, "E-WIDE"),
    ("N13.5", 46.15, 47.45, "BRIDGE_SWIM"),
    ("N14", 47.45, 51.00, "E-TELE"),
    ("N15", 51.00, 56.45, "ASCENT"),
    ("N15.5", 56.45, 58.30, "BRIDGE_EXIT"),
    ("N16", 58.30, 64.00, "F"),
    ("N17", 64.00, 70.00, "A"),
]
LABELS = dict((sid, label) for sid, cam, label in NEW)
ADDED = set(LABELS)
CANDIDATE_TIMES = [10.72, 13.80, 25.84, 36.52, 46.77, 57.37]
assert len(CUTS25) == 25 and len(ref.CUTS_B) == 19
assert {c[0] for c in CUTS25 if c[0] not in [a[0] for a in ref.CUTS_B]} == ADDED
assert CUTS25[0][1] == 0 and CUTS25[-1][2] == 70
assert all(abs(CUTS25[i-1][2] - CUTS25[i][1]) < 1e-7 for i in range(1, len(CUTS25)))

def find_cut(t, cuts=CUTS25):
    for record in cuts:
        if record[1] <= t < record[2]:
            return record
    return cuts[-1]

def render(sid, source_t, w=1152, h=648, tag=None):
    return ref.render(sid, source_t, w, h, letter=tag)

def font(sz):
    return ImageFont.truetype(b.FONTPATH, sz)

def contact(out, entries, name, cols=4, tw=400, th=225):
    footer=27
    rows=math.ceil(len(entries)/cols)
    im=Image.new("RGB", (cols*tw, rows*(th+footer)), (14,27,38))
    draw=ImageDraw.Draw(im)
    f=font(17)
    for i, (sid,t,file) in enumerate(entries):
        with Image.open(file) as frame:
            im.paste(frame.resize((tw,th),Image.Resampling.LANCZOS),
                     ((i%cols)*tw,(i//cols)*(th+footer)))
        draw.text(((i%cols)*tw+8,(i//cols)*(th+footer)+th+3),
                  f"{sid} / source {t:05.2f}s", font=f, fill=(216,224,211))
    im.save(out/name, optimize=True)

def projection_diagnostics(sid, tm, cam_name):
    cam=b.camera(cam_name, tm)
    result={"shot":sid, "source_time_s":round(tm,3), "camera":cam_name,
            "camera_xyz_m":list(cam[0]),"yaw_deg":cam[1],
            "pitch_deg":cam[2],"focal_mm":cam[3]}
    if sid not in ("N01","N02","N07.5","N17"):
        center=b.interp(tm)[0]
        pt=b.projection(center,cam,1152,648)
        result["whale_center_px"]=[round(x,1) for x in pt[:2]] if pt else None
        result["whale_center_in_frame"]=bool(pt and 0 <= pt[0] < 1152 and 0 <= pt[1] < 648)
        vertices=[b.projection(v,cam,1152,648) for poly,_,_ in b.whale_items(tm) for v in poly]
        valid=[q for q in vertices if q and q[2] > 1]
        inside=[q for q in valid if 0 <= q[0] < 1152 and 0 <= q[1] < 648]
        result["proxy_visible_vertex_fraction"]=round(len(inside)/max(1,len(valid)),3)
        if inside:
            result["proxy_visible_bbox_px"]=[round(min(q[0] for q in inside),1),
                 round(min(q[1] for q in inside),1), round(max(q[0] for q in inside),1),
                 round(max(q[1] for q in inside),1)]
    for target, pos in (("s1_base",b.S1[0][:3]),("s1_inner",b.S1[3][:3]),("s1_tip",b.S1[4][:3]),
                        ("fissure_anchor",(-5,170,190))):
        q=b.projection(pos,cam,1152,648)
        result[target+"_px"]=[round(x,1) for x in q[:2]] if q else None
        result[target+"_in_frame"]=bool(q and 0<=q[0]<1152 and 0<=q[1]<648)
    return result

def xy_plan(out):
    W,H=1300,840
    im=Image.new("RGB",(W,H),(15,34,47));d=ImageDraw.Draw(im)
    ft=font(18);small=font(14)
    # X horizontal (-135..125), Y vertical (-125..235).
    def xy(x,y): return (int(110+(x+135)*3.95),int(740-(y+125)*1.85))
    for x in range(-120,121,40):
        d.line([xy(x,-125),xy(x,235)],fill=(35,56,68),width=1)
    for y in range(-100,236,40):
        d.line([xy(-135,y),xy(125,y)],fill=(35,56,68),width=1)
    p=[xy(*b.interp(t/10)[0][:2]) for t in range(0,701)]
    d.line(p,fill=(205,209,191),width=3)
    for sid,cname,label in NEW:
        pos,yaw,pitch,lens=CAMERAS[cname]
        x,y=xy(pos[0],pos[1])
        d.ellipse((x-7,y-7,x+7,y+7),fill=(116,214,223))
        a=math.radians(yaw)
        d.line((x,y,x+int(28*math.sin(a)),y-int(28*math.cos(a))),fill=(115,209,223),width=2)
        d.text((x+9,y-22),sid,font=small,fill=(191,236,238))
    d.text((28,20),"v12.6 / 25-CUT EXPERIMENT / SIX FIXED CAMERA INSERTS",fill=(226,235,234),font=ft)
    d.text((28,53),"Same 3D whale path as adopted v12.5; camera numbers provisional",fill=(152,190,202),font=small)
    im.save(out/"camera-plan-25shot.png",optimize=True)

def render_video(path, duration, variant, fps=4, size=(640,360)):
    is_split=(variant=="comparison")
    width=size[0]*(2 if is_split else 1)
    cmd=["ffmpeg","-hide_banner","-loglevel","error","-y","-f","rawvideo",
         "-pix_fmt","rgb24","-s",f"{width}x{size[1]}","-r",str(fps),
         "-i","-","-an","-c:v","libx264","-preset","veryfast",
         "-crf","25","-pix_fmt","yuv420p","-movflags","+faststart",str(path)]
    proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=subprocess.PIPE)
    try:
        for k in range(round(duration*fps)):
            edit_t=k/fps
            source_t=min(69.999,(edit_t*70.0/duration))
            sid25=find_cut(source_t)[0]
            new=render(sid25,source_t,*size,tag="25")
            if is_split:
                sid19=ref.cut_at(source_t,"B")[0]
                old=render(sid19,source_t,*size,tag="19")
                frame=Image.new("RGB",(width,size[1]))
                frame.paste(old,(0,0));frame.paste(new,(size[0],0))
            else:
                frame=new
            proc.stdin.write(frame.tobytes())
            if k and k%100==0:
                print(f"{path.name} {k}/{round(duration*fps)} frames",flush=True)
    finally:
        proc.stdin.close()
    err=proc.stderr.read().decode()
    if proc.wait()!=0:
        raise RuntimeError(f"ffmpeg error: {err[-1500:]}")
    print(f"VIDEO OK: {path}",flush=True)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--out",default="./output")
    parser.add_argument("--videos",action="store_true")
    args=parser.parse_args()
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    keys=out/"keyframes";keys.mkdir(parents=True,exist_ok=True)
    overview=[];extras=[];qa=[]
    for sid,st,en,cam in CUTS25:
        t=(st+en)/2
        dst=keys/f"{sid}-middle-{t:05.2f}s.png"
        render(sid,t).save(dst,optimize=True)
        overview.append((sid,t,dst))
        entry=projection_diagnostics(sid,t,cam)
        entry.update({"start_s":st,"end_s":en,"duration_s":round(en-st,3),
                      "new_test_insert":sid in ADDED,"author_approved_camera":False})
        qa.append(entry)
        if sid in ADDED:
            for k,fraction in enumerate((.13,.50,.87)):
                tm=st+(en-st)*fraction
                dst=keys/f"{sid}-extra-{k+1:02d}-{tm:05.2f}s.png"
                render(sid,tm).save(dst,optimize=True)
                extras.append((sid,tm,dst))
    contact(out,overview,"overview-25shot.png",cols=5,tw=360,th=203)
    contact(out,extras,"insert-18frames-contact.png",cols=3,tw=480,th=270)
    xy_plan(out)
    pairs=[]
    for sid,tm in zip([x[0] for x in NEW],CANDIDATE_TIMES):
        oldsid=ref.cut_at(tm,"B")[0]
        img=Image.new("RGB",(1152*2,648),(15,32,44))
        img.paste(render(oldsid,tm,tag="19"),(0,0))
        img.paste(render(sid,tm,tag="25"),(1152,0))
        p=out/f"ab-{sid}-{tm:05.2f}s.png"
        img.save(p,optimize=True)
        pairs.append({"new_shot":sid,"source_time_s":tm,"old_19_shot":oldsid,
                      "side_by_side_file":p.name})
    report={
        "project":"Ruosen / episode 01 ending / 空に降る雪",
        "version":"v12.6-25shot-PROBE",
        "structure_author_approved":False,
        "reference_structure":"v12.5 B 19 shots (author approved)",
        "reference_unchanged":True,
        "source_trajectory":"v12.5 shared low-poly WH-01 proxy, source time 0..70s",
        "experiment_25_shots":len(CUTS25),
        "new_insert_count":len(NEW),
        "source_duration_s":70,
        "extended_edit_duration_s":80,
        "extended_edit_note":"Uniform 80/70 global retime, not separate physics or tuned emotional pacing",
        "limitations":["No physical WH-01 final mesh",
                       "No thick-rock occlusion or collision clearance validation",
                       "Moonlight raytrace not implemented",
                       "N16 tail still has not fully exited by 63.8s",
                       "Flower 4.5-cm scale and actual petal motion not cinematic final",
                       "25-cut candidate camera angles and durations not approved"],
        "cuts":qa,
        "ab_stills":pairs,
    }
    (out/"qa-25shot.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    print("QA / 25 contiguous / 6 new:",len(qa),len(extras),flush=True)
    print("INSERT VISIBILITY",json.dumps([{"id":x["shot"],
        "whale_center_in_frame":x.get("whale_center_in_frame"),
        "visible_vertex_fraction":x.get("proxy_visible_vertex_fraction"),
        "s1_base_in_frame":x["s1_base_in_frame"],
        "s1_tip_in_frame":x["s1_tip_in_frame"],
        "fissure_anchor_in_frame":x["fissure_anchor_in_frame"]}
        for x in qa if x["new_test_insert"]],ensure_ascii=False),flush=True)
    if args.videos:
        render_video(out/"25cut-70s-4fps.mp4",70,"25")
        render_video(out/"25cut-80s-4fps.mp4",80,"25")
        render_video(out/"compare-19-vs-25-70s-4fps.mp4",70,"comparison")
    print("DONE v12.6",flush=True)

if __name__=="__main__":
    main()
