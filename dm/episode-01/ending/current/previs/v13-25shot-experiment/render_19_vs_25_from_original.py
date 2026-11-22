#!/usr/bin/env python3
"""v13 19-vs-25 diagnostic edit; exact v12.5 B rendering and world spline.

The approved v12.5 original and all four imported source files are UNMODIFIED.
Only six new static viewpoint shots are inserted in the v13 edit.
All times are original absolute times, 0..70s. This is not the independent
lowpoly 25-shot proxy created earlier in the chat.
"""
import argparse, hashlib, json, math, subprocess, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE=Path(__file__).resolve().parent
ORIGINAL_DIR=HERE.parent/"v12-lowpoly-v12.5-cut-test"
sys.path.insert(0,str(ORIGINAL_DIR))
import ruosuen_v12_5_cut_compare as original
b=original.b

TIMELINE=json.loads((HERE/"25shot-experiment-timing-proposal.json").read_text(encoding="utf-8"))
CUTS25=[(s["id"],float(s["start_s"]),float(s["end_s"]),s["camera"]) for s in TIMELINE["cuts"]]
CUTS19=list(original.CUTS_B)
assert len(CUTS19)==19 and len(CUTS25)==25
assert CUTS25[0][1]==0.0 and CUTS25[-1][2]==70.0
assert all(abs(CUTS25[i][2]-CUTS25[i+1][1])<1e-8 for i in range(24))
assert [c[0] for c in CUTS25 if c[0] not in {"N04.5","N05.5","N08.5","N10.5","N14.5","N15.5"}]==[c[0] for c in CUTS19]

# Cinematic experimental cameras only, fixed; no new 3D world or whale animation.
# tuple: (XYZ metres, yaw degrees, pitch degrees, focal mm)
EXPERIMENT_CAMERAS={
    "N04.5": ((-64.0,-56.0,6.4), -38.0, 20.0, 22.0),
    "N05.5": ((-58.0,-84.0,4.1), -51.0, 34.0, 23.0),
    "N08.5": ((10.0,-116.0,5.0), 18.0, 12.0, 20.0),
    "N10.5": ((45.0,-32.0,6.0), 42.0, -6.0, 35.0),
    "N14.5": ((-58.0,-84.0,4.1), 25.0, 27.0, 55.0),
    "N15.5": ((10.0,-40.0,20.0), 0.0, 39.0, 35.0),
}
# Match render-specific layer semantics (real scene, no special new geometry).
LAYER_SOURCE={
    "N04.5":"N04",
    "N05.5":"N05",
    "N08.5":"N09",
    "N10.5":"N10",
    "N14.5":"N14",
    "N15.5":"N15",
}
_original_camera=b.camera
_original_points=b.draw_points
_original_water=b.draw_water_marks
_original_roof=b.draw_roof_and_moon

def make_unmodified_probes():
    return {
        (shot,t): np.asarray(original.render(shot,t,width=640,height=360,letter=None)).copy()
        for shot,t in (
            ("N03",6.20),("N04A",8.10),("N04B",9.85),("N05",12.50),
            ("N06",15.50),("N07.5",20.10),("N08",23.20),
            ("N09",28.20),("N10",35.90),("N14",50.60),
            ("N16",63.80),("N17",67.00),
        )
    }

def install_additive_cameras():
    def camera(name,t):
        if name.startswith("INSERT_"):
            return EXPERIMENT_CAMERAS[name[len("INSERT_"):]]
        return _original_camera(name,t)

    def draw_points(img,cam,t,shot):
        return _original_points(img,cam,t,LAYER_SOURCE.get(shot,shot))

    def draw_water(img,cam,t,shot):
        return _original_water(img,cam,t,LAYER_SOURCE.get(shot,shot))

    def draw_roof(img,cam,shot,t):
        return _original_roof(img,cam,LAYER_SOURCE.get(shot,shot),t)

    b.camera=camera
    b.draw_points=draw_points
    b.draw_water_marks=draw_water
    b.draw_roof_and_moon=draw_roof
    for id,start,end,_ in CUTS25:
        if id in EXPERIMENT_CAMERAS:
            b.SHOTS.append((id,start,end,"supplementary experimental viewpoint","INSERT_"+id,(start+end)/2))

def at(cuts,t):
    for sh,start,end,cam in cuts:
        if start<=t<end:return sh
    return cuts[-1][0]

def frame19(t,size=(640,360)):
    return original.render(at(CUTS19,t),t,*size,letter=None)

