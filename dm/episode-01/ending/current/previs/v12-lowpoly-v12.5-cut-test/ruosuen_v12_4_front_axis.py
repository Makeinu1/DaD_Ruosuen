#!/usr/bin/env python3
"""Camera-axis comparison v12.4 for N01-N03 (+N17 matching A), editable low-poly.

Run alongside unchanged v12.3 scripts:
    python ruosuen_v12_4_front_axis.py --out ./output
Requires numpy and Pillow. Author unapproved; no adopted camera values.
"""
import argparse, json, math
from pathlib import Path
import ruosuen_v12_camera_revision as previous
from PIL import Image, ImageDraw, ImageFont

base=previous.base
ORIGINAL_CAMERA=base.camera
ORIGINAL_WATERMARKS=base.draw_water_marks
# The previous v12.3 had a false jump from the pre-4.5 fallback to 4.5s.
# Add early approach stations continuing toward -Y through the existing 4.5-10.5s keypoints.
base.STATIONS=[(-1.0,-90,73,-12),(0.0,-90,65,-12),(3.0,-90,42,-10)] + base.STATIONS

# Distinct cameras, not a dolly/zoom or magical change of whale course.
# A must remain exactly the same for opening N01 and closing N17.
CANDIDATE_CAMERAS={
    'A':((-18,-93,3),-24,18.5,18),
    'RIPPLE':((-90,-40,2.8),0,-5,28),
    'SUB':((-90,-18,3.2),0,-21,55)
}

def camera(name,t):
    return CANDIDATE_CAMERAS.get(name,ORIGINAL_CAMERA(name,t))
base.camera=camera

def draw_water_marks(img,cam,t,shot):
    if shot not in ('N02','N03'):
        return ORIGINAL_WATERMARKS(img,cam,t,shot)
    W,H=img.size
    draw=ImageDraw.Draw(img)
    u=base.clamp((t-3.0)/4.0)
    # Diagnostic concentric wavefronts (not emissive rings or floating magic).
    # World coordinates use the same continuous travel axis as the whale: X ~ -90, Y decreases.
    y=11-9*u
    for i,radius in enumerate([3.5+4.6*u,7.5+4.6*u,12+4.6*u,17+4.6*u]):
        line=[]
        for j in range(101):
            a=2*base.PI*j/100
            point=(-90+radius*math.cos(a),y+radius*math.sin(a),.08)
            q=base.projection(point,cam,W,H)
            if q:line.append((q[0],q[1]))
        if len(line)>2:
            draw.line(line,fill=(93,140,157),width=3 if i<2 else 2)
base.draw_water_marks=draw_water_marks

# Keep the whale facing the spectator on the opening approach. Introduce its
# nose-up orientation only as it prepares to break the surface; position path
# remains 3D continuous and N04's original orientation is recovered at 7.7s.
ORIGINAL_POSE=base.pose
def frontal_underwater_pose(t):
    if t>=7.7:
        return ORIGINAL_POSE(t)
    import numpy as np
    cp,v=base.interp(t)
    w=base.clamp((t-6.5)/1.2)
    w=w*w*(3-2*w)
    level=base.unit(base.N([v[0],v[1],0]))
    f=base.unit((1-w)*level+w*base.unit(v))
    side=base.unit(base.N([-f[1],f[0],0]))
    up=base.unit(np.cross(f,side))
    return cp,f,side,up
base.pose=frontal_underwater_pose

# The early silhouette is a dark, non-emissive underwater mass. Raise only its
# preview contrast to remain readable at storyboard size; no new light source.
ORIGINAL_PAINT=base.paint_poly_items
_CURRENT_SHOT=None
def legible_underwater_proxy(img,items,cam):
    if _CURRENT_SHOT=='N03' and len(items)==len(base.MESH):
        scale=.50/.26
        items=[(polygon,tuple(min(255,int(v*scale)) for v in color),layer)
               for polygon,color,layer in items]
    return ORIGINAL_PAINT(img,items,cam)
base.paint_poly_items=legible_underwater_proxy

FRAMES=[('N01',1.50),('N02',3.35),('N02',4.30),('N02',5.30),
        ('N03',5.70),('N03',6.20),('N03',7.10),
        ('N04',8.00), # continuity-only comparison; N04 camera is UNCHANGED
        ('N17',67.00)]

