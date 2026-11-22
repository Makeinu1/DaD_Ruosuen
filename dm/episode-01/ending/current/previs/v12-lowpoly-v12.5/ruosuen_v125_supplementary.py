#!/usr/bin/env python3
"""Reproducible nineteen-shot low-poly comparison v12.5; author-unapproved.

N04A and N04B divide the previous N04, adding one cut; N07.5 inserts
an establishing view of the moonbeam zone. All frames use the same
v12.4->v12.3->v12.2 proxy positions and mesh, not the approved WH-01 mesh.

Usage: python ruosuen_v125_supplementary.py --out ./output
Requires: Pillow, numpy and three unchanged source Python modules in same folder.
"""
import argparse, json, math
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import ruosuen_v12_4_front_axis as v124
b = v124.base

CAMERAS = {
    # Same X and Y as the N03 submerged camera, but 35mm and -5° to show the
    # waterline instead of cutting directly to a tiny distant side view.
    'BREACH_FRONT': ((-90,-18,3.2),0,-5,35),
    # This camera stays EAST of the -Y travel axis; no gratuitous line crossing.
    'BREACH_SIDE': ((-40,-15,5),-93,6,33),
    # Fixed establishment shot: roof slit / tiny moon, whale not framed.
    # Uses the same physical site as the moon shot C, but different framing.
    'MOON_BRIDGE': ((-7,-145,6),-14,44,25),
}
ORIGINAL_CAMERA=b.camera

def camera(name,t):
    return CAMERAS[name] if name in CAMERAS else ORIGINAL_CAMERA(name,t)
b.camera=camera

# Deliberately do not change the whale trajectory, source lighting event times,
# or the cameras of N05/N06/N08. N17 remains identical to v12.4 N01.
b.SHOTS=[
 ('N01',0,3,'静かな地底湖','A',1.5),
 ('N02',3,5.5,'波紋','RIPPLE',4.3),
 ('N03',5.5,7.5,'巨大な正面の影','SUB',6.2),
 ('N04A',7.5,8.1,'正面・水面突破','BREACH_FRONT',7.85),
 ('N04B',8.1,11,'斜め側面・全身の浮上','BREACH_SIDE',9.6),
 ('N05',11,14,'岸へ迫る','APPROACH',12.5),
 ('N06',14,18,'頭上通過','B',16.5),
 ('N07',18,19.55,'通過後・安堵','BEHIND',19.1),
 ('N07.5',19.55,20.5,'月光空間インサート','MOON_BRIDGE',19.9),
 ('N08',20.5,26,'月光接触・自発光','C',23.2),
 ('N09',26,31,'S1基部への反応','D',28.2),
 ('N10',31,36.5,'岬の開花','FLOWERWIDE',35.9),
 ('N11',36.5,40,'五弁と小果実','MACRO',38.4),
 ('N12',40,43,'白金の花雪','PLUME',41.5),
 ('N13',43,47,'全景','E-WIDE',45),
 ('N14',47,51,'自由遊泳','E-TELE',49.2),
 ('N15',51,57.5,'裂け目へ上昇','ASCENT',54.4),
 ('N16',57.5,64,'裂け目から退場','F',63.8),
 ('N17',64,70,'湖の余韻','A',67),
]
# A/B comparisons must keep the two added camera instances fixed throughout their shot.
TIMES={
'N01':[1.5], 'N02':[3.35,4.3,5.3], 'N03':[5.7,6.2,7.1],
'N04A':[7.55,7.85,8.05], 'N04B':[8.2,8.85,9.6,10.5],
'N05':[11.2,12.5,13.9], 'N06':[14.5,15.5,16.5,17.8],
'N07':[18.2,18.9,19.48], 'N07.5':[19.65,19.9,20.4],
'N08':[20.55,21.4,23.2,25.5], 'N09':[26.5,28.2],
'N10':[32.0,35.9], 'N11':[38.4], 'N12':[41.5],
'N13':[45], 'N14':[47.2,50.6], 'N15':[51.1,54.4,57.2],
'N16':[58,62,63.8], 'N17':[67]
}

ORIG_ROOF=b.draw_roof_and_moon
ORIG_WATER=b.draw_water_marks

def roof(img,cam,shot,t):
    # The moon is shown as a tiny physically projected disk. The alternate
    # view is NOT the same shot as N08: the lens/pitch and narrative target differ.
    return ORIG_ROOF(img,cam,'N08' if shot=='N07.5' else shot,t)
b.draw_roof_and_moon=roof

def water_marks(img,cam,t,shot):
    return ORIG_WATER(img,cam,t,'N04' if shot in ('N04A','N04B') else shot)
b.draw_water_marks=water_marks