def frame25(t,size=(640,360)):
    sid=at(CUTS25,t)
    image=original.render(sid,t,*size,letter=None)
    if sid=="N04.5":
        # Original v12.5 water-breach cue on the SAME world spline.
        original.breach_spray(image,b.camera("INSERT_"+sid,t),t)
    return image

def image_digest(im):
    return hashlib.sha256(np.asarray(im).tobytes()).hexdigest()

def check_reproduction(before):
    diffs={}
    for (shot,t),old in before.items():
        now=np.asarray(original.render(shot,t,width=640,height=360,letter=None))
        assert old.shape==now.shape
        delta=int(np.max(np.abs(old.astype(np.int16)-now.astype(np.int16))))
        assert delta==0, f"Original v12.5 frame changed: {shot}@{t}s max delta={delta}"
        diffs[f"{shot}-{t}"]=image_digest(Image.fromarray(now))
    print("PASS: 12 original v12.5 frames unchanged, byte-identical",flush=True)
    return diffs

def saved_png_check():
    # GitHub source keyframes are the objective reproduction anchor.
    out={}
    for shot,t in [("N04A",8.10),("N04B",9.85),("N07.5",20.10)]:
        fp=ORIGINAL_DIR/"keyframes"/f"{shot}-{t:05.2f}s.png"
        saved=np.asarray(Image.open(fp).convert("RGB"),dtype=np.int16)
        new=np.asarray(original.render(shot,t,1152,648),dtype=np.int16)
        mae=float(np.mean(np.abs(saved-new)))
        out[f"{shot}-{t:05.2f}"]=mae
        assert mae==0.0,f"Published source keyframe reproduction failed: {fp}, mae={mae}"
    print("PASS: 3 preserved GitHub 19-cut keyframes reproduced pixel-identically",flush=True)
    return out

def motion_check():
    # All sample times within the new cut intervals; time-dependent, not a slideshow.
    observations={}
    for sh,s,e,cam in CUTS25:
        if sh not in EXPERIMENT_CAMERAS:continue
        a=frame25(s+0.18*(e-s),size=(480,270))
        z=frame25(s+0.82*(e-s),size=(480,270))
        aa=np.asarray(a)
        bb=np.asarray(z)
        change=float(np.mean(np.any(aa!=bb,axis=2)))
        observations[sh]=round(change,6)
        assert change>0.0002, f"{sh}: no frame-to-frame change"
    print("PASS: 6 new inserts exhibit continuous time-dependent changes",observations,flush=True)
    return observations

def projection_diagnostics():
    result={}
    for sh,s,e,c in CUTS25:
        if sh not in EXPERIMENT_CAMERAS: continue
        t=(s+e)/2
        cam=b.camera("INSERT_"+sh,t)
        P=b.interp(t)[0]
        q=b.projection(P,cam,640,360)
        whale_center=list(map(lambda x:round(float(x),2),q[:2])) if q else None
        flowers={}
        for label,p in (("S1_base",(40,-52,3)),("S1_tip",(85,30,3))):
            qf=b.projection(p,cam,640,360)
            flowers[label]=list(map(lambda x:round(float(x),1),qf[:2])) if qf else None
        result[sh]={"t":round(t,2),"camera":cam,"whale_center_px":whale_center,"S1_px":flowers,"whale_visible_center":bool(q and -70<q[0]<710 and -70<q[1]<430)}
        print("CAM_QA",sh,result[sh],flush=True)
    return result

def captioned(im,header,footer,total_width=1280):
    w,h=im.size
    canvas=Image.new("RGB",(total_width,432),(11,18,28))
    d=ImageDraw.Draw(canvas)
    canvas.paste(im,(0,32))
    d.rectangle((0,0,total_width,31),fill=(12,26,36))
    d.rectangle((0,392,total_width,431),fill=(12,26,36))
    font=ImageFont.truetype(b.FONTPATH,16)
    sm=ImageFont.truetype(b.FONTPATH,13)
    d.text((12,7),header,font=font,fill=(231,238,232))
    d.text((12,401),footer,font=sm,fill=(215,217,202))
    d.line((640,0,640,432),fill=(128,139,137),width=2)
    return canvas

def comp_frame(t):
    sidA=at(CUTS19,t)
    sidB=at(CUTS25,t)
    a=frame19(t)
    z=frame25(t)
    both=Image.new("RGB",(1280,360))
    both.paste(a,(0,0));both.paste(z,(640,0))
    top=f"LEFT  Original approved v12.5 B / 19 cuts   |   RIGHT  v13 diagnostic / 25 cuts"
    bottom=f"{t:05.2f}s   ORIGINAL: {sidA}                               EXPERIMENT: {sidB}"
    return captioned(both,top,bottom)