def make_contact(out,frames):
    TW,TH=576,324;footer=34;cols=3;rows=math.ceil(len(frames)/cols)
    img=Image.new('RGB',(TW*cols,(TH+footer)*rows),(11,25,37));d=ImageDraw.Draw(img)
    font=ImageFont.truetype(base.FONTPATH,18)
    for i,x in enumerate(frames):
        f=out/x['filename'];x0=(i%cols)*TW;y0=(i//cols)*(TH+footer)
        with Image.open(f) as src:img.paste(src.resize((TW,TH),Image.Resampling.LANCZOS),(x0,y0))
        d.text((x0+12,y0+TH+5),f"{x['shot']}  {x['time']:.2f}s  {x['camera']}  {x['yaw_deg']:+g}°",font=font,fill=(212,228,230))
    img.save(out/'contact-sheet-v12.4-front-axis.png',optimize=True)


def make_plan(out,frames):
    from PIL import ImageDraw
    W,H=1240,720;img=Image.new('RGB',(W,H),(17,35,47));d=ImageDraw.Draw(img)
    font=ImageFont.truetype(base.FONTPATH,24)
    small=ImageFont.truetype(base.FONTPATH,18)
    # Top-down XY map, fixed meters-to-pixels. Viewer toward bottom, lake at top.
    def xy(x,y):return (int(620+(x+60)*3.1),int(590-(y+75)*3.1))
    for yy in (-60,-30,0,30,60):
        a=xy(-160,yy);b=xy(130,yy)
        d.line([a,b],fill=(37,58,69),width=1)
    for xx in (-120,-90,-60,-30,0,30):
        a=xy(xx,-100);b=xy(xx,95);d.line([a,b],fill=(37,58,69),width=1)
    shore=[xy(x,y) for x,y in base.SHORE if -150<=x<=150 and -90<=y<=95]
    if len(shore)>1:d.line(shore,fill=(106,113,99),width=3)
    # Main trajectory, not two different whale routes
    tvals=[0+i*.08 for i in range(130)]
    pts=[xy(*base.interp(t)[0][:2]) for t in tvals if t<=10.4]
    d.line(pts,fill=(198,201,188),width=5)
    for t in (3.35,4.3,5.7,6.2,7.1,8.0):
        p=base.interp(t)[0];x,y=xy(p[0],p[1]);d.ellipse((x-7,y-7,x+7,y+7),fill=(227,209,169))
        d.text((x+13,y-12),f'{t:g}s',font=small,fill=(227,222,192))
    cams=[('A / N01=N17',base.camera('A',1.5),(140,198,218)),
          ('N02 / RIPPLE',base.camera('RIPPLE',4.3),(114,202,205)),
          ('N03 / SUB',base.camera('SUB',6.2),(237,189,123))]
    for label,(pos,yaw,pitch,lens),color in cams:
        x,y=xy(pos[0],pos[1]);d.ellipse((x-9,y-9,x+9,y+9),fill=color)
        rad=math.radians(yaw);xx=x+int(64*math.sin(rad));yy=y-int(64*math.cos(rad))
        d.line([(x,y),(xx,yy)],fill=color,width=4)
        d.polygon([(xx,yy),(xx+7,yy+14),(xx-7,yy+14)],fill=color)
        d.text((x+12,y+12),label,font=small,fill=color)
    a=xy(-90,11);d.ellipse((a[0]-10,a[1]-10,a[0]+10,a[1]+10),outline=(116,169,182),width=3)
    d.text((30,27),'v12.4  CAMERA AXIS · TOP-DOWN SCHEMATIC',font=font,fill=(235,240,235))
    d.text((30,62),'X=-90m whale approach axis · nose toward camera / land (-Y)',font=small,fill=(166,201,210))
    d.text((30,H-42),'Diagram: spatial reference, not an extra film shot. All camera values are unapproved.',font=small,fill=(158,185,193))
    img.save(out/'scene-front-axis-v12.4.png',optimize=True)


def main(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    counts={};frames=[]
    for shot,t in FRAMES:
        global _CURRENT_SHOT
        _CURRENT_SHOT=shot
        counts[shot]=counts.get(shot,0)+1
        fname=f'{shot}-{counts[shot]:02d}-{t:05.2f}s.png'
        record=base.render_one(shot,t,out/fname)
        record['note']='N01=N17 fixed A; N02/N03 face-on vs whale route' if shot in ('N01','N02','N03','N17') else 'N04 unchanged camera; continuity reference'
        frames.append(record)
    make_contact(out,frames);make_plan(out,frames)
    tests=[]
    for t in (5.7,6.2,7.1):
        center,fwd,_,_=base.pose(t)
        cam=base.camera('SUB',t)
        # Angular difference: whale velocity to camera direction XY
        toCam=base.N(cam[0])[:2]-center[:2]
        v=fwd[:2]
        ang=math.degrees(math.acos(float(max(-1,min(1,base.N(toCam).dot(v)/(max(1e-9,math.sqrt(float(base.N(toCam).dot(toCam))))*max(1e-9,math.sqrt(float(v.dot(v))))))))))
        tests.append({'t_s':t,'whale_center_m':[round(x,3) for x in center.tolist()], 'front_approach_off_axis_deg':round(ang,2),'camera_range_m':round(float(base.N(toCam).dot(base.N(toCam)))**.5,2)})
    report={'version':'v12.4 FRONT APPROACH CAMERA TEST','status':'AUTHOR REVIEW ONLY / NOT APPROVED',
     'unchanged':'N04 onward cinematic cameras and original v12.3 frames; WH-01 scale and anatomy proxy',
     'changed':'N01 and N17 matched yaw; N02/N03 cameras align to approaching whale on X=-90 axis; expanding wavefronts; early interpolation continuous; underwater whale remains level then eases to original breach pose by 7.7s',
     'cameras':{k:{'xyz':v[0],'yaw':v[1],'pitch':v[2],'focal_mm':v[3]} for k,v in CANDIDATE_CAMERAS.items()},
     'stations_pre_4_5s':[(-1.0,-90,73,-12),(0.0,-90,65,-12),(3.0,-90,42,-10)],
     'frames':frames,'axis_validation':tests,
     'limitations':['N03 proxy does not perform physically accurate water refraction, opacity or occlusion','N02/N03 cameras change viewing position at a cut; no dolly','N03→N04 cut angle and scale remain to be judged','A matching N01=N17 is preserved, but adopted C01/C19 source art has not been pixel compared','N01 N02 should not show whale clearly before N03']}
    (out/'camera-front-axis-v12.4.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'frames':len(frames),'qa':tests},ensure_ascii=False))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',default='./v12.4-output');a=p.parse_args();main(a.out)