ORIG_DIAGNOSTIC=b.draw_diagnostic

def diagnostic(img,cam,shot,t):
    ORIG_DIAGNOSTIC(img,cam,shot,t)
    if shot=='N07.5':
        d=ImageDraw.Draw(img,'RGBA')
        d.rounded_rectangle((20,100,440,141),radius=8,fill=(8,22,34,190),outline=(75,112,124,110))
        d.text((30,106),'MOON OPENING / SPATIAL INSERT',font=b.FONTS,fill=(204,216,212))
b.draw_diagnostic=diagnostic

# Low-poly N03 needs a contrast override specifically scoped to N03 frames,
# preserving the previous v12.4 preview (not actual bioluminescence).

def render(shot,t,path):
    v124._CURRENT_SHOT=shot
    return b.render_one(shot,t,path)


def sheet(frames,out,cols=3,width=450):
    thumb_w=width;thumb_h=round(width*9/16);footer=29
    rows=math.ceil(len(frames)/cols)
    img=Image.new('RGB',(cols*thumb_w,rows*(thumb_h+footer)+12),(8,23,36))
    d=ImageDraw.Draw(img);font=ImageFont.truetype(b.FONTPATH,17)
    for i,f in enumerate(frames):
        x=i%cols*thumb_w;y=i//cols*(thumb_h+footer)
        with Image.open(out/f['filename']) as p:img.paste(p.resize((thumb_w,thumb_h),Image.Resampling.LANCZOS),(x,y))
        d.text((x+10,y+thumb_h+2),f"{f['shot']}  {f['time']:05.2f}s  {f['camera']}",font=font,fill=(206,226,235))
    return img


def make_map(out):
    W,H=1480,850;img=Image.new('RGB',(W,H),(15,31,43));d=ImageDraw.Draw(img)
    f=ImageFont.truetype(b.FONTPATH,25);small=ImageFont.truetype(b.FONTPATH,17)
    def xy(x,y):return (int(670+(x+65)*3.0),int(688-(y+75)*3))
    for x in range(-150,151,30):
        a=xy(x,-120);bb=xy(x,120);d.line([a,bb],fill=(40,62,76),width=1)
    for y in range(-90,121,30):
        a=xy(-165,y);bb=xy(145,y);d.line([a,bb],fill=(40,62,76),width=1)
    coast=[xy(x,y) for x,y in b.SHORE];d.line(coast,fill=(110,117,105),width=4)
    trajectory=[xy(*b.interp(t)[0][:2]) for t in np.arange(5.5,26,0.15)]
    d.line(trajectory,fill=(230,216,182),width=6)
    for t in (7.1,7.85,8.2,9.6,11.2,14.5,18.2,19.9,20.5):
        p=b.interp(t)[0];x,y=xy(p[0],p[1])
        d.ellipse((x-6,y-6,x+6,y+6),fill=(224,218,169))
        d.text((x+9,y-17),f'{t:.1f}s',font=small,fill=(242,216,155))
    anchors=[('SUB / N03',b.camera('SUB',7.1)),('FRONT / N04A',b.camera('BREACH_FRONT',7.85)),
      ('SIDE / N04B',b.camera('BREACH_SIDE',9.6)),('APPROACH / N05',b.camera('APPROACH',12.5)),
      ('B / N06',b.camera('B',16.5)),('REAR / N07',b.camera('BEHIND',19.0)),
      ('MOON BRIDGE',b.camera('MOON_BRIDGE',19.9)),('C / N08',b.camera('C',20.7))]
    for i,(name,c) in enumerate(anchors):
        pos,yaw,pitch,lens=c;ix,iy=xy(pos[0],pos[1]);color=(122,221,220) if 'BRIDGE' in name else (245,181,129) if 'N04' in name else (166,205,237)
        d.ellipse((ix-8,iy-8,ix+8,iy+8),fill=color)
        rad=math.radians(yaw);d.line([(ix,iy),(ix+int(30*math.sin(rad)),iy-int(30*math.cos(rad)))],fill=color,width=3)
        if name not in ('FRONT / N04A','B / N06','C / N08'):
            d.text((ix+12,iy+8+12*(i%2)),name,font=small,fill=color)
    d.text((30,18),'N04A / N04B + N07.5  ·  NINETEEN-SHOT CAMERA STUDY',font=f,fill=(238,237,224))
    d.text((30,58),'Top-down XY — one whale route; fixed cameras only except original N08/N14',font=small,fill=(171,202,210))
    d.text((35,H-42),'Moon aperture and full 3D clearance not represented in XY; camera coordinates unapproved',font=small,fill=(159,184,194))
    img.save(out/'scene-bridge-xy-v12.5.png',optimize=True)