def writer(frames,filename,fps=8):
    cmd=[
        "ffmpeg","-hide_banner","-loglevel","error","-y",
        "-f","rawvideo","-pix_fmt","rgb24","-s","1280x432",
        "-r",str(fps),"-i","-","-an","-c:v","libx264","-preset","veryfast",
        "-crf","24","-pix_fmt","yuv420p","-movflags","+faststart",str(filename),
    ]
    p=subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=subprocess.PIPE)
    try:
        for i,im in enumerate(frames):
            p.stdin.write(im.tobytes())
    finally:
        p.stdin.close()
    err=p.stderr.read().decode(errors="replace")
    rc=p.wait()
    if rc:
        raise RuntimeError(f"ffmpeg error {rc}: {err[-1000:]}")

def video_info(path):
    r=subprocess.check_output(["ffprobe","-v","error","-select_streams","v:0",
        "-show_entries","stream=nb_frames,r_frame_rate,width,height","-of","json",str(path)])
    return json.loads(r)["streams"][0]

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--out",default=str(HERE/"rendered"))
    ap.add_argument("--fps",type=int,default=8)
    ap.add_argument("--preview-only",action="store_true")
    args=ap.parse_args()
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    before=make_unmodified_probes()
    install_additive_cameras()
    reproduced=check_reproduction(before)
    saved=saved_png_check()
    motion=motion_check()
    cams=projection_diagnostics()
    # Representative frames and cut boundary diagnostics on ONE set of coordinates.
    thumb_w,thumb_h=400,225
    cols=5;rows=5;pad=12;top=34
    sheet=Image.new("RGB",(cols*(thumb_w+pad)+pad,rows*(thumb_h+pad)+pad+top),(8,16,24))
    d=ImageDraw.Draw(sheet)
    d.text((15,10),"Ruosuen v13 | 25 experimental camera cuts | ORIGINAL V12.5 SCENE",fill=(232,236,232))
    for i,(id,s,e,c) in enumerate(CUTS25):
        image=frame25((s+e)/2,size=(640,360)).resize((thumb_w,thumb_h),Image.Resampling.LANCZOS)
        x=pad+i%cols*(thumb_w+pad)
        y=top+pad+i//cols*(thumb_h+pad)
        sheet.paste(image,(x,y))
        if id in EXPERIMENT_CAMERAS:
            d.rectangle((x,y,x+thumb_w-1,y+thumb_h-1),outline=(244,197,107),width=4)
    sheet.save(out/"contact_25shots_original_geometry.png",optimize=True)
    with open(out/"camera_qa_25.json","w",encoding="utf-8") as f:
        json.dump({"original_pixel_digests":reproduced,
                  "saved_original_keyframe_mae":saved,
                  "insert_motion_changed_fraction":motion,
                  "insert_camera_projections":cams,
                  "19_source":"unchanged source GitHub PR #39 v12.5 B",
                  "25_source":"inserts only, same time and original geometry",
                  "duration_s":70,"original_cuts":len(CUTS19),"new_cuts":len(CUTS25)},
                  f,indent=2,ensure_ascii=False)
    if not args.preview_only:
        fps=args.fps
        print("RENDER full 0-70 s / both camera edits",flush=True)
        full=out/"compare_original19_vs_experiment25_FULL_70s.mp4"
        writer((comp_frame(i/fps) for i in range(70*fps)),full,fps)
        print("WROTE",full,video_info(full),flush=True)
        # Focus comparison: ± around each added cut, using the same original global time.
        # 6 inserts -> six focus blocks, not an artificial resimulation.
        windows=[]
        for sh,s,e,_ in CUTS25:
            if sh in EXPERIMENT_CAMERAS:
                windows.append((max(0,s-1.0),min(70,e+1.0)))
        highlight=out/"compare_original19_vs_experiment25_INSERTS_6.mp4"
        times=[a+i/fps for a,z in windows for i in range(int(round((z-a)*fps)))]
        writer((comp_frame(t) for t in times),highlight,fps)
        print("WROTE",highlight,video_info(highlight),flush=True)
    print("PASS: v12.5 baseline was not modified; 25 camera cut experiment complete",flush=True)

if __name__=="__main__":
    main()