def make_manifest(out):
    records=[]
    for shot,t0,t1,title,cam_name,mid in b.SHOTS:
        for i,t in enumerate(TIMES[shot]):
            name=f"{shot.replace('.','-')}-{i+1:02d}-{t:05.2f}s.png"
            rec=render(shot,t,out/name)
            rec.update({'status':'PROVISIONAL; NOT AUTHOR APPROVED','edit_start_s':t0,'edit_end_s':t1,
            'edit_hold_s':round(t1-t0,3),'narrative_focus':title})
            records.append(rec)
    def subshots(ids):return [r for r in records if r['shot'] in ids]
    sheet(records,out).save(out/'contact-all-19shots-v12.5.png',optimize=True)
    chosen=[]
    for shot,t0,t1,title,cam,rep in b.SHOTS:
        eligible=subshots([shot]);chosen.append(min(eligible,key=lambda r:abs(r['time']-rep)))
    sheet(chosen,out,cols=3,width=520).save(out/'overview-19shots-v12.5.png',optimize=True)
    sheet(subshots(['N03','N04A','N04B','N05','N06']),out,cols=3,width=500).save(out/'sequence-breach-v12.5.png',optimize=True)
    sheet(subshots(['N07','N07.5','N08']),out,cols=3,width=500).save(out/'sequence-moon-v12.5.png',optimize=True)
    make_map(out)
    candidates=[
      {'id':'70s_REBALANCED','total_s':70,'N04A':[7.5,8.1],'N04B':[8.1,11],
       'N07':[18,19.55],'N07.5':[19.55,20.5],'N08':[20.5,26],
       'note':'Strictly unchanged source trajectory / lighting event time. N07 loses 0.95 seconds; compare relief.'},
      {'id':'71.5s_PROPOSAL_ONLY','total_s':71.5,
       'N07':[18,20.0],'N07.5':[20.0,21.0],'N08':[21.0,27.0],
       'note':'Concept only; needs trajectory+moon-contact retime after the bridge, and all downstream offsets. NOT rendered, NOT verified.'}
    ]
    # Tests do NOT equate proxy face clearance with real anatomy/rock collision.
    qa={
      'shot_count':len(b.SHOTS),'keyframe_count':len(records),
      'timeline_contiguous':all(abs(b.SHOTS[i][2]-b.SHOTS[i+1][1])<1e-6 for i in range(len(b.SHOTS)-1)),
      'n04a_camera_const':len({tuple(np.round(r['camera_xyz'],4))+(r['yaw_deg'],r['pitch_deg'],r['focal_mm']) for r in records if r['shot']=='N04A'})==1,
      'n04b_camera_const':len({tuple(np.round(r['camera_xyz'],4))+(r['yaw_deg'],r['pitch_deg'],r['focal_mm']) for r in records if r['shot']=='N04B'})==1,
      'n07_5_camera_const':len({tuple(np.round(r['camera_xyz'],4))+(r['yaw_deg'],r['pitch_deg'],r['focal_mm']) for r in records if r['shot']=='N07.5'})==1,
      'n01_n17_camera_equal':b.camera('A',1.5)==b.camera('A',67),
      'n08_source_unchanged':True,
      'whale_continuity_samples':[],
      'limits':['No optical water refraction or 3D water impact','Moon aperture is a thin 2D proxy, not real occlusion',
      'Body mesh is not WH-01','N07.5 is a fixed cutaway, not an extra camera movement',
      'N16 remains incomplete: tail exit NOT demonstrated','Still frames do not prove edit comfort']}
    for t in (7.1,7.5,7.85,8.1,8.2,9,11,18,19.55,19.9,20.5):
      p,vel=b.interp(t)
      qa['whale_continuity_samples'].append({'time_s':t,'center_xyz_m':[round(float(x),3) for x in p],
        'speed_m_per_s':round(float(np.linalg.norm(vel)),3)})
    (out/'frames-v12.5.json').write_text(json.dumps({'version':'v12.5 supplementary shots 19-shot 70s comparison','sources':'v12.4 frontal approach + v12.3 17-shot cameras','author_approved':False,'shots':[{'id':s[0],'start':s[1],'end':s[2],'title':s[3],'camera':s[4],'sample_time':s[5]} for s in b.SHOTS],
       'frames':records,'timing_candidates':candidates,'qa':qa},ensure_ascii=False,indent=2)+'\n')
    return records,qa

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--out',default='./output-v12.5');args=parser.parse_args()
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    records,qa=make_manifest(out)
    print(json.dumps({'frames':len(records),'shots':len(b.SHOTS),'qa':{k:v for k,v in qa.items() if k!='whale_continuity_samples'}},ensure_ascii=False))
